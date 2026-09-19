"""Language code normalisation (Step 1.3, LOCAL; written against results/schema_inspection.md).

Canonical form: FLORES-200 `lang_Scrp` (ISO 639-3 + ISO 15924, e.g. `amh_Ethi`).
Observed identifier formats (Step 1.2, see results/schema_inspection.md):

  MURI-IT    `language` = bare ISO 639-3, no script (`swa`, `ace`), 200 languages
             plus one non-language value `code`; several are macrolanguage codes
  NLLB-200   202 `lang_Scrp` codes (special_tokens_map.json)
  FLORES-200 204 `lang_Scrp` single-language configs (+ pairs `x-eng_Latn`, + `all`)
  Belebele   122 `lang_Scrp` configs; `dialect` column repeats the config name

Everything here reads committed files only, so the mapping is identical on LOCAL
and SERVER and can be re-derived without the raw data:

  results/schema/{nllb200__codes.txt, flores200__configs.txt, belebele__configs.txt}
  results/schema/muri_it__language__scripts.csv   dominant Unicode script per MURI code
  configs/reference/iso-639-3.tab, iso-639-3-macrolanguages.tab, joshi_lang2tax.txt

Mapping targets are NLLB ∪ FLORES-200 codes. Belebele-only codes are romanised
test variants (hin_Latn, ben_Latn, ...) and are membership checks only, never
targets: MURI text is in the native script, and admitting them would make every
such language look script-ambiguous.

Resolution order for one MURI code:
  1. EXCLUDED         not a natural language
  2. DECISIONS        explicit per-code decision + rationale (ambiguous macrolanguages etc.)
  3. direct           the ISO 639-3 code itself has target variants
  4. macro->member    a macrolanguage whose active members have target variants
  5. member->macro    an individual language whose macrolanguage has target variants
  6. constructed      not in NLLB/FLORES at all: `iso3_Scrp` built from the dominant
                      script, so the language is dropped visibly at the NLLB intersection
  7. unmapped         with a reason; never dropped silently
Within 3-5, the variant is chosen by script: the one whose ISO 15924 script matches
the dominant Unicode script of the MURI text. No match, or a genuine two-script
mix, is left unmapped with a reason rather than guessed.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pandas as pd

from src.utils.io import CONFIGS_DIR, SCHEMA_DIR

REFERENCE_DIR = CONFIGS_DIR / "reference"
FLORES_CODE_RE = re.compile(r"^(?P<lang>[a-z]{3})_(?P<script>[A-Z][a-z]{3})$")

# First word of the Unicode character name (as reported by inspect_schema) -> ISO 15924.
# HAN is deliberately ambiguous: Simplified and Traditional share the block.
UNICODE_TO_ISO15924: dict[str, tuple[str, ...]] = {
    "LATIN": ("Latn",), "CYRILLIC": ("Cyrl",), "ARABIC": ("Arab",), "DEVANAGARI": ("Deva",),
    "BENGALI": ("Beng",), "ETHIOPIC": ("Ethi",), "HEBREW": ("Hebr",), "TIBETAN": ("Tibt",),
    "MYANMAR": ("Mymr",), "ARMENIAN": ("Armn",), "THAI": ("Thai",), "GREEK": ("Grek",),
    "KANNADA": ("Knda",), "THAANA": ("Thaa",), "GEORGIAN": ("Geor",), "MALAYALAM": ("Mlym",),
    "LAO": ("Laoo",), "TAMIL": ("Taml",), "KHMER": ("Khmr",), "TELUGU": ("Telu",),
    "SINHALA": ("Sinh",), "ORIYA": ("Orya",), "GURMUKHI": ("Guru",), "GUJARATI": ("Gujr",),
    "HIRAGANA": ("Jpan",), "KATAKANA": ("Jpan",), "HAN": ("Hans", "Hant"), "HANGUL": ("Hang",),
    "CANADIAN SYLLABICS": ("Cans",), "CHEROKEE": ("Cher",), "TIFINAGH": ("Tfng",),
    "OL CHIKI": ("Olck",), "MEETEI MAYEK": ("Mtei",), "NKO": ("Nkoo",), "SYRIAC": ("Syrc",),
}

# A second script this common, when it is also a candidate variant's script, means the
# pool really mixes two written forms (e.g. Kurdish), not just URLs/English in the text.
MIXED_SCRIPT_SHARE = 0.25

EXCLUDED: dict[str, str] = {
    "code": "programming-code examples, not a natural language",
}

# Explicit decisions: (target or None, confidence, rationale). Every entry is logged.
DECISIONS: dict[str, tuple[str | None, str, str]] = {
    "ara": ("arb_Arab", "assumed",
            "macrolanguage with 9 target members (arb + dialects); MURI 'Arabic' taken as Modern Standard Arabic"),
    "fas": ("pes_Arab", "assumed",
            "macrolanguage: pes (Iranian Persian) vs prs (Dari); pes, the dominant written variety, assumed"),
    "msa": ("zsm_Latn", "assumed",
            "macrolanguage with 6 target members incl. ind_Latn; MURI has no separate 'ind', so this pool "
            "may contain Indonesian: verify on text before selecting"),
    "nor": ("nob_Latn", "assumed",
            "macrolanguage: nob (Bokmal) vs nno (Nynorsk); Bokmal assumed, pool may contain Nynorsk"),
    "lav": ("lvs_Latn", "assumed",
            "macrolanguage: lvs (Standard Latvian) vs ltg (Latgalian); standard variety assumed"),
    "zho": ("zho_Hans", "assumed",
            "Hans vs Hant not separable by Unicode block; Simplified assumed. Pool membership unaffected: "
            "both variants are in NLLB, FLORES-200 and Belebele"),
    "fil": ("tgl_Latn", "inferred",
            "Filipino is the standardised register of Tagalog (FLORES+ renamed FLORES-200 tgl_Latn to "
            "fil_Latn); merged with MURI 'tgl'"),
    "hbs": (None, "-",
            "ambiguous: Serbo-Croatian macrolanguage; its Latin-script text (79%) cannot be split between "
            "hrv/bos/srp without a classifier"),
    "kur": (None, "-",
            "ambiguous: text is 57% Arabic / 43% Latin script, i.e. Sorani (ckb_Arab) and Kurmanji (kmr_Latn) "
            "mixed under one code; recoverable by a per-row script split if ever needed"),
}

# Joshi et al. (2020) lang2tax.txt is keyed by English name and mixes a long class-0 name
# list with a curated section (classes 1-5) that uses Wikipedia-style names. Several
# languages appear in both under different names (sinhala,0 / sinhalese,1; sotho,0 /
# sesotho,1; fulfulde,0 / fula,1; rundi,0 / kirundi,1), so a plain ISO-name match can
# land on the class-0 duplicate. These aliases point at the curated entry. Value = exact
# lang2tax name. Pool languages still at level 0 are listed in the summary for review.
JOSHI_ALIASES: dict[str, str] = {
    "zho_Hans": "mandarin",         # no "chinese" entry
    "pan_Guru": "eastern punjabi",  # Gurmukhi-script Punjabi; "western punjabi" is Shahmukhi
    "sin_Sinh": "sinhalese",        # not the class-0 "sinhala" duplicate
    "sot_Latn": "sesotho",          # not the class-0 "sotho" duplicate
    "fuv_Latn": "fula",             # not the class-0 "fulfulde"/"fulani" duplicates
    "run_Latn": "kirundi",          # not the class-0 "rundi" duplicate
    "nso_Latn": "northern sotho",   # ISO name "Pedi"
    "lug_Latn": "luganda",          # ISO name "Ganda"
    "ilo_Latn": "ilocano",          # ISO name "Iloko"
}


# --------------------------------------------------------------------------- inputs


def _lines(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


@dataclass(frozen=True)
class Inventories:
    nllb: frozenset[str]
    flores: frozenset[str]
    belebele: frozenset[str]

    @property
    def targets(self) -> frozenset[str]:
        return self.nllb | self.flores

    def variants(self, iso3: str) -> list[str]:
        return sorted(c for c in self.targets if c[:3] == iso3)


@lru_cache(maxsize=None)
def load_inventories(schema_dir: Path = SCHEMA_DIR) -> Inventories:
    flores = [c for c in _lines(schema_dir / "flores200__configs.txt") if FLORES_CODE_RE.match(c)]
    inv = Inventories(nllb=frozenset(_lines(schema_dir / "nllb200__codes.txt")),
                      flores=frozenset(flores),
                      belebele=frozenset(_lines(schema_dir / "belebele__configs.txt")))
    for name in ("nllb", "flores", "belebele"):
        bad = [c for c in getattr(inv, name) if not FLORES_CODE_RE.match(c)]
        if bad:
            raise ValueError(f"{name} inventory has non lang_Scrp codes: {bad[:5]}")
    return inv


@dataclass(frozen=True)
class IsoTables:
    ref_name: dict[str, str]
    scope: dict[str, str]
    members: dict[str, list[str]]  # macrolanguage -> active individual members
    parent: dict[str, str]         # active individual member -> macrolanguage


@lru_cache(maxsize=None)
def load_iso_tables(reference_dir: Path = REFERENCE_DIR) -> IsoTables:
    iso = pd.read_csv(reference_dir / "iso-639-3.tab", sep="\t", keep_default_na=False, dtype=str)
    mac = pd.read_csv(reference_dir / "iso-639-3-macrolanguages.tab", sep="\t", keep_default_na=False, dtype=str)
    mac = mac[mac["I_Status"].str.strip() == "A"]
    return IsoTables(ref_name=dict(zip(iso["Id"], iso["Ref_Name"].str.strip())),
                     scope=dict(zip(iso["Id"], iso["Scope"])),
                     members=mac.groupby("M_Id")["I_Id"].apply(list).to_dict(),
                     parent=dict(zip(mac["I_Id"], mac["M_Id"])))


@dataclass(frozen=True)
class ScriptInfo:
    script_1: str
    share_1: float
    script_2: str
    share_2: float


@lru_cache(maxsize=None)
def load_script_profile(schema_dir: Path = SCHEMA_DIR) -> dict[str, ScriptInfo]:
    df = pd.read_csv(schema_dir / "muri_it__language__scripts.csv", keep_default_na=False)
    return {r.value: ScriptInfo(r.script_1, float(r.share_1 or 0), r.script_2, float(r.share_2 or 0))
            for r in df.itertuples(index=False)}


# --------------------------------------------------------------------------- mapping


@dataclass(frozen=True)
class Mapping:
    muri_code: str
    flores_code: str | None
    method: str        # excluded | decision | direct | macro->member | member->macro | constructed | unmapped
    confidence: str    # exact | inferred | assumed | -
    reason: str        # why, for every non-trivial outcome
    multi_script: bool  # target language has >1 script variant in NLLB/FLORES
    macro_mismatch: bool  # MURI code and target differ in macrolanguage/individual scope

    @property
    def mapped(self) -> bool:
        return self.flores_code is not None


def is_flores_code(code: str) -> bool:
    """
    >>> is_flores_code("amh_Ethi"), is_flores_code("amh"), is_flores_code("AMH_ethi")
    (True, False, False)
    """
    return bool(FLORES_CODE_RE.match(code))


def split_flores_code(code: str) -> tuple[str, str]:
    """
    >>> split_flores_code("zho_Hant")
    ('zho', 'Hant')
    """
    m = FLORES_CODE_RE.match(code)
    if not m:
        raise ValueError(f"Not a FLORES-style lang_Scrp code: {code!r}")
    return m["lang"], m["script"]


def _pick_by_script(variants: list[str], info: ScriptInfo | None) -> tuple[str | None, str]:
    """Choose among target variants by the MURI text's dominant script."""
    if info is None:
        if len(variants) == 1:
            return variants[0], "no script profile; single variant taken"
        return None, "no script profile to choose between " + ", ".join(variants)
    wanted = UNICODE_TO_ISO15924.get(info.script_1, ())
    hits = [v for v in variants if split_flores_code(v)[1] in wanted]
    if len(hits) != 1:
        what = "no variant" if not hits else f"{len(hits)} variants"
        return None, (f"{what} of {', '.join(variants)} matches dominant script "
                      f"{info.script_1} ({info.share_1:.0%})")
    second = UNICODE_TO_ISO15924.get(info.script_2, ())
    rivals = [v for v in variants if v != hits[0] and split_flores_code(v)[1] in second]
    if rivals and info.share_2 >= MIXED_SCRIPT_SHARE:
        return None, (f"mixed scripts: {info.script_1} {info.share_1:.0%} / {info.script_2} "
                      f"{info.share_2:.0%} match both {hits[0]} and {rivals[0]}")
    return hits[0], f"script {info.script_1} ({info.share_1:.0%})"


