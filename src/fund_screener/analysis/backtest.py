"""基金回测模块"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional
from loguru import logger

from fund_screener.data.fetcher import FundDataFetcher
from fund_screener.data.database import FundRepository


class FundBacktest:
    """基金回测器"""

    def __init__(self, db, fetcher: FundDataFetcher):
        self.db = db
        self.repo = FundRepository(db)
        self.fetcher = fetcher

    def backtest_fund(self, fund_code: str, years: int = 3) -> Optional[Dict]:
        """回测单只基金

        Args:
            fund_code: 基金代码
            years: 回测年限

        Returns:
            回测结果字典
        """
        # 获取基金净值数据
        nav_data = self.repo.get_fund_nav(fund_code)

        if not nav_data or len(nav_data) < years * 252 * 0.8:
            logger.warning(f"基金 {fund_code} 数据不足，无法回测")
            return None

        # 转换为DataFrame
        nav_df = pd.DataFrame([{"date": n.nav_date, "nav": n.nav} for n in nav_data])

        nav_df = nav_df.sort_values("date")

        # 获取回测起止日期
        end_date = nav_df["date"].max()
        start_date = end_date - timedelta(days=365 * years)

        # 截取回测期间数据
        backtest_df = nav_df[nav_df["date"] >= start_date].copy()

        if len(backtest_df) < years * 252 * 0.5:
            logger.warning(f"基金 {fund_code} 回测期间数据不足")
            return None

        # 计算基金收益
        start_nav = backtest_df["nav"].iloc[0]
        end_nav = backtest_df["nav"].iloc[-1]

        if start_nav <= 0:
            return None

        total_return = (end_nav / start_nav) - 1
        annual_return = (1 + total_return) ** (1 / years) - 1

        # 计算最大回撤
        rolling_max = backtest_df["nav"].expanding().max()
        drawdown = (backtest_df["nav"] - rolling_max) / rolling_max
        max_drawdown = drawdown.min()

        result = {
            "total_return": round(total_return * 100, 2),
            "annual_return": round(annual_return * 100, 2),
            "max_drawdown": round(max_drawdown * 100, 2),
        }

        return result

    def backtest_with_benchmark(
        self, fund_code: str, years: int = 3, benchmark: str = "000300"
    ) -> Optional[Dict]:
        """带基准对比的回测

        Args:
            fund_code: 基金代码
            years: 回测年限
            benchmark: 基准代码（默认沪深300）

        Returns:
            回测结果字典
        """
        # 基金回测
        fund_result = self.backtest_fund(fund_code, years)

        if not fund_result:
            return None

        # 获取基金结束日期
        nav_data = self.repo.get_fund_nav(fund_code)
        if not nav_data:
            return fund_result

        end_date = max(n.nav_date for n in nav_data)
        start_date = end_date - timedelta(days=365 * years)

        # 获取基准数据
        benchmark_df = self.fetcher.fetch_benchmark_data(
            symbol=benchmark,
            start_date=start_date.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d"),
        )

        if benchmark_df.empty:
            logger.warning(f"基准 {benchmark} 数据获取失败")
            return fund_result

        # 计算基准收益
        benchmark_start = benchmark_df["close"].iloc[0]
        benchmark_end = benchmark_df["close"].iloc[-1]

        if benchmark_start <= 0:
            return fund_result

        benchmark_total = (benchmark_end / benchmark_start) - 1
        benchmark_annual = (1 + benchmark_total) ** (1 / years) - 1

        excess_return = fund_result["total_return"] - benchmark_total * 100

        result = {
            **fund_result,
            "benchmark_code": benchmark,
            "benchmark_return": round(benchmark_total * 100, 2),
            "benchmark_annual": round(benchmark_annual * 100, 2),
            "excess_return": round(excess_return, 2),
        }

        # 保存回测结果
        self.repo.save_backtest(fund_code, years, result)

        return result

    def batch_backtest(self, fund_codes: list, years_list: list = [3, 5]) -> Dict:
        """批量回测

        Args:
            fund_codes: 基金代码列表
            years_list: 回测年限列表

        Returns:
            回测结果汇总
        """
        results = {}

        for fund_code in fund_codes:
            fund_results = {}

            for years in years_list:
                result = self.backtest_with_benchmark(fund_code, years)
                if result:
                    fund_results[f"{years}y"] = result

            if fund_results:
                results[fund_code] = fund_results

        return results
