"""SQLAlchemy数据库模型定义"""

from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Float, Index, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from fund_screener.config.settings import (
    DATABASE_URL,
    DB_TYPE,
    MARIADB_URL,
    SQLITE_URL,
)

# 数据库选择逻辑：
# 1. 优先使用 DATABASE_URL 环境变量（向后兼容）
# 2. 根据 DB_TYPE 选择数据库类型
# 3. 默认使用 MariaDB
if DATABASE_URL:
    engine_url = DATABASE_URL
elif DB_TYPE == "mariadb":
    engine_url = MARIADB_URL
elif DB_TYPE == "postgresql":
    from fund_screener.config.settings import POSTGRESQL_URL

    engine_url = POSTGRESQL_URL
else:
    engine_url = SQLITE_URL
engine = create_engine(engine_url, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Fund(Base):
    """基金基础信息表"""

    __tablename__ = "funds"

    fund_code = Column(String(10), primary_key=True, comment="基金代码")
    fund_name = Column(String(100), nullable=False, comment="基金名称")
    fund_type = Column(String(50), comment="基金类型")
    manager = Column(String(100), comment="基金经理")
    establish_date = Column(Date, comment="成立日期")
    fund_size = Column(Float, comment="基金规模（亿）")
    company = Column(String(100), comment="基金公司")
    is_quant = Column(Integer, default=0, comment="是否量化基金(0-否/1-是)")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )


class FundNav(Base):
    """基金每日净值表"""

    __tablename__ = "fund_nav"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(10), nullable=False, index=True, comment="基金代码")
    nav_date = Column(Date, nullable=False, index=True, comment="净值日期")
    nav = Column(Float, comment="单位净值")
    accumulated_nav = Column(Float, comment="累计净值")
    daily_return = Column(Float, comment="日涨跌幅")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    __table_args__ = ({"sqlite_autoincrement": True},)


class FundMetrics(Base):
    """基金风险指标计算表"""

    __tablename__ = "fund_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(10), nullable=False, index=True, comment="基金代码")
    calc_date = Column(Date, nullable=False, comment="计算日期")

    # 收益指标
    annual_return_1y = Column(Float, comment="近1年年化收益")
    annual_return_3y = Column(Float, comment="近3年年化收益")
    annual_return_5y = Column(Float, comment="近5年年化收益")

    # 风险指标
    sharpe_ratio = Column(Float, comment="夏普比率")
    max_drawdown = Column(Float, comment="最大回撤")
    volatility = Column(Float, comment="年化波动率")
    calmar_ratio = Column(Float, comment="卡玛比率")
    monthly_win_rate = Column(Float, comment="月度胜率")
    manager_score = Column(Float, comment="基金经理评分")

    # 综合评分
    total_score = Column(Float, comment="综合评分")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    __table_args__ = ({"sqlite_autoincrement": True},)


class BacktestResult(Base):
    """回测结果表"""

    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(10), nullable=False, index=True, comment="基金代码")
    period_years = Column(Integer, nullable=False, comment="回测年限")

    # 基金收益
    total_return = Column(Float, comment="累计收益")
    annual_return = Column(Float, comment="年化收益")
    max_drawdown = Column(Float, comment="最大回撤")

    # 基准对比
    benchmark_code = Column(String(10), comment="基准代码")
    benchmark_return = Column(Float, comment="基准累计收益")
    benchmark_annual = Column(Float, comment="基准年化收益")
    excess_return = Column(Float, comment="超额收益")

    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    __table_args__ = ({"sqlite_autoincrement": True},)


class SelectedFund(Base):
    """本次筛选出的基金"""

    __tablename__ = "selected_funds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(10), nullable=False, comment="基金代码")
    fund_name = Column(String(100), comment="基金名称")
    rank = Column(Integer, comment="排名")
    total_score = Column(Float, comment="综合评分")
    annual_return_3y = Column(Float, comment="近3年收益")
    sharpe_ratio = Column(Float, comment="夏普比率")
    max_drawdown = Column(Float, comment="最大回撤")
    screening_date = Column(Date, comment="筛选日期")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    __table_args__ = ({"sqlite_autoincrement": True},)


def init_db():
    """初始化数据库表"""
    Base.metadata.create_all(bind=engine)
    print(f"✅ 数据库初始化完成: {engine_url}")


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
