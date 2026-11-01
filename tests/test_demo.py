"""Smoke tests for the demo and the CLI."""

from acp.cli import main
from acp.demo import report_blob, run_demo
from acp.protocols.anp.adapter import ANPAdapter


def test_demo_matches_ada_and_priya_and_hides_canaries() -> None:
    report = run_demo()
    assert [item.candidate_id for item in report.teacher_matches] == ["teacher-ada"]
    assert [item.candidate_id for item in report.student_matches] == ["student-priya"]
    blob = report_blob(report)
    for secret in report.withheld_values:
        assert secret not in blob
    assert "not matched" in report.text
    assert report.task["status"]["state"] == "TASK_STATE_COMPLETED"


def test_anp_projection_is_a_stub() -> None:
    projected = ANPAdapter().project_did("did:example:state-board")
    assert projected["status"] == "not_implemented"
    assert projected["agentCardPath"] == "/.well-known/agent-card.json"


def test_cli_demo(capsys) -> None:
    assert main(["demo"]) == 0
    captured = capsys.readouterr()
    assert "teacher-ada" in captured.out
    assert "742 Evergreen Terrace" not in captured.out
