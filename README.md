# 基金筛选系统

自用基金筛选工具，重点筛选稳健增长、长期复利的基金，支持定投策略。

> **当前版本**：v1.2.0  
> **最后更新**：2026-02-17

## 版本记录

| 版本 | 日期 | 修改内容 |
|------|------|---------|
| v1.0.0 | 2026-02-17 | 初始版本，完成MVP核心功能 |
| v1.1.0 | 2026-02-17 | 新增企业微信机器人推送支持 |
| v1.2.0 | 2026-02-17 | 新增邮件推送功能，支持SMTP协议 |

## 功能特性

- 📊 **全市场基金筛选**：从所有公募基金中筛选优质标的
- 📈 **多维度指标**：夏普比率、最大回撤、卡玛比率、月度胜率
- 🎯 **综合评分**：多因子加权打分，量化基金质量
- 📉 **历史回测**：对比沪深300等基准，查看超额收益
- 📱 **多渠道推送**：支持 Server酱、企业微信机器人、邮件推送
- ⏰ **定时任务**：支持定时自动筛选和推送

## 快速开始

### 1. 安装依赖

```bash
# 使用 uv 安装依赖（推荐）
uv venv
uv pip install -r config/requirements.txt

# 或使用 pip
pip install -r config/requirements.txt
```

### 2. 配置环境变量

```bash
# 复制示例配置文件
cp config/.env.example config/.env

# 编辑 .env 文件，配置推送渠道（至少配置一个）
vim config/.env
```

**推送渠道配置（至少配置一个）：**

| 渠道 | 获取方式 | 环境变量 |
|------|---------|---------|
| Server酱 | 访问 https://sct.ftqq.com/ 注册获取SCKEY | `SERVER_CHAN_KEY` |
| 企业微信 | 在企业微信群中添加机器人，复制Webhook地址 | `WECOM_WEBHOOK` |
| 邮件 | 配置SMTP服务（Gmail/QQ邮箱/163邮箱等） | `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_RECEIVER` |

**邮件配置提示**：
- Gmail：需要在账户设置中生成应用专用密码
- QQ邮箱：需要在设置中开启SMTP服务并获取授权码
- 163邮箱：需要在设置中开启SMTP服务并获取授权码

### 3. 初始化数据库

```bash
# 初始化数据库表
python main.py init
```

### 4. 首次运行

```bash
# 方案一：完整流程（推荐）
python main.py run-all

# 方案二：分步执行
python main.py update-funds  # 更新基金列表
python main.py screen        # 执行筛选
python main.py backtest      # 执行回测
python main.py notify        # 推送报告
```

## 使用指南

### 命令说明

```bash
# 初始化数据库
python main.py init

# 更新基金基础数据（首次运行需要）
python main.py update-funds

# 执行筛选
python main.py screen

# 执行回测
python main.py backtest

# 推送报告到微信/企业微信
python main.py notify

# 测试推送功能（验证Server酱和企业微信配置）
python main.py test-notify

# 完整流程（筛选+回测+推送）
python main.py run-all

# 启动定时任务（每周一 09:00 自动执行）
python main.py schedule
```

### 筛选标准

系统会从以下几个维度评估基金：

**硬性门槛**：
- 成立时间 > 3年
- 基金规模 > 2亿
- 最大回撤 < 25%
- 夏普比率 > 0.8
- 近3年年化收益 > 5%

**评分权重**：
- 3年年化收益：30%
- 夏普比率：25%
- 卡玛比率：20%
- 月度胜率：15%
- 回撤控制：10%

### 配置文件

编辑 `config/settings.py` 可以调整筛选参数：

```python
SCREENING_CONFIG = {
    "min_establish_years": 3,      # 最少成立年限
    "min_fund_size": 2.0,          # 最小规模（亿）
    "max_drawdown": 25.0,          # 最大回撤上限
    "min_sharpe": 0.8,             # 最小夏普比率
    "min_annual_return": 5.0,      # 最小年化收益
    "top_n": 10,                   # 输出前N只基金
}
```

## 项目结构

```
fund-screener/
├── config/
│   ├── settings.py          # 配置文件
│   ├── requirements.txt     # Python依赖
│   └── .env.example         # 环境变量示例
├── data/
│   ├── models.py            # 数据库模型
│   ├── database.py          # 数据库操作
│   └── fetcher.py           # 数据抓取（AKShare）
├── analysis/
│   ├── indicators.py        # 指标计算
│   ├── screener.py          # 筛选逻辑
│   └── backtest.py          # 回测模块
├── report/
│   ├── generator.py         # 报告生成
│   └── notifier.py          # 消息推送
├── main.py                  # 主入口
└── README.md
```

## 数据源

- **基金数据**：AKShare（免费）
- **基准指数**：沪深300、中证全债等

## 免责声明

- 本工具仅供参考，不构成投资建议
- 基金过往业绩不代表未来表现
- 投资有风险，入市需谨慎

## License

MIT