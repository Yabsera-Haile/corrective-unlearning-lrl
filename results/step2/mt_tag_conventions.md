# MT language-tag conventions (Step 2B prerequisite)

Read from each model's own tokenizer files; nothing about the tag format is assumed.
Target languages from `configs/languages.yaml`: ben_Beng, swh_Latn, amh_Ethi, tel_Telu

## MADLAD-400 — `google/madlad400-3b-mt` (instruction side)

- revision: `fa184c675da0b5c9e1c8694fccd4e12e2d422094`
- architecture: ['T5ForConditionalGeneration'], d_model=1024, layers=32, vocab_size=256000, dtype=None
- generation_config: {"_from_model_config": true, "decoder_start_token_id": 0, "eos_token_id": 2, "pad_token_id": 1, "transformers_version": "4.35.0"}
- tokenizer_config keys: ['added_tokens_decoder', 'additional_special_tokens', 'clean_up_tokenization_spaces', 'eos_token', 'extra_ids', 'legacy', 'model_max_length', 'pad_token', 'sp_model_kwargs', 'tokenizer_class', 'unk_token']
- added_tokens.json: {}
- **language tags in the vocabulary: 492** matching `<2xx>`; first 12: `<2Arab>`, `<2Armn>`, `<2Beng>`, `<2CA>`, `<2Cans>`, `<2Cher>`, `<2Cyrl>`, `<2Deva>`, `<2Ethi>`, `<2Geor>`, `<2Grek>`, `<2Gujr>`
- tag body lengths: {4: 30, 2: 168, 3: 256, 8: 10, 5: 2, 15: 2, 7: 16, 12: 1, 10: 1, 11: 1, 6: 3, 9: 1, 13: 1} (2 = ISO 639-1-style, 3 = ISO 639-3-style, more = with script)

Resolved for this project's targets (candidates searched, not assumed):

| language | ISO 639-3 | candidates present in vocab | chosen tag | token id |
|---|---|---|---|---|
| Bengali (`ben_Beng`) | ben | `<2bn>` | `<2bn>` | 23 |
| Swahili (`swh_Latn`) | swh | `<2sw>` | `<2sw>` | 134 |
| Amharic (`amh_Ethi`) | amh | `<2am>` | `<2am>` | 7 |
| Telugu (`tel_Telu`) | tel | `<2te>` | `<2te>` | 139 |

Usage implied by the tokenizer: MADLAD is a T5-style model whose *source text* is prefixed with the target-language tag, e.g. `<2sw> Hello world`. No forced BOS token.

## NLLB-200 — `facebook/nllb-200-distilled-600M` (response side)

- revision: `f8d333a098d19b4fd9a8b18f94170487ad3f821d`
- `added_tokens.json`: not available (EntryNotFoundError)
- architecture: ['M2M100ForConditionalGeneration'], d_model=1024, encoder_layers=12, vocab_size=256206, max_length=200, dtype=float32
- generation_config: {"_from_model_config": true, "bos_token_id": 0, "decoder_start_token_id": 2, "eos_token_id": 2, "max_length": 200, "pad_token_id": 1, "transformers_version": "4.27.0.dev0"}
- tokenizer_config: src_lang=None, tgt_lang=None, keys=['additional_special_tokens', 'bos_token', 'cls_token', 'eos_token', 'mask_token', 'model_max_length', 'name_or_path', 'pad_token', 'sep_token', 'sp_model_kwargs', 'special_tokens_map_file', 'src_lang', 'tgt_lang', 'tokenizer_class', 'unk_token']
- special_tokens_map additional_special_tokens: 202 FLORES-style codes
- **language codes in the vocabulary: 202**; first 8: `ace_Arab`, `ace_Latn`, `acm_Arab`, `acq_Arab`, `aeb_Arab`, `afr_Latn`, `ajp_Arab`, `aka_Latn`

| language | code | in vocab | token id (forced_bos_token_id) |
|---|---|---|---|
| Bengali | `ben_Beng` | yes | 256026 |
| Swahili | `swh_Latn` | yes | 256168 |
| Amharic | `amh_Ethi` | yes | 256009 |
| Telugu | `tel_Telu` | yes | 256172 |

Usage implied by the tokenizer: NLLB sets the *source* language on the tokenizer (`src_lang`) and forces the target code as the first generated token (`forced_bos_token_id`). The tag is not prefixed to the source text.
