"""清洗：城市名归一、技能词抽取、描述文本规整。"""

from __future__ import annotations

import json
import re
from pathlib import Path

CITY_SUFFIXES = ("市", "特别行政区")

WHITESPACE_RE = re.compile(r"\s+")


def normalize_city(city: str) -> str:
    """`北京市` -> `北京`；`上海 浦东` -> `上海`；空值原样返回。"""
    if not city:
        return ""
    text = WHITESPACE_RE.sub("", city)
    for sep in ("·", "-", "（", "(", "/"):
        if sep in text:
            text = text.split(sep, 1)[0]
    for suffix in CITY_SUFFIXES:
        if text.endswith(suffix):
            text = text[: -len(suffix)]
    return text


def normalize_text(text: str) -> str:
    """压缩空白，去掉零宽字符。"""
    if not text:
        return ""
    text = text.replace("\u200b", "").replace("\xa0", " ")
    return WHITESPACE_RE.sub(" ", text).strip()


def load_skills(path: str | Path) -> dict[str, list[str]]:
    """读技能词典：{规范名: [别名...]}。"""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("技能词典必须是 JSON 对象")
    return {str(k): [str(x) for x in v] for k, v in data.items()}


def extract_skills(text: str, dictionary: dict[str, list[str]]) -> list[str]:
    """在文本里找技能词，返回规范名列表（去重、排序）。

    大小写不敏感；英文按子串匹配（够用，后面可以换成 jieba + 词典）。
    """
    if not text:
        return []
    haystack = text.lower()
    hits = []
    for canonical, aliases in dictionary.items():
        for word in [canonical, *aliases]:
            if word.lower() in haystack:
                hits.append(canonical)
                break
    return sorted(set(hits))