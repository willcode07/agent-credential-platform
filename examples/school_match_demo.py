"""End-to-end education example.

The platform core matches ``Candidate`` profiles to ``Opportunity``
requirements. This script is one vertical on top of that core:

1. A state board (issuer) writes teaching-license credentials and a school
   writes enrollment credentials. Both include claims the matcher must not
   see (home address, date of birth, student number).
2. Each holder builds a mock selective disclosure. A verifier checks the
   issuer and the shape of the proof.
3. Revealed claims are mapped to generic candidates. Grade band and
   placement are derived here, not inside the matcher.
4. North High's opening and program are opportunities: lists of claim
   requirements. The generic matcher ranks the candidates.
5. The summary is stored as a completed A2A task. Withheld claims stay out
   of the artifact.

Run from a checkout, after ``pip install -e ".[dev]"``::

    python examples/school_match_demo.py
    acp demo
"""

from acp.demo import run_demo


def main() -> int:
    print(run_demo().text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
