"""Step 2 environment probe (SERVER, GPU).

Proves the environment can actually do the Step 2 work rather than merely importing:
a real matmul on every GPU, a real GlotLID load and prediction in all four target
languages, a real LaBSE encode, and a pysbd sentence split.

Outputs
  results/step2/env_probe.md

Usage (repo root, venv active):
  python -m src.utils.env_probe
"""

from __future__ import annotations

import argparse
import importlib
import platform
import sys
import time

from src.utils.io import REPO_ROOT, write_result

GLOTLID_REPO = "cis-lmu/glotlid"
GLOTLID_FILE = "model.bin"
LABSE_MODEL = "sentence-transformers/LaBSE"

# Short sentences for the four target languages plus English, used to prove that GlotLID
# labels them correctly and that LaBSE places each next to its English counterpart.
SAMPLES: dict[str, tuple[str, str]] = {
    "eng_Latn": ("Good morning, today is a fine day.", "Good morning, today is a fine day."),
    "amh_Ethi": ("ሰላም ለሁላችሁ። ዛሬ ጥሩ ቀን ነው።", "Hello everyone. Today is a good day."),
    "ben_Beng": ("আজ আবহাওয়া খুব ভালো।", "The weather is very good today."),
    "swh_Latn": ("Habari ya asubuhi, leo ni siku njema.", "Good morning, today is a good day."),
    "tel_Telu": ("ఈ రోజు వాతావరణం చాలా బాగుంది.", "The weather is very good today."),
}

MATMUL_N = 4096
MATMUL_ITERS = 20


def probe_versions(L: list[str]) -> None:
    L.append(f"- python: **{platform.python_version()}** ({sys.executable})")
    for mod in ("torch", "transformers", "accelerate", "sentencepiece", "pysbd",
                "sentence_transformers", "fasttext", "datasets", "pandas", "pyarrow"):
        try:
            m = importlib.import_module(mod)
            L.append(f"- `{mod}`: {getattr(m, '__version__', '(no __version__)')}")
        except Exception as e:  # noqa: BLE001
            L.append(f"- `{mod}`: **IMPORT FAILED** — {type(e).__name__}: {e}")


def probe_gpus(L: list[str]) -> bool:
    try:
        import torch
    except Exception as e:  # noqa: BLE001
        L.append(f"- torch import failed: {e}")
        return False
    L.append(f"- torch {torch.__version__}, built for CUDA {torch.version.cuda}, "
             f"cuda available: {torch.cuda.is_available()}, devices: {torch.cuda.device_count()}")
    if not torch.cuda.is_available():
        L.append("- **no CUDA device visible** — the translation pilot cannot run")
        return False
    ok = True
    L.append("")
    L.append("| gpu | name | capability | memory | bf16 matmul | TFLOP/s |")
    L.append("|---|---|---|---|---|---|")
    for i in range(torch.cuda.device_count()):
        try:
            props = torch.cuda.get_device_properties(i)
            dev = torch.device(f"cuda:{i}")
            a = torch.randn(MATMUL_N, MATMUL_N, device=dev, dtype=torch.bfloat16)
            b = torch.randn(MATMUL_N, MATMUL_N, device=dev, dtype=torch.bfloat16)
            torch.cuda.synchronize(dev)
            t0 = time.time()
            for _ in range(MATMUL_ITERS):
                c = a @ b
            torch.cuda.synchronize(dev)
            dt = time.time() - t0
            tflops = 2 * MATMUL_N ** 3 * MATMUL_ITERS / dt / 1e12
            checksum = float(c.float().abs().mean())
            L.append(f"| {i} | {props.name} | {props.major}.{props.minor} | "
                     f"{props.total_memory / 1e9:.1f} GB | ok (mean |c|={checksum:.2f}) | {tflops:.1f} |")
            del a, b, c
            torch.cuda.empty_cache()
        except Exception as e:  # noqa: BLE001
            ok = False
            L.append(f"| {i} | **FAILED** | | | {type(e).__name__}: {str(e)[:60]} | |")
    return ok


