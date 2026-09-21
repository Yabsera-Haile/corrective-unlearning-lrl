# English contamination-source inspection (Step 2A)

- **sources:** MURI-IT English MRI (local parquet), LongForm (C4/Wikipedia preferred)
- **note:** no selection or filtering happens here; filter columns are counts only. GlotLID runs in 2C, not here.

## MURI-IT English MRI

- **scan:** 15 shards in 27s
- **examples:** 15,000
- **columns:** `input`, `output`, `language`, `dataset_name`, `subdataset_name`, `split`
- **used as:** instruction=`input`, response=`output`, subset=`subdataset_name`

Example rows (truncated):
```
[0]
  input: "Describe the contents of a Jiu Jitsu course."
  output: "Published October 31, 2012 at 3306 × 2459 in 31-days-of-randomness-personal-inspiration-29 – Little Things\t\nIt was an amazing tournament, with unique contents o…(+660 chars)"
  language: "eng"
  dataset_name: "MRI"
  subdataset_name: "culturax/OSCAR-2019"
  split: "test"
[1]
  input: "Describe the photo detail."
  output: "Photo Detail - Farnham Maxwell Lyte - Cascade d'Enfer a Luchon, Pyrenees\nFarnham Maxwell Lyte\nWith the photographer's red inked signature and publisher Theophil…(+1018 chars)"
  language: "eng"
  dataset_name: "MRI"
  subdataset_name: "culturax/mC4"
  split: "test"
[2]
  input: "Describe the Arbor Video Doorbell."
  output: "Yesterday, an explosion occurred in a coal mine in Siberia, a region of Russia, and the latest tolls speak about 100 deaths. It is the deadliest mining accident…(+3145 chars)"
  language: "eng"
  dataset_name: "MRI"
  subdataset_name: "culturax/OSCAR-2019"
  split: "test"
```

**Counts and filter preview** (each rule counted independently; a row can trip several):
| subset | n | drop instruction summarize translate | drop response code fence | drop response html | drop response md table | drop response latex | drop response empty or short | drop response very long | drop duplicate response | kept by all |
|---|---|---|---|---|---|---|---|---|---|---|
| culturax/OSCAR-2019 | 554 | 1 | 0 | 2 | 0 | 0 | 11 | 13 | 0 | 527 |
| culturax/OSCAR-2109 | 981 | 3 | 0 | 2 | 0 | 1 | 105 | 5 | 0 | 866 |
| culturax/OSCAR-2201 | 102 | 0 | 0 | 1 | 0 | 0 | 5 | 4 | 0 | 92 |
| culturax/OSCAR-2301 | 443 | 3 | 0 | 1 | 0 | 0 | 17 | 19 | 0 | 403 |
| culturax/mC4 | 5506 | 109 | 2 | 19 | 0 | 19 | 3 | 68 | 0 | 5290 |
| wikipedia | 7414 | 2 | 0 | 2 | 26 | 1 | 206 | 145 | 0 | 7033 |

**Response length (characters)**
| subset | n | p10 | p25 | p50 | p75 | p90 | p99 |
|---|---|---|---|---|---|---|---|
| culturax/OSCAR-2019 | 554 | 373 | 826 | 2095 | 4777 | 9460 | 30033 |
| culturax/OSCAR-2109 | 981 | 196 | 351 | 875 | 2252 | 4534 | 16620 |
| culturax/OSCAR-2201 | 102 | 300 | 1018 | 2818 | 4995 | 8706 | 29220 |
| culturax/OSCAR-2301 | 443 | 377 | 953 | 2779 | 6583 | 12232 | 51045 |
| culturax/mC4 | 5506 | 626 | 1231 | 2324 | 4175 | 7026 | 22612 |
| wikipedia | 7414 | 401 | 880 | 1960 | 4062 | 7899 | 28873 |

**Instruction length (characters)**
| subset | n | p10 | p25 | p50 | p75 | p90 | p99 |
|---|---|---|---|---|---|---|---|
| culturax/OSCAR-2019 | 554 | 31 | 41 | 52 | 70 | 89 | 350 |
| culturax/OSCAR-2109 | 981 | 33 | 42 | 56 | 73 | 93 | 221 |
| culturax/OSCAR-2201 | 102 | 30 | 37 | 50 | 63 | 71 | 96 |
| culturax/OSCAR-2301 | 443 | 30 | 39 | 52 | 70 | 91 | 177 |
| culturax/mC4 | 5506 | 34 | 43 | 56 | 72 | 93 | 306 |
| wikipedia | 7414 | 21 | 27 | 38 | 51 | 66 | 106 |

## LongForm — `akoksal/LongForm`

- **splits:** `train`: 23,652, `validation`: 2,042, `test`: 2,045
- **features:** `input`: Value(dtype='string', id=None), `output`: Value(dtype='string', id=None), `source`: Value(dtype='string', id=None), `subset`: Value(dtype='string', id=None)
- **identifier-like columns:** `source`
- `source`: 8 distinct — `C4`=10,000, `Wikipedia`=5,000, `StackExchange`=4,380, `Natural Instructions`=3,684, `WikiHow`=2,500, `BEA-GEC`=1,203, `BigBench`=600, `Enron`=372
- **examples:** 27,739
- **columns:** `input`, `output`, `source`, `subset`, `_split`
- **used as:** instruction=`input`, response=`output`, subset=`source`

