# Language profile summary (Step 1.4)

- generated 2026-09-21 10:51 UTC on STUDENT-199, commit 71886a1, mode **full**
- volume basis for thresholds: `mri_clean_lo` — MURI's own MRI subset after dedup, conservative end of the bracket. MRI is the only in-language instruction data: the other subsets (xP3, SuperNaturalInstructions, ...) contribute short classification rows and, for some languages, English instructions.
- counts cover all MURI splits; lengths in **characters**, over deduplicated rows

## Intersection attrition

| stage | languages | dropped |
|---|---|---|
| MURI-IT `language` values | 201 |  |
| natural languages (excl. `code`) | 200 | -1 |
| given a FLORES-style code (198 MURI codes; 2 unmapped; merges) | 197 | -3 |
| ∩ NLLB-200 | 150 | -47 |
| ∩ FLORES-200 | 150 | -0 |
| ∩ Belebele  = **candidate pool** | 103 | -47 |

Dropped at ∩ NLLB-200 (no NLLB/FLORES entry; code constructed from ISO 639-3 + script): `bre_Latn`, `nds_Latn`, `chv_Cyrl`, `sah_Cyrl`, `oss_Cyrl`, `lat_Latn`, `div_Thaa`, `ido_Latn`, `new_Deva`, `wln_Latn`, `arg_Latn`, `fry_Latn`, `sme_Latn`, `hif_Latn`, `nav_Latn`, `kom_Cyrl`, `cos_Latn`, `chm_Cyrl`, `bar_Latn`, `mwl_Latn`, `myv_Cyrl`, `udm_Cyrl`, `glv_Latn`, `cor_Latn`, `roh_Latn`, `krc_Cyrl`, `ava_Cyrl`, `tyv_Cyrl`, `nia_Latn`, `ton_Latn`, `mdf_Cyrl`, `lah_Arab`, `stq_Latn`, `haw_Latn`, `bis_Latn`, `ven_Latn`, `xal_Cyrl`, `alt_Cyrl`, `srn_Latn`, `kbd_Cyrl`, `chr_Cher`, `iku_Cans`, `jam_Latn`, `kal_Latn`, `guc_Latn`, `zha_Latn`, `ady_Cyrl`

Dropped at ∩ Belebele: `tat_Cyrl`, `cym_Latn`, `epo_Latn`, `bel_Cyrl`, `gla_Latn`, `oci_Latn`, `ltz_Latn`, `ydd_Hebr`, `gle_Latn`, `bak_Cyrl`, `uig_Arab`, `glg_Latn`, `tuk_Latn`, `san_Deva`, `ace_Latn`, `lim_Latn`, `lij_Latn`, `ban_Latn`, `fao_Latn`, `srd_Latn`, `crh_Latn`, `scn_Latn`, `quy_Latn`, `szl_Latn`, `vec_Latn`, `bug_Latn`, `fur_Latn`, `pap_Latn`, `lmo_Latn`, `kas_Arab`, `ayr_Latn`, `kbp_Latn`, `mai_Deva`, `fij_Latn`, `smo_Latn`, `pag_Latn`, `ewe_Latn`, `dzo_Tibt`, `awa_Deva`, `kon_Latn`, `fon_Latn`, `dik_Latn`, `run_Latn`, `sag_Latn`, `aka_Latn`, `kik_Latn`, `tum_Latn`

## Unmapped MURI-IT languages: **2** of 200 (+1 excluded non-language)

- `hbs` (Serbo-Croatian): ambiguous: Serbo-Croatian macrolanguage; its Latin-script text (79%) cannot be split between hrv/bos/srp without a classifier
- `kur` (Kurdish): ambiguous: text is 57% Arabic / 43% Latin script, i.e. Sorani (ckb_Arab) and Kurmanji (kmr_Latn) mixed under one code; recoverable by a per-row script split if ever needed
- full log with reasons for every value: `results/code_mapping_log.csv`

## Non-exact mappings (24; constructed codes excluded)

