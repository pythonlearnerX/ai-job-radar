"""分析：这批 JD 到底在要什么。"""

from __future__ import annotations

import statistics
from collections import Counter
from dataclasses import dataclass, field

from .models import JobPosting


@dataclass
class Summary:
    total: int
    with_salary: int
    salary_median: float | None
    by_city: list[tuple[str, int]] = field(default_factory=list)
    by_edu: list[tuple[str, int]] = field(default_factory=list)
    top_skills: list[tuple[str, int]] = field(default_factory=list)


def count_by(items: list[str]) -> list[tuple[str, int]]:
    """计数并按次数降序；空字符串忽略。"""
    counter = Counter(item for item in items if item)
    return counter.most_common()


def top_skills(jobs: list[JobPosting], n: int = 15) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for job in jobs:
        counter.update(job.skills)
    return counter.most_common(n)


def salary_by_city(jobs: list[JobPosting]) -> list[tuple[str, float, int]]:
    """各城市月薪中位数（只看有薪资的），按中位数降序。"""
    buckets: dict[str, list[float]] = {}
    for job in jobs:
        mid = job.salary_mid
        if mid is None or not job.city:
            continue
        buckets.setdefault(job.city, []).append(mid)
    rows = [(city, round(statistics.median(vals), 1), len(vals)) for city, vals in buckets.items()]
    return sorted(rows, key=lambda r: -r[1])


def summarize(jobs: list[JobPosting], top_n: int = 15) -> Summary:
    salaries = [job.salary_mid for job in jobs if job.salary_mid is not None]
    return Summary(
        total=len(jobs),
        with_salary=len(salaries),
        salary_median=round(statistics.median(salaries), 1) if salaries else None,
        by_city=count_by([job.city for job in jobs]),
        by_edu=count_by([job.edu for job in jobs]),
        top_skills=top_skills(jobs, top_n),
    )