# ai-job-radar

[![CI](https://github.com/pythonlearnerX/ai-job-radar/actions/workflows/ci.yml/badge.svg)](https://github.com/pythonlearnerX/ai-job-radar/actions/workflows/ci.yml)

> 抓岗位 JD，看清市场到底要什么。
> 采集 → 解析 → 清洗 → 入库 → 统计 → 报告，一条流水线跑完。

**现在能做到什么**：把一批岗位文本（样例或自己抓的）变成「技能 Top 榜 + 城市薪资分布」的 Markdown 报告。
**还没做**：真实站点的爬虫适配（见文末 TODO，那是你接下来要写的部分）。

---

## 数据流

```text
  ┌─────────┐   ┌──────────┐   ┌──────────┐   ┌─────────┐   ┌──────────┐
  │ fetcher │──▶│  parser  │──▶│ cleaner  │──▶│ storage │──▶│ analyzer │
  │ 拿文本  │   │ 拆字段   │   │ 归一+技能│   │ SQLite  │   │ 统计     │
  └─────────┘   └──────────┘   └──────────┘   └─────────┘   └────┬─────┘
       ▲                                                          │
  本地样例 / 真实 URL                                     ┌───────▼───────┐
                                                          │    report     │
                                                          │ Markdown 报告 │
                                                          └───────────────┘
```

每一层都能单独测，互不依赖网络——这是这套结构最值钱的地方。

## 快速开始

```bash
git clone git@github.com:pythonlearnerX/ai-job-radar.git
cd ai-job-radar
python -m venv .venv
.venv\Scripts\activate          # macOS / Linux: source .venv/bin/activate
pip install -e ".[dev]"

python -m job_radar run          # 读 data/sample 的 4 条样例，入库
python -m job_radar stats        # 控制台看汇总
python -m job_radar report       # 生成 outputs/report.md
```

装完之后也可以直接用 `jobradar run`。

样例输出：

```text
岗位总数：4
月薪中位数：40.8K（3 条有薪资）
技能 Top：
  Python          4
  RAG             4
  Docker          3
  FastAPI         3
  Prompt工程       3
```

完整报告长这样：[docs/example-report.md](docs/example-report.md)

## 命令

| 命令 | 作用 |
| --- | --- |
| `jobradar run [--input DIR]` | 读目录下所有 `.txt`，解析后入库（重复的自动跳过） |
| `jobradar stats` | 终端汇总：总数、中位数薪资、技能 Top10、城市分布 |
| `jobradar report [-o PATH] [--top N]` | 生成 Markdown 报告 |
| `jobradar --db PATH ...` | 指定数据库（默认 `data/jobs.db`） |
| `jobradar --skills PATH ...` | 指定技能词典（默认 `configs/skills.json`） |

## 目录

```text
ai-job-radar/
├─ job_radar/
│  ├─ models.py     # JobPosting：一条岗位
│  ├─ fetcher.py    # 采集：本地样例 + fetch_url（TODO 在这里）
│  ├─ parser.py     # 键值解析 + 薪资正则
│  ├─ cleaner.py    # 城市归一、技能词典抽取
│  ├─ storage.py    # SQLite，UNIQUE 去重
│  ├─ analyzer.py   # 计数、中位数、Top N
│  ├─ report.py     # Markdown 渲染
│  └─ cli.py        # argparse 子命令
├─ configs/skills.json   # 技能词典：规范名 → 别名
├─ data/sample/*.txt     # 4 条脱敏样例
├─ tests/                # 35 个用例
└─ outputs/              # 生成的报告（不进 git）
```

## 设计说明

- **为什么样例用 `键：值` 格式**：先把「文本 → 结构」这条逻辑跑通，再谈「怎么拿到文本」。否则一上来就死在反爬上。
- **为什么去重用 `UNIQUE(company, title, city)`**：断点续跑时重复抓同一岗位是常态，靠数据库约束去重比在代码里 `if` 更可靠。
- **为什么技能抽取用词典而不是模型**：规则可解释、能被人手工修正、跑一次 0 成本。等数据量上千再考虑 embedding 聚类。
- **为什么薪资存「千元/月」**：`30-60K·15薪` 和 `25-45K·14薪` 直接比是错的，必须按 12 个月折算再比（`salary_mid` 干的就是这件事）。

## 测试

```bash
pytest -q     # 35 passed
```

覆盖：薪资正则（含 `20k-35k`、`面议`、写反的区间）、键值解析、城市归一、技能抽取、
入库去重、空库出报告、目录不存在、端到端 run → stats → report。

## 踩过的坑

1. **`20k-35k` 匹配失败**：正则只允许 K 出现在第二个数字后面。改成 `(\d+)\s*[kK]?\s*[-~]\s*(\d+)\s*[kK]?` 才吃得住。
2. **`logging.basicConfig` 只生效一次**：测试里反复调 `main()`，第二次开始日志写到了已经释放的 stderr。加 `force=True` 解决。
3. **中文表格对不齐**：终端里中文字符占两格，`len()` 算的是一格。暂时不修，列进 TODO。

## TODO（下一步，按难度排）

- [ ] **P0** 实现 `fetch_url` 的真实抓取：robots.txt → 限速 → 重试 → 断点续跑（`fetcher.py` 里已写清单）
- [ ] **P0** 加一个 `sites.yaml`，把「站点 → 列表页规则 → 详情页规则」配置化，代码里不写死选择器
- [ ] **P1** 技能抽取从「子串匹配」升级成「jieba 分词 + 词典」，解决 `Java` 命中 `JavaScript` 这类误判
- [ ] **P1** 中文列宽对齐（东亚字符宽度计算）
- [ ] **P1** 技能共现分析：同时出现 RAG + vLLM 的岗位有多少
- [ ] **P2** 导出 CSV，方便 Excel 里筛
- [ ] **P2** 周更任务：GitHub Actions 定时跑，生成趋势对比

## 合规

只用公开岗位信息，不抓个人信息、不绕过登录、控制频率；数据仅用于个人学习与自我定位。

## License

MIT