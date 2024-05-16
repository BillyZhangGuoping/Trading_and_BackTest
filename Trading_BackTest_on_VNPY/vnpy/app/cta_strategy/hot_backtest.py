import os
import importlib
import traceback
from datetime import datetime
from threading import Thread
from pathlib import Path
from inspect import getfile

from vnpy.trader.mddata import mddata_client
from vnpy.trader.setting import SETTINGS
from vnpy.event import Event, EventEngine
from vnpy.trader.engine import BaseEngine, MainEngine
from vnpy.trader.constant import Interval
from vnpy.trader.utility import extract_vt_symbol
from vnpy.trader.object import HistoryRequest
from trader.mddata.rqdata import rqdata_client
from vnpy.trader.database import database_manager
from vnpy.app.cta_strategy import CtaTemplate
from vnpy.app.cta_strategy.backtesting import (
    BacktestingEngine, OptimizationSetting, BacktestingMode
)
from tzlocal import get_localzone
LOCAL_TZ = get_localzone()



class HotBackTest:
    def __init__(self):
        self.test = 0


