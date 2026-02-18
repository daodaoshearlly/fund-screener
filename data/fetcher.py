"""AKShare数据抓取模块"""

import time
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from loguru import logger
from config.settings import AKSHARE_TIMEOUT, MAX_RETRIES, RETRY_DELAY


class FundDataFetcher:
    """基金数据抓取器"""

    def __init__(self):
        self.session = None

    def _retry_fetch(self, func, *args, **kwargs):
        """带重试机制的数据抓取"""
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"抓取失败 (尝试 {attempt + 1}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error(f"抓取最终失败: {e}")
                    raise

    def fetch_all_fund_list(self) -> pd.DataFrame:
        """获取所有基金列表"""
        logger.info("正在获取基金列表...")
        df = self._retry_fetch(ak.fund_name_em)

        # 数据清洗
        df = df.rename(
            columns={
                "基金代码": "fund_code",
                "基金简称": "fund_name",
                "基金类型": "fund_type",
            }
        )

        # 只保留需要的列
        columns = ["fund_code", "fund_name", "fund_type"]
        df = df[[col for col in columns if col in df.columns]]

        logger.info(f"获取到 {len(df)} 只基金")
        return df

    def fetch_fund_info(self, fund_code: str) -> Optional[Dict]:
        """获取基金详细信息"""
        try:
            # 获取基金概况
            info_df = self._retry_fetch(
                ak.fund_individual_basic_info_xq, symbol=fund_code
            )

            if info_df.empty:
                return None

            # 解析基金信息
            info = {}
            for _, row in info_df.iterrows():
                key = row.get("名称", "")
                value = row.get("内容", "")

                if "成立日期" in key:
                    try:
                        info["establish_date"] = pd.to_datetime(value).date()
                    except:
                        pass
                elif "基金规模" in key:
                    try:
                        info["fund_size"] = float(value.replace("亿元", "").strip())
                    except:
                        pass
                elif "基金管理人" in key:
                    info["company"] = value
                elif "基金经理" in key:
                    info["manager"] = value

            return info
        except Exception as e:
            logger.error(f"获取基金 {fund_code} 信息失败: {e}")
            return None

    def fetch_fund_nav(
        self, fund_code: str, start_date: str = None, end_date: str = None
    ) -> pd.DataFrame:
        """获取基金净值历史"""
        # 默认获取最近5年数据
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365 * 5)).strftime("%Y%m%d")

        try:
            df = self._retry_fetch(
                ak.fund_open_fund_daily_em,
                fund=fund_code,
                start_date=start_date,
                end_date=end_date,
            )

            if df.empty:
                return pd.DataFrame()

            # 数据清洗
            df = df.rename(
                columns={
                    "净值日期": "nav_date",
                    "单位净值": "nav",
                    "累计净值": "accumulated_nav",
                    "日增长率": "daily_return",
                }
            )

            # 转换日期格式
            df["nav_date"] = pd.to_datetime(df["nav_date"]).dt.date

            # 转换数值类型
            for col in ["nav", "accumulated_nav", "daily_return"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            # 日涨跌幅转换为小数
            if "daily_return" in df.columns:
                df["daily_return"] = df["daily_return"] / 100

            # 按日期升序排列
            df = df.sort_values("nav_date")

            return df
        except Exception as e:
            logger.error(f"获取基金 {fund_code} 净值失败: {e}")
            return pd.DataFrame()

    def fetch_benchmark_data(
        self, symbol: str = "000300", start_date: str = None, end_date: str = None
    ) -> pd.DataFrame:
        """获取基准指数数据（沪深300等）"""
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365 * 5)).strftime("%Y%m%d")

        try:
            # 尝试获取指数历史行情
            df = self._retry_fetch(
                ak.index_zh_a_hist,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
            )

            if df.empty:
                return pd.DataFrame()

            # 数据清洗
            df = df.rename(
                columns={
                    "日期": "date",
                    "收盘": "close",
                }
            )

            df["date"] = pd.to_datetime(df["date"]).dt.date
            df["close"] = pd.to_numeric(df["close"], errors="coerce")

            # 计算日收益率
            df["daily_return"] = df["close"].pct_change()

            return df[["date", "close", "daily_return"]]
        except Exception as e:
            logger.error(f"获取基准 {symbol} 数据失败: {e}")
            return pd.DataFrame()


def init_fund_data(db, fetcher: FundDataFetcher, limit: int = None):
    """初始化基金基础数据"""
    from data.database import FundRepository

    repo = FundRepository(db)

    # 获取基金列表
    fund_list = fetcher.fetch_all_fund_list()

    if limit:
        fund_list = fund_list.head(limit)

    logger.info(f"开始初始化 {len(fund_list)} 只基金的基础信息...")

    for idx, row in fund_list.iterrows():
        fund_code = row["fund_code"]

        # 检查是否已存在
        existing = repo.get_fund_by_code(fund_code)
        if existing:
            continue

        # 获取详细信息
        info = fetcher.fetch_fund_info(fund_code)

        if info:
            fund_data = {
                "fund_code": fund_code,
                "fund_name": row["fund_name"],
                "fund_type": row.get("fund_type", ""),
                **info,
            }
            repo.upsert_fund(fund_data)

            if (idx + 1) % 100 == 0:
                logger.info(f"已处理 {idx + 1}/{len(fund_list)} 只基金")

        # 避免请求过快
        time.sleep(0.5)

    logger.info("基金基础数据初始化完成")
