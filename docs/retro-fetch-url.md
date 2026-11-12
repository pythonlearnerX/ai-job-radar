# 复盘：给采集层加可靠性外壳（fetch_url）

> 时间：2026-11-11 ~ 11-12 ｜ 位置：`job_radar/fetcher.py` ｜ 结果：41 tests passed，CI 双版本绿

---

## 一句话

把「一次性发请求、失败就崩」改成「限速 → 分类重试 → 断点续跑」，
让采集任务在**会失败**的现实里能跑完、能续跑、不把对方网站打挂。

---

## 做了什么

| 能力 | 实现 | 关键点 |
| --- | --- | --- |
| 失败分类 | `HTTPError` 先判 `400 <= code < 500` 直接抛，其余重试 | `HTTPError` 是 `URLError` 的子类，`except` 顺序决定行为 |
| 指数退避 | `sleep(backoff * 2 ** (attempt - 1))` | 1s / 2s / 4s；最后一次失败不睡，直接抛 |
| 进程内限速 | `_throttle()`：算「还差多少」而不是无脑 sleep | 用 `time.monotonic()`，不受校时影响 |
| 断点续跑 | `seen.txt` + `load_seen` / `mark_seen` | 每写一条追加一次，进程被杀也只丢当前这条 |

配套 6 个单元测试：成功返回、5xx 重试后成功、4xx 只发 1 次、网络错误重试到放弃、两次请求间隔、seen 文件读写。

---

## 三个决策，以及为什么

**1. 为什么用标准库 `urllib`，不用 `requests`**
本机连不上 PyPI（代理超时）。更重要的理由：这个模块只有一个请求需求，`requests` 带来的便利不值得多一个依赖。**能用标准库解决就别加依赖**，是写工具类代码的基本原则。

**2. 为什么重试次数固定为 3**
不是技术最优，是业务权衡：3 次覆盖了绝大多数瞬时抖动（1s+2s+4s ≈ 7 秒窗口），再多次只是在拖长失败时间。**如果是付费 API，还要把重试成本算进去**——重试 10 次可能比失败更贵。

**3. 为什么限速是进程内的**
数据量在千级、串行为主，上 Redis 令牌桶属于过度设计。但**明确知道它的边界**：开多进程就失效，那时必须换成集中式限流。

---

## 踩的坑（比代码值钱）

| 坑 | 现象 | 怎么定位 | 教训 |
| --- | --- | --- | --- |
| 文件被存成 GBK | `SyntaxError: 'utf-8' codec can't decode byte 0xb5` | 报错里中文变乱码 | 中文 Windows 的编辑器默认 GBK；`.editorconfig` + VS Code 强制 UTF-8 |
| 替换代码时删多了 | `ImportError: cannot import name 'FetchError'` | 搜「名字在不在」：`Select-String "FetchError" fetcher.py` | 替换整段前先 `git diff`，或先提交一次再改 |
| `.gitignore` 吞掉数据目录 | 本地 41 passed，CI 必红；Install 绿、Test 红 | `git ls-files data` 为空；`git check-ignore -v` 指出第 71 行 | 模板复制来的 ignore 规则要逐条读；本地绿 CI 红优先查「该提交的没提交」 |

**最有价值的一次排查**：CI 红了之后，先看步骤——`Install success / Test failure`，
一句话排除了「环境不兼容」，直接奔着数据去，5 分钟定位到 `.gitignore`。

---

## 验证

```text
pytest -q                     41 passed
GitHub Actions run #3         Python 3.10 ✅ / 3.12 ✅
```

---

## 这一版**没有**什么（面试要主动说）

| 缺失 | 后果 | 补法 |
| --- | --- | --- |
| robots.txt 检查 | 合规风险 | 下一步做 |
| jitter 抖动 | 高并发下惊群：所有客户端同一毫秒重试 | `sleep(backoff * 2**n + random())` |
| 分布式限速 | 多进程失效 | Redis 令牌桶 |
| 并发抓取 | 慢 | 上 `asyncio` 前先确认目标站点能承受 |
| 持久化队列 | 崩溃丢掉「正在抓」的那条 | 上千条后再引入 |
| 编码探测 | 非 UTF-8 页面乱码 | 按 `Content-Type` 或 `chardet` |

---

## 如果重做，会怎么改

1. **先写 `sites.yaml`，再写 parser**。现在采集逻辑和站点规则还混在一起，加第二个站点就要改代码。
2. **加一个 `Fetcher` 类代替模块级全局变量**。`_last_request_at` 是全局状态，两个测试并行跑就会互相干扰（现在靠传 `delay=0` 绕开）。
3. **重试策略抽成参数对象**。`retries/backoff/timeout` 三个参数已经开始长了，再加 jitter、可重试状态码表会爆。

---

## 面试可讲的三段

1. **失败分类**：「按状态码分可重试与不可重试，4xx 立刻失败，5xx 指数退避」——展示你知道重试不是万能的。
2. **限速的语义**：「控制的是请求发出时刻的间隔，所以等待必须在发出之前；用单调时钟避免校时跳变」——展示你想清楚了时序。
3. **CI 排查**：「本地绿 CI 红，先看失败步骤，Install 绿说明不是环境问题，`git ls-files` 发现数据没提交，`git check-ignore` 定位到 ignore 规则」——展示排查方法而不是运气。

---

记录人：pythonlearnerX ｜ 2026-11-12