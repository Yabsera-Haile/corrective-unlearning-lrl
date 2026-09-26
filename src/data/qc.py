"""Quality-control primitives shared by 2A, 2C and the pilot.

  LanguageID       GlotLID (D2.8): the same language filter MURI applied
  degeneration     repetition-loop metrics for MT output
  expansion_ratio  target characters per English character, the quantity 2A needs to
                   predict translated length before spending GPU time

Nothing here decides thresholds; callers report distributions and choose from them.
"""

from __future__ import annotations

import zlib
from collections import Counter
from dataclasses import dataclass

GLOTLID_REPO = "cis-lmu/glotlid"
GLOTLID_FILE = "model.bin"


def fasttext_top1(model, texts: list[str]) -> list[tuple[str, float]]:
    """Top-1 (label, prob) per text, working around fasttext 0.9.2 under NumPy 2.

    fasttext's Python wrapper returns `np.array(probs, copy=False)`, which NumPy 2 rejects
    ("Unable to avoid copy while creating an array"). The model itself is fine, so call the
    C++ binding (`model.f.multilinePredict`) and read the plain lists it returns. Falls back
    to the public API for a fasttext build that has fixed the wrapper or lacks `.f`.
    Texts must already be newline-free and non-empty.
    """
    if not texts:
        return []
    binding = getattr(model, "f", None)
    if binding is not None and hasattr(binding, "multilinePredict"):
        labels, probs = binding.multilinePredict(texts, 1, 0.0, "strict")
    else:
        labels, probs = model.predict(texts, k=1)
    return [(lab[0].replace("__label__", "") if len(lab) else "",
             float(p[0]) if len(p) else 0.0)
            for lab, p in zip(labels, probs)]


class LanguageID:
    """GlotLID wrapper. Labels are `__label__iso639-3_Script`, i.e. our canonical codes."""

    def __init__(self, repo: str = GLOTLID_REPO, filename: str = GLOTLID_FILE):
        import fasttext
        from src.utils.hf import download_with_retry
        self.model = fasttext.load_model(download_with_retry(repo, filename))

    @staticmethod
    def _clean(text: str) -> str:
        return " ".join(text.split())

    def predict(self, text: str) -> tuple[str, float]:
        return self.predict_many([text])[0]

    def predict_many(self, texts: list[str]) -> list[tuple[str, float]]:
        """fasttext needs newline-free, non-empty strings; empty texts get ("", 0.0)."""
        cleaned = [self._clean(t) for t in texts]
        nonempty = [(i, t) for i, t in enumerate(cleaned) if t]
        preds = fasttext_top1(self.model, [t for _, t in nonempty])
        by_index = {i: pred for (i, _), pred in zip(nonempty, preds)}
        return [by_index.get(i, ("", 0.0)) for i in range(len(cleaned))]


@dataclass(frozen=True)
class Degeneration:
    compression_ratio: float   # zlib size / raw size; low means repetitive
    top_ngram_share: float     # share of the most frequent n-gram among all n-grams
    distinct_ngram_ratio: float

    @property
    def worst(self) -> float:
        """One number for ranking: higher = more degenerate."""
        return max(self.top_ngram_share, 1.0 - self.distinct_ngram_ratio,
                   max(0.0, 0.35 - self.compression_ratio) / 0.35)


def degeneration(text: str, word_n: int = 4, char_n: int = 12) -> Degeneration:
    """Repetition metrics. Word n-grams where the script uses spaces, char n-grams otherwise
    (Amharic, Telugu and Bengali segment differently, so a word-only metric would mislead)."""
    raw = text.encode("utf-8", "surrogatepass")
    comp = len(zlib.compress(raw, 6)) / max(1, len(raw))
    words = text.split()
    if len(words) >= word_n * 4:
        grams = [" ".join(words[i:i + word_n]) for i in range(len(words) - word_n + 1)]
    else:
        s = "".join(text.split())
        grams = [s[i:i + char_n] for i in range(max(0, len(s) - char_n + 1))]
    if not grams:
        return Degeneration(comp, 0.0, 1.0)
    counts = Counter(grams)
    return Degeneration(comp, counts.most_common(1)[0][1] / len(grams), len(counts) / len(grams))


def expansion_ratio(target_text: str, english_text: str) -> float:
    return len(target_text) / max(1, len(english_text))


def length_bin(n_chars: int, edges: tuple[int, ...]) -> int:
    """Index of the bin n_chars falls into; len(edges) is the open-ended top bin."""
    for i, e in enumerate(edges):
        if n_chars < e:
            return i
    return len(edges)
