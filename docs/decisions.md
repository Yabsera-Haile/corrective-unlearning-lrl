# Design decisions

The method section is written from this file. Each entry states the decision, why it was
taken, and what it commits us to. Numbers cite the results file they came from.

---

## Step 1 — language selection (settled 2026-09-21)

### D1.1 Canonical language codes are FLORES-200 `lang_Scrp`
MURI-IT labels languages with bare ISO 639-3 codes and no script; NLLB-200, FLORES-200 and
Belebele all use `lang_Scrp`. Mapping runs MURI → FLORES-200 by direct match, ISO 639-3
macrolanguage membership (SIL table, committed in `configs/reference/`), and choice of script
from the dominant Unicode script of the MURI text.

**Consequence:** 2 of 200 MURI languages are unmapped and named (`hbs`, `kur`, both genuinely
ambiguous), 1 excluded as not a language (`code`). Every outcome is logged in
`results/code_mapping_log.csv`; nothing is dropped silently.

### D1.2 Candidate pool = MURI ∩ NLLB-200 ∩ FLORES-200 ∩ Belebele
**Result:** 103 languages. Attrition 201 → 200 → 197 → 150 → 150 → 103
(`results/language_profile_summary.md`). Belebele is the binding intersection; NLLB-200 and
FLORES-200 cover the same languages, so neither constrains beyond the other.

### D1.3 Clean pools come from MURI-IT's MRI subset only
MURI-IT bundles its own reverse-instruction data (`MRI`) with xP3, SuperNaturalInstructions,
WikiHow, flan_v2_tulu and OpenAssistant. Only MRI is in-language instruction data with a
human-written response; the others contribute short classification targets and, for some
languages, English instructions.

**Rationale:** ranking on total volume is actively misleading. Yoruba has 5,911 deduplicated
examples but 145 MRI; Tagalog has 1,443 and 0. Selecting on total volume would have put
languages into the study with 10-40x less usable clean data than they appeared to have.

**Consequence:** per-language clean volume is capped at 15,000 (MURI's own per-language cap).
MURI deduplicates per language rather than per subset, so the exact MRI-unique count is
bracketed by `mri_clean_lo`/`mri_clean_hi` in `results/language_candidates.csv`; all sizing
uses the conservative `lo`.

### D1.4 Volume threshold 5,000; four languages selected
Chosen from the 500/1,000/2,000/5,000 sensitivity table: 84 of 103 pool languages pass at
5,000, so the threshold is not what constrains the design. Selected `ben_Beng` (Joshi 3),
`swh_Latn` (2), `amh_Ethi` (2), `tel_Telu` (1): four distinct scripts, one Latin, three
non-Latin, three resource levels. Sizes are identical across languages (7,000 C-train +
7,000 C-repair) so pool size is never confounded with resource level. Rejected candidates and
reasons are recorded in `configs/languages.yaml`.

---

## Step 2 — contamination and mixtures (settled 2026-09-21)

### D2.1 MURI provenance: the manipulated variable is the response
MURI builds each example by translating a human-written document into English with
**MADLAD-400-3B-MT**, generating an English instruction with **Mixtral-8x7B**, translating that
instruction back with **MADLAD-400-3B-MT**, and filtering with **GlotLID**. NLLB is not involved.

**Consequence:** in the clean pools the *instruction* is already machine-translated and the
*response* is human-written. The variable this project manipulates is therefore the response:
human-written versus machine-translated. Any claim about "MT contamination" in this work is a
claim about response-side MT.

### D2.2 Contamination is genre-matched
Contaminated examples are built from English data produced by the same reverse-instructions
method as MURI (MURI-IT English MRI, and LongForm's C4/Wikipedia subsets), not from Tülu chat
data.

**Rationale:** clean data is web/Wikipedia documents; Tülu is chat-assistant answers. Drawing
contamination from Tülu would make clean and contaminated differ in genre as well as in MT-ness,
and any measured damage could be a genre effect rather than a translation effect.

### D2.3 The instruction side is held constant
Contaminated instructions are translated with **MADLAD-400-3B-MT** — the same system MURI used —
and only the responses are translated with **NLLB-200-distilled-600M**.

**Consequence:** the single systematic difference between a clean and a contaminated example is
whether the response is human-written or NLLB output. Instruction-side MT artefacts are present
in both conditions and therefore cannot explain a difference between them.

### D2.4 Contamination is additive, not substitutive
Every mixture keeps all 7,000 clean C-train examples per language; contaminated examples are
added on top. With r = n_contam / (7,000 + n_contam): **n_contam = 778 (r=10%), 2,333 (r=25%),
7,000 (r=50%)**. The sets are nested: r10 ⊂ r25 ⊂ r50.

**Trade-off, accepted:** total training size grows with r, so mixtures are not size-matched.
The alternative — replacing clean examples with contaminated ones — would confound damage from
contamination with damage from losing clean data, which is the worse confound for this question.

### D2.5 Dev sets are held out entirely from training
Each language gets **495 clean MRI** examples (Swahili's spare count after 7,000+7,000, applied
equally to all four) plus **495 matched contaminated** examples, disjoint from C-train and
C-repair. Used for detector validation and as open-ended generation prompts; never trained on.

### D2.6 A fixed English backbone, identical across mixtures
A fixed sample of Tülu 3 English SFT data (default 10,000, configurable), identical in every
mixture, excluding `tulu_v3.9_aya_100k`, keeping `oasst1` only where GlotLID confirms English,
stratified by source, and **disjoint from every English example used as a contamination source**.
Code and math sources are kept, because English collateral metrics (GSM8K and similar) need them.

**Rationale:** holding the backbone fixed means differences between mixtures come from the
contamination, not from backbone resampling. The disjointness rule prevents an English
contamination source from also appearing, untranslated, in the backbone.

### D2.7 One fixed chat template everywhere
Base models have no chat template, so `src/data/template.py` defines one and both training and
evaluation use it. Loss is computed on assistant tokens only.

```
<|user|>
{instruction}
<|assistant|>
{response}{eos}
```

### D2.8 Contaminated examples must pass the same language filter as clean ones
Contaminated responses must be identified as the target language by GlotLID, the filter MURI
itself applied.

**Rationale:** real web MT that reaches training corpora has typically passed a language-ID
filter. Keeping the filter makes the contamination realistic rather than trivially detectable
as off-target text. The per-language rejection rate is reported and is itself a finding about
NLLB quality at this resource level.

### D2.9 Contaminated responses are length-matched to clean responses
Final contaminated examples are selected by stratified sampling over length bins so that the
character-length distribution matches the clean C-train distribution per language; quantiles are
reported before and after.

**Rationale:** twice load-bearing. It stops response length from being a shortcut feature for
the detector, and it stops the model from learning "contaminated examples are shorter/longer"
rather than anything about translationese. Sequence-length drops (over `max_seq_len`) are
applied at equal rates to clean and contaminated so the matching survives.
