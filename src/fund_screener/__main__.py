#!/usr/bin/env python3
"""基金筛选系统 - 主入口

使用方法:
1. 初始化数据库: python -m fund_screener init
2. 更新基金数据: python -m fund_screener update-funds
3. 执行筛选: python -m fund_screener screen [--limit 100]
4. 执行回测: python -m fund_screener backtest
5. 推送报告: python -m fund_screener notify
6. 完整流程: python -m fund_screener run-all
7. 启动定时任务: python -m fund_screener schedule
"""

import os
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from loguru import logger
from fund_screener.data.models import init_db, SessionLocal
from fund_screener.data.fetcher import FundDataFetcher, init_fund_data
from fund_screener.data.database import FundRepository
from fund_screener.analysis.screener import FundScreener
from fund_screener.analysis.backtest import FundBacktest
from fund_screener.report.generator import ReportGenerator
from fund_screener.report.notifier import MultiNotifier

# 配置日志
logger.add(
    "logs/fund_screener.log",
    rotation="500 MB",
    retention="10 days",
    level="INFO",
    encoding="utf-8",
)


def init_database():
    """初始化数据库"""
    logger.info("初始化数据库...")
    init_db()
    logger.success("数据库初始化完成")


def update_fund_data(limit: int = None):
    """更新基金基础数据"""
    logger.info("开始更新基金数据...")

    db = SessionLocal()
    fetcher = FundDataFetcher()

    try:
        init_fund_data(db, fetcher, limit=limit)
        logger.success("基金数据更新完成")
    except Exception as e:
        logger.error(f"更新基金数据失败: {e}")
    finally:
        db.close()


def screen_funds(limit: int = None, save_report: bool = True):
    """执行基金筛选"""
    logger.info("开始基金筛选...")

    db = SessionLocal()
    fetcher = FundDataFetcher()

    try:
        screener = FundScreener(db, fetcher)
        selected_funds = screener.screen_funds(limit=limit)

        if selected_funds:
            logger.success(f"筛选完成，共 {len(selected_funds)} 只基金入选")

            # 生成报告
            generator = ReportGenerator()
            report_content = generator.generate_text_report(selected_funds)

            print("\n" + "=" * 60)
            print(report_content)
            print("=" * 60 + "\n")

            # 保存报告
            if save_report:
                md_report = generator.generate_markdown_report(selected_funds)
                generator.save_report(
                    md_report,
                    f"reports/fund_report_{datetime.now().strftime('%Y%m%d')}.md",
                )

            return selected_funds
        else:
            logger.warning("没有基金通过筛选")
            return []

    except Exception as e:
        logger.error(f"筛选失败: {e}")
        import traceback

        traceback.print_exc()
        return []
    finally:
        db.close()


def run_backtest():
    """执行回测"""
    logger.info("开始回测...")

    db = SessionLocal()
    fetcher = FundDataFetcher()
    repo = FundRepository(db)

    try:
        # 获取筛选出的基金
        selected = repo.get_selected_funds()

        if not selected:
            logger.warning("没有筛选结果，请先执行筛选")
            return {}

        fund_codes = [f.fund_code for f in selected]

        backtest = FundBacktest(db, fetcher)
        results = backtest.batch_backtest(fund_codes, years_list=[3, 5])

        logger.success(f"回测完成，共 {len(results)} 只基金")
        return results

    except Exception as e:
        logger.error(f"回测失败: {e}")
        import traceback

        traceback.print_exc()
        return {}
    finally:
        db.close()


def send_notification():
    """发送推送通知"""
    logger.info("发送推送通知...")

    db = SessionLocal()
    repo = FundRepository(db)

    try:
        # 获取最新筛选结果
        selected = repo.get_selected_funds()

        if not selected:
            logger.warning("没有筛选结果，无法推送")
            return False

        # 构造基金数据
        funds_data = []
        for s in selected:
            metrics = repo.get_metrics(s.fund_code)
            funds_data.append(
                {
                    "fund_code": s.fund_code,
                    "fund_name": s.fund_name,
                    "metrics": {
                        "total_score": s.total_score,
                        "annual_return_3y": s.annual_return_3y,
                        "sharpe_ratio": s.sharpe_ratio,
                        "max_drawdown": s.max_drawdown,
                    },
                }
            )

        # 生成报告
        generator = ReportGenerator()
        report_content = generator.generate_text_report(funds_data)

        # 发送推送（同时支持Server酱和企业微信）
        notifier = MultiNotifier()
        results = notifier.send_fund_report(report_content)

        success = any(results.values()) if results else False

        if success:
            logger.success(f"推送完成: {results}")
        else:
            logger.error("推送失败")

        return success

    except Exception as e:
        logger.error(f"推送失败: {e}")
        return False
    finally:
        db.close()


