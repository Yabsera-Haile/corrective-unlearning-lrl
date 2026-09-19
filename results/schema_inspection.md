# Schema inspection (Step 1.2)

- **generated:** 2026-09-19 16:29 UTC
- **host / repo commit:** CTexT-GPU / 4dcd178
- **versions:** python 3.13.13, datasets 3.6.0, pyarrow 20.0.0
- **HF auth:** token present, user `yab333`
- **CPU cap (CU_NUM_PROC):** 4
- **sources:** muri_it, muri_it_language_split, nllb200, flores200, flores_plus, belebele, tulu3_sft

## muri_it — `akoksal/muri-it`

_clean repair data (combined release)_

- **revision:** d4a210119d09c61ca0c427af2114a54faaf0293c
- **gated:** False
- **files:** 17 files, 3850.8 MB
- **bytes by extension:** .parquet 3850.8 MB, .md 0.0 MB, .gitattributes 0.0 MB
- **first files:** `.gitattributes`, `README.md`, `data/test-00000-of-00001.parquet`, `data/train-00000-of-00013.parquet`, `data/train-00001-of-00013.parquet`, `data/train-00002-of-00013.parquet`, `data/train-00003-of-00013.parquet`, `data/train-00004-of-00013.parquet`
- **configs:** 1 (from get_dataset_config_names)
- **first configs:** `default`
- **config-name formats:**
  - word(s) / name: 1 — e.g. `default`
- **full list:** `results/schema/muri_it__configs.txt`
- **viewer row counts:** partial=False; per split: test=111,427, train=2,005,648, validation=111,424
- **full table:** `results/schema/muri_it__viewer_rows.csv`

### streamed slice: config `default`

- **splits:** `train`, `validation`, `test`
- **sampled:** first 500 rows of `train` (15.0s)

| column | declared feature | observed python types |
|---|---|---|
| `input` | Value(dtype='string', id=None) | str×500 |
| `output` | Value(dtype='string', id=None) | str×500 |
| `dataset_name` | Value(dtype='string', id=None) | str×500 |
| `subdataset_name` | Value(dtype='string', id=None) | str×416, NoneType×84 |
| `language` | Value(dtype='string', id=None) | str×500 |
| `language_name` | Value(dtype='string', id=None) | str×500 |
| `split` | Value(dtype='string', id=None) | str×500 |

Example rows (strings truncated to 160 chars, lists to 4 items):
```
[0]
  input: "Предоставьте информацию о Batagay Airport."
  output: "Аэропорт «Батага́й» — региональный аэропорт посёлка Батагай Верхоянского улуса Якутии, расположен в 2,5 км юго-восточнее посёлка. Обеспечивает регулярное авиасо…(+561 chars)"
  dataset_name: "MRI"
  subdataset_name: "wikipedia"
  language: "rus"
  language_name: "Russian"
  split: "train"
[1]
  input: "Quin es lo nom de la comuna en Bretanha, França?"
  output: "Plouilio en breton ( Ploumilliau /Plouilio en francés) es una comuna bretona, situada dins lo departament de las Còstas d'Arvòr e la region de Bretanha."
  dataset_name: "MRI"
  subdataset_name: "culturax/OSCAR-2109"
  language: "oci"
  language_name: "Occitan (post 1500)"
  split: "train"
[2]
  input: "In this task, you are given music product reviews in German language. The goal is to classify the review as \"POS\" if the overall sentiment of the review is posi…(+602 chars)"
  output: "POS"
  dataset_name: "SuperNaturalInstructionv2"
  subdataset_name: "task481_cls_german_music_classification"
  language: "deu"
  language_name: "German"
  split: "train"
```

- **identifier-like column `dataset_name`** — 6 distinct in 500 sampled rows; top: `MRI`×379, `xP3`×39, `SuperNaturalInstructionv2`×37, `flan_v2_tulu`×29, `WikiHow`×12, `OpenAssistant`×4
  - word(s) / name: 5 — e.g. `SuperNaturalInstructionv2`, `xP3`, `flan_v2_tulu`, `WikiHow`, `OpenAssistant`
  - XX/XXX (upper-case code): 1 — e.g. `MRI`
- **identifier-like column `language`** — 141 distinct in 500 sampled rows; top: `eng`×33, `fra`×12, `urd`×8, `hin`×8, `ben`×8, `tel`×8, `tur`×7, `snd`×7
  - xxx (ISO 639-3-like): 141 — e.g. `rus`, `oci`, `deu`, `swe`, `shn`, `guj`
- **identifier-like column `language_name`** — 141 distinct in 500 sampled rows; top: `English`×33, `French`×12, `Urdu`×8, `Hindi`×8, `Bengali`×8, `Telugu`×8, `Turkish`×7, `Sindhi`×7
  - word(s) / name: 141 — e.g. `Russian`, `Occitan (post 1500)`, `German`, `Swedish`, `Shan`, `Gujarati`
- **identifier-like column `split`** — 1 distinct in 500 sampled rows; top: `train`×500
  - word(s) / name: 1 — e.g. `train`

### full local copy: `data/raw/muri-it`

- **parquet files:** 15; rows per split: test=111,427, train=2,005,648, validation=111,424
- **arrow schema (first shard):**
```
input: string
output: string
dataset_name: string
subdataset_name: string
language: string
split: string
language_name: string
```
- **`dataset_name`** (full scan): 6 distinct values → `results/schema/muri_it__dataset_name__values.csv`
  - word(s) / name: 5 — e.g. `xP3`, `SuperNaturalInstructionv2`, `flan_v2_tulu`, `WikiHow`, `OpenAssistant`
  - XX/XXX (upper-case code): 1 — e.g. `MRI`
  - top 10: `MRI`=1,718,449, `xP3`=184,000, `SuperNaturalInstructionv2`=161,986, `flan_v2_tulu`=100,000, `WikiHow`=54,578, `OpenAssistant`=9,486
  - bottom 5: `xP3`=184,000, `SuperNaturalInstructionv2`=161,986, `flan_v2_tulu`=100,000, `WikiHow`=54,578, `OpenAssistant`=9,486
- **`language`** (full scan): 201 distinct values → `results/schema/muri_it__language__values.csv`
  - xxx (ISO 639-3-like): 200 — e.g. `eng`, `spa`, `hin`, `zho`, `fra`, `fas`
  - word(s) / name: 1 — e.g. `code`
  - top 10: `eng`=125,995, `spa`=38,090, `hin`=30,291, `zho`=29,630, `fra`=29,559, `fas`=28,595, `jpn`=28,448, `ara`=26,403, `ben`=25,674, `vie`=25,087
  - bottom 5: `tir`=166, `zha`=128, `sun`=112, `sag`=104, `ady`=104
