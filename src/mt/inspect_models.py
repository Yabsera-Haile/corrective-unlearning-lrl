"""Step 2B prerequisite — inspect the MT models' language-tag conventions (SERVER, CPU).

The two systems tag the target language differently and the spec forbids assuming either
format, so this reads each model's actual tokenizer files and reports what is in them:

  google/madlad400-3b-mt            instruction side (D2.3), eng -> target
  facebook/nllb-200-distilled-600M  response side, eng -> target

Only small/medium JSON files are downloaded (tokenizer.json, config.json, ...), never the
weights, so this runs on CPU in the lean environment.

Outputs
  results/step2/mt_tag_conventions.md   evidence and the resolved tags (also printed)
  results/step2/mt_language_tags.json   machine-readable: per target language, the MADLAD
                                        prefix token and the NLLB code + token id, for 2B

Usage (repo root, venv active):
  python -m src.mt.inspect_models
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml
from huggingface_hub import HfApi, hf_hub_download

from src.utils.io import CONFIGS_DIR, REPO_ROOT, write_result, rel

MADLAD_REPO = "google/madlad400-3b-mt"
NLLB_REPO = "facebook/nllb-200-distilled-600M"

MADLAD_TAG_RE = re.compile(r"^<2[A-Za-z][A-Za-z0-9_\-]*>$")
NLLB_CODE_RE = re.compile(r"^[a-z]{3}_[A-Z][a-z]{3}$")
SMALL_JSON = ("config.json", "generation_config.json", "special_tokens_map.json",
              "tokenizer_config.json", "added_tokens.json")


def load_vocab(repo: str, revision: str) -> dict[str, int]:
    """token -> id from tokenizer.json, covering both Unigram (list) and BPE (dict) vocabs."""
    path = hf_hub_download(repo, "tokenizer.json", revision=revision)
    with open(path, encoding="utf-8") as fh:
        tok = json.load(fh)
    vocab: dict[str, int] = {}
    model_vocab = (tok.get("model") or {}).get("vocab")
    if isinstance(model_vocab, dict):
        vocab.update({str(k): int(v) for k, v in model_vocab.items()})
    elif isinstance(model_vocab, list):  # Unigram: [[piece, score], ...], index is the id
        vocab.update({str(entry[0]): i for i, entry in enumerate(model_vocab)})
    for added in tok.get("added_tokens") or []:
        vocab[str(added["content"])] = int(added["id"])
    return vocab


def small_json(repo: str, revision: str, rep_lines: list[str]) -> dict[str, dict]:
    out = {}
    for name in SMALL_JSON:
        try:
            with open(hf_hub_download(repo, name, revision=revision), encoding="utf-8") as fh:
                out[name] = json.load(fh)
        except Exception as e:  # noqa: BLE001 — absent files are informative, not fatal
            rep_lines.append(f"- `{name}`: not available ({type(e).__name__})")
    return out


def targets() -> list[dict]:
    cfg = yaml.safe_load((CONFIGS_DIR / "languages.yaml").read_text(encoding="utf-8"))
    return cfg["languages"]


def inspect_madlad(rev: str, langs: list[dict], L: list[str]) -> dict[str, dict]:
    L.append(f"## MADLAD-400 — `{MADLAD_REPO}` (instruction side)")
    L.append("")
    L.append(f"- revision: `{rev}`")
    cfgs = small_json(MADLAD_REPO, rev, L)
    cfg, gen = cfgs.get("config.json", {}), cfgs.get("generation_config.json", {})
    L.append(f"- architecture: {cfg.get('architectures')}, d_model={cfg.get('d_model')}, "
             f"layers={cfg.get('num_layers')}, vocab_size={cfg.get('vocab_size')}, "
             f"dtype={cfg.get('torch_dtype')}")
    L.append(f"- generation_config: {json.dumps(gen)}")
    L.append(f"- tokenizer_config keys: {sorted(cfgs.get('tokenizer_config.json', {}))}")
    L.append(f"- added_tokens.json: {json.dumps(cfgs.get('added_tokens.json'))[:200]}")

    vocab = load_vocab(MADLAD_REPO, rev)
    tags = sorted(t for t in vocab if MADLAD_TAG_RE.match(t))
    L.append(f"- **language tags in the vocabulary: {len(tags)}** matching `<2xx>`; "
             f"first 12: {', '.join(f'`{t}`' for t in tags[:12])}")
    by_len: dict[int, int] = {}
    for t in tags:
        by_len[len(t) - 3] = by_len.get(len(t) - 3, 0) + 1
    L.append(f"- tag body lengths: {by_len} (2 = ISO 639-1-style, 3 = ISO 639-3-style, more = with script)")
    L.append("")
    L.append("Resolved for this project's targets (candidates searched, not assumed):")
    L.append("")
    L.append("| language | ISO 639-3 | candidates present in vocab | chosen tag | token id |")
    L.append("|---|---|---|---|---|")
    resolved = {}
    for lang in langs:
        iso3 = lang["code"][:3]
        iso1 = {"ben": "bn", "swh": "sw", "amh": "am", "tel": "te"}.get(iso3, "")
        cands = [f"<2{c}>" for c in (iso1, iso3, lang["code"].lower(), lang["code"]) if c]
        present = [c for c in dict.fromkeys(cands) if c in vocab]
        chosen = present[0] if present else None
        resolved[lang["code"]] = {"tag": chosen, "token_id": vocab.get(chosen) if chosen else None,
                                  "candidates_present": present}
        L.append(f"| {lang['name']} (`{lang['code']}`) | {iso3} | "
                 f"{', '.join(f'`{c}`' for c in present) or '**none**'} | "
                 f"{f'`{chosen}`' if chosen else '**UNRESOLVED**'} | {vocab.get(chosen) if chosen else ''} |")
    L.append("")
    L.append("Usage implied by the tokenizer: MADLAD is a T5-style model whose *source text* is "
             "prefixed with the target-language tag, e.g. `<2sw> Hello world`. No forced BOS token.")
    return resolved


def inspect_nllb(rev: str, langs: list[dict], L: list[str]) -> dict[str, dict]:
    L.append("")
    L.append(f"## NLLB-200 — `{NLLB_REPO}` (response side)")
    L.append("")
    L.append(f"- revision: `{rev}`")
    cfgs = small_json(NLLB_REPO, rev, L)
    cfg, gen = cfgs.get("config.json", {}), cfgs.get("generation_config.json", {})
    tok_cfg = cfgs.get("tokenizer_config.json", {})
    L.append(f"- architecture: {cfg.get('architectures')}, d_model={cfg.get('d_model')}, "
             f"encoder_layers={cfg.get('encoder_layers')}, vocab_size={cfg.get('vocab_size')}, "
             f"max_length={cfg.get('max_length')}, dtype={cfg.get('torch_dtype')}")
    L.append(f"- generation_config: {json.dumps(gen)}")
    L.append(f"- tokenizer_config: src_lang={tok_cfg.get('src_lang')!r}, tgt_lang={tok_cfg.get('tgt_lang')!r}, "
             f"keys={sorted(tok_cfg)}")
    special = cfgs.get("special_tokens_map.json", {})
    codes_in_special = [t for t in (special.get("additional_special_tokens") or []) if NLLB_CODE_RE.match(t)]
    L.append(f"- special_tokens_map additional_special_tokens: {len(codes_in_special)} FLORES-style codes")

    vocab = load_vocab(NLLB_REPO, rev)
    codes = sorted(t for t in vocab if NLLB_CODE_RE.match(t))
    L.append(f"- **language codes in the vocabulary: {len(codes)}**; first 8: "
             f"{', '.join(f'`{c}`' for c in codes[:8])}")
    L.append("")
    L.append("| language | code | in vocab | token id (forced_bos_token_id) |")
    L.append("|---|---|---|---|")
    resolved = {}
    for lang in langs:
        code = lang["code"]
        tid = vocab.get(code)
        resolved[code] = {"code": code, "token_id": tid, "in_vocab": code in vocab}
        L.append(f"| {lang['name']} | `{code}` | {'yes' if code in vocab else '**NO**'} | {tid if tid is not None else ''} |")
    L.append("")
    L.append("Usage implied by the tokenizer: NLLB sets the *source* language on the tokenizer "
             "(`src_lang`) and forces the target code as the first generated token "
             "(`forced_bos_token_id`). The tag is not prefixed to the source text.")
    return resolved


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description=__doc__,
                            formatter_class=argparse.RawDescriptionHelpFormatter).parse_args(argv)
    api = HfApi()
    langs = targets()
    L = ["# MT language-tag conventions (Step 2B prerequisite)", "",
         "Read from each model's own tokenizer files; nothing about the tag format is assumed.",
         f"Target languages from `configs/languages.yaml`: "
         f"{', '.join(l['code'] for l in langs)}", ""]

    madlad_rev = api.model_info(MADLAD_REPO).sha
    nllb_rev = api.model_info(NLLB_REPO).sha
    madlad = inspect_madlad(madlad_rev, langs, L)
    nllb = inspect_nllb(nllb_rev, langs, L)

    tags = {"madlad": {"repo": MADLAD_REPO, "revision": madlad_rev, "languages": madlad,
                       "usage": "prefix the source text with the tag"},
            "nllb": {"repo": NLLB_REPO, "revision": nllb_rev, "languages": nllb,
                     "usage": "tokenizer.src_lang=eng_Latn; generate with forced_bos_token_id"}}
    unresolved = [c for c, v in madlad.items() if not v["tag"]] + [c for c, v in nllb.items() if not v["in_vocab"]]
    if unresolved:
        L += ["", f"> **UNRESOLVED for {', '.join(unresolved)}** — do not write the 2B job until "
                  "these are settled by inspection."]

    text = "\n".join(L) + "\n"
    print(text)
    out = write_result(text, "step2/mt_tag_conventions.md")
    write_result(tags, "step2/mt_language_tags.json")
    print(f"report: {rel(out)}  |  tags: results/step2/mt_language_tags.json")
    return 1 if unresolved else 0


if __name__ == "__main__":
    raise SystemExit(main())
