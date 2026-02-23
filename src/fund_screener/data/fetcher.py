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
                elif "投资策略" in key:
                    # 提取投资策略文本用于量化基金识别
                    info["investment_strategy"] = value

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

    def detect_quant_fund(self, fund_name: str, investment_strategy: str = None) -> int:
        """识别是否为量化基金
        
        Args:
            fund_name: 基金名称
            investment_strategy: 投资策略描述（可选）
        
        Returns:
            1: 量化基金
            0: 非量化基金
        """
        # 基金名称中的量化关键词（高置信度）
        high_confidence_keywords = ['量化', '多因子', '对冲', '市场中性']
        
        # 基金名称中的量化关键词（中置信度）
        medium_confidence_keywords = ['指数增强', 'Smart Beta', 'smart beta']
        
        # 投资策略中的量化关键词
        strategy_keywords = ['量化模型', '多因子模型', '算法', '程序化', '数学模型', '量化选股', '因子选股']
        
        # 检查基金名称
        if fund_name:
            for kw in high_confidence_keywords:
                if kw in fund_name:
                    return 1
            
            for kw in medium_confidence_keywords:
                if kw in fund_name:
                    # 指数增强可能是量化，也可能是主动，需要结合策略判断
                    if investment_strategy:
                        for skw in strategy_keywords:
                            if skw in investment_strategy:
                                return 1
                    break
        
        # 检查投资策略描述
        if investment_strategy:
            for kw in strategy_keywords:
                if kw in investment_strategy:
                    return 1
        
        return 0

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


