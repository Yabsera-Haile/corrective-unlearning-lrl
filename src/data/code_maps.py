"""Language code normalisation (Step 1.3, LOCAL).

Canonical form: FLORES-200 style `lang_Scrp` (ISO 639-3 language + ISO 15924
script, e.g. `amh_Ethi`). NLLB, FLORES and Belebele all derive from that family;
the other sources are mapped into it.

The mapping tables are deliberately NOT written yet. They are written against the
identifier lists that inspect_schema.py dumps to results/schema/ on the server,
not against assumed formats. Until then this module only knows the canonical
format itself.
"""

from __future__ import annotations

import re

FLORES_CODE_RE = re.compile(r"^(?P<lang>[a-z]{3})_(?P<script>[A-Z][a-z]{3})$")


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


if __name__ == "__main__":
    import doctest

    failures, _ = doctest.testmod()
    raise SystemExit(1 if failures else print("code_maps doctests passed"))
