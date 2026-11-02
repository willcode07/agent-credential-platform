"""Bundled walkthrough.

The core platform has no market. ``acp demo`` runs the education example,
which maps schools, teachers, and students onto generic candidates and
opportunities.
"""

from acp.verticals.education import DemoReport, report_blob, run_demo

__all__ = ["DemoReport", "report_blob", "run_demo"]
