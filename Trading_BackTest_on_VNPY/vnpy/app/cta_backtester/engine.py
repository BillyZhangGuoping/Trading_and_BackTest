import os
import importlib
import traceback
from datetime import datetime, timedelta
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
from vnpy.trader.database import database_manager
from vnpy.app.cta_strategy import CtaTemplate
from vnpy.app.cta_strategy.backtesting import (
    BacktestingEngine, OptimizationSetting, BacktestingMode
)
from tzlocal import get_localzone
from vnpy.addon.hotfutures import HotFuturesHandler

LOCAL_TZ = get_localzone()
APP_NAME = "CtaBacktester"

EVENT_BACKTESTER_LOG = "eBacktesterLog"
EVENT_BACKTESTER_BACKTESTING_FINISHED = "eBacktesterBacktestingFinished"
EVENT_BACKTESTER_OPTIMIZATION_FINISHED = "eBacktesterOptimizationFinished"


class BacktesterEngine(BaseEngine):
    """
    For running CTA strategy backtesting.
    """

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine):
        """"""
        super().__init__(main_engine, event_engine, APP_NAME)

        self.classes = {}
        self.backtesting_engine = None
        self.thread = None

        # Backtesting reuslt
        self.result_df = None
        self.result_statistics = None

        # Optimization result
        self.result_values = None

    def init_engine(self):
        """"""
        self.write_log("初始化CTA回测引擎")

        self.backtesting_engine = BacktestingEngine()
        # Redirect log from backtesting engine outside.
        self.backtesting_engine.output = self.write_log

        self.load_strategy_class()
        self.write_log("策略文件加载完成")

        self.init_rqdata()

    def init_rqdata(self):
        """
        Init JQData client.
        """
        result = mddata_client.init()
        md_data_api = SETTINGS["mddata.api"]
        if result:
            self.write_log(f"{md_data_api}数据接口初始化成功")

    def write_log(self, msg: str):
        """"""
        event = Event(EVENT_BACKTESTER_LOG)
        event.data = msg
        self.event_engine.put(event)

    def load_strategy_class(self):
        """
        Load strategy class from source code.
        """
        app_path = Path(__file__).parent.parent
        path1 = app_path.joinpath("cta_strategy", "strategies")
        self.load_strategy_class_from_folder(
            path1, "vnpy.app.cta_strategy.strategies")

        path2 = Path.cwd().joinpath("strategies")
        self.load_strategy_class_from_folder(path2, "strategies")

    def load_strategy_class_from_folder(self, path: Path, module_name: str = ""):
        """
        Load strategy class from certain folder.
        """
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                # Load python source code file
                if filename.endswith(".py"):
                    strategy_module_name = ".".join(
                        [module_name, filename.replace(".py", "")])
                    self.load_strategy_class_from_module(strategy_module_name)
                # Load compiled pyd binary file
                elif filename.endswith(".pyd"):
                    strategy_module_name = ".".join(
                        [module_name, filename.split(".")[0]])
                    self.load_strategy_class_from_module(strategy_module_name)

    def load_strategy_class_from_module(self, module_name: str):
        """
        Load strategy class from module file.
        """
        try:
            module = importlib.import_module(module_name)
            importlib.reload(module)

            for name in dir(module):
                value = getattr(module, name)
                if (isinstance(value, type) and issubclass(value, CtaTemplate) and value is not CtaTemplate):
                    self.classes[value.__name__] = value
        except:  # noqa
            msg = f"策略文件{module_name}加载失败，触发异常：\n{traceback.format_exc()}"
            self.write_log(msg)

    def reload_strategy_class(self):
        """"""
        self.classes.clear()
        self.load_strategy_class()
        self.write_log("策略文件重载刷新完成")

    def get_strategy_class_names(self):
        """"""
        return list(self.classes.keys())



    def run_backtesting(
        self,
        class_name: str,
        vt_symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
        rate: float,
        slippage: float,
        size: int,
        pricetick: float,
        capital: int,
        inverse: bool,
        setting: dict
    ):
        """"""
        self.result_df = None
        self.result_statistics = None

        engine = self.backtesting_engine
        engine.clear_data()

        if interval == Interval.TICK.value:
            mode = BacktestingMode.TICK
        else:
            mode = BacktestingMode.BAR

        engine.set_parameters(
            vt_symbol=vt_symbol,
            interval=interval,
            start=start,
            end=end,
            rate=rate,
            slippage=slippage,
            size=size,
            pricetick=pricetick,
            capital=capital,
            inverse=inverse,
            mode=mode
        )
        vt_local = "1"
        strategy_class = self.classes[class_name]

        engine.add_strategy(
            strategy_class,
            vt_local,
            setting
        )

        engine.load_data()

        try:
            engine.run_backtesting()
        except Exception:
            msg = f"策略回测失败，触发异常：\n{traceback.format_exc()}"
            self.write_log(msg)

            self.thread = None
            return

        self.result_df = engine.calculate_result()
        self.result_statistics = engine.calculate_statistics(output=False)

        # Clear thread object handler.
        self.thread = None

        # Put backtesting done event
        event = Event(EVENT_BACKTESTER_BACKTESTING_FINISHED)
        self.event_engine.put(event)

    def start_backtesting(
        self,
        class_name: str,
        vt_symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
        rate: float,
        slippage: float,
        size: int,
        pricetick: float,
        capital: int,
        inverse: bool,
        setting: dict
    ):
        if self.thread:
            self.write_log("已有任务在运行中，请等待完成")
            return False

        self.write_log("-" * 40)
        self.thread = Thread(
            target=self.run_backtesting,
            args=(
                class_name,
                vt_symbol,
                interval,
                start,
                end,
                rate,
                slippage,
                size,
                pricetick,
                capital,
                inverse,
                setting
            )
        )
        self.thread.start()

        return True

    def get_result_df(self):
        """"""
        return self.result_df

    def get_result_statistics(self):
        """"""
        return self.result_statistics

    def get_result_values(self):
        """"""
        return self.result_values

    def get_default_setting(self, class_name: str):
        """"""
        strategy_class = self.classes[class_name]
        return strategy_class.get_class_parameters()

    def run_optimization(
        self,
        class_name: str,
        vt_symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
        rate: float,
        slippage: float,
        size: int,
        pricetick: float,
        capital: int,
        inverse: bool,
        optimization_setting: OptimizationSetting,
        use_ga: bool
    ):
        """"""
        if use_ga:
            self.write_log("开始遗传算法参数优化")
        else:
            self.write_log("开始多进程参数优化")

        self.result_values = None

        engine = self.backtesting_engine
        engine.clear_data()

        if interval == Interval.TICK:
            mode = BacktestingMode.TICK
        else:
            mode = BacktestingMode.BAR

        engine.set_parameters(
            vt_symbol=vt_symbol,
            interval=interval,
            start=start,
            end=end,
            rate=rate,
            slippage=slippage,
            size=size,
            pricetick=pricetick,
            capital=capital,
            inverse=inverse,
            mode=mode
        )

        strategy_class = self.classes[class_name]
        vt_local = "1"
        engine.add_strategy(
            strategy_class,
            vt_local,
            {}
        )

        if use_ga:
            self.result_values = engine.run_ga_optimization(
                optimization_setting,
                output=False
            )
        else:
            self.result_values = engine.run_optimization(
                optimization_setting,
                output=False
            )

        # Clear thread object handler.
        self.thread = None
        self.write_log("多进程参数优化完成")

        # Put optimization done event
        event = Event(EVENT_BACKTESTER_OPTIMIZATION_FINISHED)
        self.event_engine.put(event)

    def start_optimization(
        self,
        class_name: str,
        vt_symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
        rate: float,
        slippage: float,
        size: int,
        pricetick: float,
        capital: int,
        inverse: bool,
        optimization_setting: OptimizationSetting,
        use_ga: bool
    ):
        if self.thread:
            self.write_log("已有任务在运行中，请等待完成")
            return False

        self.write_log("-" * 40)
        self.thread = Thread(
            target=self.run_optimization,
            args=(
                class_name,
                vt_symbol,
                interval,
                start,
                end,
                rate,
                slippage,
                size,
                pricetick,
                capital,
                inverse,
                optimization_setting,
                use_ga
            )
        )
        self.thread.start()

        return True



    def run_downloading(
        self,
        vt_symbol: str,
        interval: str,
        start: datetime,
        end: datetime
    ):
        """
        Query bar data from JQData.
        """

        hot_symbol, hot_exchange = vt_symbol.split(".")
        if hot_exchange == "HOT":
            hot_handler = HotFuturesHandler(hot_symbol)
            download_list = hot_handler.get_daily_contracts(start,end)
            self.write_log(f"{vt_symbol}-对应的主力合约分别为：")
            for query_item in download_list:
                self.write_log(f"从{self.convertTime(query_item['start_date'])} 到 {self.convertTime(query_item['end_date'])} 的"
                               f"主力合约是 {query_item['contract_code']}")
                query_item['start_date'] = query_item['start_date'] - timedelta(days = 60)

        else:
            download_list = [{'start_date': start, 'end_date': end, 'contract_code': vt_symbol}]

        for query_item in download_list:
            start = query_item['start_date'].astimezone(LOCAL_TZ)
            end = query_item['end_date'].astimezone(LOCAL_TZ)
            vt_symbol = query_item['contract_code']

            self.write_log(f"{vt_symbol}-{interval}开始下载历史数据")

            try:
                symbol, exchange = extract_vt_symbol(vt_symbol)
            except ValueError:
                self.write_log(f"{vt_symbol}解析失败，请检查交易所后缀")
                self.thread = None
                return

            req = HistoryRequest(
                symbol=symbol,
                exchange=exchange,
                interval=Interval(interval),
                start=start,
                end=end
            )

            contract = self.main_engine.get_contract(vt_symbol)

            try:
                # If history data provided in gateway, then query
                if contract and contract.history_data:
                    data = self.main_engine.query_history(
                        req, contract.gateway_name
                    )
                # Otherwise use RQData to query data
                else:
                    bar_start = None
                    bar_end = None
                    bar_overview_list = database_manager.get_bar_overview()
                    for bar_overview in bar_overview_list:
                        if bar_overview.symbol == symbol and bar_overview.exchange == exchange and bar_overview.interval == Interval(interval):
                            bar_start = bar_overview.start.astimezone(LOCAL_TZ)
                            bar_end = bar_overview.end.astimezone(LOCAL_TZ)
                            if bar_start <= start:
                                req = HistoryRequest(
                                    symbol=symbol,
                                    exchange=exchange,
                                    interval=Interval(interval),
                                    start=bar_end,
                                    end=end
                                )
                data = mddata_client.query_history(req)

                if data:
                    database_manager.save_bar_data(data)
                    if bar_end:
                        self.write_log(
                            f"{symbol}，数据库已有 {self.convertTime(bar_start)} 到 {bar_end}数据，从 {self.convertTime(bar_end)} 到{self.convertTime(end)}历史数据下载完成")
                    else:
                        self.write_log(
                            f"{symbol}，从 {self.convertTime(start)} 到{self.convertTime(end)}历史数据下载完成")
                else:
                    if bar_end:
                        self.write_log(
                            f"{symbol}，数据库已有 {self.convertTime(bar_start)} 到 {self.convertTime(bar_end)}数据，从 {self.convertTime(bar_end)} 到{self.convertTime(end)}或无历史数据")
                    else:
                        self.write_log(
                            f"{symbol}，从 {self.convertTime(start)} 到{self.convertTime(end)}历史数据下载失败")

            except Exception:
                msg = f"数据下载失败，触发异常：\n{traceback.format_exc()}"
                self.write_log(msg)
        self.write_log(f"--下载历史数据任务结束--")
        # Clear thread object handler.
        self.thread = None

    def convertTime(self,timestamp):
        return timestamp.strftime('%Y%m%d %H:%M:%S')

    def start_downloading(
        self,
        vt_symbol: str,
        interval: str,
        start: datetime,
        end: datetime
    ):
        if self.thread:
            self.write_log("已有任务在运行中，请等待完成")
            return False

        self.write_log("-" * 40)
        self.thread = Thread(
            target=self.run_downloading,
            args=(
                vt_symbol,
                interval,
                start,
                end
            )
        )
        self.thread.start()

        return True

    def get_all_trades(self):
        """"""
        return self.backtesting_engine.get_all_trades()

    def get_all_orders(self):
        """"""
        return self.backtesting_engine.get_all_orders()

    def get_all_daily_results(self):
        """"""
        return self.backtesting_engine.get_all_daily_results()

    def get_history_data(self):
        """"""
        return self.backtesting_engine.history_data

    def get_strategy_class_file(self, class_name: str):
        """"""
        strategy_class = self.classes[class_name]
        file_path = getfile(strategy_class)
        return file_path