Example rows (truncated):
```
[0]
  input: "What are the positions held by Beto O'Rourke, Lupe Valdez, and Veronica Escobar on decriminalizing unauthorized border crossings in the US?"
  output: "The liberal mainstream media squealed with delight last week when they announced Ted Cruz was only 4 points ahead of Democrat Beto O’Rourke.\nThe the bottom drop…(+1057 chars)"
  source: "C4"
  subset: "search-engine"
  _split: "train"
[1]
  input: "For example, for the original quote we shall use, 'One swallow does not a summer make'. If someone were to say 'One good quote does not a philosopher make' (No …(+145 chars)"
  output: "The word I've heard used for this on the linguistics blog Language Log is snowclone (it's derived from phrases of the format 'If Eskimos have N words for snow, …(+652 chars)"
  source: "Natural Instructions"
  subset: "task225 english language answer generation"
  _split: "train"
[2]
  input: "Describe the U.S.-Mexico border. Respond in detail."
  output: "President Donald Trump’s border wall with Mexico will have an initial price tag of between $12 billion and $15 billion, according to Congressional Republican le…(+3972 chars)"
  source: "C4"
  subset: "instruction"
  _split: "train"
```

**Counts and filter preview** (each rule counted independently; a row can trip several):
| subset | n | drop instruction summarize translate | drop response code fence | drop response html | drop response md table | drop response latex | drop response empty or short | drop response very long | drop duplicate response | kept by all |
|---|---|---|---|---|---|---|---|---|---|---|
| BEA-GEC | 1203 | 15 | 0 | 0 | 0 | 0 | 15 | 0 | 0 | 1173 |
| BigBench | 600 | 9 | 0 | 0 | 0 | 0 | 112 | 0 | 274 | 261 |
| C4 | 10000 | 32 | 0 | 11 | 0 | 4 | 112 | 0 | 17 | 9825 |
| Enron | 372 | 0 | 0 | 1 | 0 | 0 | 155 | 2 | 16 | 203 |
| Natural Instructions | 3684 | 533 | 0 | 0 | 0 | 0 | 676 | 0 | 1 | 2480 |
| StackExchange | 4380 | 122 | 2 | 48 | 5 | 69 | 431 | 0 | 2 | 3723 |
| WikiHow | 2500 | 0 | 0 | 19 | 0 | 2 | 18 | 15 | 32 | 2416 |
| Wikipedia | 5000 | 1 | 0 | 0 | 0 | 0 | 1718 | 0 | 34 | 3281 |

**Response length (characters)**
| subset | n | p10 | p25 | p50 | p75 | p90 | p99 |
|---|---|---|---|---|---|---|---|
| BEA-GEC | 1203 | 438 | 722 | 1048 | 1385 | 1966 | 3377 |
| BigBench | 600 | 118 | 261 | 962 | 1531 | 2107 | 3280 |
| C4 | 10000 | 563 | 1125 | 2163 | 3573 | 4860 | 6093 |
| Enron | 372 | 29 | 86 | 325 | 1196 | 2713 | 9992 |
| Natural Instructions | 3684 | 146 | 236 | 526 | 1357 | 2176 | 4101 |
| StackExchange | 4380 | 201 | 379 | 712 | 1293 | 2251 | 5200 |
| WikiHow | 2500 | 588 | 1033 | 3747 | 7480 | 10468 | 17369 |
| Wikipedia | 5000 | 111 | 163 | 270 | 447 | 688 | 1325 |

**Instruction length (characters)**
| subset | n | p10 | p25 | p50 | p75 | p90 | p99 |
|---|---|---|---|---|---|---|---|
| BEA-GEC | 1203 | 528 | 815 | 1127 | 1463 | 2045 | 3470 |
| BigBench | 600 | 274 | 1489 | 5395 | 6829 | 8104 | 9531 |
| C4 | 10000 | 41 | 55 | 73 | 98 | 125 | 201 |
| Enron | 372 | 53 | 66 | 80 | 102 | 130 | 209 |
| Natural Instructions | 3684 | 426 | 583 | 1531 | 5534 | 10989 | 23251 |
| StackExchange | 4380 | 258 | 416 | 758 | 1510 | 2902 | 7313 |
| WikiHow | 2500 | 42 | 54 | 85 | 107 | 120 | 138 |
| Wikipedia | 5000 | 28 | 41 | 54 | 69 | 85 | 120 |

## Allocation feasibility

- **need:** 8,600 per language x 4 = **34,400** for fully disjoint allocations (7,000 mixture + 495 dev + ~15% headroom)
- **preferred sources (MURI-eng + LongForm C4/Wikipedia):** 32,500 raw, **29,733** after the filter preview
- **other LongForm subsets (only if short; report separately if used):** 10,239 raw, 7,840 after preview

**Short by 4,667** for fully disjoint allocations: 29,733 available, 34,400 needed.
- disjoint across languages would give **7,433 per language** (need 8,600) — NOT enough
- adding LongForm's other subsets would reach 37,573 (enough)
- otherwise: allow cross-language overlap, keep `origin_id` on every example, and report the overlap fraction per language pair (permitted by 2A)

Within a language every English source is used at most once either way; that constraint is never relaxed.