- **`language_name`** (full scan): 201 distinct values → `results/schema/muri_it__language_name__values.csv`
  - word(s) / name: 200 — e.g. `English`, `Spanish`, `Hindi`, `Chinese`, `French`, `Persian`
  - other: 1 — e.g. `KabiyÃ¨`
  - top 10: `English`=125,995, `Spanish`=38,090, `Hindi`=30,291, `Chinese`=29,630, `French`=29,559, `Persian`=28,595, `Japanese`=28,448, `Arabic`=26,403, `Bengali`=25,674, `Vietnamese`=25,087
  - bottom 5: `Tigrinya`=166, `Zhuang`=128, `Sundanese`=112, `Sango`=104, `Adyghe`=104
- **`split`** (full scan): 3 distinct values → `results/schema/muri_it__split__values.csv`
  - word(s) / name: 3 — e.g. `train`, `test`, `validation`
  - top 10: `train`=2,005,648, `test`=111,427, `validation`=111,424
  - bottom 5: `train`=2,005,648, `test`=111,427, `validation`=111,424
- script profile: up to 30 rows per value of ['language', 'language_name'], letters from ['input', 'output'] (first 1000 chars each)
  - `language` → `results/schema/muri_it__language__scripts.csv`; dominant script counts: LATIN=129, CYRILLIC=26, ARABIC=9, DEVANAGARI=7, HEBREW=2, BENGALI=2, TIBETAN=2, MYANMAR=2, ETHIOPIC=2, ARMENIAN=1, THAI=1, GREEK=1, KANNADA=1, THAANA=1, GEORGIAN=1, MALAYALAM=1, LAO=1, TAMIL=1, KHMER=1, TELUGU=1, SINHALA=1, ORIYA=1, GURMUKHI=1, GUJARATI=1, HIRAGANA=1, HAN=1, HANGUL=1, CANADIAN SYLLABICS=1, CHEROKEE=1
  - 33 values with <90% letters in one script (need an explicit decision in code_maps):
| value | rows | script_1 | share | script_2 | share | script_3 | share |
|---|---|---|---|---|---|---|---|
| tha | 30 | THAI | 0.893 | LATIN | 0.105 | HAN | 0.001 |
| bul | 30 | CYRILLIC | 0.882 | LATIN | 0.118 |  | 0.0 |
| lao | 30 | LAO | 0.892 | LATIN | 0.089 | HIRAGANA | 0.006 |
| tam | 30 | TAMIL | 0.832 | LATIN | 0.152 | GURMUKHI | 0.008 |
| tel | 30 | TELUGU | 0.883 | LATIN | 0.103 | TAMIL | 0.011 |
| zha | 30 | LATIN | 0.785 | HAN | 0.141 | ARABIC | 0.059 |
| sin | 30 | SINHALA | 0.883 | LATIN | 0.117 |  | 0.0 |
| kur | 30 | ARABIC | 0.567 | LATIN | 0.432 | CYRILLIC | 0.0 |
| ori | 30 | ORIYA | 0.834 | LATIN | 0.144 | DEVANAGARI | 0.013 |
| asm | 30 | BENGALI | 0.882 | LATIN | 0.118 |  | 0.0 |
| ben | 30 | BENGALI | 0.822 | LATIN | 0.165 | ARABIC | 0.01 |
| pan | 30 | GURMUKHI | 0.894 | LATIN | 0.097 | MALAYALAM | 0.008 |
| mar | 30 | DEVANAGARI | 0.836 | LATIN | 0.127 | ARABIC | 0.011 |
| guj | 30 | GUJARATI | 0.817 | LATIN | 0.153 | ARABIC | 0.016 |
| jpn | 30 | HIRAGANA | 0.343 | HAN | 0.27 | LATIN | 0.209 |
| hbs | 30 | LATIN | 0.791 | CYRILLIC | 0.209 |  | 0.0 |
| urd | 30 | ARABIC | 0.889 | LATIN | 0.098 | TAMIL | 0.007 |
| chv | 30 | CYRILLIC | 0.862 | LATIN | 0.138 |  | 0.0 |
| ara | 30 | ARABIC | 0.632 | LATIN | 0.365 | HIRAGANA | 0.002 |
| hin | 30 | DEVANAGARI | 0.703 | LATIN | 0.278 | MALAYALAM | 0.013 |
| fas | 30 | ARABIC | 0.761 | LATIN | 0.239 |  | 0.0 |
| zho | 30 | HAN | 0.767 | LATIN | 0.201 | ARABIC | 0.031 |
| kor | 30 | HANGUL | 0.829 | LATIN | 0.158 | HAN | 0.013 |
| mdf | 30 | CYRILLIC | 0.85 | LATIN | 0.146 | TIBETAN | 0.002 |
| chm | 30 | CYRILLIC | 0.824 | LATIN | 0.176 |  | 0.0 |
| oss | 30 | CYRILLIC | 0.847 | LATIN | 0.153 |  | 0.0 |
| kik | 30 | LATIN | 0.864 | MALAYALAM | 0.045 | DEVANAGARI | 0.042 |
| awa | 30 | DEVANAGARI | 0.854 | LATIN | 0.146 |  | 0.0 |
| bam | 30 | LATIN | 0.846 | TAMIL | 0.032 | MALAYALAM | 0.031 |
| aka | 30 | LATIN | 0.846 | DEVANAGARI | 0.08 | ARABIC | 0.022 |
| crh | 30 | LATIN | 0.842 | CYRILLIC | 0.158 |  | 0.0 |
| iku | 30 | CANADIAN SYLLABICS | 0.884 | LATIN | 0.114 | HEBREW | 0.001 |
| chr | 30 | CHEROKEE | 0.865 | LATIN | 0.131 | GREEK | 0.003 |
  - `language_name` → `results/schema/muri_it__language_name__scripts.csv`; dominant script counts: LATIN=129, CYRILLIC=26, ARABIC=9, DEVANAGARI=7, HEBREW=2, BENGALI=2, TIBETAN=2, MYANMAR=2, ETHIOPIC=2, ARMENIAN=1, THAI=1, GREEK=1, KANNADA=1, THAANA=1, GEORGIAN=1, MALAYALAM=1, LAO=1, TAMIL=1, KHMER=1, TELUGU=1, SINHALA=1, ORIYA=1, GURMUKHI=1, GUJARATI=1, HIRAGANA=1, HAN=1, HANGUL=1, CANADIAN SYLLABICS=1, CHEROKEE=1
  - 33 values with <90% letters in one script (need an explicit decision in code_maps):
