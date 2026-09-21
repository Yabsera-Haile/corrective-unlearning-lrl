"""Translation engine for 2B, run first as the pilot (SERVER, GPU).

  instruction  google/madlad400-3b-mt          eng -> target   (D2.3: same system MURI used)
  response     facebook/nllb-200-distilled-600M eng -> target

Tag conventions are read from results/step2/mt_language_tags.json, produced by
src/mt/inspect_models.py from the models' own tokenizer files:
MADLAD prefixes the source text with `<2xx>`; NLLB sets tokenizer.src_lang and forces the
target code as the first generated token.

Segmentation: NLLB handles ~512 tokens and responses are document-length, so responses are
split into paragraphs, then sentences (pysbd), translated sentence by sentence and rejoined
with the paragraph structure preserved. Instructions are short but are segmented too when
they exceed the token budget.

Decoding is greedy (num_beams=1, do_sample=False) for both systems; NLLB's shipped
generation_config caps max_length at 200 tokens, which is overridden explicitly here.

Resumable: work is split into shards; a shard is written to .tmp and renamed, so an
interrupted run re-does only the shard it was in the middle of.

Usage (repo root, venv active):
  python -m src.mt.translate --language amh_Ethi --gpu 0 --input data/pools/pilot_candidates.jsonl \
      --out-dir data/contamination_pilot
  python -m src.mt.translate --language amh_Ethi --stub   # pipeline only, no models
"""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol, Sequence

from src.utils.io import DATA_DIR, RESULTS_DIR, read_json, rel, write_result

MADLAD_REPO = "google/madlad400-3b-mt"
NLLB_REPO = "facebook/nllb-200-distilled-600M"
NLLB_SRC_LANG = "eng_Latn"
TAGS_PATH = RESULTS_DIR / "step2" / "mt_language_tags.json"
SHARD_SIZE = 250
MAX_SRC_TOKENS = 384          # per segment, well inside NLLB's ~512
GEN_MAX_NEW_TOKENS = 512      # overrides NLLB's generation_config max_length=200
DECODING = {"num_beams": 1, "do_sample": False}


class Translator(Protocol):
    def translate(self, texts: Sequence[str]) -> list[str]: ...


@dataclass
class Segmenter:
    """Paragraph- and sentence-aware splitting with a token budget."""
    token_len: Callable[[str], int]
    max_tokens: int = MAX_SRC_TOKENS
    _seg: object = field(default=None, repr=False)

    def _sentences(self, text: str) -> list[str]:
        if self._seg is None:
            import pysbd
            self._seg = pysbd.Segmenter(language="en", clean=False)
        return [s for s in self._seg.segment(text) if s.strip()]

    def _hard_split(self, text: str) -> list[str]:
        """Last resort for a single sentence over budget: split on words."""
        words, out, cur = text.split(), [], []
        for w in words:
            cur.append(w)
            if self.token_len(" ".join(cur)) >= self.max_tokens:
                out.append(" ".join(cur))
                cur = []
        if cur:
            out.append(" ".join(cur))
        return out or [text]

    def split(self, text: str) -> list[list[str]]:
        """-> per paragraph, a list of segments that each fit the budget."""
        paragraphs = [p for p in text.split("\n\n")]
        out = []
        for para in paragraphs:
            if not para.strip():
                out.append([])
                continue
            segments = []
            for sent in self._sentences(para):
                segments.extend([sent] if self.token_len(sent) <= self.max_tokens
                                else self._hard_split(sent))
            out.append(segments)
        return out

    @staticmethod
    def join(translated: list[list[str]]) -> str:
        return "\n\n".join(" ".join(s for s in para if s).strip() for para in translated).strip()


def translate_documents(docs: Sequence[str], translator: Translator, segmenter: Segmenter,
                        progress: Callable[[int, int], None] | None = None) -> list[str]:
    """Segment every document, translate all segments in length-sorted batches, reassemble."""
    layouts = [segmenter.split(d) for d in docs]
    flat: list[str] = []
    index: list[tuple[int, int, int]] = []
    for di, paras in enumerate(layouts):
        for pi, segs in enumerate(paras):
            for si, seg in enumerate(segs):
                index.append((di, pi, si))
                flat.append(seg)
    if not flat:
        return ["" for _ in docs]
    order = sorted(range(len(flat)), key=lambda i: -len(flat[i]))
    out: list[str] = [""] * len(flat)
    done = 0
    for start in range(0, len(order), translator.batch_size):
        batch_idx = order[start:start + translator.batch_size]
        for i, text in zip(batch_idx, translator.translate([flat[i] for i in batch_idx])):
            out[i] = text
        done += len(batch_idx)
        if progress:
            progress(done, len(flat))
    rebuilt = [[["" for _ in segs] for segs in paras] for paras in layouts]
    for (di, pi, si), text in zip(index, out):
        rebuilt[di][pi][si] = text
    return [Segmenter.join(paras) for paras in rebuilt]


