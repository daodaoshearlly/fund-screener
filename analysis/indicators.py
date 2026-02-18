"""基金指标计算模块"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from loguru import logger


class FundIndicators:
    """基金指标计算器"""

    @staticmethod
    def calculate_annual_return(
        nav_series: pd.Series, years: int = 3
    ) -> Optional[float]:
        """计算年化收益率

        Args:
            nav_series: 净值序列（按时间升序排列）
            years: 计算年限

        Returns:
            年化收益率（百分比）
        """
        if len(nav_series) < years * 252 * 0.8:  # 至少需要80%的数据
            return None

        try:
            # 取最近N年的数据
            start_nav = nav_series.iloc[0]
            end_nav = nav_series.iloc[-1]

            if start_nav <= 0:
                return None

            total_return = (end_nav / start_nav) - 1
            annual_return = (1 + total_return) ** (1 / years) - 1

            return annual_return * 100  # 转换为百分比
        except Exception as e:
            logger.error(f"计算年化收益失败: {e}")
            return None

    @staticmethod
    def calculate_sharpe_ratio(
        returns: pd.Series, risk_free_rate: float = 0.03
    ) -> Optional[float]:
        """计算夏普比率

        Args:
            returns: 日收益率序列（小数形式）
            risk_free_rate: 无风险利率（年化，默认3%）

        Returns:
            夏普比率
        """
        if len(returns) < 60:  # 至少需要60个数据点
            return None

        try:
            # 日无风险利率
            daily_rf = (1 + risk_free_rate) ** (1 / 252) - 1

            # 超额收益
            excess_returns = returns - daily_rf

            # 年化夏普比率
            sharpe = np.sqrt(252) * excess_returns.mean() / returns.std()

            return sharpe
        except Exception as e:
            logger.error(f"计算夏普比率失败: {e}")
            return None

    @staticmethod
    def calculate_max_drawdown(nav_series: pd.Series) -> Optional[float]:
        """计算最大回撤

        Args:
            nav_series: 净值序列（按时间升序排列）

        Returns:
            最大回撤（百分比，负值）
        """
        if len(nav_series) < 60:
            return None

        try:
            # 计算历史最高点
            rolling_max = nav_series.expanding().max()

            # 计算回撤
            drawdown = (nav_series - rolling_max) / rolling_max

            # 最大回撤
            max_drawdown = drawdown.min()

            return max_drawdown * 100  # 转换为百分比
        except Exception as e:
            logger.error(f"计算最大回撤失败: {e}")
            return None

    @staticmethod
    def calculate_volatility(returns: pd.Series) -> Optional[float]:
        """计算年化波动率

        Args:
            returns: 日收益率序列（小数形式）

        Returns:
            年化波动率（百分比）
        """
        if len(returns) < 60:
            return None

        try:
            volatility = np.sqrt(252) * returns.std()
            return volatility * 100  # 转换为百分比
        except Exception as e:
            logger.error(f"计算波动率失败: {e}")
            return None

    @staticmethod
    def calculate_calmar_ratio(
        nav_series: pd.Series, years: int = 3
    ) -> Optional[float]:
        """计算卡玛比率（年化收益/最大回撤的绝对值）

        Args:
            nav_series: 净值序列
            years: 计算年限

        Returns:
            卡玛比率
        """
        annual_return = FundIndicators.calculate_annual_return(nav_series, years)
        max_drawdown = FundIndicators.calculate_max_drawdown(nav_series)

        if annual_return is None or max_drawdown is None or max_drawdown >= 0:
            return None

        try:
            calmar = annual_return / abs(max_drawdown)
            return calmar
        except Exception as e:
            logger.error(f"计算卡玛比率失败: {e}")
            return None

    @staticmethod
    def calculate_monthly_win_rate(
        returns: pd.Series, dates: pd.Series
    ) -> Optional[float]:
        """计算月度胜率（每月正收益的概率）

        Args:
            returns: 日收益率序列
            dates: 日期序列

        Returns:
            月度胜率（0-1之间）
        """
        if len(returns) < 60:
            return None

        try:
            # 创建DataFrame
            df = pd.DataFrame({"date": dates, "return": returns})
            df["date"] = pd.to_datetime(df["date"])
            df["year_month"] = df["date"].dt.to_period("M")

            # 按月汇总收益
            monthly_returns = df.groupby("year_month")["return"].sum()

            # 计算胜率
            win_rate = (monthly_returns > 0).sum() / len(monthly_returns)

            return win_rate
        except Exception as e:
            logger.error(f"计算月度胜率失败: {e}")
            return None

    @staticmethod
    def calculate_all_metrics(nav_df: pd.DataFrame) -> Dict:
        """计算所有指标

        Args:
            nav_df: DataFrame包含nav_date, nav, daily_return列

        Returns:
            指标字典
        """
        metrics = {}

        if nav_df.empty or len(nav_df) < 60:
            return metrics

        nav_series = nav_df["nav"]
        returns = nav_df["daily_return"].dropna()
        dates = nav_df["nav_date"]

        # 计算各期限指标
        periods = {"1y": 252, "3y": 252 * 3, "5y": 252 * 5}

        for period_name, days in periods.items():
            if len(nav_series) >= days * 0.8:
                recent_nav = nav_series.tail(days)
                recent_returns = returns.tail(days)

                years = days / 252

                # 年化收益
                annual_return = FundIndicators.calculate_annual_return(
                    recent_nav, int(years)
                )
                if annual_return is not None:
                    metrics[f"annual_return_{period_name}"] = round(annual_return, 2)

        # 风险指标（基于最近3年）
        if len(nav_series) >= 252 * 3 * 0.8:
            recent_nav = nav_series.tail(252 * 3)
            recent_returns = returns.tail(252 * 3)

            # 夏普比率
            sharpe = FundIndicators.calculate_sharpe_ratio(recent_returns)
            if sharpe is not None:
                metrics["sharpe_ratio"] = round(sharpe, 2)

            # 最大回撤
            max_dd = FundIndicators.calculate_max_drawdown(recent_nav)
            if max_dd is not None:
                metrics["max_drawdown"] = round(max_dd, 2)

            # 波动率
            vol = FundIndicators.calculate_volatility(recent_returns)
            if vol is not None:
                metrics["volatility"] = round(vol, 2)

            # 卡玛比率
            calmar = FundIndicators.calculate_calmar_ratio(recent_nav, 3)
            if calmar is not None:
                metrics["calmar_ratio"] = round(calmar, 2)

            # 月度胜率
            win_rate = FundIndicators.calculate_monthly_win_rate(
                recent_returns, dates.tail(len(recent_returns))
            )
            if win_rate is not None:
                metrics["monthly_win_rate"] = round(win_rate, 2)

        return metrics


def filter_funds_by_metrics(metrics: Dict, config: Dict) -> bool:
    """根据硬性门槛筛选基金

    Args:
        metrics: 指标字典
        config: 筛选配置

    Returns:
        是否通过筛选
    """
    # 检查必需指标是否存在
    required_metrics = ["annual_return_3y", "sharpe_ratio", "max_drawdown"]
    for metric in required_metrics:
        if metric not in metrics:
            return False

    # 硬性门槛检查
    if metrics.get("max_drawdown", 0) > config["max_drawdown"]:
        return False

    if metrics.get("sharpe_ratio", 0) < config["min_sharpe"]:
        return False

    if metrics.get("annual_return_3y", 0) < config["min_annual_return"]:
        return False

    return True


def calculate_fund_score(metrics: Dict, weights: Dict) -> Optional[float]:
    """计算基金综合评分

    Args:
        metrics: 指标字典
        weights: 权重配置

    Returns:
        综合评分（0-100）
    """
    score = 0
    total_weight = sum(weights.values())

    # 收益评分（越高越好，假设10%为满分）
    if "annual_return_3y" in metrics:
        return_score = min(metrics["annual_return_3y"] / 10, 1) * 100
        score += return_score * weights["annual_return_3y"] / total_weight

    # 夏普评分（假设2.0为满分）
    if "sharpe_ratio" in metrics:
        sharpe_score = min(metrics["sharpe_ratio"] / 2, 1) * 100
        score += sharpe_score * weights["sharpe_ratio"] / total_weight

    # 卡玛评分（假设3.0为满分）
    if "calmar_ratio" in metrics:
        calmar_score = min(metrics["calmar_ratio"] / 3, 1) * 100
        score += calmar_score * weights["calmar_ratio"] / total_weight

    # 胜率评分（本身就是百分比）
    if "monthly_win_rate" in metrics:
        win_rate_score = metrics["monthly_win_rate"] * 100
        score += win_rate_score * weights["monthly_win_rate"] / total_weight

    # 回撤控制评分（越低越好，假设-10%为满分）
    if "max_drawdown" in metrics:
        drawdown = abs(metrics["max_drawdown"])
        dd_score = max(0, (30 - drawdown) / 30) * 100  # 30%回撤为0分
        score += dd_score * weights["max_drawdown_control"] / total_weight

    return round(score, 2)
