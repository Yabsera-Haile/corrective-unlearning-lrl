"""Language code normalisation.

Datasets disagree on language codes: ISO 639-1 ("sw"), ISO 639-3 ("swa"/"swh"),
FLORES-200 style ("swh_Latn"), BCP-47 ("sw-KE"). Everything in this repo is keyed
on a single canonical form: ISO 639-3 lowercase, optionally with a script
suffix kept separately.

The alias table below is deliberately small; extend it in Step 1 as new
datasets are inspected rather than guessing mappings up front.
"""

from __future__ import annotations

import re

# ISO 639-1 -> ISO 639-3. Extend as needed.
ISO1_TO_ISO3: dict[str, str] = {
    "af": "afr", "am": "amh", "ar": "ara", "bn": "ben", "en": "eng",
    "fr": "fra", "ha": "hau", "hi": "hin", "ig": "ibo", "ne": "npi",
    "si": "sin", "so": "som", "sw": "swa", "ta": "tam", "te": "tel",
    "ti": "tir", "ur": "urd", "xh": "xho", "yo": "yor", "zu": "zul",
}

# Individual-language / macrolanguage aliases that should collapse together.
# Key: code seen in the wild, value: canonical code. Extend as needed.
ALIASES: dict[str, str] = {
    "swh": "swa",
}

_CODE_RE = re.compile(r"^([A-Za-z]{2,3})(?:[_-]([A-Za-z]{4}))?(?:[_-]([A-Za-z]{2}|\d{3}))?$")


def split_code(code: str) -> tuple[str, str | None]:
    """Split a raw code into (language, script). Region subtags are dropped.

    >>> split_code("swh_Latn")
    ('swh', 'Latn')
    >>> split_code("sw-KE")
    ('sw', None)
    """
    m = _CODE_RE.match(code.strip())
    if not m:
        raise ValueError(f"Unrecognised language code: {code!r}")
    lang, script, _region = m.groups()
    return lang.lower(), script.title() if script else None


def normalise(code: str) -> str:
    """Return the canonical ISO 639-3 code for any supported input form.

    >>> normalise("sw"), normalise("swh_Latn"), normalise("SWA")
    ('swa', 'swa', 'swa')
    """
    lang, _script = split_code(code)
    if len(lang) == 2:
        if lang not in ISO1_TO_ISO3:
            raise KeyError(f"No ISO 639-3 mapping for {lang!r}; add it to ISO1_TO_ISO3")
        lang = ISO1_TO_ISO3[lang]
    return ALIASES.get(lang, lang)


if __name__ == "__main__":
    import doctest

    doctest.testmod(verbose=False)
    print("code_maps doctests passed")
