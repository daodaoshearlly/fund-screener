# 基金筛选系统 - 技术方案

> **当前版本**：v1.5.0  
> **最后更新**：2026-02-23  
> **文档状态**：已确认

## 版本记录

| 版本 | 日期 | 修改内容 | 修改人 |
|------|------|---------|--------|
| v1.0.0 | 2026-02-17 | 初始版本，完成MVP核心功能（数据抓取、指标计算、筛选、回测、Server酱推送） | Claude |
| v1.1.0 | 2026-02-17 | 新增企业微信机器人推送支持，与Server酱并行使用 | Claude |
| v1.2.0 | 2026-02-17 | 新增邮件推送功能，支持SMTP协议发送报告 | Claude |
| v1.3.0 | 2026-02-23 | 新增基金经理维度分析，综合评分引入经理评分 | Claude |
| v1.4.0 | 2026-02-23 | 新增量化基金识别功能，优化数据库批量写入性能，邮件支持多收件人 | Claude |

---

## 项目概述

**目标**：自用基金筛选工具，重点筛选稳健增长、长期复利的基金，支持定投策略  
**技术栈**：Python + SQLite/PostgreSQL + Server酱/企业微信  
**数据频率**：每周定时筛选推送一次  
**推送渠道**：Server酱（个人微信）+ 企业微信机器人（群推送）  

---

## 核心筛选逻辑

### 目标定位
- **A. 稳健增长**：每年都能正收益（月度胜率 > 60%）
- **C. 长期复利**：3年/5年累计收益高

### 筛选条件

#### 硬性门槛（必须满足）
- 成立时间 > 3年
- 基金规模 > 2亿
- 最大回撤 < 25%
- 夏普比率 > 0.8
- 近3年年化收益 > 5%

#### 多因子加权评分（总分100）
```python
score = (
    年化收益率_3年 * 30% +      # 长期收益能力
    夏普比率 * 25% +             # 风险调整后收益
    卡玛比率 * 20% +             # 收益/最大回撤
    月度胜率 * 15% +             # 稳健性
    最大回撤控制 * 10%           # 抗跌性
)
```

---

## 数据存储设计

### 数据表结构

| 表名 | 内容 | 更新频率 |
|------|------|---------|
| `funds` | 基金基础信息（代码、名称、类型、经理、成立日期、规模） | 每周 |
| `fund_nav` | 每日净值（OHLC） | 每日收盘后 |
| `fund_metrics` | 计算好的指标（年化收益、夏普比率、最大回撤、月度胜率、卡玛比率） | 每周 |
| `backtest_results` | 回测结果（持有3年/5年收益、基准对比） | 每周 |
| `selected_funds` | 本次筛选出的基金Top N | 每次运行 |

---

## 回测基准

| 基金类型 | 对比基准 |
|---------|---------|
| 股票型/混合型 | 沪深300指数 (000300.SH) |
| 债券型 | 中证全债指数 (H11001.CSI) |
| 指数增强型 | 对应的宽基指数 |

**回测输出**：
- 持有3年/5年的累计收益
- 年化收益
- 最大回撤
- 与基准的超额收益

---

## 技术架构

```
定时任务 (APScheduler)
    ↓
数据抓取 (AKShare) → SQLite/PostgreSQL
    ↓
指标计算 (pandas/numpy) → 筛选出Top N
    ↓
生成报告 (文字 + 图表) → MultiNotifier推送
    ↓
    ├─→ Server酱 → 个人微信
    └─→ 企业微信机器人 → 企业微信群
```

---

## 推送渠道配置

| 渠道 | 用途 | 获取方式 | 环境变量 |
|------|------|---------|---------|
| Server酱 | 推送到个人微信 | https://sct.ftqq.com/ | `SERVER_CHAN_KEY` |
| 企业微信机器人 | 推送到企业微信群 | 群设置 → 添加机器人 | `WECOM_WEBHOOK` |
| 邮件 | 推送到邮箱 | SMTP服务配置 | `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_RECEIVER` |

**配置说明**：
- 三个渠道可同时配置，推送时会发送到所有已配置的渠道
- 至少配置一个渠道才能收到推送通知

**邮件配置示例**：
- Gmail: `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`, 需要应用专用密码
- QQ邮箱: `SMTP_HOST=smtp.qq.com`, `SMTP_PORT=587`, 使用授权码
- 163邮箱: `SMTP_HOST=smtp.163.com`, `SMTP_PORT=465`, 使用授权码

---

## 推送内容格式

```
📊 本周基金筛选报告（YYYY-MM-DD）

🥇 Top N 稳健复利基金：

1. 【基金名称】
   - 近3年收益: +XX.X% | 基准: +XX.X% ⬆️+XX.X%
   - 夏普比率: X.XX | 最大回撤: XX.X%
   - 综合评分: XX.X

2. 【基金名称】...

📈 详细图表: [点击查看]
⏰ 下次更新: YYYY-MM-DD
```

---

## 项目文件结构

```
fund-screener/
├── config/
│   └── settings.py          # 配置（数据库、Server酱key、筛选参数）
├── data/
│   ├── fetcher.py           # AKShare数据抓取
│   ├── database.py          # 数据库连接和操作
│   └── models.py            # SQLAlchemy模型定义
├── analysis/
│   ├── indicators.py        # 指标计算（夏普、回撤、卡玛等）
│   ├── screener.py          # 筛选逻辑和打分算法
│   └── backtest.py          # 回测模块
├── report/
│   ├── generator.py         # 报告生成
│   └── notifier.py          # Server酱推送
├── .env.example             # 环境变量示例
├── pyproject.toml           # 项目配置（uv规范）
├── requirements.txt         # Python依赖（兼容模式）
├── main.py                  # 主入口，定时任务调度
└── README.md                # 项目说明
```

