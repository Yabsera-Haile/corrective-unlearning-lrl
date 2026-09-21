# English source allocation (Step 2A, recomputed from committed counts)

- **inputs:** `results/step2/english_source_counts.csv`, `english_source_lengths.csv`

## Allocation feasibility

- **need:** 8,600 per language x 4 = **34,400** for fully disjoint allocations (7,000 mixture + 495 dev + ~15% headroom)
- **preferred sources (MURI-eng + LongForm C4/Wikipedia):** 30,000 raw, **27,317** after the filter preview
  - MURI-eng / culturax/OSCAR-2019: 527
  - MURI-eng / culturax/OSCAR-2109: 866
  - MURI-eng / culturax/OSCAR-2201: 92
  - MURI-eng / culturax/OSCAR-2301: 403
  - MURI-eng / culturax/mC4: 5,290
  - MURI-eng / wikipedia: 7,033
  - LongForm / C4: 9,825
  - LongForm / Wikipedia: 3,281
- **other subsets (StackExchange, WikiHow, NLP tasks, ...; only if short, and then reported separately in every table):** 12,739 raw, 10,256 after preview

- **length compatibility:** LongForm/Wikipedia (p50=270 chars) sit below the 500-character median used by the other preferred sources. Excluding them leaves **24,036** length-compatible candidates (24,036 vs 27,317); see D2.9.

**Short by 7,083** for fully disjoint allocations: 27,317 available, 34,400 needed.
- disjoint across languages would give **6,829 per language** (need 8,600) — NOT enough
- adding LongForm's other subsets would reach 37,573 (enough)
- otherwise: allow cross-language overlap, keep `origin_id` on every example, and report the overlap fraction per language pair (permitted by 2A)

Within a language every English source is used at most once either way; that constraint is never relaxed.
