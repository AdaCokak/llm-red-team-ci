import json
from pathlib import Path

from scripts.build_trend import load_reports, render_trend


def test_trend_orders_reports_and_calculates_rate(tmp_path: Path) -> None:
    newer = {
        "created_at": "2026-10-20T11:00:00+00:00",
        "git_sha": "bbbbbbbb2222",
        "summary": {
            "total": 50,
            "passed": 49,
            "failed": 1,
            "errors": 0,
            "critical_failures": 1,
        },
    }
    older = {
        "created_at": "2026-10-19T11:00:00+00:00",
        "git_sha": "aaaaaaaa1111",
        "summary": {
            "total": 50,
            "passed": 50,
            "failed": 0,
            "errors": 0,
            "critical_failures": 0,
        },
    }
    (tmp_path / "red-team-new.json").write_text(json.dumps(newer))
    nested = tmp_path / "history"
    nested.mkdir()
    (nested / "red-team-old.json").write_text(json.dumps(older))

    rendered = render_trend(load_reports(tmp_path))

    assert rendered.index("aaaaaaaa") < rendered.index("bbbbbbbb")
    assert "2.0%" in rendered
