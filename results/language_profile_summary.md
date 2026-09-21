# Language profile summary (Step 1.4)

- generated 2026-09-21 10:30 UTC on CTexT-GPU, commit 05ab46d, mode **full**
- volume column for thresholds: `muri_n_after_dedup` (all MURI splits); lengths in **characters**, over deduplicated rows

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

Dropped at ∩ Belebele: `glg_Latn`, `tat_Cyrl`, `cym_Latn`, `epo_Latn`, `bel_Cyrl`, `gla_Latn`, `oci_Latn`, `ltz_Latn`, `ydd_Hebr`, `gle_Latn`, `bak_Cyrl`, `uig_Arab`, `tuk_Latn`, `san_Deva`, `aka_Latn`, `ace_Latn`, `lim_Latn`, `lij_Latn`, `ban_Latn`, `fao_Latn`, `srd_Latn`, `crh_Latn`, `scn_Latn`, `quy_Latn`, `szl_Latn`, `vec_Latn`, `fon_Latn`, `run_Latn`, `kik_Latn`, `tum_Latn`, `bug_Latn`, `fur_Latn`, `pap_Latn`, `lmo_Latn`, `kas_Arab`, `ayr_Latn`, `kbp_Latn`, `mai_Deva`, `fij_Latn`, `smo_Latn`, `pag_Latn`, `ewe_Latn`, `dzo_Tibt`, `awa_Deva`, `kon_Latn`, `dik_Latn`, `sag_Latn`

## Unmapped MURI-IT languages: **2** of 200 (+1 excluded non-language)

- `hbs` (Serbo-Croatian): ambiguous: Serbo-Croatian macrolanguage; its Latin-script text (79%) cannot be split between hrv/bos/srp without a classifier
- `kur` (Kurdish): ambiguous: text is 57% Arabic / 43% Latin script, i.e. Sorani (ckb_Arab) and Kurmanji (kmr_Latn) mixed under one code; recoverable by a per-row script split if ever needed
- full log with reasons for every value: `results/code_mapping_log.csv`

## Non-exact mappings (24; constructed codes excluded)

- assumed: `zho`→`zho_Hans`, `fas`→`pes_Arab`, `ara`→`arb_Arab`, `msa`→`zsm_Latn`, `nor`→`nob_Latn`, `lav`→`lvs_Latn`
- inferred: `ori`→`ory_Orya`, `swa`→`swh_Latn`, `nep`→`npi_Deva`, `mlg`→`plt_Latn`, `mon`→`khk_Cyrl`, `sqi`→`als_Latn`, `aze`→`azj_Latn`, `yid`→`ydd_Hebr`, `pus`→`pbt_Arab`, `uzb`→`uzn_Latn`, `ace`→`ace_Latn`, `que`→`quy_Latn`, `kas`→`kas_Arab`, `aym`→`ayr_Latn`, `orm`→`gaz_Latn`, `ful`→`fuv_Latn`, `fil`→`tgl_Latn`, `din`→`dik_Latn`
- multi-script targets resolved by script: 4; macro/individual mismatches: 21
- **in the pool with an assumed mapping (verify before selecting):** zho_Hans, pes_Arab, arb_Arab, zsm_Latn, nob_Latn, lvs_Latn
- Joshi match methods in pool: {'name': 82, 'muri-name': 11, 'alias': 8, 'last-word': 2}
- pool languages at Joshi 0 (class-0 list may hold a duplicate of a curated name; review): `shn_Mymr`=shan

## Volume threshold sensitivity (candidate pool)

| total examples | languages | Latin | non-Latin | Joshi level:count | Joshi 0-2 | repair pool at 50/50 ≥ |
|---|---|---|---|---|---|---|
| ≥ 500 | 100 | 60 | 40 | 0:1 1:40 2:14 3:22 4:16 5:7 | 55 (32 Latin) | 250 |
| ≥ 1,000 | 100 | 60 | 40 | 0:1 1:40 2:14 3:22 4:16 5:7 | 55 (32 Latin) | 500 |
| ≥ 2,000 | 96 | 56 | 40 | 0:1 1:37 2:14 3:21 4:16 5:7 | 52 (29 Latin) | 1,000 |
| ≥ 5,000 | 89 | 50 | 39 | 0:1 1:31 2:13 3:21 4:16 5:7 | 45 (23 Latin) | 2,500 |