def init_fund_data(db, fetcher: FundDataFetcher, limit: int = None, max_workers: int = 10):
    """初始化/更新基金基础数据
    
    优化：
    1. 多线程并行抓取数据
    2. 批量写入数据库，减少 commit 开销
    已存在的基金也会更新数据
    
    Args:
        db: 数据库会话
        fetcher: 数据抓取器
        limit: 限制处理数量
        max_workers: 并行线程数（默认10）
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from fund_screener.data.database import FundRepository
    from fund_screener.data.models import Fund

    repo = FundRepository(db)

    # 获取基金列表
    fund_list = fetcher.fetch_all_fund_list()

    if limit:
        fund_list = fund_list.head(limit)

    total = len(fund_list)
    
    # 获取已存在的基金代码（用于区分新增/更新）
    existing_codes = set(f.fund_code for f in db.query(Fund.fund_code).all())
    
    logger.info(f"开始更新 {total} 只基金的基础信息，已存在 {len(existing_codes)} 只...（并行线程数: {max_workers}）")

    # 准备基金数据列表
    fund_items = []
    for idx, row in fund_list.iterrows():
        fund_items.append({
            'fund_code': row["fund_code"],
            'fund_name': row["fund_name"],
            'fund_type': row.get("fund_type", ""),
            'is_new': row["fund_code"] not in existing_codes,
        })

    # 多线程并行抓取
    funds_to_save = []
    new_count = 0
    update_count = 0
    failed_count = 0
    lock = __import__('threading').Lock()
    
    def fetch_single_fund(item):
        """抓取单个基金信息"""
        fund_code = item['fund_code']
        try:
            info = fetcher.fetch_fund_info(fund_code, skip_retry=True)
            if info:
                is_quant = fetcher.detect_quant_fund(
                    item['fund_name'], 
                    info.get("investment_strategy")
                )
                info.pop("investment_strategy", None)
                return {
                    'fund_code': fund_code,
                    'fund_name': item['fund_name'],
                    'fund_type': item['fund_type'],
                    'is_quant': is_quant,
                    'is_new': item['is_new'],
                    **info,
                }
        except Exception:
            pass
        return None

    # 使用线程池并行抓取
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_single_fund, item): item for item in fund_items}
        
        completed = 0
        for future in as_completed(futures):
            result = future.result()
            if result:
                funds_to_save.append(result)
                if result['is_new']:
                    new_count += 1
                else:
                    update_count += 1
            else:
                failed_count += 1
            
            completed += 1
            if completed % 1000 == 0:
                logger.info(f"抓取进度: {completed}/{total}, 成功: {new_count + update_count}, 失败: {failed_count}")

    # 批量写入数据库
    if funds_to_save:
        logger.info(f"批量写入 {len(funds_to_save)} 只基金数据...")
        # 移除 is_new 字段，不写入数据库
        for fund in funds_to_save:
            fund.pop('is_new', None)
        repo.batch_upsert_funds(funds_to_save, batch_size=100)

    logger.info(f"基金基础数据更新完成: 新增 {new_count} 只, 更新 {update_count} 只, 抓取失败 {failed_count} 只")



def init_nav_data(db, fetcher: FundDataFetcher, limit: int = None, max_workers: int = 10, min_records: int = 500):
    """初始化/更新基金净值数据（批量并行抓取）
    
    优化：
    1. 多线程并行抓取净值数据
    2. 批量写入数据库，减少 commit 开销
    3. 只抓取缺少净值数据或数据不足的基金
    
    Args:
        db: 数据库会话
        fetcher: 数据抓取器
        limit: 限制处理数量（测试用）
        max_workers: 并行线程数（默认10）
        min_records: 最少需要的历史记录数（默认500条，约2年交易日）
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from fund_screener.data.database import FundRepository
    from fund_screener.data.models import Fund, FundNav
    from fund_screener.config.settings import NAV_BATCH_SIZE
    
    repo = FundRepository(db)
    
    # 获取所有基金
    all_funds = db.query(Fund).all()
    
    if limit:
        all_funds = all_funds[:limit]
    
    total = len(all_funds)
    logger.info(f"开始更新 {total} 只基金的净值数据...（并行线程数: {max_workers}）")
    
    # 筛选需要抓取净值的基金（缺少数据或数据不足）
    funds_to_fetch = []
    for fund in all_funds:
        nav_count = db.query(FundNav).filter(FundNav.fund_code == fund.fund_code).count()
        if nav_count < min_records:
            funds_to_fetch.append(fund)
    
    logger.info(f"需要抓取净值的基金: {len(funds_to_fetch)} 只（当前数据不足 {min_records} 条）")
    
    if not funds_to_fetch:
        logger.info("所有基金净值数据已完整")
        return
    
    # 多线程并行抓取
    nav_results = []  # [(fund_code, nav_data), ...]
    success_count = 0
    failed_count = 0
    empty_count = 0
    
    def fetch_single_nav(fund):
        """抓取单个基金净值"""
        try:
            nav_df = fetcher.fetch_fund_nav(fund.fund_code)
            if not nav_df.empty:
                return (fund.fund_code, nav_df.to_dict("records"))
            return (fund.fund_code, None)
        except Exception as e:
            logger.debug(f"抓取基金 {fund.fund_code} 净值失败: {e}")
            return (fund.fund_code, None)
    
    # 使用线程池并行抓取
    completed = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_single_nav, fund): fund for fund in funds_to_fetch}
        
        for future in as_completed(futures):
            fund_code, nav_data = future.result()
            if nav_data:
                nav_results.append((fund_code, nav_data))
                success_count += 1
            elif nav_data is None:
                failed_count += 1
            else:
                empty_count += 1
            
            completed += 1
            if completed % 500 == 0:
                logger.info(f"抓取进度: {completed}/{len(funds_to_fetch)}, 成功: {success_count}, 失败: {failed_count}, 无数据: {empty_count}")
    
    # 批量写入数据库
    if nav_results:
        logger.info(f"批量写入 {len(nav_results)} 只基金的净值数据...")
        for fund_code, nav_data in nav_results:
            repo.batch_save_nav_data(fund_code, nav_data, batch_size=NAV_BATCH_SIZE)
    
    logger.info(f"基金净值数据更新完成: 成功 {success_count} 只, 失败 {failed_count} 只, 无数据 {empty_count} 只")