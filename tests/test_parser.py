from pathlib import Path

import pytest

from job_radar.parser import build_posting, parse_kv, parse_salary


@pytest.mark.parametrize(
    "text,expected",
    [
        ("30-60K·15薪", (30, 60, 15)),
        ("20k-35k", (20, 35, 12)),
        ("15-25千", (15, 25, 12)),
        ("25~45K", (25, 45, 12)),
        ("60-30K", (30, 60, 12)),  # 写反了要纠正
    ],
)
def test_parse_salary_ok(text, expected):
    assert parse_salary(text) == expected


@pytest.mark.parametrize("text", ["", "面议", "薪资面谈", "10K 起"])
def test_parse_salary_missing(text):
    assert parse_salary(text) == (None, None, 12)


def test_parse_kv_basic():
    text = """公司：字节跳动
职位：大模型应用开发
城市：北京市
薪资：30-60K·15薪
"""
    fields = parse_kv(text)
    assert fields["company"] == "字节跳动"
    assert fields["title"] == "大模型应用开发"
    assert fields["city"] == "北京市"


def test_parse_kv_free_text_goes_to_desc():
    text = """公司：A
职位：B
描述：负责 RAG 建设
还要熟悉 Docker
"""
    fields = parse_kv(text)
    assert "RAG" in fields["desc"]
    assert "Docker" in fields["desc"]


def test_build_posting_sets_salary():
    job = build_posting({"company": "A", "title": "B", "salary": "30-60K·15薪"})
    assert (job.salary_min, job.salary_max, job.salary_months) == (30, 60, 15)
    assert job.salary_mid == pytest.approx(56.25)


def test_build_posting_empty_salary():
    job = build_posting({"company": "A", "title": "B"})
    assert job.salary_mid is None
    assert job.salary_text == "面议"