---

## 开发计划

| 天数 | 任务 |
|------|------|
| 1-2 | 搭建项目结构，配置PostgreSQL，实现数据抓取模块 |
| 3-4 | 实现指标计算（年化收益、夏普比率、最大回撤、卡玛比率、月度胜率） |
| 5-6 | 实现筛选逻辑和打分算法 |
| 7-8 | 实现回测模块（持有收益+基准对比） |
| 9-10 | 集成Server酱推送，测试定时任务 |

---

## 前置准备

1. **推送渠道**（至少配置一个）：
   - Server酱：访问 http://sc.ftqq.com 注册，获取SCKEY
   - 企业微信：在企业微信群中添加机器人，复制Webhook地址
2. **数据库**：SQLite（默认，无需安装）或 PostgreSQL
3. **Python环境**：Python 3.9+

---

*创建日期：2026-02-17*

---

## 量化基金识别（v1.4.0 新增）

### 识别策略

采用**关键词匹配**策略，分为两个层次：

#### 高置信度关键词（名称匹配即判定）

| 关键词 | 说明 | 示例 |
|--------|------|------|
| 量化 | 明确的量化策略基金 | 西部利得量化成长混合A |
| 多因子 | 多因子量化模型 | 大摩多因子策略混合 |
| 对冲 | 量化对冲/市场中性策略 | 华泰柏瑞量化对冲 |
| 市场中性 | 市场中性策略 | 嘉实绝对收益市场中性 |

#### 中置信度关键词（需结合策略判断）

| 关键词 | 判断逻辑 | 说明 |
|--------|----------|------|
| 指数增强 | 结合投资策略判断 | 部分是量化增强，部分是主动增强 |
| Smart Beta | 结合投资策略判断 | 需确认是否采用量化模型 |

### 数据模型变更

```sql
-- 基金表新增量化标识
ALTER TABLE funds ADD COLUMN is_quant INT DEFAULT 0 COMMENT '是否量化基金(0-否/1-是)';
```

---

## 邮件推送功能（v1.2.0 + v1.4.0）

### 支持的邮箱服务

| 邮箱 | SMTP服务器 | 端口 | 加密方式 | 认证方式 |
|------|-----------|------|---------|----------|
| Gmail | smtp.gmail.com | 587 | TLS | 应用专用密码 |
| QQ邮箱 | smtp.qq.com | 465 | SSL | 授权码 |
| 163邮箱 | smtp.163.com | 465 | SSL | 授权码 |
| 126邮箱 | smtp.126.com | 465 | SSL | 授权码 |

### 多收件人支持（v1.4.0 新增）

```bash
# 收件人配置支持逗号分隔
EMAIL_RECEIVER=user1@example.com,user2@example.com
```

### SSL/TLS 自动适配

```python
# 根据端口自动选择加密方式
if self.smtp_port == 465:
    # SSL加密连接（QQ/163/126邮箱）
    with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
        server.login(self.smtp_user, self.smtp_password)
        server.sendmail(self.smtp_user, receivers, msg.as_string())
else:
    # TLS加密连接（Gmail等）
    with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
        server.starttls()
        server.login(self.smtp_user, self.smtp_password)
        server.sendmail(self.smtp_user, receivers, msg.as_string())
```

---

## 性能优化（v1.5.0 新增：多线程并行抓取）

### 优化前后对比

| 方案 | 26135只基金耗时 | 提升 |
|------|-----------------|------|
| 串行抓取（单线程） | ~40分钟 | - |
| 并行抓取（10线程） | ~5-10分钟 | **4-8倍** |

### 核心实现

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def init_fund_data(db, fetcher, max_workers=10):
    # 多线程并行抓取
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_single_fund, item): item for item in fund_items}
        for future in as_completed(futures):
            result = future.result()
            # 收集结果...
```

### 优化策略

1. **多线程并行抓取**：使用 ThreadPoolExecutor，默认 10 线程
2. **更新已存在基金**：不再跳过已存在的基金，每次运行都会更新最新数据
3. **批量写入数据库**：每 100 条 commit 一次

### 使用方式

```bash
# 更新所有基金（新增 + 已存在）
uv run fund-screener update-funds

# 限制数量测试
uv run fund-screener update-funds --limit 100
```

---

## 测试命令

```bash
# 测试推送功能（验证所有已配置渠道）
uv run fund-screener test-notify
```

输出示例：
```
==================================================
测试消息推送功能
==================================================

📋 渠道配置状态：
------------------------------
Server酱: ✅ 已配置
企业微信: ❌ 未配置
邮件推送: ✅ 已配置

📤 推送测试结果：
------------------------------
Server酱: ✅ 成功
邮件推送: ✅ 成功

==================================================
```
==================================================

📋 渠道配置状态：
------------------------------
Server酱: ✅ 已配置
企业微信: ❌ 未配置
   环境变量: WECOM_WEBHOOK
   获取方式: 企业微信群添加机器人获取
邮件推送: ✅ 已配置

📤 推送测试结果：
------------------------------
Server酱: ✅ 成功
邮件推送: ✅ 成功

==================================================
```