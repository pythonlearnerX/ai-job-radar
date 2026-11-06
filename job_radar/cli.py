"""命令行入口。

    jobradar run --input data/sample      # 读样例 → 解析 → 入库
    jobradar stats                        # 控制台看汇总
    jobradar report -o outputs/report.md  # 生成 Markdown 报告
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import cleaner, parser
from .analyzer import summarize
from .fetcher import load_samples
from .models import JobPosting
from .report import render_markdown, write_report
from .storage import JobStore

LOG = logging.getLogger("jobradar")

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "data" / "jobs.db"
DEFAULT_SKILLS = ROOT / "configs" / "skills.json"
DEFAULT_SAMPLE = ROOT / "data" / "sample"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="jobradar", description="抓岗位 JD，看清市场要什么")
    p.add_argument("--db", default=None, help=f"数据库路径（默认 {DEFAULT_DB}）")
    p.add_argument("--skills", default=None, help="技能词典 JSON 路径")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="command", required=True, metavar="命令")

    run = sub.add_parser("run", help="采集并解析")
    run.add_argument("--input", default=None, help="样例目录（默认 data/sample）")

    sub.add_parser("stats", help="控制台看汇总")

    rep = sub.add_parser("report", help="生成 Markdown 报告")
    rep.add_argument("-o", "--out", default=str(ROOT / "outputs" / "report.md"))
    rep.add_argument("--top", type=int, default=15, help="技能 Top N")

    return p


def _resolve(path: str | None, default: Path) -> Path:
    return Path(path) if path else default


def _parse_one(raw, dictionary: dict[str, list[str]]) -> JobPosting:
    fields = parser.parse_kv(raw.text)
    job = parser.build_posting(fields, source=raw.source, url=raw.url, raw_text=raw.text)
    job.city = cleaner.normalize_city(job.city)
    job.raw_text = cleaner.normalize_text(job.raw_text)
    job.skills = cleaner.extract_skills(f"{job.title} {job.raw_text}", dictionary)
    return job


def _cmd_run(store: JobStore, args: argparse.Namespace, dictionary) -> int:
    input_dir = _resolve(args.input, DEFAULT_SAMPLE)
    raws = load_samples(input_dir)
    if not raws:
        LOG.error("目录里没有 .txt 样例：%s", input_dir)
        return 1

    jobs = [_parse_one(raw, dictionary) for raw in raws]
    inserted = store.save_many(jobs)
    LOG.info("读入 %s 条，新入库 %s 条（库内共 %s 条）", len(jobs), inserted, store.count())
    for job in jobs:
        print(f"  {job}")
    return 0


def _cmd_stats(store: JobStore, args: argparse.Namespace) -> int:
    jobs = store.all()
    s = summarize(jobs)
    print(f"岗位总数：{s.total}")
    if s.salary_median is not None:
        print(f"月薪中位数：{s.salary_median}K（{s.with_salary} 条有薪资）")
    print("技能 Top：")
    for skill, count in s.top_skills[:10]:
        print(f"  {skill:<16}{count}")
    print("城市：")
    for city, count in s.by_city[:10]:
        print(f"  {city:<10}{count}")
    return 0


def _cmd_report(store: JobStore, args: argparse.Namespace) -> int:
    jobs = store.all()
    if not jobs:
        LOG.error("库里没数据，先跑 jobradar run")
        return 1
    s = summarize(jobs, args.top)
    target = write_report(args.out, render_markdown(jobs, s))
    LOG.info("报告已生成：%s", target)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)-7s %(message)s",
        stream=sys.stderr,
        force=True,  # 允许测试里反复调用 main()，每次都重新绑定当前 stderr
    )
    try:
        store = JobStore(_resolve(args.db, DEFAULT_DB))
        dictionary = cleaner.load_skills(_resolve(args.skills, DEFAULT_SKILLS))
        handlers = {
            "run": lambda: _cmd_run(store, args, dictionary),
            "stats": lambda: _cmd_stats(store, args),
            "report": lambda: _cmd_report(store, args),
        }
        return handlers[args.command]()
    except (ValueError, FileNotFoundError) as exc:
        LOG.error("%s", exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())