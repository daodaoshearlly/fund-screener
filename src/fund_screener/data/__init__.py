"""数据模块"""

from .models import *
from .database import FundRepository
from .fetcher import FundDataFetcher, init_fund_data
