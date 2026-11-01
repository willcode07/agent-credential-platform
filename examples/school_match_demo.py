"""End-to-end launch-market demo.

Same walkthrough as ``acp demo``:

1. A state board issues teaching-license credentials and a school issues
   enrollment credentials. Both include claims the matcher must not see
   (home address, date of birth, student number).
2. Each holder builds a mock selective-disclosure proof and a verifier
   checks the issuer and the shape of the proof.
3. Teacher and student profiles are built only from the revealed claims.
4. A rule matcher ranks them for North High's mathematics opening.
5. The summary is stored as a completed A2A task. The artifact repeats the
   summary and not the withheld claims.

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
