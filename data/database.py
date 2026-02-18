"""数据库操作模块"""

from typing import List, Optional
from datetime import date, datetime
from sqlalchemy.orm import Session
from data.models import Fund, FundNav, FundMetrics, BacktestResult, SelectedFund


class FundRepository:
    """基金数据仓库"""

    def __init__(self, db: Session):
        self.db = db

    def get_all_funds(self) -> List[Fund]:
        """获取所有基金"""
        return self.db.query(Fund).all()

    def get_fund_by_code(self, fund_code: str) -> Optional[Fund]:
        """根据代码获取基金"""
        return self.db.query(Fund).filter(Fund.fund_code == fund_code).first()

    def upsert_fund(self, fund_data: dict) -> Fund:
        """更新或插入基金信息"""
        fund = self.get_fund_by_code(fund_data["fund_code"])
        if fund:
            for key, value in fund_data.items():
                setattr(fund, key, value)
            fund.updated_at = datetime.now()
        else:
            fund = Fund(**fund_data)
            self.db.add(fund)
        self.db.commit()
        return fund

    def get_fund_nav(
        self, fund_code: str, start_date: date = None, end_date: date = None
    ) -> List[FundNav]:
        """获取基金净值历史"""
        query = self.db.query(FundNav).filter(FundNav.fund_code == fund_code)
        if start_date:
            query = query.filter(FundNav.nav_date >= start_date)
        if end_date:
            query = query.filter(FundNav.nav_date <= end_date)
        return query.order_by(FundNav.nav_date).all()

    def save_nav_data(self, fund_code: str, nav_data: List[dict]):
        """批量保存净值数据"""
        for data in nav_data:
            existing = (
                self.db.query(FundNav)
                .filter(
                    FundNav.fund_code == fund_code, FundNav.nav_date == data["nav_date"]
                )
                .first()
            )

            if not existing:
                nav_record = FundNav(fund_code=fund_code, **data)
                self.db.add(nav_record)

        self.db.commit()

    def save_metrics(self, fund_code: str, metrics: dict):
        """保存基金指标"""
        metrics_record = FundMetrics(
            fund_code=fund_code, calc_date=date.today(), **metrics
        )
        self.db.add(metrics_record)
        self.db.commit()

    def get_metrics(self, fund_code: str) -> Optional[FundMetrics]:
        """获取最新指标"""
        return (
            self.db.query(FundMetrics)
            .filter(FundMetrics.fund_code == fund_code)
            .order_by(FundMetrics.calc_date.desc())
            .first()
        )

    def save_backtest(self, fund_code: str, period: int, result: dict):
        """保存回测结果"""
        backtest = BacktestResult(fund_code=fund_code, period_years=period, **result)
        self.db.add(backtest)
        self.db.commit()

    def save_selected_funds(self, funds: List[dict]):
        """保存筛选结果"""
        # 清空旧的筛选结果
        self.db.query(SelectedFund).delete()

        # 插入新的结果
        for fund_data in funds:
            selected = SelectedFund(screening_date=date.today(), **fund_data)
            self.db.add(selected)

        self.db.commit()

    def get_selected_funds(self) -> List[SelectedFund]:
        """获取最新筛选结果"""
        return self.db.query(SelectedFund).order_by(SelectedFund.rank).all()
