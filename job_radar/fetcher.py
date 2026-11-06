"""采集层。

分两条路：
1. `load_samples()`  读本地样例，离线可跑，测试和演示都用它。
2. `fetch_url()`     真实抓取，**留给你实现**（TODO 里写了要做的事）。

真正的爬虫要考虑：robots.txt、频率限制、重试、User-Agent、断点续跑。
这些都不适合塞进第一版——先把「文本 → 结构化」跑通，再去解决「怎么拿到文本」。
"""

from __future__ import annotations

import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RawJob:
    """采集到的一段原始文本 + 出处。"""

    text: str
    source: str
    url: str = ""


def load_samples(directory: str | Path) -> list[RawJob]:
    """读目录下所有 .txt 当成一条岗位。文件名就是 source。"""
    folder = Path(directory)
    if not folder.exists():
        raise FileNotFoundError(f"样例目录不存在：{folder}")

    jobs: list[RawJob] = []
    for path in sorted(folder.glob("*.txt")):
        jobs.append(
            RawJob(
                text=path.read_text(encoding="utf-8"),
                source=path.name,
                url="",
            )
        )
    return jobs


def fetch_url(url: str, *, delay: float = 2.0, timeout: float = 10.0) -> RawJob:
    """抓单个页面（最小实现，仅作起点）。

    TODO 你要补的：
      1. 抓之前先看 robots.txt（`/robots.txt`），不允许的路径直接放弃。
      2. 加 `User-Agent`，否则会被直接拒。
      3. 失败重试 3 次，指数退避（1s、2s、4s）。
      4. 每次请求之间 sleep(delay)，别把人家站点打挂。
      5. 断点续跑：抓过的 URL 记到 `data/seen.txt`，下次跳过。
      6. 解析 HTML 用 BeautifulSoup 或 lxml，把正文抽出来再交给 parser。
    """
    time.sleep(delay)  # 先限速，别一上来就猛冲
    request = urllib.request.Request(url, headers={"User-Agent": "ai-job-radar/0.1 (learning project)"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        text = response.read().decode(charset, errors="ignore")
    return RawJob(text=text, source=url, url=url)