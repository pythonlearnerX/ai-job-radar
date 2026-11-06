import pytest

from job_radar.models import JobPosting
from job_radar.storage import JobStore


def _job(**kw):
    base = dict(company="A", title="B", city="北京", salary_min=20, salary_max=30, skills=["Python"])
    base.update(kw)
    return JobPosting(**base)


@pytest.fixture()
def store(tmp_path):
    return JobStore(tmp_path / "jobs.db")


def test_save_and_load_roundtrip(store):
    store.save(_job())
    jobs = store.all()
    assert len(jobs) == 1
    assert jobs[0].skills == ["Python"]
    assert jobs[0].salary_mid == 25.0


def test_duplicate_is_skipped(store):
    assert store.save(_job()) is True
    assert store.save(_job()) is False
    assert store.count() == 1


def test_same_company_different_title_both_saved(store):
    store.save(_job(title="A岗"))
    store.save(_job(title="B岗"))
    assert store.count() == 2


def test_none_salary_survives_roundtrip(store):
    store.save(_job(salary_min=None, salary_max=None))
    job = store.all()[0]
    assert job.salary_mid is None
    assert job.salary_text == "面议"


def test_counts(store):
    assert store.count() == 0
    assert store.save_many([_job(title="A"), _job(title="B")]) == 2