def probe_glotlid(L: list[str]) -> bool:
    try:
        import fasttext
        from huggingface_hub import hf_hub_download
        path = hf_hub_download(GLOTLID_REPO, GLOTLID_FILE)
        t0 = time.time()
        model = fasttext.load_model(path)
        L.append(f"- loaded `{GLOTLID_REPO}/{GLOTLID_FILE}` in {time.time() - t0:.1f}s "
                 f"(fasttext {getattr(fasttext, '__version__', '?')})")
    except Exception as e:  # noqa: BLE001
        L.append(f"- **GlotLID unavailable** — {type(e).__name__}: {e}")
        L.append("  Without it the 2A/2C language filter (D2.8) cannot run. Try the fasttext "
                 "package pinned by the data-selection project on this machine.")
        return False
    ok = True
    L.append("")
    L.append("| expected | predicted | confidence | text |")
    L.append("|---|---|---|---|")
    for code, (text, _) in SAMPLES.items():
        labels, probs = model.predict(text.replace("\n", " "), k=1)
        got = labels[0].replace("__label__", "")
        hit = got == code
        ok &= hit
        L.append(f"| `{code}` | {'`' + got + '`' if hit else '**' + got + '**'} | "
                 f"{probs[0]:.3f} | {text[:40]} |")
    L.append("")
    L.append("GlotLID labels are `iso639-3_Script`, i.e. the same canonical form as the rest of "
             "the project." if ok else "**Some samples were mislabelled — check before relying on "
             "the filter.** (Short sentences are the hardest case for LID; the 2C filter runs on "
             "full responses.)")
    return ok


def probe_labse(L: list[str]) -> bool:
    """Coverage check for the coherence encoder: each target sentence must sit closest to
    its own English translation, otherwise the encoder does not really cover that language."""
    try:
        from sentence_transformers import SentenceTransformer
        t0 = time.time()
        model = SentenceTransformer(LABSE_MODEL)
        L.append(f"- loaded `{LABSE_MODEL}` in {time.time() - t0:.1f}s, "
                 f"max_seq_length={model.max_seq_length}")
    except Exception as e:  # noqa: BLE001
        L.append(f"- **LaBSE unavailable** — {type(e).__name__}: {e}")
        return False
    codes = [c for c in SAMPLES if c != "eng_Latn"]
    src = model.encode([SAMPLES[c][0] for c in codes], normalize_embeddings=True)
    tgt = model.encode([SAMPLES[c][1] for c in codes], normalize_embeddings=True)
    sim = src @ tgt.T
    L.append("")
    L.append("| language | cos(text, own English) | max cos(text, other English) | covered |")
    L.append("|---|---|---|---|")
    ok = True
    for i, c in enumerate(codes):
        own = float(sim[i, i])
        other = float(max(sim[i, j] for j in range(len(codes)) if j != i))
        covered = own > 0.5 and own > other
        ok &= covered
        L.append(f"| `{c}` | {own:.3f} | {other:.3f} | {'yes' if covered else '**NO**'} |")
    L.append("")
    L.append("A language whose own translation is not clearly the nearest neighbour is not "
             "usable for the coherence measurement; pick another encoder for it.")
    return ok


def probe_pysbd(L: list[str]) -> bool:
    try:
        import pysbd
        seg = pysbd.Segmenter(language="en", clean=False)
        text = ("Dr. Smith went to Washington. He arrived at 3 p.m. on Jan. 5, 2021! "
                "Was it worth it? Yes — very much so.")
        sents = seg.segment(text)
        L.append(f"- pysbd split {len(sents)} sentences from a 4-sentence probe: "
                 + " | ".join(s.strip()[:40] for s in sents))
        return len(sents) == 4
    except Exception as e:  # noqa: BLE001
        L.append(f"- **pysbd unavailable** — {type(e).__name__}: {e}")
        return False


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    L = ["# Step 2 environment probe", ""]
    results = {}

    L.append("## Versions")
    L.append("")
    probe_versions(L)

    L.append("")
    L.append("## GPUs (real bf16 matmul on each device)")
    L.append("")
    results["gpu"] = probe_gpus(L)

    L.append("")
    L.append("## GlotLID (D2.8 language filter)")
    L.append("")
    results["glotlid"] = probe_glotlid(L)

    L.append("")
    L.append("## LaBSE (coherence encoder coverage)")
    L.append("")
    results["labse"] = probe_labse(L)

    L.append("")
    L.append("## pysbd (sentence segmentation for NLLB)")
    L.append("")
    results["pysbd"] = probe_pysbd(L)

    L.append("")
    L.append("## Verdict")
    L.append("")
    for k, v in results.items():
        L.append(f"- {k}: {'ok' if v else '**FAILED**'}")
    text = "\n".join(L) + "\n"
    print(text)
    out = write_result(text, "step2/env_probe.md")
    print(f"report: {out.relative_to(REPO_ROOT).as_posix()}")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
