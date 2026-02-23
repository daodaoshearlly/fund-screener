"""消息推送模块（Server酱 + 企业微信 + 邮件）"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
import requests
from typing import Optional, List
from loguru import logger
from fund_screener.config.settings import (
    SERVER_CHAN_KEY,
    WECOM_WEBHOOK,
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASSWORD,
    EMAIL_RECEIVER,
)


class ServerChanNotifier:
    """Server酱推送器"""

    def __init__(self, sckey: Optional[str] = None):
        self.sckey = sckey or SERVER_CHAN_KEY
        self.base_url = "https://sctapi.ftqq.com"

    def send_message(self, title: str, content: str) -> bool:
        """发送消息到微信

        Args:
            title: 消息标题
            content: 消息内容（支持Markdown）

        Returns:
            是否发送成功
        """
        if not self.sckey:
            logger.error("Server酱 SCKEY 未配置")
            return False

        url = f"{self.base_url}/{self.sckey}.send"

        payload = {
            "title": title,
            "desp": content,
            "channel": "9",  # 微信通道
        }

        try:
            response = requests.post(url, data=payload, timeout=30)
            result = response.json()

            if result.get("code") == 0:
                logger.info("Server酱消息推送成功")
                return True
            else:
                logger.error(f"Server酱消息推送失败: {result.get('message')}")
                return False

        except Exception as e:
            logger.error(f"Server酱推送请求异常: {e}")
            return False

    def send_fund_report(self, report_content: str, title: str = None) -> bool:
        """发送基金报告

        Args:
            report_content: 报告内容
            title: 自定义标题

        Returns:
            是否发送成功
        """
        if not title:
            from datetime import datetime

            title = f"📊 基金筛选报告 {datetime.now().strftime('%m/%d')}"

        return self.send_message(title, report_content)

    def test_connection(self) -> bool:
        """测试Server酱连接

        Returns:
            连接是否成功
        """
        if not self.sckey:
            logger.error("Server酱 SCKEY 未配置，请前往 https://sct.ftqq.com/ 获取")
            return False

        return self.send_message(
            "🔔 基金筛选系统测试",
            "Server酱连接测试成功！\n\n系统已就绪，将定时推送基金筛选报告。",
        )


class WeComNotifier:
    """企业微信机器人推送器"""

    def __init__(self, webhook: Optional[str] = None):
        self.webhook = webhook or WECOM_WEBHOOK

    def send_message(self, content: str, mentioned_list: List[str] = None) -> bool:
        """发送消息到企业微信群

        Args:
            content: 消息内容（文本格式）
            mentioned_list: @的用户列表（如 ["@all", "user1"]）

        Returns:
            是否发送成功
        """
        if not self.webhook:
            logger.error("企业微信 Webhook 未配置")
            return False

        payload = {
            "msgtype": "text",
            "text": {
                "content": content,
            },
        }

        if mentioned_list:
            payload["text"]["mentioned_list"] = mentioned_list

        try:
            response = requests.post(self.webhook, json=payload, timeout=30)
            result = response.json()

            if result.get("errcode") == 0:
                logger.info("企业微信消息推送成功")
                return True
            else:
                logger.error(f"企业微信消息推送失败: {result.get('errmsg')}")
                return False

        except Exception as e:
            logger.error(f"企业微信推送请求异常: {e}")
            return False

    def send_markdown(self, content: str) -> bool:
        """发送Markdown格式消息

        Args:
            content: Markdown格式内容

        Returns:
            是否发送成功
        """
        if not self.webhook:
            logger.error("企业微信 Webhook 未配置")
            return False

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": content,
            },
        }

        try:
            response = requests.post(self.webhook, json=payload, timeout=30)
            result = response.json()

            if result.get("errcode") == 0:
                logger.info("企业微信Markdown消息推送成功")
                return True
            else:
                logger.error(f"企业微信消息推送失败: {result.get('errmsg')}")
                return False

        except Exception as e:
            logger.error(f"企业微信推送请求异常: {e}")
            return False

    def send_fund_report(self, report_content: str) -> bool:
        """发送基金报告（Markdown格式）

        Args:
            report_content: 报告内容

        Returns:
            是否发送成功
        """
        return self.send_markdown(report_content)

    def test_connection(self) -> bool:
        """测试企业微信连接

        Returns:
            连接是否成功
        """
        if not self.webhook:
            logger.error("企业微信 Webhook 未配置")
            logger.info("获取方式：在企业微信群中添加机器人，复制Webhook地址")
            return False

        return self.send_message(
            "🔔 基金筛选系统测试\n\n企业微信连接测试成功！系统已就绪。"
        )


class EmailNotifier:
    """邮件推送器"""

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        receiver: Optional[str] = None,
    ):
        self.smtp_host = smtp_host or SMTP_HOST
        self.smtp_port = smtp_port or SMTP_PORT
        self.smtp_user = smtp_user or SMTP_USER
        self.smtp_password = smtp_password or SMTP_PASSWORD
        self.receiver = receiver or EMAIL_RECEIVER

    def send_message(
        self, subject: str, content: str, content_type: str = "plain"
    ) -> bool:
        """发送邮件

        Args:
            subject: 邮件主题
            content: 邮件内容
            content_type: 内容类型（plain/html）

        Returns:
            是否发送成功
        """
        if not all([self.smtp_host, self.smtp_user, self.smtp_password, self.receiver]):
            logger.error("邮件配置不完整")
            return False

        try:
            # 构造邮件
            msg = MIMEMultipart()
            msg["From"] = formataddr(["基金筛选系统", self.smtp_user])
            msg["To"] = self.receiver
            msg["Subject"] = subject

            # 添加正文
            msg.attach(MIMEText(content, content_type, "utf-8"))

            # 发送邮件
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)

                # 支持多个收件人
                receivers = [r.strip() for r in self.receiver.split(",")]
                server.sendmail(self.smtp_user, receivers, msg.as_string())

            logger.info("邮件推送成功")
            return True

        except smtplib.SMTPException as e:
            logger.error(f"邮件发送失败: {e}")
            return False
        except Exception as e:
            logger.error(f"邮件推送异常: {e}")
            return False

    def send_html(self, subject: str, html_content: str) -> bool:
        """发送HTML格式邮件

        Args:
            subject: 邮件主题
            html_content: HTML格式内容

        Returns:
            是否发送成功
        """
        return self.send_message(subject, html_content, content_type="html")

    def send_fund_report(self, report_content: str, title: str = None) -> bool:
        """发送基金报告

        Args:
            report_content: 报告内容（Markdown格式）
            title: 邮件主题

        Returns:
            是否发送成功
        """
        if not title:
            from datetime import datetime

            title = f"📊 基金筛选报告 {datetime.now().strftime('%Y-%m-%d')}"

        # 将Markdown转换为简单HTML
        html_content = self._markdown_to_html(report_content)
        return self.send_html(title, html_content)

    def _markdown_to_html(self, markdown_text: str) -> str:
        """简单Markdown转HTML

        Args:
            markdown_text: Markdown文本

        Returns:
            HTML文本
        """
        # 简单替换
        html = markdown_text

        # 换行
        html = html.replace("\n", "<br>\n")

        # 标题
        lines = html.split("<br>\n")
        for i, line in enumerate(lines):
            if line.startswith("### "):
                lines[i] = f"<h3>{line[4:]}</h3>"
            elif line.startswith("## "):
                lines[i] = f"<h2>{line[3:]}</h2>"
            elif line.startswith("# "):
                lines[i] = f"<h1>{line[2:]}</h1>"

        html = "<br>\n".join(lines)

        # 粗体
        import re

        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)

        # 分隔线
        html = html.replace("---", "<hr>")

        # 包装在HTML文档中
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #555; }}
        h3 {{ color: #666; }}
        hr {{ border: 1px solid #eee; margin: 20px 0; }}
    </style>
</head>
<body>
{html}
</body>
</html>
"""

    def test_connection(self) -> bool:
        """测试邮件连接

        Returns:
            连接是否成功
        """
        if not all([self.smtp_host, self.smtp_user, self.smtp_password]):
            logger.error("邮件SMTP配置不完整")
            logger.info("配置方法：")
            logger.info("1. Gmail: 需要生成应用专用密码")
            logger.info("2. QQ邮箱: 使用授权码")
            logger.info("3. 163邮箱: 使用授权码")
            return False

        return self.send_message(
            "🔔 基金筛选系统测试",
            "邮件推送测试成功！\n\n系统已就绪，将定时推送基金筛选报告。",
        )