| value | rows | script_1 | share | script_2 | share | script_3 | share |
|---|---|---|---|---|---|---|---|
| Thai | 30 | THAI | 0.893 | LATIN | 0.105 | HAN | 0.001 |
| Bulgarian | 30 | CYRILLIC | 0.882 | LATIN | 0.118 |  | 0.0 |
| Lao | 30 | LAO | 0.892 | LATIN | 0.089 | HIRAGANA | 0.006 |
| Tamil | 30 | TAMIL | 0.832 | LATIN | 0.152 | GURMUKHI | 0.008 |
| Telugu | 30 | TELUGU | 0.883 | LATIN | 0.103 | TAMIL | 0.011 |
| Zhuang | 30 | LATIN | 0.785 | HAN | 0.141 | ARABIC | 0.059 |
| Sinhala | 30 | SINHALA | 0.883 | LATIN | 0.117 |  | 0.0 |
| Kurdish | 30 | ARABIC | 0.567 | LATIN | 0.432 | CYRILLIC | 0.0 |
| Oriya (macrolanguage) | 30 | ORIYA | 0.834 | LATIN | 0.144 | DEVANAGARI | 0.013 |
| Assamese | 30 | BENGALI | 0.882 | LATIN | 0.118 |  | 0.0 |
| Bengali | 30 | BENGALI | 0.822 | LATIN | 0.165 | ARABIC | 0.01 |
| Panjabi | 30 | GURMUKHI | 0.894 | LATIN | 0.097 | MALAYALAM | 0.008 |
| Marathi | 30 | DEVANAGARI | 0.836 | LATIN | 0.127 | ARABIC | 0.011 |
| Gujarati | 30 | GUJARATI | 0.817 | LATIN | 0.153 | ARABIC | 0.016 |
| Japanese | 30 | HIRAGANA | 0.343 | HAN | 0.27 | LATIN | 0.209 |
| Serbo-Croatian | 30 | LATIN | 0.791 | CYRILLIC | 0.209 |  | 0.0 |
| Urdu | 30 | ARABIC | 0.889 | LATIN | 0.098 | TAMIL | 0.007 |
| Chuvash | 30 | CYRILLIC | 0.862 | LATIN | 0.138 |  | 0.0 |
| Arabic | 30 | ARABIC | 0.632 | LATIN | 0.365 | HIRAGANA | 0.002 |
| Hindi | 30 | DEVANAGARI | 0.703 | LATIN | 0.278 | MALAYALAM | 0.013 |
| Persian | 30 | ARABIC | 0.761 | LATIN | 0.239 |  | 0.0 |
| Chinese | 30 | HAN | 0.767 | LATIN | 0.201 | ARABIC | 0.031 |
| Korean | 30 | HANGUL | 0.829 | LATIN | 0.158 | HAN | 0.013 |
| Moksha | 30 | CYRILLIC | 0.85 | LATIN | 0.146 | TIBETAN | 0.002 |
| Mari (Russia) | 30 | CYRILLIC | 0.824 | LATIN | 0.176 |  | 0.0 |
| Ossetian | 30 | CYRILLIC | 0.847 | LATIN | 0.153 |  | 0.0 |
| Kikuyu | 30 | LATIN | 0.864 | MALAYALAM | 0.045 | DEVANAGARI | 0.042 |
| Awadhi | 30 | DEVANAGARI | 0.854 | LATIN | 0.146 |  | 0.0 |
| Bambara | 30 | LATIN | 0.846 | TAMIL | 0.032 | MALAYALAM | 0.031 |
| Akan | 30 | LATIN | 0.846 | DEVANAGARI | 0.08 | ARABIC | 0.022 |
| Crimean Tatar | 30 | LATIN | 0.842 | CYRILLIC | 0.158 |  | 0.0 |
| Inuktitut | 30 | CANADIAN SYLLABICS | 0.884 | LATIN | 0.114 | HEBREW | 0.001 |
| Cherokee | 30 | CHEROKEE | 0.865 | LATIN | 0.131 | GREEK | 0.003 |

_(muri_it: 47s, 0 error(s))_

## muri_it_language_split — `akoksal/muri-it-language-split`

_clean repair data (per-language configs of the same corpus)_

- **revision:** 4987fc82a54145caf778efec6a682863591be1f2
- **gated:** False
- **files:** 605 files, 3444.7 MB
- **bytes by extension:** .parquet 3444.5 MB, .md 0.2 MB, .gitattributes 0.0 MB
- **first files:** `.gitattributes`, `README.md`, `ace/test-00000-of-00001.parquet`, `ace/train-00000-of-00001.parquet`, `ace/validation-00000-of-00001.parquet`, `ady/test-00000-of-00001.parquet`, `ady/train-00000-of-00001.parquet`, `ady/validation-00000-of-00001.parquet`
- **configs:** 201 (from get_dataset_config_names)
- **first configs:** `ace`, `ady`, `afr`, `aka`, `alt`, `amh`, `ara`, `arg`, `asm`, `ava`
- **last configs:** `yid`, `yor`, `zha`, `zho`, `zul`
- **config-name formats:**
  - xxx (ISO 639-3-like): 200 — e.g. `ace`, `ady`, `afr`, `aka`, `alt`, `amh`
  - word(s) / name: 1 — e.g. `code`
- **full list:** `results/schema/muri_it_language_split__configs.txt`
- **viewer row counts:** partial=False; per split: test=111,427, train=2,005,648, validation=111,424
- **rows per config (min/q1/median/q3/max):** 104 / 3,183 / 9,647 / 15,000 / 125,995
- **full table:** `results/schema/muri_it_language_split__viewer_rows.csv`

### streamed slice: config `ace`

- **splits:** `train`, `validation`, `test`
- **sampled:** first 500 rows of `train` (3.5s)

| column | declared feature | observed python types |
|---|---|---|
| `input` | Value(dtype='string', id=None) | str×500 |
| `output` | Value(dtype='string', id=None) | str×500 |
| `dataset_name` | Value(dtype='string', id=None) | str×500 |
| `subdataset_name` | Value(dtype='string', id=None) | str×500 |
| `language` | Value(dtype='string', id=None) | str×500 |
| `split` | Value(dtype='string', id=None) | str×500 |
| `language_name` | Value(dtype='string', id=None) | str×500 |

