"""End-to-end school matching walkthrough used by ``acp demo``."""

import json
from dataclasses import dataclass

from acp.credentials.did import DIDDocument, MockDIDResolver
from acp.credentials.zkp import SelectiveDisclosureProver, SelectiveDisclosureVerifier
from acp.matching.matcher import match_students, match_teachers
from acp.matching.profiles import StudentProfile, TeacherProfile
from acp.protocols.a2a.tasks import TaskService
from acp.protocols.anp.adapter import ANPAdapter
from acp.protocols.mcp.server import MCPAdapter
from acp.samples import (
    NORTH_HIGH_DID,
    STATE_BOARD,
    STUDENT_REVEAL,
    TEACHER_REVEAL,
    WITHHELD_VALUES,
    launch_credentials,
    north_high,
)


@dataclass(frozen=True)
class DemoReport:
    """What the demo concluded, plus the text it prints."""

    text: str
    task: dict
    teacher_matches: list
    student_matches: list
    withheld_values: tuple[str, ...]


def run_demo() -> DemoReport:
    """Disclose, match, and record an A2A task. Hidden claims stay off the artifact."""
    school = north_high()
    credentials = {item.id: item for item in launch_credentials()}
    prover = SelectiveDisclosureProver()
    verifier = SelectiveDisclosureVerifier()
    trusted = {STATE_BOARD, NORTH_HIGH_DID}

    resolver = MockDIDResolver()
    resolver.register(
        DIDDocument(id=STATE_BOARD, service=[{"type": "Issuer", "endpoint": "local"}])
    )
    resolver.resolve(STATE_BOARD)

    teachers: list[TeacherProfile] = []
    for credential_id, profile_id in (
        ("vc-license-ada", "teacher-ada"),
        ("vc-license-ben", "teacher-ben"),
    ):
        proof = prover.prove(credentials[credential_id], TEACHER_REVEAL)
        result = verifier.verify(proof, trusted_issuers=trusted)
        if not result.ok:
            raise RuntimeError(result.reason)
        teachers.append(_teacher_from_revealed(profile_id, proof.revealed))

    students: list[StudentProfile] = []
    for credential_id, profile_id in (
        ("vc-enrollment-priya", "student-priya"),
        ("vc-enrollment-leo", "student-leo"),
    ):
        proof = prover.prove(credentials[credential_id], STUDENT_REVEAL)
        result = verifier.verify(proof, trusted_issuers=trusted)
        if not result.ok:
            raise RuntimeError(result.reason)
        students.append(_student_from_revealed(profile_id, proof.revealed))

    opening = school.openings[0]
    program = school.programs[0]
    teacher_matches = match_teachers(opening, teachers)
    student_matches = match_students(program, students)
    text = _render(school.name, opening.id, teachers, students, teacher_matches, student_matches)

    task_response = TaskService().send_message(
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


def _teacher_from_revealed(profile_id: str, revealed: dict) -> TeacherProfile:
    return TeacherProfile(
        id=profile_id,
        display_name=revealed["preferred_name"],
        subjects=list(revealed["subjects"]),
        grade_min=int(revealed["grade_min"]),
        grade_max=int(revealed["grade_max"]),
        mode=revealed["mode"],
        location=revealed["location"],
        license_active=revealed["license_status"] == "active",
    )


def _student_from_revealed(profile_id: str, revealed: dict) -> StudentProfile:
    return StudentProfile(
        id=profile_id,
        display_name=revealed["preferred_name"],
        grade_level=int(revealed["grade_level"]),
        interests=list(revealed["interests"]),
        mode=revealed["mode"],
        location=revealed["location"],
    )


def _render(
    school_name: str,
    target_id: str,
    teachers: list[TeacherProfile],
    students: list[StudentProfile],
    teacher_matches: list,
    student_matches: list,
) -> str:
    teacher_names = {teacher.id: teacher.display_name for teacher in teachers}
    student_names = {student.id: student.display_name for student in students}
    matched_teachers = {match.candidate_id for match in teacher_matches}
    matched_students = {match.candidate_id for match in student_matches}
    lines = [
        "Agent Credential Platform — school matching demo",
        f"School: {school_name}",
        "Profiles were built from revealed claims only.",
        "",
        f"Teachers for opening {target_id}:",
    ]
    for match in teacher_matches:
        name = teacher_names[match.candidate_id]
        reason = "; ".join(match.reasons)
        lines.append(f"- {name} ({match.candidate_id}) score {match.score}: {reason}")
    for teacher in teachers:
        if teacher.id not in matched_teachers:
            lines.append(f"- {teacher.display_name} ({teacher.id}) not matched")
    lines.append("")
    lines.append(f"Students for program {target_id}:")
    for match in student_matches:
        name = student_names[match.candidate_id]
        reason = "; ".join(match.reasons)
        lines.append(f"- {name} ({match.candidate_id}) score {match.score}: {reason}")
    for student in students:
        if student.id not in matched_students:
            lines.append(f"- {student.display_name} ({student.id}) not matched")
    lines.append("")
    return "\n".join(lines)


def report_blob(report: DemoReport) -> str:
    """Text plus the task JSON, for leak checks."""
    return report.text + json.dumps(report.task)
