"""数据模型：一条岗位记录。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class JobPosting:
    """一条岗位。薪资单位统一为「千元 / 月」。"""

    company: str
    title: str
    city: str = ""
    salary_min: int | None = None
    salary_max: int | None = None
    salary_months: int = 12
    edu: str = ""
    exp: str = ""
    skills: list[str] = field(default_factory=list)
    source: str = ""
    url: str = ""
    raw_text: str = ""

    @property
    def salary_mid(self) -> float | None:
        """月薪中位数（按 12 个月折算，方便横向比较）。"""
        if self.salary_min is None or self.salary_max is None:
            return None
        return (self.salary_min + self.salary_max) / 2 * self.salary_months / 12

    @property
    def salary_text(self) -> str:
        if self.salary_min is None or self.salary_max is None:
            return "面议"
        base = f"{self.salary_min}-{self.salary_max}K"
        return base if self.salary_months == 12 else f"{base}·{self.salary_months}薪"

    def __str__(self) -> str:
        return f"{self.company} | {self.title} | {self.city} | {self.salary_text}"