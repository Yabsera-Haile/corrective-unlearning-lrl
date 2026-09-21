"""Step 2A — inspect the English contamination-source candidates (SERVER).

Same discipline as Step 1.2: describe what is actually there before any selection
logic is written. Nothing here selects or filters for real; the filter section only
*counts* how many examples each proposed rule would remove, which is what decides
whether the pool is large enough and whether LongForm's other subsets are needed.

Sources (D2.2: contamination must be genre-matched to MURI's reverse instructions)
  MURI-IT English MRI   local parquet, rows with language == eng and dataset_name == MRI
  LongForm              akoksal/LongForm; C4 and Wikipedia subsets are the preferred part,
                        Stack Exchange / WikiHow / NLP-task subsets only if counts fall short

Requirement to check against (2A): 7,000 mixture + 495 dev = 7,495 per language, plus ~15%
headroom for post-translation filtering ~= 8,600 per language, so ~34,400 for four disjoint
allocations.

GlotLID is NOT run here: it needs the GPU-side environment, and its rejection rate is a 2C
number. Everything below is CPU-only and text-based.

Outputs
  results/step2/english_source_inspection.md   full report (also printed)
  results/step2/english_source_counts.csv      per source x subset: counts, filter preview
  results/step2/english_source_lengths.csv     per source x subset: length quantiles

Usage (repo root, venv active):
  python -m src.data.inspect_english_sources [--muri-only|--longform-only]
"""

from __future__ import annotations

import argparse
import itertools
import re
import time
from collections import Counter
from dataclasses import dataclass

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from datasets import load_dataset

from src.data.inspect_schema import Report, _short, find_id_columns, guarded, SourceSummary, Source
from src.utils.io import RAW_DIR, REPO_ROOT, RESULTS_DIR, num_proc, write_result

MURI_DIR = RAW_DIR / "muri-it"
LONGFORM_REPO = "akoksal/LongForm"
MRI_SUBSET = "MRI"

PER_LANGUAGE_NEED = 8_600  # 7,000 + 495, +15% headroom
N_LANGUAGES = 4

# D2.2: the genre-matched part of LongForm. Exact names as they appear in its `source`
# column; substring matching would wrongly admit WikiHow.
LONGFORM_PREFERRED = ("C4", "Wikipedia")
# A source whose median response is shorter than this cannot carry the clean length
# distribution through translation (D2.9).
MIN_RESPONSE_P50 = 500

# Filter previews. Each is (name, predicate on the row dict, why). Reported separately so the
# real 2A filter set can be chosen from the counts instead of guessed at now.
TASK_WORD_RE = re.compile(r"\b(summari[sz]e|translat)", re.I)
CODE_FENCE_RE = re.compile(r"```|~~~|<code[ >]|<pre[ >]")
HTML_RE = re.compile(r"</?(div|span|table|tr|td|th|ul|ol|li|br|img|a) ?[^>]*>", re.I)
MD_TABLE_RE = re.compile(r"^\s*\|.*\|\s*$", re.M)
LATEX_RE = re.compile(r"\\begin\{|\\frac|\$\$")

FILTERS: tuple[tuple[str, str, str], ...] = (
    ("instruction_summarize_translate", "instruction", "MURI applied the same filter"),
    ("response_code_fence", "response", "code block markup"),
    ("response_html", "response", "HTML markup"),
    ("response_md_table", "response", "markdown table rows"),
    ("response_latex", "response", "LaTeX / math markup"),
    ("response_empty_or_short", "response", "under 200 characters"),
    ("response_very_long", "response", "over 20,000 characters"),
    ("duplicate_response", "response", "exact duplicate of an earlier response"),
)

QUANTILES = (0.1, 0.25, 0.5, 0.75, 0.9, 0.99)


@dataclass
class Rows:
    """Normalised view of a candidate source: instruction/response/subset per example."""
    key: str
    rows: list[dict]
    columns: list[str]
    instruction_col: str
    response_col: str
    subset_col: str | None


def flag_row(name: str, instruction: str, response: str, seen: set) -> bool:
    if name == "instruction_summarize_translate":
        return bool(TASK_WORD_RE.search(instruction))
    if name == "response_code_fence":
        return bool(CODE_FENCE_RE.search(response))
    if name == "response_html":
        return bool(HTML_RE.search(response))
    if name == "response_md_table":
        return bool(MD_TABLE_RE.search(response))
    if name == "response_latex":
        return bool(LATEX_RE.search(response))
    if name == "response_empty_or_short":
        return len(response.strip()) < 200
    if name == "response_very_long":
        return len(response.strip()) > 20_000
    if name == "duplicate_response":
        key = response.strip()
        if key in seen:
            return True
        seen.add(key)
        return False
    raise ValueError(name)