class MultiNotifier:
    """多渠道推送器（支持Server酱、企业微信、邮件）"""

    def __init__(
        self,
        enable_server_chan: bool = True,
        enable_wecom: bool = True,
        enable_email: bool = True,
    ):
        self.server_chan = ServerChanNotifier() if enable_server_chan else None
        self.wecom = WeComNotifier() if enable_wecom else None
        self.email = EmailNotifier() if enable_email else None

    def send_fund_report(self, report_content: str, title: str = None) -> dict:
        """发送基金报告到所有已配置的渠道

        Args:
            report_content: 报告内容
            title: 标题

        Returns:
            各渠道推送结果
        """
        results = {}

        # Server酱推送
        if self.server_chan and self.server_chan.sckey:
            results["server_chan"] = self.server_chan.send_fund_report(
                report_content, title
            )

        # 企业微信推送
        if self.wecom and self.wecom.webhook:
            results["wecom"] = self.wecom.send_fund_report(report_content)

        # 邮件推送
        if self.email and self.email.smtp_user and self.email.receiver:
            results["email"] = self.email.send_fund_report(report_content, title)

        # 汇总结果
        success_count = sum(1 for v in results.values() if v)
        total_count = len(results)

        if success_count == total_count:
            logger.success(f"所有渠道推送成功 ({success_count}/{total_count})")
        elif success_count > 0:
            logger.warning(f"部分渠道推送成功 ({success_count}/{total_count})")
        else:
            logger.error("所有渠道推送失败")

        return results

    def test_connection(self) -> dict:
        """测试所有已配置渠道的连接

        Returns:
            各渠道测试结果
        """
        results = {}

        if self.server_chan and self.server_chan.sckey:
            results["server_chan"] = self.server_chan.test_connection()

        if self.wecom and self.wecom.webhook:
            results["wecom"] = self.wecom.test_connection()

        if self.email and self.email.smtp_user:
            results["email"] = self.email.test_connection()

        return results


def test_notifier():
    """测试推送功能"""
    print("=" * 50)
    print("测试消息推送功能")
    print("=" * 50)

    # 测试多渠道推送
    notifier = MultiNotifier()
    results = notifier.test_connection()

    print("\n测试结果：")
    print("-" * 30)

    if not results:
        print("⚠️ 未配置任何推送渠道")
        print("\n配置方法：")
        print("1. Server酱：设置环境变量 SERVER_CHAN_KEY")
        print("   获取地址：https://sct.ftqq.com/")
        print("2. 企业微信：设置环境变量 WECOM_WEBHOOK")
        print("   获取方式：在企业微信群中添加机器人")
        print("3. 邮件推送：设置环境变量 SMTP_HOST/USER/PASSWORD/RECEIVER")
        print("   支持Gmail、QQ邮箱、163邮箱等SMTP服务")
    else:
        for channel, success in results.items():
            status = "✅ 成功" if success else "❌ 失败"
            print(f"{channel}: {status}")
