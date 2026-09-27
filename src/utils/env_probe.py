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

from src.utils.io import REPO_ROOT, write_result, rel

GLOTLID_REPO = "cis-lmu/glotlid"
GLOTLID_FILE = "model.bin"
LABSE_MODEL = "sentence-transformers/LaBSE"

# Short sentences for the four target languages plus English, used to prove that GlotLID
# labels them correctly and that LaBSE places each next to its English counterpart.
# One sentence per language, each on a DIFFERENT topic: the LaBSE check asks whether a
# sentence is nearest to its own translation, so two languages sharing an English sentence
# would tie and look like a failure.
SAMPLES: dict[str, tuple[str, str]] = {
    "eng_Latn": ("The committee published its report yesterday.",
                 "The committee published its report yesterday."),
    "amh_Ethi": ("ኢትዮጵያ በምሥራቅ አፍሪካ የምትገኝ ሀገር ናት።",
                 "Ethiopia is a country located in East Africa."),
    "ben_Beng": ("আজ আবহাওয়া খুব ভালো।", "The weather is very good today."),
    "swh_Latn": ("Watoto wanacheza mpira uwanjani.",
                 "The children are playing football on the field."),
    "tel_Telu": ("ఈ పుస్తకం చాలా ఆసక్తికరంగా ఉంది.", "This book is very interesting."),
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
            for _ in range(3):   # warm up: the first device would otherwise be charged for
                c = a @ b        # CUDA context creation and cuBLAS autotuning
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
        from src.utils.hf import download_with_retry
        path = download_with_retry(GLOTLID_REPO, GLOTLID_FILE)
        t0 = time.time()
        model = fasttext.load_model(path)
        L.append(f"- loaded `{GLOTLID_REPO}/{GLOTLID_FILE}` in {time.time() - t0:.1f}s "
                 f"(fasttext {getattr(fasttext, '__version__', '?')})")
    except Exception as e:  # noqa: BLE001
        L.append(f"- **GlotLID unavailable** — {type(e).__name__}: {e}")
        L.append("  Without it the 2A/2C language filter (D2.8) cannot run. Try the fasttext "
                 "package pinned by the data-selection project on this machine.")
        return False
    from src.data.qc import fasttext_top1  # same NumPy-2-safe path the pipeline uses

    ok = True
    L.append("")
    L.append("| expected | predicted | confidence | text |")
    L.append("|---|---|---|---|")
    codes = list(SAMPLES)
    preds = fasttext_top1(model, [" ".join(SAMPLES[c][0].split()) for c in codes])
    for code, (got, prob) in zip(codes, preds):
        text = SAMPLES[code][0]
        probs = [prob]
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


MT_SMOKE_SENTENCE = "The committee published its report on water quality yesterday."
MT_WEIGHTS = {"google/madlad400-3b-mt": "model.safetensors",
              "facebook/nllb-200-distilled-600M": "pytorch_model.bin"}


def _cached(repo: str, filename: str) -> bool:
    from huggingface_hub import try_to_load_from_cache
    return isinstance(try_to_load_from_cache(repo, filename), str)


def probe_mt(L: list[str]) -> bool | None:
    """Load both MT systems through the pipeline's own HFTranslator and translate one
    sentence into every target language, then language-ID the output.

    This is the check that would have caught NLLB's .bin weights being refused by
    transformers on torch < 2.6 here, instead of two stages later. Skipped (not failed)
    when the weights are not cached yet, so a fresh machine is not stalled on a 14 GB
    download at stage 04; prefetch_models.sh fetches them in the background.
    """
    missing = [r for r, f in MT_WEIGHTS.items() if not _cached(r, f)]
    if missing:
        L.append(f"- **skipped**: not cached yet: {', '.join(missing)} (prefetch_models.sh "
                 "fetches them; the pilot re-checks)")
        return None
    import torch
    from src.data.pools import languages
    from src.data.qc import LanguageID
    from src.mt.translate import MADLAD_REPO, NLLB_REPO, NLLB_SRC_LANG, HFTranslator, load_tags
    t0 = time.time()
    madlad = HFTranslator(MADLAD_REPO, "cuda:0", 4)
    nllb = HFTranslator(NLLB_REPO, "cuda:0", 4, src_lang=NLLB_SRC_LANG)
    L.append(f"- loaded both systems on cuda:0 in {time.time() - t0:.0f}s "
             f"(torch {torch.__version__}); source: \"{MT_SMOKE_SENTENCE}\"")
    lid = LanguageID()
    L += ["", "| language | system | output | GlotLID |", "|---|---|---|---|"]
    ok = True
    for lang in languages():
        code = lang["code"]
        tag, bos = load_tags(code)
        madlad.prefix, nllb.forced_bos_token_id = f"{tag} ", bos
        for name, system in (("MADLAD", madlad), ("NLLB", nllb)):
            out = system.translate([MT_SMOKE_SENTENCE])[0]
            got, prob = lid.predict(out)
            hit = got == code and out.strip() != ""
            ok &= hit
            L.append(f"| `{code}` | {name} | {out[:60]} | "
                     f"{'`' + got + '`' if hit else '**' + (got or 'empty') + '**'} {prob:.2f} |")
    del madlad, nllb
    torch.cuda.empty_cache()
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
    from datetime import datetime, timezone
    L = ["# Step 2 environment probe", "",
         f"- run at {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC", ""]
    results = {}

    L.append("## Versions")
    L.append("")
    probe_versions(L)

    # Each section is isolated: a crash in one must not stop the others or, worse, stop the
    # report being written — the stage summary would then show the PREVIOUS run's verdict.
    sections = (("gpu", "GPUs (real bf16 matmul on each device)", probe_gpus),
                ("glotlid", "GlotLID (D2.8 language filter)", probe_glotlid),
                ("labse", "LaBSE (coherence encoder coverage)", probe_labse),
                ("pysbd", "pysbd (sentence segmentation for NLLB)", probe_pysbd),
                ("mt", "MT smoke test (MADLAD + NLLB through the pipeline, GlotLID on output)", probe_mt))
    for key, title, fn in sections:
        L += ["", f"## {title}", ""]
        try:
            results[key] = fn(L)
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            L.append(f"- **probe crashed** — {type(e).__name__}: {str(e)[:200]}")
            results[key] = False

    L.append("")
    L.append("## Verdict")
    L.append("")
    for k, v in results.items():
        L.append(f"- {k}: {'skipped' if v is None else 'ok' if v else '**FAILED**'}")
    text = "\n".join(L) + "\n"
    print(text)
    out = write_result(text, "step2/env_probe.md")
    print(f"report: {rel(out)}")
    return 0 if all(v is not False for v in results.values()) else 1  # skipped != failed


if __name__ == "__main__":
    raise SystemExit(main())