def describe(rows: Rows, rep: Report) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Schema, examples, per-subset counts, length quantiles and filter preview."""
    rep.kv("examples", f"{len(rows.rows):,}")
    rep.kv("columns", ", ".join(f"`{c}`" for c in rows.columns))
    rep.kv("used as", f"instruction=`{rows.instruction_col}`, response=`{rows.response_col}`, "
                      f"subset=`{rows.subset_col or '(none)'}`")
    rep()
    rep("Example rows (truncated):")
    rep.code(itertools.chain.from_iterable(
        [f"[{i}]"] + [f"  {c}: {_short(r.get(c))}" for c in rows.columns]
        for i, r in enumerate(rows.rows[:3])))

    counts, lengths = [], []
    subsets = sorted({str(r.get(rows.subset_col, "(all)")) for r in rows.rows})
    for subset in subsets:
        sub = [r for r in rows.rows
               if rows.subset_col is None or str(r.get(rows.subset_col)) == subset]
        instr = [str(r.get(rows.instruction_col) or "") for r in sub]
        resp = [str(r.get(rows.response_col) or "") for r in sub]
        seen: set = set()
        flags = {name: 0 for name, _, _ in FILTERS}
        kept = 0
        for i, r in zip(instr, resp):
            hit = False
            for name, _, _ in FILTERS:
                if flag_row(name, i, r, seen):
                    flags[name] += 1
                    hit = True
            kept += not hit
        counts.append({"source": rows.key, "subset": subset, "n": len(sub),
                       **{f"drop_{k}": v for k, v in flags.items()},
                       "kept_all_filters": kept})
        q_i = pd.Series([len(x) for x in instr]).quantile(QUANTILES)
        q_r = pd.Series([len(x) for x in resp]).quantile(QUANTILES)
        lengths.append({"source": rows.key, "subset": subset, "n": len(sub),
                        **{f"instr_p{int(q * 100)}": int(q_i[q]) for q in QUANTILES},
                        **{f"resp_p{int(q * 100)}": int(q_r[q]) for q in QUANTILES}})
    counts_df, lengths_df = pd.DataFrame(counts), pd.DataFrame(lengths)

    rep()
    rep("**Counts and filter preview** (each rule counted independently; a row can trip several):")
    rep.table(["subset", "n", *[f"drop {n.replace('_', ' ')}" for n, _, _ in FILTERS], "kept by all"],
              counts_df[["subset", "n", *[f"drop_{n}" for n, _, _ in FILTERS], "kept_all_filters"]]
              .itertuples(index=False))
    rep()
    rep("**Response length (characters)**")
    rep.table(["subset", "n", *[f"p{int(q * 100)}" for q in QUANTILES]],
              lengths_df[["subset", "n", *[f"resp_p{int(q * 100)}" for q in QUANTILES]]].itertuples(index=False))
    rep()
    rep("**Instruction length (characters)**")
    rep.table(["subset", "n", *[f"p{int(q * 100)}" for q in QUANTILES]],
              lengths_df[["subset", "n", *[f"instr_p{int(q * 100)}" for q in QUANTILES]]].itertuples(index=False))
    return counts_df, lengths_df


def load_muri_english(rep: Report) -> Rows:
    files = sorted(f for f in MURI_DIR.rglob("*.parquet") if ".cache" not in f.parts)
    if not files:
        raise SystemExit(f"no parquet under {MURI_DIR}; run scripts/server/01_download_data.sh")
    cols = ["input", "output", "language", "dataset_name", "subdataset_name", "split"]
    kept = []
    t0 = time.time()
    for f in files:
        for batch in pq.ParquetFile(f).iter_batches(columns=cols, batch_size=20_000):
            tbl = pa.Table.from_batches([batch])
            mask = pc.and_(pc.equal(tbl["language"], "eng"), pc.equal(tbl["dataset_name"], MRI_SUBSET))
            sel = tbl.filter(mask)
            if sel.num_rows:
                kept.extend(sel.to_pylist())
    rep.kv("scan", f"{len(files)} shards in {time.time() - t0:.0f}s")
    return Rows("MURI-eng", kept, cols, "input", "output", "subdataset_name")


def load_longform(rep: Report, n_probe: int) -> Rows:
    dsd = load_dataset(LONGFORM_REPO)
    rep.kv("splits", ", ".join(f"`{k}`: {len(v):,}" for k, v in dsd.items()))
    rows, columns = [], None
    for split, ds in dsd.items():
        columns = columns or list(ds.features)
        for r in ds:
            r["_split"] = split
            rows.append(r)
    any_split = next(iter(dsd.values()))
    rep.kv("features", ", ".join(f"`{c}`: {any_split.features[c]}" for c in columns))
    probe = rows[:n_probe]
    id_cols = find_id_columns(probe, columns)
    rep.kv("identifier-like columns", ", ".join(f"`{c}`" for c in id_cols) or "(none)")
    for c in id_cols:
        vals = Counter(str(r.get(c)) for r in rows)
        rep(f"- `{c}`: {len(vals)} distinct — " + ", ".join(f"`{v}`={n:,}" for v, n in vals.most_common(12)))
    # Do not assume which column is which: pick by name, then by mean length.
    text_cols = [c for c in columns
                 if sum(len(str(r.get(c) or "")) for r in probe) / max(1, len(probe)) > 20]
    instr = next((c for c in text_cols if re.search(r"instr|input|prompt|question", c, re.I)), None)
    resp = next((c for c in text_cols if re.search(r"out|resp|answer|target|completion", c, re.I)), None)
    if instr is None or resp is None:
        by_len = sorted(text_cols, key=lambda c: sum(len(str(r.get(c) or "")) for r in probe))
        instr, resp = instr or by_len[0], resp or by_len[-1]
        rep(f"- column roles inferred by length: instruction=`{instr}`, response=`{resp}`")
    subset = next((c for c in id_cols if re.search(r"source|subset|dataset|origin", c, re.I)), None)
    return Rows("LongForm", rows, columns + ["_split"], instr, resp, subset)


def is_preferred(row) -> bool:
    """D2.2 genre match: MURI's own English MRI, plus LongForm's C4/Wikipedia subsets only.

    Matched by exact subset name. A substring match on "wiki" would also pull in LongForm's
    WikiHow, which the spec excludes from the preferred set.
    """
    if row["source"] == "MURI-eng":
        return True
    return row["source"] == "LongForm" and row["subset"] in LONGFORM_PREFERRED


def allocation_section(rep: Report, counts: pd.DataFrame, lengths: pd.DataFrame | None = None) -> None:
    rep.h(2, "Allocation feasibility")
    need_total = PER_LANGUAGE_NEED * N_LANGUAGES
    mask = counts.apply(is_preferred, axis=1)
    preferred, other = counts[mask], counts[~mask]
    rep.kv("need", f"{PER_LANGUAGE_NEED:,} per language x {N_LANGUAGES} = **{need_total:,}** "
                   f"for fully disjoint allocations (7,000 mixture + 495 dev + ~15% headroom)")
    rep.kv("preferred sources (MURI-eng + LongForm C4/Wikipedia)",
           f"{int(preferred['n'].sum()):,} raw, **{int(preferred['kept_all_filters'].sum()):,}** "
           "after the filter preview")
    for r in preferred.itertuples(index=False):
        rep(f"  - {r.source} / {r.subset}: {r.kept_all_filters:,}")
    rep.kv("other subsets (StackExchange, WikiHow, NLP tasks, ...; only if short, and then "
           "reported separately in every table)",
           f"{int(other['n'].sum()):,} raw, {int(other['kept_all_filters'].sum()):,} after preview")
    have = int(preferred["kept_all_filters"].sum())

    # D2.9 length matching needs sources whose responses can match the clean length
    # distribution; very short responses cannot, whatever the translation does to them.
    if lengths is not None:
        med = lengths.set_index(["source", "subset"])["resp_p50"]
        short = [(s, sub) for (s, sub), m in med.items()
                 if m < MIN_RESPONSE_P50 and is_preferred({"source": s, "subset": sub})]
        if short:
            lost = int(sum(preferred.set_index(["source", "subset"]).loc[k, "kept_all_filters"] for k in short))
            rep()
            rep(f"- **length compatibility:** {', '.join(f'{s}/{sub} (p50={int(med[(s, sub)])} chars)' for s, sub in short)} "
                f"sit below the {MIN_RESPONSE_P50}-character median used by the other preferred sources. "
                f"Excluding them leaves **{have - lost:,}** length-compatible candidates "
                f"({have - lost:,} vs {have:,}); see D2.9.")
    if have >= need_total:
        rep(f"\n**Sufficient**: {have:,} >= {need_total:,}. Four disjoint per-language allocations "
            "are possible from the preferred sources alone.")
    else:
        with_other = have + int(other["kept_all_filters"].sum())
        per_lang = have // N_LANGUAGES
        rep(f"\n**Short by {need_total - have:,}** for fully disjoint allocations: {have:,} available, "
            f"{need_total:,} needed.")
        rep(f"- disjoint across languages would give **{per_lang:,} per language** "
            f"(need {PER_LANGUAGE_NEED:,}) — {'enough' if per_lang >= PER_LANGUAGE_NEED else 'NOT enough'}")
        rep(f"- adding LongForm's other subsets would reach {with_other:,} "
            f"({'enough' if with_other >= need_total else 'still short'})")
        rep("- otherwise: allow cross-language overlap, keep `origin_id` on every example, and "
            "report the overlap fraction per language pair (permitted by 2A)")
        rep("\nWithin a language every English source is used at most once either way; that "
            "constraint is never relaxed.")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--muri-only", action="store_true")
    ap.add_argument("--longform-only", action="store_true")
    ap.add_argument("--probe-rows", type=int, default=500, help="rows used to infer column roles")
    ap.add_argument("--from-counts", action="store_true",
                    help="LOCAL: recompute only the allocation section from the committed "
                         "results/step2 CSVs (no data scan, no network)")
    args = ap.parse_args(argv)
    pa.set_cpu_count(num_proc())
    pa.set_io_thread_count(num_proc())

    if args.from_counts:
        counts_df = pd.read_csv(RESULTS_DIR / "step2/english_source_counts.csv")
        lengths_df = pd.read_csv(RESULTS_DIR / "step2/english_source_lengths.csv")
        rep = Report()
        rep("# English source allocation (Step 2A, recomputed from committed counts)")
        rep()
        rep.kv("inputs", "`results/step2/english_source_counts.csv`, `english_source_lengths.csv`")
        allocation_section(rep, counts_df, lengths_df)
        out = write_result(rep.text(), "step2/english_source_allocation.md")
        print(f"wrote {out.relative_to(REPO_ROOT).as_posix()}")
        return 0

    rep = Report()
    rep("# English contamination-source inspection (Step 2A)")
    rep()
    rep.kv("sources", "MURI-IT English MRI (local parquet), LongForm (C4/Wikipedia preferred)")
    rep.kv("note", "no selection or filtering happens here; filter columns are counts only. "
                   "GlotLID runs in 2C, not here.")

    counts, lengths = [], []
    if not args.longform_only:
        summary = SourceSummary(Source("muri_eng", "akoksal/muri-it", "English MRI contamination source"))
        rep.h(2, "MURI-IT English MRI")
        rows = guarded("load MURI-eng", summary, rep, lambda: load_muri_english(rep))
        if rows:
            c, l = describe(rows, rep)
            counts.append(c)
            lengths.append(l)
    if not args.muri_only:
        summary = SourceSummary(Source("longform", LONGFORM_REPO, "English reverse-instruction source"))
        rep.h(2, f"LongForm — `{LONGFORM_REPO}`")
        rows = guarded("load LongForm", summary, rep, lambda: load_longform(rep, args.probe_rows))
        if rows:
            c, l = describe(rows, rep)
            counts.append(c)
            lengths.append(l)

    if counts:
        counts_df = pd.concat(counts, ignore_index=True)
        lengths_df = pd.concat(lengths, ignore_index=True)
        allocation_section(rep, counts_df, lengths_df)
        write_result(counts_df, "step2/english_source_counts.csv")
        write_result(lengths_df, "step2/english_source_lengths.csv")
    out = write_result(rep.text(), "step2/english_source_inspection.md")

    print("\n" + "=" * 20 + " ENGLISH SOURCE POOL: SUMMARY " + "=" * 20)
    if counts:
        for r in counts_df.itertuples(index=False):
            print(f"  {r.source:<10} {str(r.subset):<28} n={r.n:>7,}  kept by all filters={r.kept_all_filters:>7,}")
        print(f"  need {PER_LANGUAGE_NEED:,}/language x {N_LANGUAGES} = {PER_LANGUAGE_NEED * N_LANGUAGES:,}; "
              f"preferred sources keep {int(counts_df[(counts_df['source'] == 'MURI-eng') | (counts_df['subset'].str.contains('c4|wiki', case=False, na=False))]['kept_all_filters'].sum()):,}")
    print(f"  report: {out.relative_to(REPO_ROOT).as_posix()}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
