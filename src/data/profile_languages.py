"""Step 1.4 — profile candidate languages (LOCAL to write, SERVER to run).

Not written yet, by design: the spec requires the profiling logic to be written
against the schema observed by inspect_schema.py (Step 1.2), not an assumed one.
Run `bash scripts/server/02_profile_languages.sh --inspect-only` on the server,
push results/, then this module is written on LOCAL.
"""

from __future__ import annotations

import sys


def main() -> int:
    print("profile_languages: not implemented yet — waiting on Step 1.2 schema inspection output.\n"
          "Run: bash scripts/server/02_profile_languages.sh --inspect-only", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
