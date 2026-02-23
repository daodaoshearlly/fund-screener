"""AKShare数据抓取模块"""

import time
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from loguru import logger
from fund_screener.config.settings import AKSHARE_TIMEOUT, MAX_RETRIES, RETRY_DELAY


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

    def fetch_fund_info(self, fund_code: str, skip_retry: bool = False) -> Optional[Dict]:
        """获取基金详细信息
        
        注意：蛋卷基金 API (danjuanfunds.com) 部分基金不支持：
        - result_code=600001: 该基金暂不销售
        - 部分字段缺失：数据不完整
        这些情况属于正常，返回 None 跳过即可
        """
        try:
            # 获取基金概况（失败直接跳过，不重试）
            if skip_retry:
                info_df = ak.fund_individual_basic_info_xq(symbol=fund_code)
            else:
                info_df = self._retry_fetch(
                    ak.fund_individual_basic_info_xq, symbol=fund_code
                )

            if info_df.empty:
                return None

            # 解析基金信息 - 新格式: item/value 列
            info = {}
            for _, row in info_df.iterrows():
                key = row.get("item", "")
                value = row.get("value", "")

                if "成立时间" in key or "成立日期" in key:
                    try:
                        info["establish_date"] = pd.to_datetime(value).date()
                    except:
                        pass
                elif "最新规模" in key or "基金规模" in key:
                    try:
                        # 处理不同格式："29.37亿" 或 "29.37"
                        val = str(value).replace("亿", "").strip()
                        if val:
                            info["fund_size"] = float(val)
                    except:
                        pass
                elif "基金公司" in key or "基金管理人" in key:
                    info["company"] = value
                elif "基金经理" in key:
                    info["manager"] = value
                elif "基金类型" in key:
                    info["fund_type"] = value

            return info if info else None
        except KeyError as e:
            # KeyError: 'data' - 蛋卷平台不销售该基金，正常情况
            # KeyError: 'xxx not in index' - 返回数据不完整，正常情况
            # 不输出日志，静默跳过
            return None
        except Exception as e:
            # 其他异常才记录
            logger.warning(f"获取基金 {fund_code} 信息异常: {e}")
            return None

    def fetch_fund_nav(
        self, fund_code: str, start_date: str = None, end_date: str = None
    ) -> pd.DataFrame:
        """获取基金净值历史
        
        注意：部分基金（货币基金、理财基金）接口不支持，
        这些情况返回空 DataFrame，跳过即可
        """
        try:
            # 直接获取，不重试（失败说明接口不支持，静默跳过）
            df = ak.fund_open_fund_info_em(
                symbol=fund_code,
                indicator="单位净值走势",
                period="成立来",
            )

            if df.empty:
                return pd.DataFrame()

            # 数据清洗
            df = df.rename(
                columns={
                    "净值日期": "nav_date",
                    "单位净值": "nav",
                    "日增长率": "daily_return",
                }
            )

            # 转换日期格式
            df["nav_date"] = pd.to_datetime(df["nav_date"]).dt.date

            # 转换数值类型
            for col in ["nav", "daily_return"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            # 日涨跌幅转换为小数
            if "daily_return" in df.columns:
                df["daily_return"] = df["daily_return"] / 100

            # 按日期升序排列
            df = df.sort_values("nav_date")

            # 日期过滤
            if start_date:
                start = pd.to_datetime(start_date).date()
                df = df[df["nav_date"] >= start]
            if end_date:
                end = pd.to_datetime(end_date).date()
                df = df[df["nav_date"] <= end]

            # 累计净值默认等于单位净值（接口不提供）
            if "accumulated_nav" not in df.columns:
                df["accumulated_nav"] = df["nav"]

            return df
        except Exception as e:
            # 货币基金、理财基金等特殊类型基金没有净值走势数据，属于正常情况
            # 降级为 DEBUG 级别，避免日志噪音
            logger.debug(f"获取基金 {fund_code} 净值失败（非净值型基金）: {e}")
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
    from fund_screener.data.database import FundRepository

    repo = FundRepository(db)

    # 获取基金列表
    fund_list = fetcher.fetch_all_fund_list()

    if limit:
        fund_list = fund_list.head(limit)

    total = len(fund_list)
    saved = 0
    skipped = 0
    
    logger.info(f"开始初始化 {total} 只基金的基础信息...")

    for idx, row in fund_list.iterrows():
        fund_code = row["fund_code"]

        # 检查是否已存在
        existing = repo.get_fund_by_code(fund_code)
        if existing:
            skipped += 1
            continue

        # 获取详细信息（失败直接跳过，不重试）
        try:
            info = fetcher.fetch_fund_info(fund_code, skip_retry=True)
        except Exception:
            info = None

        if info:
            fund_data = {
                "fund_code": fund_code,
                "fund_name": row["fund_name"],
                "fund_type": row.get("fund_type", ""),
                **info,
            }
            repo.upsert_fund(fund_data)
            saved += 1

        # 每500条输出进度
        if (idx + 1) % 500 == 0:
            logger.info(f"进度: {idx + 1}/{total}, 已保存: {saved}, 已跳过: {skipped}")

    logger.info(f"基金基础数据初始化完成: 保存 {saved} 只, 跳过已存在 {skipped} 只")
