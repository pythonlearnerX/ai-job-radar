"""报告：把分析结果写成一份能发出去的 Markdown。"""

from __future__ import annotations

from pathlib import Path

from .analyzer import Summary, salary_by_city
from .models import JobPosting


def _table(header: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def render_markdown(jobs: list[JobPosting], summary: Summary, title: str = "岗位画像报告") -> str:
    parts: list[str] = [f"# {title}", ""]

    parts.append("## 一、概览")
    parts.append("")
    if summary.total == 0:
        parts.append("> 没有数据。先跑 `jobradar run`。")
        return "\n".join(parts) + "\n"

    salary_line = (
        f"月薪中位数 **{summary.salary_median}K**（{summary.with_salary}/{summary.total} 条有薪资）"
        if summary.salary_median is not None
        else "**没有可用薪资数据**"
    )
    parts.append(_table(["指标", "数值"], [
        ["岗位总数", str(summary.total)],
        ["薪资", salary_line],
        ["城市数", str(len(summary.by_city))],
        ["技能种类", str(len(summary.top_skills))],
    ]))
    parts.append("")

    if summary.top_skills:
        parts.append("## 二、最常被要求的技能")
        parts.append("")
        max_count = summary.top_skills[0][1]
        rows = [
            [skill, str(count), "█" * max(1, round(count / max_count * 20))]
            for skill, count in summary.top_skills
        ]
        parts.append(_table(["技能", "出现次数", ""], rows))
        parts.append("")

    if summary.by_city:
        parts.append("## 三、城市分布")
        parts.append("")
        parts.append(_table(["城市", "岗位数"], [[c, str(n)] for c, n in summary.by_city]))
        parts.append("")

    city_salary = salary_by_city(jobs)
    if city_salary:
        parts.append("## 四、各城市月薪中位数（K）")
        parts.append("")
        parts.append(_table(["城市", "中位数", "样本数"], [[c, str(m), str(n)] for c, m, n in city_salary]))
        parts.append("")

    if summary.by_edu:
        parts.append("## 五、学历要求")
        parts.append("")
        parts.append(_table(["学历", "岗位数"], [[e, str(n)] for e, n in summary.by_edu]))
        parts.append("")

    parts.append("## 六、样本明细")
    parts.append("")
    parts.append(_table(
        ["公司", "职位", "城市", "薪资", "技能"],
        [[j.company, j.title, j.city, j.salary_text, "、".join(j.skills)] for j in jobs],
    ))
    parts.append("")
    parts.append("---")
    parts.append("")
    parts.append("> 数据来自公开岗位 JD，仅用于个人学习与自我定位，不用于商业用途。")
    return "\n".join(parts) + "\n"


def write_report(path: str | Path, content: str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target