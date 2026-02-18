"""报告生成模块"""

from datetime import datetime
from typing import List, Dict
from loguru import logger


class ReportGenerator:
    """报告生成器"""

    def __init__(self):
        pass

    def generate_text_report(
        self, funds: List[Dict], backtest_results: Dict = None
    ) -> str:
        """生成文字报告

        Args:
            funds: 筛选出的基金列表
            backtest_results: 回测结果

        Returns:
            报告文本
        """
        today = datetime.now().strftime("%Y-%m-%d")

        report_lines = [
            f"📊 基金筛选报告（{today}）",
            "",
            f"🥇 Top {len(funds)} 稳健复利基金：",
            "",
        ]

        for idx, fund in enumerate(funds, 1):
            metrics = fund.get("metrics", {})
            fund_code = fund.get("fund_code", "")
            fund_name = fund.get("fund_name", "")

            # 基本信息
            report_lines.append(f"{idx}. 【{fund_name}】({fund_code})")

            # 收益指标
            return_3y = metrics.get("annual_return_3y", 0)
            return_5y = metrics.get("annual_return_5y", 0)

            if return_3y:
                report_lines.append(f"   📈 近3年收益: +{return_3y:.1f}%")
            if return_5y:
                report_lines.append(f"   📈 近5年收益: +{return_5y:.1f}%")

            # 风险指标
            sharpe = metrics.get("sharpe_ratio", 0)
            max_dd = metrics.get("max_drawdown", 0)
            calmar = metrics.get("calmar_ratio", 0)
            win_rate = metrics.get("monthly_win_rate", 0)

            report_lines.append(
                f"   🎯 夏普比率: {sharpe:.2f} | 最大回撤: {max_dd:.1f}%"
            )

            if calmar:
                report_lines.append(f"   📊 卡玛比率: {calmar:.2f}")
            if win_rate:
                report_lines.append(f"   ✅ 月度胜率: {win_rate * 100:.0f}%")

            # 回测对比
            if backtest_results and fund_code in backtest_results:
                bt_3y = backtest_results[fund_code].get("3y", {})
                if bt_3y:
                    excess = bt_3y.get("excess_return", 0)
                    benchmark = bt_3y.get("benchmark_code", "")
                    if excess:
                        emoji = "🚀" if excess > 0 else "⚠️"
                        report_lines.append(
                            f"   {emoji} 相对{benchmark}超额收益: {excess:+.1f}%"
                        )

            # 综合评分
            score = metrics.get("total_score", 0)
            report_lines.append(f"   ⭐ 综合评分: {score:.1f}/100")
            report_lines.append("")

        # 免责声明
        report_lines.extend(
            [
                "---",
                "⚠️ 免责声明：",
                "• 本报告仅供参考，不构成投资建议",
                "• 基金过往业绩不代表未来表现",
                "• 投资有风险，入市需谨慎",
                "",
                f"⏰ 下次更新: 下周一 09:00",
            ]
        )

        return "\n".join(report_lines)

    def generate_markdown_report(
        self, funds: List[Dict], backtest_results: Dict = None
    ) -> str:
        """生成Markdown格式报告（用于详细查看）

        Args:
            funds: 筛选出的基金列表
            backtest_results: 回测结果

        Returns:
            Markdown格式报告
        """
        today = datetime.now().strftime("%Y-%m-%d")

        lines = [
            f"# 📊 基金筛选报告（{today}）",
            "",
            f"## 🥇 Top {len(funds)} 稳健复利基金",
            "",
        ]

        for idx, fund in enumerate(funds, 1):
            metrics = fund.get("metrics", {})
            fund_code = fund.get("fund_code", "")
            fund_name = fund.get("fund_name", "")
            fund_type = fund.get("fund_type", "")

            lines.append(f"### {idx}. {fund_name} ({fund_code})")
            lines.append(f"**类型**: {fund_type}")
            lines.append("")

            # 创建表格
            lines.append("| 指标 | 数值 |")
            lines.append("|------|------|")

            if "annual_return_3y" in metrics:
                lines.append(f"| 近3年年化收益 | {metrics['annual_return_3y']:.2f}% |")
            if "annual_return_5y" in metrics:
                lines.append(f"| 近5年年化收益 | {metrics['annual_return_5y']:.2f}% |")
            if "sharpe_ratio" in metrics:
                lines.append(f"| 夏普比率 | {metrics['sharpe_ratio']:.2f} |")
            if "max_drawdown" in metrics:
                lines.append(f"| 最大回撤 | {metrics['max_drawdown']:.2f}% |")
            if "calmar_ratio" in metrics:
                lines.append(f"| 卡玛比率 | {metrics['calmar_ratio']:.2f} |")
            if "monthly_win_rate" in metrics:
                lines.append(f"| 月度胜率 | {metrics['monthly_win_rate'] * 100:.1f}% |")
            if "volatility" in metrics:
                lines.append(f"| 年化波动率 | {metrics['volatility']:.2f}% |")

            lines.append(
                f"| **综合评分** | **{metrics.get('total_score', 0):.1f}/100** |"
            )
            lines.append("")

            # 回测结果
            if backtest_results and fund_code in backtest_results:
                lines.append("#### 回测对比（沪深300）")
                lines.append("")

                for period, result in backtest_results[fund_code].items():
                    lines.append(f"**{period}年回测**：")
                    lines.append(
                        f"- 基金累计收益: {result.get('total_return', 0):.2f}%"
                    )
                    lines.append(
                        f"- 基金年化收益: {result.get('annual_return', 0):.2f}%"
                    )
                    lines.append(
                        f"- 基准累计收益: {result.get('benchmark_return', 0):.2f}%"
                    )
                    lines.append(f"- 超额收益: {result.get('excess_return', 0):+.2f}%")
                    lines.append("")

        lines.extend(
            [
                "---",
                "**免责声明**：",
                "- 本报告仅供参考，不构成投资建议",
                "- 基金过往业绩不代表未来表现",
                "- 投资有风险，入市需谨慎",
                "",
                f"*报告生成时间: {today}*",
            ]
        )

        return "\n".join(lines)

    def save_report(self, content: str, filename: str = None):
        """保存报告到文件

        Args:
            content: 报告内容
            filename: 文件名
        """
        if not filename:
            filename = f"fund_report_{datetime.now().strftime('%Y%m%d')}.md"

        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"报告已保存: {filename}")
        except Exception as e:
            logger.error(f"保存报告失败: {e}")