Example rows (strings truncated to 160 chars, lists to 4 items):
```
[0]
  input: "Misamis Oriental adalah saboh provinsi di Filipina. Peu ibu kota jih?"
  output: "Propinsi Misamis Oriental nakeuh saboh propinsi di Filipina. Nang nanggroejih nakeuh Cagayan de Oro City.\n\nFilipina"
  dataset_name: "MRI"
  subdataset_name: "wikipedia"
  language: "ace"
  split: "train"
  language_name: "Achinese"
[1]
  input: "Peu nan desa nyan?"
  output: "Alue Deah Teungoh nakeuh saboh gampông nyang na lam keucamatan Meuraxa, Kabupaten Banda Acèh, provinsi Acèh, Indonesia."
  dataset_name: "MRI"
  subdataset_name: "wikipedia"
  language: "ace"
  split: "train"
  language_name: "Achinese"
[2]
  input: "Peu keuh Drosophila clavitibia?"
  output: "Drosophila clavitibia nakeuh saboh spèsiès nibak takson Drosophila.\n\nNè \n Seuneubeuet bak Global Biodiversity Information Facility\n Seuneubeuet bak Encyclopedia…(+20 chars)"
  dataset_name: "MRI"
  subdataset_name: "wikipedia"
  language: "ace"
  split: "train"
  language_name: "Achinese"
```

- **identifier-like column `dataset_name`** — 1 distinct in 500 sampled rows; top: `MRI`×500
  - XX/XXX (upper-case code): 1 — e.g. `MRI`
- **identifier-like column `subdataset_name`** — 1 distinct in 500 sampled rows; top: `wikipedia`×500
  - word(s) / name: 1 — e.g. `wikipedia`
- **identifier-like column `language`** — 1 distinct in 500 sampled rows; top: `ace`×500
  - xxx (ISO 639-3-like): 1 — e.g. `ace`
- **identifier-like column `split`** — 1 distinct in 500 sampled rows; top: `train`×500
  - word(s) / name: 1 — e.g. `train`
- **identifier-like column `language_name`** — 1 distinct in 500 sampled rows; top: `Achinese`×500
  - word(s) / name: 1 — e.g. `Achinese`

_(muri_it_language_split: 15s, 0 error(s))_

## nllb200 — `facebook/nllb-200-distilled-600M`

_contamination generator; only its language codes are inspected_

- **revision:** f8d333a098d19b4fd9a8b18f94170487ad3f821d
- **gated:** False
- **files:** 9 files, 2482.7 MB
- **bytes by extension:** .bin 2460.5 MB, .json 17.3 MB, .model 4.9 MB, .md 0.0 MB, .gitattributes 0.0 MB
- **first files:** `.gitattributes`, `README.md`, `config.json`, `generation_config.json`, `pytorch_model.bin`, `sentencepiece.bpe.model`, `special_tokens_map.json`, `tokenizer.json`
- **small JSON files scanned:** `config.json`, `generation_config.json`, `special_tokens_map.json`, `tokenizer_config.json`
- `config.json`: no code-like strings
- `generation_config.json`: no code-like strings
- `special_tokens_map.json` at `/additional_special_tokens[]`: 202 × lang_Scrp (FLORES-style) — e.g. `ace_Arab`, `ace_Latn`, `acm_Arab`, `acq_Arab`, `aeb_Arab`, `afr_Latn`
- `tokenizer_config.json`: no code-like strings
- **language codes:** 202 → `results/schema/nllb200__codes.txt`
- code-name formats:
  - lang_Scrp (FLORES-style): 202 — e.g. `ace_Arab`, `ace_Latn`, `acm_Arab`, `acq_Arab`, `aeb_Arab`, `afr_Latn`

_(nllb200: 4s, 0 error(s))_

## flores200 — `facebook/flores`

_primary eval, chrF++ (gated)_

- **revision:** 71abf77d8b7beb5cfef59898d6b24d92ab7654fc
- **gated:** auto
- **files:** 1224 files, 276.2 MB
- **bytes by extension:** .parquet 275.8 MB, .md 0.4 MB, .gitattributes 0.0 MB
- **first files:** `.gitattributes`, `README.md`, `data/all/dev-00000-of-00001.parquet`, `data/all/devtest-00000-of-00001.parquet`, `data/language/ace_Arab/dev-00000-of-00001.parquet`, `data/language/ace_Arab/devtest-00000-of-00001.parquet`, `data/language/ace_Latn/dev-00000-of-00001.parquet`, `data/language/ace_Latn/devtest-00000-of-00001.parquet`
- **configs:** 611 (from README card metadata (get_dataset_config_names failed: DatasetNotFoundError))
- **first configs:** `ace_Arab`, `ace_Arab-eng_Latn`, `ace_Latn`, `ace_Latn-eng_Latn`, `acm_Arab`, `acm_Arab-eng_Latn`, `acq_Arab`, `acq_Arab-eng_Latn`, `aeb_Arab`, `aeb_Arab-eng_Latn`
- **last configs:** `zho_Hant-eng_Latn`, `zsm_Latn`, `zsm_Latn-eng_Latn`, `zul_Latn`, `zul_Latn-eng_Latn`
- **config-name formats:**
  - lang_Scrp-lang_Scrp (pair): 406 — e.g. `ace_Arab-eng_Latn`, `ace_Latn-eng_Latn`, `acm_Arab-eng_Latn`, `acq_Arab-eng_Latn`, `aeb_Arab-eng_Latn`, `afr_Latn-eng_Latn`
  - lang_Scrp (FLORES-style): 204 — e.g. `ace_Arab`, `ace_Latn`, `acm_Arab`, `acq_Arab`, `aeb_Arab`, `afr_Latn`
  - xxx (ISO 639-3-like): 1 — e.g. `all`
- **full list:** `results/schema/flores200__configs.txt`
- **ERROR in viewer row counts:** `HTTPError: 404 Client Error: Not Found for url: https://datasets-server.huggingface.co/size?dataset=facebook%2Fflores`

### streamed slice: config `ace_Arab`

- **ERROR in stream ace_Arab:** `DatasetNotFoundError: Dataset 'facebook/flores' is a gated dataset on the Hub. Visit the dataset page at https://huggingface.co/datasets/facebook/flores to ask for access.` — accept the terms at https://huggingface.co/datasets/facebook/flores with the same HF account, then `huggingface-cli login` on the server

_(flores200: 2s, 2 error(s))_

## flores_plus — `openlanguagedata/flores_plus`

_maintained FLORES successor (gated); codes may differ from FLORES-200_