def run_all():
    """执行完整流程"""
    logger.info("=" * 60)
    logger.info("开始执行完整流程...")
    logger.info("=" * 60)

    # 1. 筛选基金
    selected_funds = screen_funds(save_report=True)

    if not selected_funds:
        logger.warning("筛选未通过，流程结束")
        return

    # 2. 执行回测
    logger.info("\n" + "=" * 60)
    backtest_results = run_backtest()

    # 3. 重新生成包含回测的报告
    db = SessionLocal()
    try:
        repo = FundRepository(db)
        selected = repo.get_selected_funds()

        funds_data = []
        for s in selected:
            metrics = repo.get_metrics(s.fund_code)
            fund_dict = {
                "fund_code": s.fund_code,
                "fund_name": s.fund_name,
                "metrics": {
                    "total_score": s.total_score,
                    "annual_return_3y": s.annual_return_3y,
                    "sharpe_ratio": s.sharpe_ratio,
                    "max_drawdown": s.max_drawdown,
                },
            }
            if metrics:
                fund_dict["metrics"].update(
                    {
                        "annual_return_1y": metrics.annual_return_1y,
                        "annual_return_5y": metrics.annual_return_5y,
                        "calmar_ratio": metrics.calmar_ratio,
                        "monthly_win_rate": metrics.monthly_win_rate,
                        "volatility": metrics.volatility,
                    }
                )
            funds_data.append(fund_dict)

        generator = ReportGenerator()
        report_content = generator.generate_text_report(funds_data, backtest_results)

        # 保存最终报告
        md_report = generator.generate_markdown_report(funds_data, backtest_results)
        generator.save_report(
            md_report, f"reports/fund_report_{datetime.now().strftime('%Y%m%d')}.md"
        )

        # 4. 发送推送（同时支持Server酱和企业微信）
        logger.info("\n" + "=" * 60)
        notifier = MultiNotifier()
        notifier.send_fund_report(report_content)

    finally:
        db.close()

    logger.info("=" * 60)
    logger.success("完整流程执行完成")
    logger.info("=" * 60)


def start_scheduler():
    """启动定时任务"""
    from apscheduler.schedulers.blocking import BlockingScheduler
    from fund_screener.config.settings import SCHEDULE_CONFIG

    logger.info("启动定时任务...")
    logger.info(
        f"配置: 每周{SCHEDULE_CONFIG['day_of_week']} {SCHEDULE_CONFIG['hour']:02d}:{SCHEDULE_CONFIG['minute']:02d}"
    )

    scheduler = BlockingScheduler()

    scheduler.add_job(
        run_all,
        "cron",
        day_of_week=SCHEDULE_CONFIG["day_of_week"],
        hour=SCHEDULE_CONFIG["hour"],
        minute=SCHEDULE_CONFIG["minute"],
        id="fund_screening",
        name="基金定时筛选",
    )

    try:
        logger.success("定时任务已启动，按 Ctrl+C 停止")
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("定时任务已停止")
        scheduler.shutdown()


def test_notifier():
    """测试推送功能"""
    from fund_screener.report.notifier import test_notifier as _test_notifier

    _test_notifier()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="基金筛选系统")
    parser.add_argument(
        "command",
        choices=[
            "init",
            "update-funds",
            "screen",
            "backtest",
            "notify",
            "test-notify",
            "run-all",
            "schedule",
        ],
        help="要执行的命令",
    )
    parser.add_argument("--limit", type=int, help="限制处理的基金数量（测试用）")

    args = parser.parse_args()

    # 创建必要目录
    os.makedirs("logs", exist_ok=True)
    os.makedirs("reports", exist_ok=True)

    if args.command == "init":
        init_database()

    elif args.command == "update-funds":
        update_fund_data(limit=args.limit)

    elif args.command == "screen":
        screen_funds(limit=args.limit)

    elif args.command == "backtest":
        run_backtest()

    elif args.command == "notify":
        send_notification()

    elif args.command == "test-notify":
        test_notifier()

    elif args.command == "run-all":
        run_all()

    elif args.command == "schedule":
        start_scheduler()


if __name__ == "__main__":
    main()
