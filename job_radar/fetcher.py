"""采集层。

分两条路：
1. `load_samples()`  读本地样例，离线可跑，测试和演示都用它。
2. `fetch_url()`     真实抓取，**留给你实现**（TODO 里写了要做的事）。

真正的爬虫要考虑：robots.txt、频率限制、重试、User-Agent、断点续跑。
这些都不适合塞进第一版——先把「文本 → 结构化」跑通，再去解决「怎么拿到文本」。
"""

from __future__ import annotations

import time
import urllib.error
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

class FetchError(Exception):
    """抓取失败：重试用尽，或客户端错误。"""


_last_request_at: float = 0.0


def _throttle(delay: float) -> None:
    """保证两次请求之间至少间隔 delay 秒。"""
    global _last_request_at
    if delay > 0:
        wait = delay - (time.monotonic() - _last_request_at)
        if wait > 0:
            time.sleep(wait)
    _last_request_at = time.monotonic()


def fetch_url(
    url: str,
    *,
    delay: float = 2.0,
    timeout: float = 10.0,
    retries: int = 3,
    backoff: float = 1.0,
) -> RawJob:
    """抓单个页面：失败重试 + 指数退避。

    delay 这一步先不用（下一步做限速），测试里都传 delay=0。
    """
    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        _throttle(delay)
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "ai-job-radar/0.1 (learning project)"},
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                text = response.read().decode(charset, errors="ignore")
            return RawJob(text=text, source=url, url=url)

        except urllib.error.HTTPError as exc:
            # HTTPError 是 URLError 的子类，必须写在前面，否则永远进不来
            if 400 <= exc.code < 500:
                raise FetchError(f"{url} 客户端错误 {exc.code}") from exc
            last_error = exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc

        if attempt < retries:
            time.sleep(backoff * 2 ** (attempt - 1))

    raise FetchError(f"{url} 重试 {retries} 次仍失败：{last_error}") from last_error
def load_seen(path: str | Path) -> set[str]:
    p = Path(path)
    if not p.exists():
        return set()
    return {line.strip() for line in p.read_text(encoding="utf-8").splitlines() if line.strip()}


def mark_seen(path: str | Path, url: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(url + "\n")