## Top 25 candidates by example count

| # | flores_code | language_name | script | joshi_level | muri_n_examples | muri_n_after_dedup | muri_n_mri | mean_instruction_len | mean_response_len | mapping_confidence |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | eng_Latn | English | Latn | 5 | 125,995 | 125,984 | 15,000 | 1061.7 | 645.4 | exact |
| 2 | spa_Latn | Spanish | Latn | 5 | 38,090 | 38,090 | 15,000 | 352.6 | 1893.6 | exact |
| 3 | hin_Deva | Hindi | Deva | 4 | 30,291 | 30,204 | 15,000 | 283.1 | 1705.9 | exact |
| 4 | zho_Hans | Chinese | Hans | 5 | 29,630 | 29,586 | 15,000 | 196.8 | 606.0 | assumed |
| 5 | fra_Latn | French | Latn | 5 | 29,559 | 29,558 | 15,000 | 252.8 | 2488.6 | exact |
| 6 | pes_Arab | Iranian Persian | Arab | 4 | 28,595 | 28,595 | 15,000 | 272.5 | 970.5 | assumed |
| 7 | jpn_Jpan | Japanese | Jpan | 5 | 28,448 | 28,448 | 15,000 | 145.3 | 1268.0 | exact |
| 8 | arb_Arab | Standard Arabic | Arab | 5 | 26,403 | 26,394 | 15,000 | 272.7 | 1163.6 | assumed |
| 9 | ben_Beng | Bengali | Beng | 3 | 25,674 | 25,673 | 15,000 | 214.9 | 1515.9 | exact |
| 10 | vie_Latn | Vietnamese | Latn | 4 | 25,087 | 25,085 | 15,000 | 235.7 | 1954.8 | exact |
| 11 | zsm_Latn | Standard Malay | Latn | 3 | 24,567 | 24,544 | 15,000 | 248.3 | 1576.5 | assumed |
| 12 | tel_Telu | Telugu | Telu | 1 | 23,914 | 23,914 | 15,000 | 205.4 | 2062.3 | exact |
| 13 | guj_Gujr | Gujarati | Gujr | 1 | 24,227 | 23,888 | 15,000 | 180.5 | 1479.1 | exact |
| 14 | ita_Latn | Italian | Latn | 4 | 23,836 | 23,833 | 15,000 | 123.5 | 2682.2 | exact |
| 15 | tam_Taml | Tamil | Taml | 3 | 23,565 | 23,565 | 15,000 | 211.8 | 1724.9 | exact |
| 16 | por_Latn | Portuguese | Latn | 4 | 23,351 | 23,350 | 15,000 | 267.2 | 2028.8 | exact |
| 17 | deu_Latn | German | Latn | 5 | 22,670 | 22,670 | 15,000 | 190.2 | 3076.1 | exact |
| 18 | mal_Mlym | Malayalam | Mlym | 1 | 22,576 | 22,575 | 15,000 | 135.0 | 1690.1 | exact |
| 19 | mar_Deva | Marathi | Deva | 2 | 22,456 | 22,271 | 15,000 | 166.4 | 1386.6 | exact |
| 20 | cat_Latn | Catalan | Latn | 4 | 22,025 | 22,025 | 15,000 | 219.1 | 2005.4 | exact |
| 21 | nld_Latn | Dutch | Latn | 4 | 21,860 | 21,859 | 15,000 | 112.3 | 2236.6 | exact |
| 22 | ory_Orya | Odia | Orya | 1 | 21,775 | 21,756 | 15,000 | 119.7 | 1305.7 | inferred |
| 23 | urd_Arab | Urdu | Arab | 3 | 21,763 | 21,748 | 15,000 | 240.5 | 1738.2 | exact |
| 24 | pan_Guru | Panjabi | Guru | 2 | 21,688 | 21,682 | 15,000 | 153.5 | 1700.5 | exact |
| 25 | rus_Cyrl | Russian | Cyrl | 4 | 21,416 | 21,415 | 15,000 | 109.9 | 3021.2 | exact |