- **revision:** 5fec6c13f9e5a4db2f745d4ec0d7c9721ddc4f06
- **gated:** auto
- **files:** 485 files, 223.7 MB
- **bytes by extension:** .jsonl 223.5 MB, .md 0.2 MB, .bib 0.0 MB, .py 0.0 MB, .gitattributes 0.0 MB, DCO 0.0 MB
- **first files:** `.gitattributes`, `.gitignore`, `CHANGELOG.md`, `DCO`, `README.md`, `bibliography.bib`, `convert_parquet_to_jsonl.py`, `dataset_cards/apd_Arab.md`
- **configs:** 231 (from get_dataset_config_names)
- **first configs:** `default`, `ace_Arab`, `ace_Latn`, `acm_Arab`, `acq_Arab`, `aeb_Arab`, `afr_Latn`, `als_Latn`, `amh_Ethi`, `apc_Arab_nort3139`
- **last configs:** `yor_Latn`, `yue_Hant`, `zgh_Tfng`, `zsm_Latn`, `zul_Latn`
- **config-name formats:**
  - lang_Scrp (FLORES-style): 222 — e.g. `ace_Arab`, `ace_Latn`, `acm_Arab`, `acq_Arab`, `aeb_Arab`, `afr_Latn`
  - lang+subtags (BCP-47-like): 8 — e.g. `apc_Arab_nort3139`, `apc_Arab_sout3123`, `cat_Latn_vale1252`, `lld_Latn_gard1241`, `nob_Latn_radical`, `oci_Latn_aran1260`
  - word(s) / name: 1 — e.g. `default`
- **full list:** `results/schema/flores_plus__configs.txt`
- **viewer row counts:** partial=False; per split: dev=452,638, devtest=446,292
- **rows per config (min/q1/median/q3/max):** 997 / 2,009 / 2,009 / 2,009 / 449,971
- **full table:** `results/schema/flores_plus__viewer_rows.csv`

### streamed slice: config `default`

- **splits:** `dev`, `devtest`
- **sampled:** first 500 rows of `dev` (1.2s)

| column | declared feature | observed python types |
|---|---|---|
| `id` | Value(dtype='int64', id=None) | int×500 |
| `iso_639_3` | Value(dtype='string', id=None) | str×500 |
| `iso_15924` | Value(dtype='string', id=None) | str×500 |
| `glottocode` | Value(dtype='string', id=None) | str×500 |
| `variant` | Value(dtype='string', id=None) | str×500 |
| `text` | Value(dtype='string', id=None) | str×500 |
| `url` | Value(dtype='string', id=None) | str×500 |
| `domain` | Value(dtype='string', id=None) | str×500 |
| `topic` | Value(dtype='string', id=None) | str×500 |
| `has_image` | Value(dtype='string', id=None) | str×500 |
| `has_hyperlink` | Value(dtype='string', id=None) | str×500 |
| `last_updated` | Value(dtype='string', id=None) | str×500 |
| `split` | Value(dtype='string', id=None) | str×500 |

Example rows (strings truncated to 160 chars, lists to 4 items):
```
[0]
  id: 0
  iso_639_3: "ace"
  iso_15924: "Arab"
  glottocode: "achi1257"
  variant: ""
  text: "يق أورو سنين، اوق علمون دري فکولتس کدوکترن يونيۏرسيتس ستانفورد ݢڤعموم اکن جتومى الت دياݢنوستيک بارو ڽڠ جوت ݢڤيليه اتو سيل منوروت جنيهجيه: چيڤ اوبيت ڽڠ جوت ݢچيتق…(+87 chars)"
  url: "https://en.wikinews.org/wiki/Scientists_say_new_medical_diagnostic_chip_can_sort_cells_anywhere_with_an_inkjet"
  domain: "wikinews"
  topic: "health"
  has_image: "yes"
  has_hyperlink: "yes"
  last_updated: "1.0"
  split: "dev"
[1]
  id: 1
  iso_639_3: "ace"
  iso_15924: "Arab"
  glottocode: "achi1257"
  variant: ""
  text: "ڤنليتي اوتام خن اترا ڽو موڠکين محسى ديتيکسي فون کى کنکر، ت.ب.س.، ايچ.اي.ۏي. ڠون مالاريا کى ڤاسيان دي نڠرو ڽڠ ݢاسين، ڽڠ توه تيڠکت کى اودڤ کى ڤڽاکيت لاݢى کنکر بوه…(+38 chars)"
  url: "https://en.wikinews.org/wiki/Scientists_say_new_medical_diagnostic_chip_can_sort_cells_anywhere_with_an_inkjet"
  domain: "wikinews"
  topic: "health"
  has_image: "yes"
  has_hyperlink: "yes"
  last_updated: "1.0"
  split: "dev"
[2]
  id: 2
  iso_639_3: "ace"
  iso_15924: "Arab"
  glottocode: "achi1257"
  variant: ""
  text: "جاس ۳۹سي ݢريڤين مڤوق لندسن ڤاچو ليڠک ڤوه ۹:۳۰ بڠوه دي سينن (۰۲۳۰ يوتيسي) ڠوت برتويه، سمڤو ݢتوڤ بندرا کى تربڠ کومرسيال."
  url: "https://en.wikinews.org/wiki/Fighter_jet_crashes_during_Children%27s_Day_airshow_in_Thailand"
  domain: "wikinews"
  topic: "accident"
  has_image: "yes"
  has_hyperlink: "yes"
  last_updated: "1.0"
  split: "dev"
```

- **identifier-like column `iso_639_3`** — 1 distinct in 500 sampled rows; top: `ace`×500
  - xxx (ISO 639-3-like): 1 — e.g. `ace`
- **identifier-like column `iso_15924`** — 1 distinct in 500 sampled rows; top: `Arab`×500
  - word(s) / name: 1 — e.g. `Arab`
- **identifier-like column `glottocode`** — 1 distinct in 500 sampled rows; top: `achi1257`×500
  - word(s) / name: 1 — e.g. `achi1257`
- **identifier-like column `variant`** — 1 distinct in 500 sampled rows; top: ``×500
  - other: 1 — e.g. ``
- **identifier-like column `domain`** — 2 distinct in 500 sampled rows; top: `wikinews`×348, `wikibooks`×152
  - word(s) / name: 2 — e.g. `wikinews`, `wikibooks`
- **identifier-like column `has_image`** — 2 distinct in 500 sampled rows; top: `yes`×372, `no`×128
  - xxx (ISO 639-3-like): 1 — e.g. `yes`
  - xx (ISO 639-1-like): 1 — e.g. `no`
- **identifier-like column `has_hyperlink`** — 2 distinct in 500 sampled rows; top: `yes`×302, `no`×198
  - xxx (ISO 639-3-like): 1 — e.g. `yes`
  - xx (ISO 639-1-like): 1 — e.g. `no`
