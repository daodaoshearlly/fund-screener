# 基金筛选系统配置

import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent.parent

# 数据库类型选择: sqlite / mariadb / postgresql
DB_TYPE = os.getenv("DB_TYPE", "mariadb")

# MariaDB 配置（默认）
MARIADB_HOST = os.getenv("MARIADB_HOST", "10.12.252.20")
MARIADB_PORT = os.getenv("MARIADB_PORT", "3306")
MARIADB_USER = os.getenv("MARIADB_USER", "fund_screener")
MARIADB_PASSWORD = os.getenv("MARIADB_PASSWORD", "H8QENPm6pmiyCpQE")
MARIADB_DATABASE = os.getenv("MARIADB_DATABASE", "fund_screener")
MARIADB_URL = f"mysql+pymysql://{MARIADB_USER}:{MARIADB_PASSWORD}@{MARIADB_HOST}:{MARIADB_PORT}/{MARIADB_DATABASE}"

# PostgreSQL 配置（保留但不启用）
# PG_HOST = os.getenv("PG_HOST", "10.12.252.20")
# PG_PORT = os.getenv("PG_PORT", "5432")
# PG_USER = os.getenv("PG_USER", "fund_screener")
# PG_PASSWORD = os.getenv("PG_PASSWORD", "H8QENPm6pmiyCpQE")
# PG_DATABASE = os.getenv("PG_DATABASE", "fund_screener")
# POSTGRESQL_URL = f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DATABASE}"

# SQLite 默认路径
SQLITE_URL = f"sqlite:///{BASE_DIR}/fund_screener.db"

# 兼容旧的 DATABASE_URL 环境变量（向后兼容）
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Server酱配置
SERVER_CHAN_KEY = os.getenv("SERVER_CHAN_KEY", "")

# 企业微信机器人配置
WECOM_WEBHOOK = os.getenv("WECOM_WEBHOOK", "")

# 邮件推送配置
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER", "")  # 接收者邮箱（多个用逗号分隔）

# 数据抓取配置
AKSHARE_TIMEOUT = 30  # AKShare请求超时时间（秒）
MAX_RETRIES = 3  # 重试次数
RETRY_DELAY = 2  # 重试间隔（秒）

# 并行抓取配置
MAX_WORKERS = 10  # 并行线程数
NAV_BATCH_SIZE = 100  # NAV数据批量写入大小

# 筛选参数配置（从环境变量读取，支持在 .env 中配置）
SCREENING_CONFIG = {
    "fund_types": os.getenv("SCREEN_FUND_TYPES", "全部").split(","),  # 基金类型
    "return_years": int(os.getenv("SCREEN_RETURN_YEARS", "3")),  # 收益计算年限
    "min_establish_years": float(os.getenv("SCREEN_MIN_ESTABLISH_YEARS", "3")),  # 最少成立年限
    "min_fund_size": float(os.getenv("SCREEN_MIN_SIZE", "2.0")),  # 最小规模（亿）
    "max_drawdown": float(os.getenv("SCREEN_MAX_DRAWDOWN", "25.0")),  # 最大回撤上限（%）
    "min_sharpe": float(os.getenv("SCREEN_MIN_SHARPE", "0.8")),  # 最小夏普比率
    "min_annual_return": float(os.getenv("SCREEN_MIN_RETURN", "5.0")),  # 最小年化收益（%）
    "min_manager_exp_years": int(os.getenv("SCREEN_MIN_MANAGER_EXP", "1")),  # 基金经理最少任职年限
    # 打分权重（总和应为100）
    "weights": {
        "annual_return_3y": 25,  # 3年年化收益权重
        "sharpe_ratio": 20,  # 夏普比率权重
        "calmar_ratio": 15,  # 卡玛比率权重
        "monthly_win_rate": 10,  # 月度胜率权重
        "max_drawdown_control": 10,  # 回撤控制权重
        "manager_score": 20,  # 基金经理评分权重
    },
    "top_n": int(os.getenv("SCREEN_TOP_N", "10")),  # 输出前N只基金
}

# 自动更新数据配置
AUTO_UPDATE_DATA = os.getenv("AUTO_UPDATE_DATA", "true").lower() == "true"

# 回测配置
BACKTEST_CONFIG = {
    "periods": [3, 5],  # 回测年限
    "benchmarks": {
        "stock": "000300",  # 沪深300
        "bond": "H11001",  # 中证全债
    },
}

# 定时任务配置（每天早上7:00运行）
SCHEDULE_CONFIG = {
    "hour": 7,  # 7点
    "minute": 0,  # 0分
}
