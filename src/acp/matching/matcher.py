"""Rule-based matcher for the school launch market.

A candidate is dropped when a hard rule fails (subject, grade band, license
when required, or mode). Survivors get a stable score so the demo can rank
them. There is no learning and no fuzzy subject map.

# OPEN QUESTION: which revealed claims is a school allowed to require before
# a match, and does a later HR / executive-screening product share this
# matcher or get a separate policy?
"""

from acp.matching.profiles import (
    Match,
    Opening,
    SchoolProfile,
    SchoolProgram,
    StudentProfile,
    TeacherProfile,
)


def match_teachers(opening: Opening, teachers: list[TeacherProfile]) -> list[Match]:
    """Rank teachers who satisfy ``opening``. Highest score first."""
    matches: list[Match] = []
    for teacher in teachers:
        reasons: list[str] = []
        if opening.subject.casefold() not in {item.casefold() for item in teacher.subjects}:
            continue
        reasons.append(f"teaches {opening.subject}")
        if not _grades_overlap(
            opening.grade_min, opening.grade_max, teacher.grade_min, teacher.grade_max
        ):
            continue
        reasons.append("grade band overlaps")
        if opening.requires_license and not teacher.license_active:
            continue
        if teacher.license_active:
            reasons.append("active license disclosed")
        if not _modes_compatible(opening.mode, teacher.mode, opening.location, teacher.location):
            continue
        reasons.append("mode and location compatible")
        score = 50 + 20 + (20 if teacher.license_active else 0) + 10
        matches.append(
            Match(
                candidate_id=teacher.id,
                candidate_role="teacher",
                target_id=opening.id,
                score=score,
                reasons=reasons,
            )
        )
    return sorted(matches, key=lambda item: (-item.score, item.candidate_id))


def match_students(program: SchoolProgram, students: list[StudentProfile]) -> list[Match]:
    """Rank students whose interests and grade fit ``program``."""
    matches: list[Match] = []
    for student in students:
        interests = {item.casefold() for item in student.interests}
        if program.subject.casefold() not in interests:
            continue
        if not program.grade_min <= student.grade_level <= program.grade_max:
            continue
        if not _modes_compatible(program.mode, student.mode, program.location, student.location):
            continue
        reasons = [
            f"interest in {program.subject}",
            "grade level inside the program",
            "mode and location compatible",
        ]
        matches.append(
            Match(
                candidate_id=student.id,
                candidate_role="student",
                target_id=program.id,
                score=80,
                reasons=reasons,
            )
        )
    return sorted(matches, key=lambda item: (-item.score, item.candidate_id))


def match_school(
    school: SchoolProfile,
    teachers: list[TeacherProfile],
    students: list[StudentProfile],
) -> dict[str, list[Match]]:
    """Match every opening to teachers and every program to students.

    Keys are ``opening:<id>`` and ``program:<id>``.
    """
    report: dict[str, list[Match]] = {}
    for opening in school.openings:
        report[f"opening:{opening.id}"] = match_teachers(opening, teachers)
    for program in school.programs:
        report[f"program:{program.id}"] = match_students(program, students)
    return report


def _grades_overlap(min_a: int, max_a: int, min_b: int, max_b: int) -> bool:
    return min_a <= max_b and min_b <= max_a


def _modes_compatible(left: str, right: str, left_location: str, right_location: str) -> bool:
    if left == "hybrid" or right == "hybrid":
        return True
    if left == "remote" and right == "remote":
        return True
    if left == "in_person" and right == "in_person":
        return left_location.casefold() == right_location.casefold()
    return False