- assumed: `zho`→`zho_Hans`, `fas`→`pes_Arab`, `ara`→`arb_Arab`, `msa`→`zsm_Latn`, `nor`→`nob_Latn`, `lav`→`lvs_Latn`
- inferred: `ori`→`ory_Orya`, `swa`→`swh_Latn`, `nep`→`npi_Deva`, `mlg`→`plt_Latn`, `mon`→`khk_Cyrl`, `sqi`→`als_Latn`, `aze`→`azj_Latn`, `yid`→`ydd_Hebr`, `pus`→`pbt_Arab`, `uzb`→`uzn_Latn`, `ace`→`ace_Latn`, `que`→`quy_Latn`, `kas`→`kas_Arab`, `aym`→`ayr_Latn`, `orm`→`gaz_Latn`, `ful`→`fuv_Latn`, `fil`→`tgl_Latn`, `din`→`dik_Latn`
- multi-script targets resolved by script: 4; macro/individual mismatches: 21
- **in the pool with an assumed mapping (verify before selecting):** pes_Arab, lvs_Latn, nob_Latn, arb_Arab, zsm_Latn, zho_Hans
- Joshi match methods in pool: {'name': 82, 'muri-name': 11, 'alias': 8, 'last-word': 2}
- pool languages at Joshi 0 (class-0 list may hold a duplicate of a curated name; review): `shn_Mymr`=shan

## Volume threshold sensitivity (candidate pool)

| total examples | languages | Latin | non-Latin | Joshi level:count | Joshi 0-2 | repair pool at 50/50 ≥ |
|---|---|---|---|---|---|---|
| ≥ 500 | 98 | 58 | 40 | 0:1 1:40 2:13 3:21 4:16 5:7 | 54 (31 Latin) | 250 |
| ≥ 1,000 | 92 | 52 | 40 | 0:1 1:35 2:12 3:21 4:16 5:7 | 48 (25 Latin) | 500 |
| ≥ 2,000 | 87 | 47 | 40 | 0:1 1:32 2:10 3:21 4:16 5:7 | 43 (20 Latin) | 1,000 |
| ≥ 5,000 | 84 | 45 | 39 | 0:1 1:29 2:10 3:21 4:16 5:7 | 40 (18 Latin) | 2,500 |

Chosen threshold: **5,000** → 84 languages pass.

## Top 25 candidates by clean MRI pool

