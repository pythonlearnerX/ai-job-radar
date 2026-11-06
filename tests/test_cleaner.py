from pathlib import Path

import pytest

from job_radar.cleaner import extract_skills, load_skills, normalize_city, normalize_text

SKILLS = {
    "RAG": ["检索增强"],
    "Docker": ["容器化"],
    "Python": [],
}


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("北京市", "北京"),
        ("上海·浦东新区", "上海"),
        ("深圳", "深圳"),
        ("杭州（西湖区）", "杭州"),
        ("", ""),
    ],
)
def test_normalize_city(raw, expected):
    assert normalize_city(raw) == expected


def test_normalize_text_strips_odd_spaces():
    assert normalize_text("负责  RAG\u200b 建设\n\n熟悉 Docker ") == "负责 RAG 建设 熟悉 Docker"


def test_extract_skills_hits_canonical_and_alias():
    text = "负责 RAG 检索增强，熟悉 容器化 部署"
    assert extract_skills(text, SKILLS) == ["Docker", "RAG"]


def test_extract_skills_empty_text():
    assert extract_skills("", SKILLS) == []


def test_extract_skills_no_hit():
    assert extract_skills("负责搬砖", SKILLS) == []


def test_load_skills_reads_json(tmp_path):
    path = tmp_path / "s.json"
    path.write_text('{"A": ["a1"], "B": []}', encoding="utf-8")
    assert load_skills(path) == {"A": ["a1"], "B": []}


def test_load_skills_rejects_non_object(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(ValueError):
        load_skills(path)