def map_muri_code(code: str, inv: Inventories | None = None, iso: IsoTables | None = None,
                  scripts: dict[str, ScriptInfo] | None = None) -> Mapping:
    inv = inv or load_inventories()
    iso = iso or load_iso_tables()
    scripts = scripts if scripts is not None else load_script_profile()
    info = scripts.get(code)
    is_macro = iso.scope.get(code) == "M"

    def result(target, method, confidence, reason, macro_mismatch=False):
        multi = target is not None and len(inv.variants(target[:3])) > 1
        return Mapping(code, target, method, confidence, reason, multi, macro_mismatch)

    if code in EXCLUDED:
        return result(None, "excluded", "-", EXCLUDED[code])

    if code in DECISIONS:
        target, confidence, why = DECISIONS[code]
        if target is not None:
            if target not in inv.targets:
                raise ValueError(f"DECISIONS[{code!r}] -> {target} is not in NLLB/FLORES-200")
            if info and split_flores_code(target)[1] not in UNICODE_TO_ISO15924.get(info.script_1, ()):
                raise ValueError(f"DECISIONS[{code!r}] -> {target} contradicts dominant script {info.script_1}")
        return result(target, "decision", confidence, why,
                      macro_mismatch=target is not None and target[:3] != code)

    direct = inv.variants(code)
    if direct:
        target, why = _pick_by_script(direct, info)
        if target is None:
            return result(None, "unmapped", "-", why)
        confidence = "exact" if len(direct) == 1 else "inferred"
        note = why if len(direct) > 1 else ""
        if is_macro:
            note = (note + "; " if note else "") + "macrolanguage code used by both MURI and the target"
        return result(target, "direct", confidence, note)

    if is_macro:
        member_variants = sorted(v for m in iso.members.get(code, []) for v in inv.variants(m))
        if member_variants:
            target, why = _pick_by_script(member_variants, info)
            if target is None:
                return result(None, "unmapped", "-", f"macrolanguage: {why}")
            return result(target, "macro->member", "inferred",
                          f"macrolanguage {code} -> only matching member {target[:3]} ({why})",
                          macro_mismatch=True)

    parent = iso.parent.get(code)
    if parent and inv.variants(parent):
        target, why = _pick_by_script(inv.variants(parent), info)
        if target is not None:
            return result(target, "member->macro", "inferred",
                          f"member of macrolanguage {parent}, which the target uses ({why})",
                          macro_mismatch=True)

    # Not covered by NLLB/FLORES: still give it a well-formed code so that it is dropped
    # visibly by the NLLB intersection rather than hidden inside "unmapped".
    scripts_ = UNICODE_TO_ISO15924.get(info.script_1, ()) if info else ()
    if len(scripts_) == 1:
        return result(f"{code}_{scripts_[0]}", "constructed", "inferred",
                      f"no NLLB-200/FLORES-200 entry{' (nor any member)' if is_macro else ''}; "
                      f"code built from ISO 639-3 + dominant script {info.script_1} ({info.share_1:.0%})")
    return result(None, "unmapped", "-",
                  "not in NLLB-200 or FLORES-200, and no unambiguous script to build a code from")