- **identifier-like column `last_updated`** — 1 distinct in 500 sampled rows; top: `1.0`×500
  - other: 1 — e.g. `1.0`
- **identifier-like column `split`** — 1 distinct in 500 sampled rows; top: `dev`×500
  - xxx (ISO 639-3-like): 1 — e.g. `dev`

### streamed slice: config `ace_Arab`

- **splits:** `dev`, `devtest`
- **sampled:** first 500 rows of `dev` (1.2s)

| column | declared feature | observed python types |
|---|---|---|
| `id` | Value(dtype='int64', id=None) | int×500 |
| `iso_639_3` | Value(dtype='string', id=None) | str×500 |
| `iso_15924` | Value(dtype='string', id=None) | str×500 |
| `glottocode` | Value(dtype='string', id=None) | str×500 |
| `variant` | Value(dtype='string', id=None) | str×500 |
| `text` | Value(dtype='string', id=None) | str×500 |
| `url` | Value(dtype='string', id=None) | str×500 |
| `domain` | Value(dtype='string', id=None) | str×500 |
| `topic` | Value(dtype='string', id=None) | str×500 |
| `has_image` | Value(dtype='string', id=None) | str×500 |
| `has_hyperlink` | Value(dtype='string', id=None) | str×500 |
| `last_updated` | Value(dtype='string', id=None) | str×500 |
| `split` | Value(dtype='string', id=None) | str×500 |

Example rows (strings truncated to 160 chars, lists to 4 items):
```
[0]
  id: 0
  iso_639_3: "ace"
  iso_15924: "Arab"
  glottocode: "achi1257"
  variant: ""
  text: "يق أورو سنين، اوق علمون دري فکولتس کدوکترن يونيۏرسيتس ستانفورد ݢڤعموم اکن جتومى الت دياݢنوستيک بارو ڽڠ جوت ݢڤيليه اتو سيل منوروت جنيهجيه: چيڤ اوبيت ڽڠ جوت ݢچيتق…(+87 chars)"
  url: "https://en.wikinews.org/wiki/Scientists_say_new_medical_diagnostic_chip_can_sort_cells_anywhere_with_an_inkjet"
  domain: "wikinews"
  topic: "health"
  has_image: "yes"
  has_hyperlink: "yes"
  last_updated: "1.0"
  split: "dev"
[1]
  id: 1
  iso_639_3: "ace"
  iso_15924: "Arab"
  glottocode: "achi1257"
  variant: ""
  text: "ڤنليتي اوتام خن اترا ڽو موڠکين محسى ديتيکسي فون کى کنکر، ت.ب.س.، ايچ.اي.ۏي. ڠون مالاريا کى ڤاسيان دي نڠرو ڽڠ ݢاسين، ڽڠ توه تيڠکت کى اودڤ کى ڤڽاکيت لاݢى کنکر بوه…(+38 chars)"
  url: "https://en.wikinews.org/wiki/Scientists_say_new_medical_diagnostic_chip_can_sort_cells_anywhere_with_an_inkjet"
  domain: "wikinews"
  topic: "health"
  has_image: "yes"
  has_hyperlink: "yes"
  last_updated: "1.0"
  split: "dev"
[2]
  id: 2
  iso_639_3: "ace"
  iso_15924: "Arab"
  glottocode: "achi1257"
  variant: ""
  text: "جاس ۳۹سي ݢريڤين مڤوق لندسن ڤاچو ليڠک ڤوه ۹:۳۰ بڠوه دي سينن (۰۲۳۰ يوتيسي) ڠوت برتويه، سمڤو ݢتوڤ بندرا کى تربڠ کومرسيال."
  url: "https://en.wikinews.org/wiki/Fighter_jet_crashes_during_Children%27s_Day_airshow_in_Thailand"
  domain: "wikinews"
  topic: "accident"
  has_image: "yes"
  has_hyperlink: "yes"
  last_updated: "1.0"
  split: "dev"
```

- **identifier-like column `iso_639_3`** — 1 distinct in 500 sampled rows; top: `ace`×500
  - xxx (ISO 639-3-like): 1 — e.g. `ace`
- **identifier-like column `iso_15924`** — 1 distinct in 500 sampled rows; top: `Arab`×500
  - word(s) / name: 1 — e.g. `Arab`
- **identifier-like column `glottocode`** — 1 distinct in 500 sampled rows; top: `achi1257`×500
  - word(s) / name: 1 — e.g. `achi1257`
- **identifier-like column `variant`** — 1 distinct in 500 sampled rows; top: ``×500
  - other: 1 — e.g. ``
- **identifier-like column `domain`** — 2 distinct in 500 sampled rows; top: `wikinews`×348, `wikibooks`×152
  - word(s) / name: 2 — e.g. `wikinews`, `wikibooks`
- **identifier-like column `has_image`** — 2 distinct in 500 sampled rows; top: `yes`×372, `no`×128
  - xxx (ISO 639-3-like): 1 — e.g. `yes`
  - xx (ISO 639-1-like): 1 — e.g. `no`
- **identifier-like column `has_hyperlink`** — 2 distinct in 500 sampled rows; top: `yes`×302, `no`×198
  - xxx (ISO 639-3-like): 1 — e.g. `yes`
  - xx (ISO 639-1-like): 1 — e.g. `no`
- **identifier-like column `last_updated`** — 1 distinct in 500 sampled rows; top: `1.0`×500
  - other: 1 — e.g. `1.0`
- **identifier-like column `split`** — 1 distinct in 500 sampled rows; top: `dev`×500
  - xxx (ISO 639-3-like): 1 — e.g. `dev`

_(flores_plus: 15s, 0 error(s))_

## belebele — `facebook/belebele`

_comprehension eval_

- **revision:** 7899cdfa4e1e0d733fd77c848e2c273cb1d32be2
- **gated:** False
- **files:** 127 files, 251.7 MB
- **bytes by extension:** .jsonl 224.6 MB, .zip 27.1 MB, .md 0.0 MB, .py 0.0 MB, .gitattributes 0.0 MB, data/README 0.0 MB
- **first files:** `.gitattributes`, `README.md`, `data.zip`, `data/README`, `data/acm_Arab.jsonl`, `data/afr_Latn.jsonl`, `data/als_Latn.jsonl`, `data/amh_Ethi.jsonl`
- **configs:** 122 (from get_dataset_config_names)
- **first configs:** `acm_Arab`, `arz_Arab`, `ceb_Latn`, `fin_Latn`, `hin_Deva`, `ita_Latn`, `khm_Khmr`, `lvs_Latn`, `npi_Deva`, `pol_Latn`
- **last configs:** `plt_Latn`, `slk_Latn`, `sun_Latn`, `tsn_Latn`, `wol_Latn`
- **config-name formats:**
  - lang_Scrp (FLORES-style): 122 — e.g. `acm_Arab`, `arz_Arab`, `ceb_Latn`, `fin_Latn`, `hin_Deva`, `ita_Latn`
