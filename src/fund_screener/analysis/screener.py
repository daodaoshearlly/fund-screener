"""基金筛选模块"""

import pandas as pd
from datetime import date, datetime
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from loguru import logger

from fund_screener.config.settings import SCREENING_CONFIG
from fund_screener.data.database import FundRepository
from fund_screener.data.fetcher import FundDataFetcher
from fund_screener.analysis.indicators import (
    FundIndicators,
    filter_funds_by_metrics,
    calculate_fund_score,
    calculate_manager_score,
)


class FundScreener:
    """基金筛选器"""

    def __init__(self, db: Session, fetcher: FundDataFetcher):
        self.db = db
        self.repo = FundRepository(db)
        self.fetcher = fetcher
        self.config = SCREENING_CONFIG

    def screen_funds(self, limit: int = None) -> List[Dict]:
        """执行基金筛选

        Args:
            limit: 限制处理的基金数量（测试用）

        Returns:
            筛选结果列表
        """
        logger.info("开始基金筛选...")

        # 获取所有基金
        funds = self.repo.get_all_funds()

        if limit:
            funds = funds[:limit]

        logger.info(f"共 {len(funds)} 只基金待筛选")

        # 获取配置的基金类型
        fund_types = self.config.get("fund_types", [])
        # 处理"全部"的情况
        if "全部" in fund_types or not fund_types:
            fund_types = None

        qualified_funds = []

        for idx, fund in enumerate(funds):
            # 检查基金类型
            if fund_types and fund.fund_type not in fund_types:
                continue

            # 检查成立年限
            if fund.establish_date:
                years_since_establish = (date.today() - fund.establish_date).days / 365
                if years_since_establish < self.config["min_establish_years"]:
                    continue

            # 检查基金规模
            if fund.fund_size and fund.fund_size < self.config["min_fund_size"]:
                continue

            # 获取净值数据（仅从数据库，不自动抓取）
            nav_data = self.repo.get_fund_nav(fund.fund_code)

            if not nav_data or len(nav_data) < 252 * 3 * 0.8:
                continue

            # 转换为DataFrame
            nav_df = pd.DataFrame(
                [
                    {
                        "nav_date": n.nav_date,
                        "nav": n.nav,
                        "daily_return": n.daily_return,
                    }
                    for n in nav_data
                ]
            )

            # 计算指标
            metrics = FundIndicators.calculate_all_metrics(nav_df)

            if not metrics:
                continue

            # 硬性门槛筛选
            if not filter_funds_by_metrics(metrics, self.config):
                continue

            # 计算基金经理评分
            manager_score = None
            if fund.manager and "manager_score" in self.config["weights"]:
                manager_score = calculate_manager_score(
                    self.db, fund.manager, self.config.get("min_manager_exp_years", 1)
                )
                if manager_score is not None:
                    metrics["manager_score"] = manager_score

            # 计算综合评分
            score = calculate_fund_score(metrics, self.config["weights"])

            if score:
                metrics["total_score"] = score

                qualified_funds.append(
                    {
                        "fund_code": fund.fund_code,
                        "fund_name": fund.fund_name,
                        "fund_type": fund.fund_type,
                        "metrics": metrics,
                    }
                )

                # 保存指标到数据库
                self.repo.save_metrics(fund.fund_code, metrics)

            if (idx + 1) % 1000 == 0:
                logger.info(
                    f"已处理 {idx + 1}/{len(funds)} 只基金，通过 {len(qualified_funds)} 只"
                )

        logger.info(f"筛选完成，共 {len(qualified_funds)} 只基金通过硬性门槛")

        # 按评分排序
        qualified_funds.sort(key=lambda x: x["metrics"]["total_score"], reverse=True)

        # 取前N名
        top_funds = qualified_funds[: self.config["top_n"]]

        # 保存筛选结果
        selected_data = [
            {
                "fund_code": f["fund_code"],
                "fund_name": f["fund_name"],
                "rank": idx + 1,
                "total_score": f["metrics"]["total_score"],
                "annual_return_3y": f["metrics"].get("annual_return_3y", 0),
                "sharpe_ratio": f["metrics"].get("sharpe_ratio", 0),
                "max_drawdown": f["metrics"].get("max_drawdown", 0),
            }
            for idx, f in enumerate(top_funds)
        ]

        self.repo.save_selected_funds(selected_data)

        logger.info(f"已保存 Top {len(top_funds)} 基金")

        return top_funds

    def get_screening_summary(self) -> Dict:
        """获取筛选汇总信息"""
        selected = self.repo.get_selected_funds()

        if not selected:
            return {"message": "暂无筛选结果"}

        return {
            "total_selected": len(selected),
            "screening_date": selected[0].screening_date.strftime("%Y-%m-%d"),
            "avg_score": sum(f.total_score for f in selected) / len(selected),
            "funds": [
                {
                    "rank": f.rank,
                    "code": f.fund_code,
                    "name": f.fund_name,
                    "score": f.total_score,
                    "return_3y": f.annual_return_3y,
                    "sharpe": f.sharpe_ratio,
                    "drawdown": f.max_drawdown,
                }
                for f in selected
            ],
        }
