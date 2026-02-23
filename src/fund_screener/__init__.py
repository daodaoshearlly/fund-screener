"""基金筛选系统

自用基金筛选工具，重点筛选稳健增长、长期复利的基金，支持定投策略。
"""

__version__ = "1.2.0"
__author__ = "Claude"

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("fund-screener")
except PackageNotFoundError:
    pass