# --------------------------------------------------------------------------- models


def load_tags(language: str) -> tuple[str, int]:
    tags = read_json(TAGS_PATH)
    madlad = tags["madlad"]["languages"][language]["tag"]
    nllb_id = tags["nllb"]["languages"][language]["token_id"]
    if not madlad or nllb_id is None:
        raise SystemExit(f"{language}: unresolved MT tags in {TAGS_PATH}; run src.mt.inspect_models")
    return madlad, int(nllb_id)


class HFTranslator:
    """Shared generate() loop for both systems."""

    def __init__(self, repo: str, device: str, batch_size: int, prefix: str = "",
                 forced_bos_token_id: int | None = None, src_lang: str | None = None):
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        self.torch = torch
        kwargs = {"src_lang": src_lang} if src_lang else {}
        self.tokenizer = AutoTokenizer.from_pretrained(repo, **kwargs)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(
            repo, torch_dtype=torch.bfloat16).to(device).eval()
        self.device, self.batch_size = device, batch_size
        self.prefix, self.forced_bos_token_id = prefix, forced_bos_token_id
        self.generated_tokens = 0

    def token_len(self, text: str) -> int:
        return len(self.tokenizer(text, add_special_tokens=False)["input_ids"])

    def translate(self, texts: Sequence[str]) -> list[str]:
        batch = [self.prefix + t for t in texts]
        enc = self.tokenizer(batch, return_tensors="pt", padding=True, truncation=True,
                             max_length=MAX_SRC_TOKENS + 32).to(self.device)
        gen_kwargs = dict(DECODING, max_new_tokens=GEN_MAX_NEW_TOKENS)
        if self.forced_bos_token_id is not None:
            gen_kwargs["forced_bos_token_id"] = self.forced_bos_token_id
        with self.torch.inference_mode():
            out = self.model.generate(**enc, **gen_kwargs)
        self.generated_tokens += int(out.numel())
        return self.tokenizer.batch_decode(out, skip_special_tokens=True)