- **full list:** `results/schema/belebele__configs.txt`
- **viewer row counts:** partial=False; per split: test=109,800
- **rows per config (min/q1/median/q3/max):** 900 / 900 / 900 / 900 / 900
- **full table:** `results/schema/belebele__viewer_rows.csv`

### streamed slice: config `acm_Arab`

- **splits:** `test`
- **sampled:** first 500 rows of `test` (1.5s)

| column | declared feature | observed python types |
|---|---|---|
| `link` | Value(dtype='string', id=None) | str×500 |
| `question_number` | Value(dtype='int64', id=None) | int×500 |
| `flores_passage` | Value(dtype='string', id=None) | str×500 |
| `question` | Value(dtype='string', id=None) | str×500 |
| `mc_answer1` | Value(dtype='string', id=None) | str×500 |
| `mc_answer2` | Value(dtype='string', id=None) | str×500 |
| `mc_answer3` | Value(dtype='string', id=None) | str×500 |
| `mc_answer4` | Value(dtype='string', id=None) | str×500 |
| `correct_answer_num` | Value(dtype='string', id=None) | str×500 |
| `dialect` | Value(dtype='string', id=None) | str×500 |
| `ds` | Value(dtype='timestamp[s]', id=None) | datetime×500 |

Example rows (strings truncated to 160 chars, lists to 4 items):
```
[0]
  link: "https://en.wikinews.org/wiki/La_La_Land_receives_record-equalling_fourteen_Oscar_nominations;_Hacksaw_Ridge_gets_six"
  question_number: 1
  flores_passage: "وحصل الفلم اللي شاركو بي رايان غوسلينغ وإيما ستون، ترشيحات بجميع الفئات الرئيسية. حصل جوسلينغ وستون ترشيحات لأفضل ممثل وممثلة على التوالي. تشمل الترشيحات الباقي…(+286 chars)"
  question: "أي جائزة ترشحت إلها أيما ستون؟"
  mc_answer1: "افضل ممثلة مساعدة"
  mc_answer2: "افضل مخرج"
  mc_answer3: "افضل ممثلة"
  mc_answer4: "افضل مونتاج"
  correct_answer_num: "3"
  dialect: "acm_Arab"
  ds: "2023-07-21 00:00:00"
[1]
  link: "https://en.wikinews.org/wiki/La_La_Land_receives_record-equalling_fourteen_Oscar_nominations;_Hacksaw_Ridge_gets_six"
  question_number: 2
  flores_passage: "وحصل الفلم اللي شاركو بي رايان غوسلينغ وإيما ستون، ترشيحات بجميع الفئات الرئيسية. حصل جوسلينغ وستون ترشيحات لأفضل ممثل وممثلة على التوالي. تشمل الترشيحات الباقي…(+286 chars)"
  question: "لأي جائزة ما تم ترشيح الفلم؟"
  mc_answer1: "افضل فلم"
  mc_answer2: "افضل تأثيرات بصرية"
  mc_answer3: "افضل فنيات صوتية"
  mc_answer4: "افضل أغنية أصلية"
  correct_answer_num: "2"
  dialect: "acm_Arab"
  ds: "2023-07-21 00:00:00"
[2]
  link: "https://en.wikinews.org/wiki/Large_earthquake_off_Japan,_tsunami_warning_issued"
  question_number: 1
  flores_passage: "أعلنت هيئة الإذاعة اليابانية أن محطة الكاشيوازاكي كاريوا للطاقة النووية بمحافظة نيكاتا  كانت تعمل بشكل طبيعي. ما بلغت شركة هوكوريكو للطاقة الكهربائية عن أي آثار…(+271 chars)"
  question: "أي من التالي استمر بالعمل بعد الزلزال؟"
  mc_answer1: "كل المفاعلات بمعمل هوكوريكو شيكا"
  mc_answer2: "المطار بايشيكاوا"
  mc_answer3: "كل خدمات السكك الحديدية"
  mc_answer4: "معمل طاقة في نيكاتا"
  correct_answer_num: "4"
  dialect: "acm_Arab"
  ds: "2023-07-21 00:00:00"
```

- **identifier-like column `correct_answer_num`** — 4 distinct in 500 sampled rows; top: `3`×147, `2`×140, `4`×112, `1`×101
  - other: 4 — e.g. `3`, `2`, `4`, `1`
- **identifier-like column `dialect`** — 1 distinct in 500 sampled rows; top: `acm_Arab`×500
  - lang_Scrp (FLORES-style): 1 — e.g. `acm_Arab`

_(belebele: 8s, 0 error(s))_

## tulu3_sft — `allenai/tulu-3-sft-mixture`

_English backbone / source pool for Step 2_

- **revision:** b14afda60f1bbebe55d5d2fa1e4df5042f97f8be
- **gated:** False
- **files:** 8 files, 1413.0 MB
- **bytes by extension:** .parquet 1413.0 MB, .md 0.0 MB, .gitattributes 0.0 MB
- **first files:** `.gitattributes`, `README.md`, `data/train-00000-of-00006.parquet`, `data/train-00001-of-00006.parquet`, `data/train-00002-of-00006.parquet`, `data/train-00003-of-00006.parquet`, `data/train-00004-of-00006.parquet`, `data/train-00005-of-00006.parquet`
- **configs:** 1 (from get_dataset_config_names)
- **first configs:** `default`
- **config-name formats:**
  - word(s) / name: 1 — e.g. `default`
- **full list:** `results/schema/tulu3_sft__configs.txt`
- **viewer row counts:** partial=False; per split: train=939,343
- **full table:** `results/schema/tulu3_sft__viewer_rows.csv`

### streamed slice: config `default`

- **splits:** `train`
- **sampled:** first 500 rows of `train` (8.8s)

| column | declared feature | observed python types |
|---|---|---|
| `id` | Value(dtype='string', id=None) | str×500 |
| `messages` | [{'content': Value(dtype='string', id=None), 'role': Value(dtype='string', id=None)}] | list×500 |
| `source` | Value(dtype='string', id=None) | str×500 |

