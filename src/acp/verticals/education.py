"""Education worked example.

Schools, teachers, and students are mapped onto ``Candidate`` and
``Opportunity``. Grade bands, licenses, and classrooms are claim names in
this file. The matcher never sees those words.

# Claim names such as ``grade_band`` and ``license_status`` belong to this
# pack. Other markets pick their own names in their own rule pack.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from acp.credentials.did import DIDDocument, MockDIDResolver
from acp.credentials.models import VerifiableCredential
from acp.credentials.store import CredentialStore
from acp.credentials.zkp import SelectiveDisclosureProver, SelectiveDisclosureVerifier
from acp.matching.matcher import match_candidates
from acp.matching.profiles import Candidate, Match, Opportunity
from acp.protocols.a2a.tasks import TaskService
from acp.protocols.anp.adapter import ANPAdapter
from acp.protocols.mcp.server import MCPAdapter
from acp.rules.pack import RulePack, load_rule_pack

STATE_BOARD = "did:example:state-board"
NORTH_HIGH_DID = "did:example:north-high"

TEACHER_ADA = "did:example:teacher-ada"
TEACHER_BEN = "did:example:teacher-ben"
STUDENT_PRIYA = "did:example:student-priya"
STUDENT_LEO = "did:example:student-leo"

# Canaries. These stay inside credentials and must not reach matcher output.
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


def education_credentials() -> list[VerifiableCredential]:
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


def education_pack() -> RulePack:
    """The education market. Requirements and trusted issuers live in JSON."""
    return load_rule_pack(Path(__file__).with_name("education.rules.json"))


def education_store() -> CredentialStore:
    pack = education_pack()
    store = CredentialStore()
    for credential in education_credentials():
        store.put(
            credential,
            tenant_id=pack.tenant_id,
            rule_pack_id=pack.id,
            retention_days=pack.retention_days,
        )
    return store


def math_teacher_opening() -> Opportunity:
    """North High's staffing need, loaded from the education rule pack."""
    return education_pack().opportunity("math-teacher-9-12")


def math_student_program() -> Opportunity:
    """North High's student program, loaded from the education rule pack."""
    return education_pack().opportunity("math-program-9-12")


def credential_type_name(credential: VerifiableCredential) -> str:
    for name in credential.type:
        if name != "VerifiableCredential":
            return name
    raise ValueError(f"{credential.id} has no credential type")


def candidate_from_revealed(profile_id: str, revealed: dict) -> Candidate:
    """Copy revealed claims and add the derived fields this vertical matches on.

    ``grade_band`` and ``placement`` are computed here so the core matcher
    stays a list of claim checks. Hidden claims are absent because they were
    never in ``revealed``.
    """
    claims = dict(revealed)
    if "grade_min" in claims and "grade_max" in claims:
        claims["grade_band"] = [int(claims["grade_min"]), int(claims["grade_max"])]
    if "mode" in claims and "location" in claims:
        claims["placement"] = _placement(str(claims["mode"]), str(claims["location"]))
    display_name = str(claims.get("preferred_name", profile_id))
    return Candidate(id=profile_id, display_name=display_name, claims=claims)


def _require_trusted(verifier, credential, proof, pack: RulePack) -> None:
    trusted = set(pack.trusted_issuers(credential_type_name(credential)))
    result = verifier.verify(proof, trusted_issuers=trusted)
    if not result.ok:
        raise RuntimeError(result.reason)


def _placement(mode: str, location: str) -> str:
    """Fold mode and location into one claim the generic matcher can compare.

    Hybrid matches any opportunity that lists ``anywhere``. Remote matches
    remote. In person matches only the same place.
    """
    if mode == "hybrid":
        return "anywhere"
    if mode == "remote":
        return "remote"
    return f"in_person:{location.casefold()}"


@dataclass(frozen=True)
class DemoReport:
    """Printed story for the education example, plus the task it recorded."""

    text: str
    task: dict
    teacher_matches: list[Match]
    student_matches: list[Match]
    withheld_values: tuple[str, ...]