class StubTranslator:
    """Deterministic fake used to exercise the pipeline without GPUs or model downloads."""

    def __init__(self, marker: str = "T", batch_size: int = 8):
        self.marker, self.batch_size, self.generated_tokens = marker, batch_size, 0

    def token_len(self, text: str) -> int:
        return max(1, len(text) // 4)

    def translate(self, texts: Sequence[str]) -> list[str]:
        self.generated_tokens += sum(len(t) // 4 for t in texts)
        return [f"[{self.marker}]{t}" for t in texts]


# --------------------------------------------------------------------------- job


def shard_paths(out_dir: Path, language: str, n_rows: int) -> list[tuple[int, Path]]:
    d = out_dir / language
    return [(i, d / f"shard_{i:04d}.jsonl") for i in range((n_rows + SHARD_SIZE - 1) // SHARD_SIZE)]


def write_status(out_dir: Path, language: str, done: int, total: int, rows: int,
                 elapsed: float, extra: str = "") -> None:
    """One screen, readable over AnyDesk."""
    path = RESULTS_DIR / "step2" / "translation_status.md"
    lines = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("| `"):
                lines[line.split("`")[1]] = line
    rate = rows / elapsed if elapsed else 0
    eta = (total - done) * SHARD_SIZE / rate / 60 if rate else 0
    lines[language] = (f"| `{language}` | {done}/{total} | {rows:,} | {rate:.2f}/s | "
                       f"{eta:.0f} min | {extra} |")
    write_result("\n".join([f"# Translation status ({time.strftime('%Y-%m-%d %H:%M')})", "",
                            "| language | shards | examples | rate | eta | note |",
                            "|---|---|---|---|---|---|", *[lines[k] for k in sorted(lines)]]) + "\n",
                 "step2/translation_status.md")


def run(language: str, rows: list[dict], out_dir: Path, instruction_mt: Translator,
        response_mt: Translator, madlad_tag: str, resume: bool = True) -> dict:
    (out_dir / language).mkdir(parents=True, exist_ok=True)
    seg_i = Segmenter(instruction_mt.token_len)
    seg_r = Segmenter(response_mt.token_len)
    shards = shard_paths(out_dir, language, len(rows))
    t0, n_done = time.time(), 0
    for shard_i, path in shards:
        chunk = rows[shard_i * SHARD_SIZE:(shard_i + 1) * SHARD_SIZE]
        if resume and path.exists() and sum(1 for _ in open(path, encoding="utf-8")) == len(chunk):
            n_done += len(chunk)
            continue
        t_shard = time.time()
        instructions = translate_documents([r["instruction_en"] for r in chunk], instruction_mt, seg_i)
        responses = translate_documents([r["response_en"] for r in chunk], response_mt, seg_r)
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            for r, instruction, response in zip(chunk, instructions, responses):
                fh.write(json.dumps({
                    "example_id": f"contam:{language}:{r['origin_id'].split(':')[-1]}",
                    "origin_id": r["origin_id"], "origin_source": r["origin_source"],
                    "language": language, "instruction": instruction, "response": response,
                    "instruction_en": r["instruction_en"], "response_en": r["response_en"],
                    "mt_instruction_system": MADLAD_REPO, "mt_response_system": NLLB_REPO,
                    "mt_instruction_tag": madlad_tag, "is_contaminated": True,
                }, ensure_ascii=False, sort_keys=True) + "\n")
        tmp.replace(path)
        n_done += len(chunk)
        print(f"    [{language}] shard {shard_i + 1}/{len(shards)}: {len(chunk)} examples in "
              f"{time.time() - t_shard:.0f}s", flush=True)
        write_status(out_dir, language, shard_i + 1, len(shards), n_done, time.time() - t0)
    elapsed = time.time() - t0
    stats = {"language": language, "examples": n_done, "seconds": round(elapsed, 1),
             "examples_per_sec": round(n_done / elapsed, 3) if elapsed else None,
             "generated_tokens": instruction_mt.generated_tokens + response_mt.generated_tokens,
             "decoding": DECODING, "max_new_tokens": GEN_MAX_NEW_TOKENS,
             "max_src_tokens": MAX_SRC_TOKENS, "shard_size": SHARD_SIZE,
             "madlad_tag": madlad_tag, "instruction_system": MADLAD_REPO,
             "response_system": NLLB_REPO}
    (out_dir / language / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    write_status(out_dir, language, len(shards), len(shards), n_done, elapsed, "done")
    return stats


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--language", required=True)
    ap.add_argument("--input", type=Path, default=DATA_DIR / "pools/pilot_candidates.jsonl")
    ap.add_argument("--out-dir", type=Path, default=DATA_DIR / "contamination_pilot")
    ap.add_argument("--gpu", type=int, default=0)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--stub", action="store_true", help="fake translators: pipeline test only")
    ap.add_argument("--no-resume", action="store_true")
    args = ap.parse_args(argv)

    rows = [json.loads(line) for line in open(args.input, encoding="utf-8")]
    if args.limit:
        rows = rows[:args.limit]
    madlad_tag, nllb_id = load_tags(args.language)
    print(f"==> {args.language}: {len(rows):,} documents | MADLAD tag {madlad_tag} | "
          f"NLLB forced_bos {nllb_id} | gpu {args.gpu}", flush=True)

    if args.stub:
        instruction_mt, response_mt = StubTranslator("I"), StubTranslator("R")
    else:
        os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
        device = f"cuda:{args.gpu}"
        instruction_mt = HFTranslator(MADLAD_REPO, device, args.batch_size, prefix=f"{madlad_tag} ")
        response_mt = HFTranslator(NLLB_REPO, device, args.batch_size,
                                   forced_bos_token_id=nllb_id, src_lang=NLLB_SRC_LANG)
    stats = run(args.language, rows, args.out_dir, instruction_mt, response_mt, madlad_tag,
                resume=not args.no_resume)
    print(f"    {args.language}: {stats['examples']:,} examples in {stats['seconds']:.0f}s "
          f"({stats['examples_per_sec']}/s) -> "
          f"{rel(args.out_dir / args.language)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
