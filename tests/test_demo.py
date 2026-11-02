"""Smoke tests for the demo and the CLI."""

from acp.cli import main
from acp.demo import report_blob, run_demo
from acp.protocols.a2a.card import build_agent_card
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
    assert report.task["metadata"]["tenantId"] == "example-tenant"
    assert report.task["metadata"]["rulePackId"] == "education"


def test_anp_description_is_derived_from_the_agent_card() -> None:
    card = build_agent_card("https://matcher.example")
    projected = ANPAdapter().project_card(card)
    assert projected["sourceOfTruth"] == "a2a-agent-card"
    assert projected["status"] == "derived_stub"
    assert projected["protocolType"] == "ANP"
    assert projected["name"] == card["name"]
    assert projected["url"] == "https://matcher.example/a2a/v1"
    pointed = ANPAdapter().project_did("did:example:state-board")
    assert pointed["sourceOfTruth"] == "a2a-agent-card"


def test_cli_demo(capsys) -> None:
    assert main(["demo"]) == 0
    captured = capsys.readouterr()
    assert "teacher-ada" in captured.out
    assert "742 Evergreen Terrace" not in captured.out