def run_demo() -> DemoReport:
    """Disclose, map onto generic types, match, and record an A2A task."""
    pack = education_pack()
    credentials = {item.id: item for item in education_credentials()}
    prover = SelectiveDisclosureProver()
    verifier = SelectiveDisclosureVerifier()

    resolver = MockDIDResolver()
    resolver.register(
        DIDDocument(id=STATE_BOARD, service=[{"type": "Issuer", "endpoint": "local"}])
    )
    resolver.resolve(STATE_BOARD)

    teachers: list[Candidate] = []
    for credential_id, profile_id in (
        ("vc-license-ada", "teacher-ada"),
        ("vc-license-ben", "teacher-ben"),
    ):
        proof = prover.prove(credentials[credential_id], TEACHER_REVEAL)
        _require_trusted(verifier, credentials[credential_id], proof, pack)
        teachers.append(candidate_from_revealed(profile_id, proof.revealed))

    students: list[Candidate] = []
    for credential_id, profile_id in (
        ("vc-enrollment-priya", "student-priya"),
        ("vc-enrollment-leo", "student-leo"),
    ):
        proof = prover.prove(credentials[credential_id], STUDENT_REVEAL)
        _require_trusted(verifier, credentials[credential_id], proof, pack)
        students.append(candidate_from_revealed(profile_id, proof.revealed))

    opening = math_teacher_opening()
    program = math_student_program()
    teacher_matches = match_candidates(opening, teachers)
    student_matches = match_candidates(program, students)
    text = _render(
        "North High",
        opening,
        program,
        teachers,
        students,
        teacher_matches,
        student_matches,
    )

    task_response = TaskService(
        tenant_id=pack.tenant_id,
        rule_pack_id=pack.id,
    ).send_message(
        {
            "message": {
                "messageId": "msg-demo-match",
                "role": "ROLE_USER",
                "parts": [{"text": text}],
            }
        }
    )
    task = task_response["task"]
    anp = ANPAdapter().project_did(STATE_BOARD)
    channels = ", ".join(
        adapter.describe()["name"] for adapter in (MCPAdapter(), ANPAdapter())
    )
    text = (
        f"{text}\n"
        f"A2A task {task['id']} is {task['status']['state']}.\n"
        f"Adapters described in this process: a2a, {channels}.\n"
        f"ANP projection for {anp['did']}: {anp['status']}.\n"
    )
    return DemoReport(
        text=text,
        task=task,
        teacher_matches=teacher_matches,
        student_matches=student_matches,
        withheld_values=WITHHELD_VALUES,
    )


def _render(
    counterparty: str,
    opening: Opportunity,
    program: Opportunity,
    teachers: list[Candidate],
    students: list[Candidate],
    teacher_matches: list[Match],
    student_matches: list[Match],
) -> str:
    lines = [
        "Agent Credential Platform — education example",
        "Teachers and students are candidates. Openings are opportunities.",
        f"Counterparty: {counterparty}",
        "Profiles were built from revealed claims only.",
        "",
        f"Candidates for {opening.name}:",
    ]
    lines.extend(_lines_for(teachers, teacher_matches))
    lines.append("")
    lines.append(f"Candidates for {program.name}:")
    lines.extend(_lines_for(students, student_matches))
    lines.append("")
    return "\n".join(lines)


def _lines_for(candidates: list[Candidate], matches: list[Match]) -> list[str]:
    names = {candidate.id: candidate.display_name for candidate in candidates}
    matched = {match.candidate_id for match in matches}
    lines: list[str] = []
    for match in matches:
        reason = "; ".join(match.reasons)
        name = names[match.candidate_id]
        lines.append(f"- {name} ({match.candidate_id}) score {match.score}: {reason}")
    for candidate in candidates:
        if candidate.id not in matched:
            lines.append(f"- {candidate.display_name} ({candidate.id}) not matched")
    return lines


def report_blob(report: DemoReport) -> str:
    """Text plus the task JSON, for leak checks."""
    return report.text + json.dumps(report.task)