def map_all(codes: list[str]) -> pd.DataFrame:
    """One row per MURI code: the complete, auditable mapping log."""
    inv, iso, scripts = load_inventories(), load_iso_tables(), load_script_profile()
    rows = []
    for code in codes:
        m = map_muri_code(code, inv, iso, scripts)
        info = scripts.get(code)
        rows.append({
            "muri_code": code, "muri_iso_name": iso.ref_name.get(code, ""),
            "muri_iso_scope": iso.scope.get(code, ""),
            "flores_code": m.flores_code or "", "method": m.method, "confidence": m.confidence,
            "multi_script": m.multi_script, "macro_mismatch": m.macro_mismatch,
            "dominant_script": info.script_1 if info else "",
            "dominant_share": info.share_1 if info else None,
            "reason": m.reason,
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- names, Joshi


def language_name(flores_code: str) -> str:
    iso = load_iso_tables()
    name = iso.ref_name.get(flores_code[:3], flores_code)
    return re.sub(r"\s*\((individual language|macrolanguage)\)", "", name)


def _norm_name(name: str) -> str:
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = re.sub(r"\(.*?\)", "", name.lower())
    return re.sub(r"\s+", " ", name).strip()


@lru_cache(maxsize=None)
def load_joshi(reference_dir: Path = REFERENCE_DIR) -> dict[str, int]:
    """lang2tax.txt `name,class`. Duplicate names with conflicting classes keep the max."""
    out: dict[str, int] = {}
    for line in _lines(reference_dir / "joshi_lang2tax.txt"):
        name, _, cls = line.rpartition(",")
        out[_norm_name(name)] = max(out.get(_norm_name(name), -1), int(cls))
    return out


def joshi_level(flores_code: str, muri_codes: list[str] = ()) -> tuple[int | None, str, str]:
    """(level, matched name, method). Methods, in order: alias, name, muri-name, last-word, none."""
    joshi, iso = load_joshi(), load_iso_tables()
    if flores_code in JOSHI_ALIASES:
        name = JOSHI_ALIASES[flores_code]
        return joshi[_norm_name(name)], name, "alias"
    candidates = [("name", iso.ref_name.get(flores_code[:3], ""))]
    candidates += [("muri-name", iso.ref_name.get(c, "")) for c in muri_codes]
    for method, name in candidates:
        if name and _norm_name(name) in joshi:
            return joshi[_norm_name(name)], _norm_name(name), method
    for method, name in candidates:  # "Plateau Malagasy" -> "malagasy"; logged as lower confidence
        last = _norm_name(name).split(" ")[-1] if name else ""
        if last in joshi:
            return joshi[last], last, "last-word"
    return None, "", "none"


if __name__ == "__main__":
    import doctest

    failures, _ = doctest.testmod()
    raise SystemExit(1 if failures else print("code_maps doctests passed"))