Example rows (strings truncated to 160 chars, lists to 4 items):
```
[0]
  id: "oasst1_5921"
  messages: [{"content": "Create a snippet of Terraform HCL code that create an AWS autoscaling group, and an ALB in front to expose an application to internet.", "role": "user"}, {"content": "Sure, here's an example Terraform HCL code that creates an AWS Autoscaling Group and an Application Load Balancer to expose an application to the internet:\n``` …(+1944 chars)", "role": "assistant"}]
  source: "ai2-adapt-dev/oasst1_converted"
[1]
  id: "oasst1_1096"
  messages: [{"content": "¿Por qué crees que cada año es más difícil tener una casa propia en comparación a décadas anteriores?", "role": "user"}, {"content": "Existen varios factores que pueden contribuir a que cada año sea más difícil tener una casa propia en comparación con décadas anteriores. Algunos de los factore…(+1219 chars)", "role": "assistant"}]
  source: "ai2-adapt-dev/oasst1_converted"
[2]
  id: "oasst1_2492"
  messages: [{"content": "Cuál es equivalente a una bombilla de 100w en led", "role": "user"}, {"content": "La equivalencia entre una bombilla incandescente de 100 vatios y un LED depende de varios factores, como la eficiencia energética del LED y la cantidad de luz q…(+582 chars)", "role": "assistant"}]
  source: "ai2-adapt-dev/oasst1_converted"
```

- **identifier-like column `source`** — 1 distinct in 500 sampled rows; top: `ai2-adapt-dev/oasst1_converted`×500
  - word(s) / name: 1 — e.g. `ai2-adapt-dev/oasst1_converted`

### full local copy: `data/raw/tulu-3-sft-mixture`

- **parquet files:** 6; rows per split: train=939,343
- **arrow schema (first shard):**
```
id: string
messages: list<element: struct<content: string, role: string>>
source: string
```
- **`source`** (full scan): 19 distinct values → `results/schema/tulu3_sft__source__values.csv`
  - word(s) / name: 19 — e.g. `ai2-adapt-dev/personahub_math_v5_regen_149960`, `ai2-adapt-dev/evol_codealpaca_heval_decontaminated`, `ai2-adapt-dev/tulu_v3.9_aya_100k`, `ai2-adapt-dev/tulu_v3.9_wildchat_100k`, `ai2-adapt-dev/flan_v2_converted`, `ai2-adapt-dev/numinamath_tir_math_decontaminated`
  - top 10: `ai2-adapt-dev/personahub_math_v5_regen_149960`=149,960, `ai2-adapt-dev/evol_codealpaca_heval_decontaminated`=107,276, `ai2-adapt-dev/tulu_v3.9_wildchat_100k`=100,000, `ai2-adapt-dev/tulu_v3.9_aya_100k`=100,000, `ai2-adapt-dev/flan_v2_converted`=89,982, `ai2-adapt-dev/numinamath_tir_math_decontaminated`=64,312, `ai2-adapt-dev/tulu_v3.9_open_math_2_gsm8k_50k`=50,000, `ai2-adapt-dev/tulu_v3.9_wildjailbreak_decontaminated_50k`=50,000, `ai2-adapt-dev/tulu_v3.9_synthetic_finalresp_wildguardmixtrain_decontaminated_50k`=50,000, `allenai/tulu-3-sft-personas-math-grade`=49,980
  - bottom 5: `ai2-adapt-dev/tulu_v3.9_sciriff_10k`=10,000, `ai2-adapt-dev/no_robots_converted`=9,500, `ai2-adapt-dev/oasst1_converted`=7,131, `ai2-adapt-dev/tulu_v3.9_table_gpt_5k`=5,000, `ai2-adapt-dev/tulu_hard_coded_repeated_10`=240
- script profile skipped (language-id columns: none; long top-level text columns: none)

_(tulu3_sft: 16s, 0 error(s))_

## Summary

```
========================= SCHEMA INSPECTION SUMMARY =========================
muri_it                  ok
    configs: 1  [word(s) / name]
    id `dataset_name`: 6 distinct (full scan), word(s) / name 5/6
    id `language`: 201 distinct (full scan), xxx (ISO 639-3-like) 200/201
    id `language_name`: 201 distinct (full scan), word(s) / name 200/201
    id `split`: 3 distinct (full scan), word(s) / name
    rows (local parquet metadata): test=111,427, train=2,005,648, validation=111,424
muri_it_language_split   ok
    configs: 201  [xxx (ISO 639-3-like) 200/201]
    id `dataset_name`: 1 distinct in slice, XX/XXX (upper-case code)
    id `subdataset_name`: 1 distinct in slice, word(s) / name
    id `language`: 1 distinct in slice, xxx (ISO 639-3-like)
    id `split`: 1 distinct in slice, word(s) / name
    id `language_name`: 1 distinct in slice, word(s) / name
    rows (viewer API): test=111,427, train=2,005,648, validation=111,424
nllb200                  ok
    id `language codes`: 202 codes, lang_Scrp (FLORES-style)
flores200                2 ERROR(S)
    configs: 611  [lang_Scrp-lang_Scrp (pair) 406/611]
    ! viewer row counts: HTTPError: 404 Client Error: Not Found for url: https://datasets-server.huggingface.co/size
    ! stream ace_Arab: DatasetNotFoundError: Dataset 'facebook/flores' is a gated dataset on the Hub. Visit the data
flores_plus              ok
    configs: 231  [lang_Scrp (FLORES-style) 222/231]
    id `iso_639_3`: 1 distinct in slice, xxx (ISO 639-3-like)
    id `iso_15924`: 1 distinct in slice, word(s) / name
    id `glottocode`: 1 distinct in slice, word(s) / name
    id `variant`: 1 distinct in slice, other
    id `domain`: 2 distinct in slice, word(s) / name
    id `has_image`: 2 distinct in slice, xxx (ISO 639-3-like) 1/2
    id `has_hyperlink`: 2 distinct in slice, xxx (ISO 639-3-like) 1/2
    id `last_updated`: 1 distinct in slice, other
    id `split`: 1 distinct in slice, xxx (ISO 639-3-like)
    rows (viewer API): dev=452,638, devtest=446,292
belebele                 ok
    configs: 122  [lang_Scrp (FLORES-style)]
    id `correct_answer_num`: 4 distinct in slice, other
    id `dialect`: 1 distinct in slice, lang_Scrp (FLORES-style)
    rows (viewer API): test=109,800
tulu3_sft                ok
    configs: 1  [word(s) / name]
    id `source`: 19 distinct (full scan), word(s) / name
    rows (local parquet metadata): train=939,343
=============================================================================
```
