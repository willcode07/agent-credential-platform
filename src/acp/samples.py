"""Fixed launch-market credentials used by the demo and the MCP server.

The withheld strings are deliberate canaries. A match report or an A2A
artifact that contains one of them has leaked a claim the holder did not
reveal.
"""

from acp.credentials.models import VerifiableCredential
from acp.credentials.store import CredentialStore
from acp.matching.profiles import Opening, SchoolProfile, SchoolProgram

STATE_BOARD = "did:example:state-board"
NORTH_HIGH_DID = "did:example:north-high"

TEACHER_ADA = "did:example:teacher-ada"
TEACHER_BEN = "did:example:teacher-ben"
STUDENT_PRIYA = "did:example:student-priya"
STUDENT_LEO = "did:example:student-leo"

# Canaries. These stay inside credentials and must not reach the matcher output.
ADA_HOME_ADDRESS = "742 Evergreen Terrace"
ADA_DATE_OF_BIRTH = "1985-04-12"
BEN_HOME_ADDRESS = "18 Baker Street"
PRIYA_STUDENT_NUMBER = "S-9912"
PRIYA_DATE_OF_BIRTH = "2010-09-01"
LEO_STUDENT_NUMBER = "S-1044"

WITHHELD_VALUES = (
    ADA_HOME_ADDRESS,
    ADA_DATE_OF_BIRTH,
    BEN_HOME_ADDRESS,
    PRIYA_STUDENT_NUMBER,
    PRIYA_DATE_OF_BIRTH,
    LEO_STUDENT_NUMBER,
)

TEACHER_REVEAL = [
    "preferred_name",
    "subjects",
    "grade_min",
    "grade_max",
    "mode",
    "location",
    "license_status",
]
STUDENT_REVEAL = [
    "preferred_name",
    "grade_level",
    "interests",
    "mode",
    "location",
]


def teaching_license(
    credential_id: str,
    holder: str,
    *,
    preferred_name: str,
    license_status: str,
    home_address: str,
    date_of_birth: str,
) -> VerifiableCredential:
    return VerifiableCredential(
        id=credential_id,
        type=["VerifiableCredential", "TeachingLicense"],
        issuer=STATE_BOARD,
        valid_from="2026-01-15T00:00:00Z",
        credential_subject={
            "id": holder,
            "preferred_name": preferred_name,
            "subjects": ["Mathematics"],
            "grade_min": 9,
            "grade_max": 12,
            "mode": "in_person",
            "location": "Springfield",
            "license_status": license_status,
            "home_address": home_address,
            "date_of_birth": date_of_birth,
        },
    )


def enrollment(
    credential_id: str,
    holder: str,
    *,
    preferred_name: str,
    grade_level: int,
    interests: list[str],
    student_number: str,
    date_of_birth: str,
) -> VerifiableCredential:
    return VerifiableCredential(
        id=credential_id,
        type=["VerifiableCredential", "StudentEnrollment"],
        issuer=NORTH_HIGH_DID,
        valid_from="2026-08-01T00:00:00Z",
        credential_subject={
            "id": holder,
            "preferred_name": preferred_name,
            "grade_level": grade_level,
            "interests": interests,
            "mode": "in_person",
            "location": "Springfield",
            "student_number": student_number,
            "date_of_birth": date_of_birth,
        },
    )


def launch_credentials() -> list[VerifiableCredential]:
    return [
        teaching_license(
            "vc-license-ada",
            TEACHER_ADA,
            preferred_name="Ada Okonkwo",
            license_status="active",
            home_address=ADA_HOME_ADDRESS,
            date_of_birth=ADA_DATE_OF_BIRTH,
        ),
        teaching_license(
            "vc-license-ben",
            TEACHER_BEN,
            preferred_name="Ben Cho",
            license_status="expired",
            home_address=BEN_HOME_ADDRESS,
            date_of_birth="1979-11-02",
        ),
        enrollment(
            "vc-enrollment-priya",
            STUDENT_PRIYA,
            preferred_name="Priya Shah",
            grade_level=10,
            interests=["Mathematics", "Robotics"],
            student_number=PRIYA_STUDENT_NUMBER,
            date_of_birth=PRIYA_DATE_OF_BIRTH,
        ),
        enrollment(
            "vc-enrollment-leo",
            STUDENT_LEO,
            preferred_name="Leo Martins",
            grade_level=4,
            interests=["Mathematics"],
            student_number=LEO_STUDENT_NUMBER,
            date_of_birth="2016-02-20",
        ),
    ]


def launch_store() -> CredentialStore:
    store = CredentialStore()
    for credential in launch_credentials():
        store.put(credential)
    return store


def north_high() -> SchoolProfile:
    math = dict(
        subject="Mathematics",
        grade_min=9,
        grade_max=12,
        mode="in_person",
        location="Springfield",
    )
    return SchoolProfile(
        id="school-north-high",
        name="North High",
        location="Springfield",
        openings=[Opening(id="math-9-12", requires_license=True, **math)],
        programs=[SchoolProgram(id="math-9-12", **math)],
    )
