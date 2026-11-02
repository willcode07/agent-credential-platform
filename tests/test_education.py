"""The education example maps onto the generic matcher. It is not the core model."""

from acp.matching.matcher import match_candidates
from acp.matching.profiles import ClaimRequirement, Opportunity
from acp.verticals.education import (
    candidate_from_revealed,
    math_student_program,
    math_teacher_opening,
)


def _teacher(**overrides: object) -> dict:
    revealed: dict[str, object] = {
        "preferred_name": "Ada Okonkwo",
        "subjects": ["Mathematics"],
        "grade_min": 9,
        "grade_max": 12,
        "mode": "in_person",
        "location": "Springfield",
        "license_status": "active",
    }
    revealed.update(overrides)
    return revealed


def test_opening_keeps_ada_and_drops_expired_license_and_other_city() -> None:
    opening = math_teacher_opening()
    ada = candidate_from_revealed("teacher-ada", _teacher())
    ben = candidate_from_revealed("teacher-ben", _teacher(license_status="expired"))
    other_city = candidate_from_revealed("teacher-cam", _teacher(location="Shelbyville"))
    matches = match_candidates(opening, [ada, ben, other_city])
    assert [item.candidate_id for item in matches] == ["teacher-ada"]
    assert matches[0].score == 100
    assert "active license disclosed" in matches[0].reasons


def test_program_drops_a_grade_outside_the_range() -> None:
    program = math_student_program()
    priya = candidate_from_revealed(
        "student-priya",
        {
            "preferred_name": "Priya Shah",
            "grade_level": 10,
            "interests": ["Mathematics"],
            "mode": "in_person",
            "location": "Springfield",
        },
    )
    leo = candidate_from_revealed(
        "student-leo",
        {
            "preferred_name": "Leo Martins",
            "grade_level": 4,
            "interests": ["Mathematics"],
            "mode": "in_person",
            "location": "Springfield",
        },
    )
    matches = match_candidates(program, [priya, leo])
    assert [item.candidate_id for item in matches] == ["student-priya"]
    assert matches[0].score == 80


def test_remote_placement_ignores_city() -> None:
    opportunity = Opportunity(
        id="remote-role",
        name="Remote role",
        requirements=[
            ClaimRequirement(
                claim="placement",
                op="one_of",
                value=["remote", "anywhere"],
                label="mode compatible",
            )
        ],
    )
    remote = candidate_from_revealed(
        "remote-person",
        {"preferred_name": "Ren", "mode": "remote", "location": "Capital City"},
    )
    local = candidate_from_revealed(
        "local-person",
        {"preferred_name": "Lee", "mode": "in_person", "location": "Springfield"},
    )
    matches = match_candidates(opportunity, [remote, local])
    assert [item.candidate_id for item in matches] == ["remote-person"]
    assert remote.claims["placement"] == "remote"
