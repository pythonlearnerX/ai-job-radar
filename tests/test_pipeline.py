"""端到端：run → stats → report。"""

from pathlib import Path

from job_radar.cli import main

SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample"


def _db(tmp_path):
    return str(tmp_path / "jobs.db")


def test_run_parses_samples(tmp_path, capsys):
    assert main(["--db", _db(tmp_path), "run", "--input", str(SAMPLE)]) == 0
    out = capsys.readouterr().out
    assert "字节跳动" in out
    assert "杭州某电商平台" in out


def test_second_run_is_idempotent(tmp_path, capsys):
    main(["--db", _db(tmp_path), "run", "--input", str(SAMPLE)])
    capsys.readouterr()
    assert main(["--db", _db(tmp_path), "run", "--input", str(SAMPLE)]) == 0
    assert "新入库 0 条" in capsys.readouterr().err


def test_stats_prints_summary(tmp_path, capsys):
    main(["--db", _db(tmp_path), "run", "--input", str(SAMPLE)])
    capsys.readouterr()
    assert main(["--db", _db(tmp_path), "stats"]) == 0
    out = capsys.readouterr().out
    assert "岗位总数：4" in out
    assert "RAG" in out


def test_report_written(tmp_path):
    main(["--db", _db(tmp_path), "run", "--input", str(SAMPLE)])
    target = tmp_path / "report.md"
    assert main(["--db", _db(tmp_path), "report", "-o", str(target)]) == 0
    text = target.read_text(encoding="utf-8")
    assert "岗位画像报告" in text
    assert "最常被要求的技能" in text
    assert "RAG" in text


def test_report_without_data_fails(tmp_path):
    assert main(["--db", _db(tmp_path), "report", "-o", str(tmp_path / "r.md")]) == 1


def test_missing_input_dir_fails(tmp_path):
    assert main(["--db", _db(tmp_path), "run", "--input", str(tmp_path / "nope")]) == 2