| # | flores_code | language_name | script | joshi_level | muri_n_examples | muri_n_after_dedup | mri_clean_lo | mri_clean_hi | mean_response_len | mapping_confidence |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | spa_Latn | Spanish | Latn | 5 | 38,090 | 38,090 | 15,000 | 15,000 | 1893.6 | exact |
| 2 | pes_Arab | Iranian Persian | Arab | 4 | 28,595 | 28,595 | 15,000 | 15,000 | 970.5 | assumed |
| 3 | jpn_Jpan | Japanese | Jpan | 5 | 28,448 | 28,448 | 15,000 | 15,000 | 1268.0 | exact |
| 4 | tel_Telu | Telugu | Telu | 1 | 23,914 | 23,914 | 15,000 | 15,000 | 2062.3 | exact |
| 5 | tam_Taml | Tamil | Taml | 3 | 23,565 | 23,565 | 15,000 | 15,000 | 1724.9 | exact |
| 6 | deu_Latn | German | Latn | 5 | 22,670 | 22,670 | 15,000 | 15,000 | 3076.1 | exact |
| 7 | cat_Latn | Catalan | Latn | 4 | 22,025 | 22,025 | 15,000 | 15,000 | 2005.4 | exact |
| 8 | pol_Latn | Polish | Latn | 4 | 20,557 | 20,557 | 15,000 | 15,000 | 1762.0 | exact |
| 9 | kor_Hang | Korean | Hang | 4 | 20,207 | 20,207 | 15,000 | 15,000 | 1540.8 | exact |
| 10 | swe_Latn | Swedish | Latn | 4 | 16,800 | 16,800 | 15,000 | 15,000 | 1918.3 | exact |
| 11 | est_Latn | Estonian | Latn | 3 | 16,000 | 16,000 | 15,000 | 15,000 | 3044.5 | exact |
| 12 | fin_Latn | Finnish | Latn | 4 | 15,600 | 15,600 | 15,000 | 15,000 | 2756.2 | exact |
| 13 | ron_Latn | Romanian | Latn | 3 | 15,400 | 15,400 | 15,000 | 15,000 | 2731.2 | exact |
| 14 | afr_Latn | Afrikaans | Latn | 3 | 15,000 | 15,000 | 15,000 | 15,000 | 3683.7 | exact |
| 15 | ceb_Latn | Cebuano | Latn | 3 | 15,000 | 15,000 | 15,000 | 15,000 | 1361.5 | exact |
| 16 | dan_Latn | Danish | Latn | 3 | 15,000 | 15,000 | 15,000 | 15,000 | 2754.4 | exact |
| 17 | ell_Grek | Modern Greek (1453-) | Grek | 3 | 15,000 | 15,000 | 15,000 | 15,000 | 3229.7 | exact |
| 18 | hun_Latn | Hungarian | Latn | 4 | 15,000 | 15,000 | 15,000 | 15,000 | 3059.9 | exact |
| 19 | isl_Latn | Icelandic | Latn | 2 | 15,000 | 15,000 | 15,000 | 15,000 | 2578.7 | exact |
| 20 | kaz_Cyrl | Kazakh | Cyrl | 3 | 15,000 | 15,000 | 15,000 | 15,000 | 2599.5 | exact |
| 21 | lit_Latn | Lithuanian | Latn | 3 | 15,000 | 15,000 | 15,000 | 15,000 | 2666.2 | exact |
| 22 | lvs_Latn | Standard Latvian | Latn | 3 | 15,000 | 15,000 | 15,000 | 15,000 | 2775.1 | assumed |
| 23 | slv_Latn | Slovenian | Latn | 3 | 15,000 | 15,000 | 15,000 | 15,000 | 3491.1 | exact |
| 24 | tgk_Cyrl | Tajik | Cyrl | 1 | 15,000 | 15,000 | 15,000 | 15,000 | 2108.0 | exact |
| 25 | fra_Latn | French | Latn | 5 | 29,559 | 29,558 | 14,999 | 15,000 | 2488.6 | exact |

## Languages whose total volume overstates the clean pool

Total counts include MURI's non-MRI subsets; these are the pool languages where the clean MRI pool is under 70% of the deduplicated total. Ranking on total volume would pick these up as far larger than they are.

| flores_code | language_name | joshi_level | muri_n_after_dedup | mri_clean_hi | mean_response_len |
|---|---|---|---|---|---|
| tgl_Latn | Tagalog | 3 | 1,443 | 0 | 108.2 |
| yor_Latn | Yoruba | 2 | 5,911 | 145 | 92.7 |
| tso_Latn | Tsonga | 1 | 4,629 | 629 | 221.9 |
| lin_Latn | Lingala | 1 | 4,678 | 679 | 166.2 |
| bam_Latn | Bambara | 1 | 4,690 | 690 | 176.7 |
| sot_Latn | Southern Sotho | 1 | 4,731 | 731 | 252.6 |
| nya_Latn | Chichewa | 1 | 4,948 | 948 | 354.1 |
| wol_Latn | Wolof | 2 | 4,952 | 952 | 479.6 |
| tsn_Latn | Tswana | 2 | 5,187 | 1,187 | 793.4 |
| xho_Latn | Xhosa | 2 | 5,901 | 1,501 | 381.8 |
| lug_Latn | Ganda | 1 | 7,122 | 3,126 | 819.4 |
| kin_Latn | Kinyarwanda | 1 | 8,235 | 4,237 | 789.7 |
| nso_Latn | Pedi | 1 | 10,651 | 6,854 | 173.1 |
| sna_Latn | Shona | 1 | 12,284 | 8,285 | 552.8 |
| zul_Latn | Zulu | 2 | 12,491 | 8,491 | 386.9 |
