"""数据库操作模块"""

from typing import List, Optional
from datetime import date, datetime
from sqlalchemy.orm import Session
from fund_screener.data.models import (
    Fund,
    FundNav,
    FundMetrics,
    BacktestResult,
    SelectedFund,
)


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

    def batch_upsert_funds(self, funds_data: List[dict], batch_size: int = 100):
        """批量更新或插入基金信息
        
        Args:
            funds_data: 基金数据列表
            batch_size: 每批提交的数量
        """
        existing_codes = set(
            f.fund_code for f in self.db.query(Fund.fund_code).all()
        )
        
        for i, fund_data in enumerate(funds_data):
            fund_code = fund_data["fund_code"]
            if fund_code in existing_codes:
                # 更新已有记录
                fund = self.db.query(Fund).filter(Fund.fund_code == fund_code).first()
                for key, value in fund_data.items():
                    setattr(fund, key, value)
                fund.updated_at = datetime.now()
            else:
                # 插入新记录
                fund = Fund(**fund_data)
                self.db.add(fund)
            
            # 批量提交
            if (i + 1) % batch_size == 0:
                self.db.commit()
        
        # 提交剩余记录
        self.db.commit()

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

    def batch_save_nav_data(self, fund_code: str, nav_data: List[dict], batch_size: int = 100):
        """批量保存净值数据（优化版本，减少数据库提交次数）
        
        Args:
            fund_code: 基金代码
            nav_data: 净值数据列表
            batch_size: 每批提交的数量
        """
        # 先查询已存在的日期
        existing_dates = set()
        existing_records = self.db.query(FundNav.nav_date).filter(
            FundNav.fund_code == fund_code
        ).all()
        for record in existing_records:
            existing_dates.add(record.nav_date)
        
        # 过滤掉已存在的记录
        new_records = [data for data in nav_data if data["nav_date"] not in existing_dates]
        
        if not new_records:
            return
        
        # 批量添加
        for i, data in enumerate(new_records):
            nav_record = FundNav(fund_code=fund_code, **data)
            self.db.add(nav_record)
            
            # 分批提交
            if (i + 1) % batch_size == 0:
                try:
                    self.db.commit()
                except Exception:
                    self.db.rollback()
        
        # 提交剩余的记录
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()

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
