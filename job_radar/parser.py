"""解析：把一段 JD 文本拆成字段。

目标是「够用就好」——先按 `键：值` 的格式解析，解析不了的正文全部并进描述，
后面用技能词典去捞关键词。真实站点结构千奇百怪，所以真正的适配放在 fetcher 层，
这一层只负责「给我一段文本，我还你一个 JobPosting」。
"""

from __future__ import annotations

import re

from .models import JobPosting

# 中文键名统一成内部字段名
KEY_ALIASES = {
    "公司": "company",
    "公司名称": "company",
    "企业": "company",
    "职位": "title",
    "岗位": "title",
    "职位名称": "title",
    "岗位名称": "title",
    "城市": "city",
    "地点": "city",
    "工作地点": "city",
    "薪资": "salary",
    "薪水": "salary",
    "薪资范围": "salary",
    "学历": "edu",
    "学历要求": "edu",
    "经验": "exp",
    "经验要求": "exp",
    "工作年限": "exp",
    "描述": "desc",
    "职位描述": "desc",
    "岗位职责": "desc",
    "任职要求": "desc",
    "要求": "desc",
}

KV_RE = re.compile(r"^\s*([^：:\s]{1,10})\s*[：:]\s*(.*)$")

# 15-25K·14薪 / 20k-35k / 15-25千 / 25~45K
# 注意：第一个数字后面可能也带 K（20k-35k），所以 K 要允许出现在分隔符前后
SALARY_RE = re.compile(
    r"(?P<low>\d{1,3})\s*[kK千]?\s*[-~－—–]\s*(?P<high>\d{1,3})\s*(?:[kK千])?"
    r"(?:\s*[·*x×]\s*(?P<months>\d{1,2})\s*薪)?"
)


def parse_salary(text: str) -> tuple[int | None, int | None, int]:
    """解析薪资，返回 (最低, 最高, 几薪)。解析不了就返回 (None, None, 12)。"""
    if not text:
        return None, None, 12
    match = SALARY_RE.search(text)
    if not match:
        return None, None, 12
    low = int(match.group("low"))
    high = int(match.group("high"))
    if low > high:  # 写反了，纠正一下
        low, high = high, low
    months = int(match.group("months") or 12)
    return low, high, months


def parse_kv(text: str) -> dict[str, str]:
    """把 `公司：字节跳动` 这种行拆成字典；不是键值对的行并进 desc。"""
    fields: dict[str, str] = {}
    extra: list[str] = []

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        match = KV_RE.match(line)
        if not match:
            extra.append(line)
            continue
        raw_key, value = match.group(1).strip(), match.group(2).strip()
        key = KEY_ALIASES.get(raw_key, raw_key)
        if key == "desc" and "desc" in fields:
            fields["desc"] = fields["desc"] + " " + value
        else:
            fields[key] = value

    if extra:
        fields["desc"] = (fields.get("desc", "") + " " + " ".join(extra)).strip()
    return fields


def build_posting(
    fields: dict[str, str],
    source: str = "",
    url: str = "",
    raw_text: str = "",
) -> JobPosting:
    low, high, months = parse_salary(fields.get("salary", ""))
    return JobPosting(
        company=fields.get("company", "").strip(),
        title=fields.get("title", "").strip(),
        city=fields.get("city", "").strip(),
        salary_min=low,
        salary_max=high,
        salary_months=months,
        edu=fields.get("edu", "").strip(),
        exp=fields.get("exp", "").strip(),
        source=source,
        url=url,
        raw_text=raw_text or fields.get("desc", ""),
    )