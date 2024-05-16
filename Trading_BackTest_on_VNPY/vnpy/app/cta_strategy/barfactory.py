
from vnpy.event import Event, EventEngine
from vnpy.trader.engine import BaseEngine, MainEngine
from vnpy.trader.constant import Interval
from vnpy.trader.object import (
    TickData,
    BarData
)

from vnpy.trader.event import EVENT_TICK
from vnpy.trader.utility import  BarGenerator
from typing import Callable

APP_NAME = "BarFactory"

class BarProductor:
    """
    BarProductor有个base_bg bargenertor默认提供1分钟bar，其他分钟长度bargenertor使用这个base_bg的一分钟bar合成
    有{间隔 - generator}字典保存不同间隔和对应的bargenerator
    有{间隔 - [注册方法]} 字典存储不同间隔和需要通知方法队列。
    """
    def __init__(self,vt_symbol):
        self.vt_symbol = vt_symbol
        self.base_bg = BarGenerator(self.on_bar,1,self._process)
        self.interval_bg = {}
        self.interval_functions_dict = {}

        self.interval_bg[(1,"1m")] = self.base_bg
        self.interval_functions_dict[(1,"1m")] = []

    def register_function(self, interval:tuple, function) -> None:
        function_list = self.get_function_list(interval)
        if function not in function_list:
            function_list.append(function)

    def get_function_list(self,interval):
        function_list = self.interval_functions_dict.get(interval,None)
        if not function_list:
            self.get_bg(interval)
            self.interval_functions_dict[interval] = []
        return self.interval_functions_dict[interval]


    def get_bg(self,interval:tuple):
        bg = self.interval_bg.get(interval, None)
        if not bg:
            self.interval_bg[interval] = BarGenerator(self.on_bar, interval[0], self._process, interval[1])
        return self.interval_bg[interval]


    def on_tick(self, tick: TickData):
        """
        Callback of new tick data update.
        """
        self.base_bg.update_tick(tick)

    def on_bar(self, bar: BarData):
        """
        Callback of new bar data update.
        """
        [bg.update_bar(bar) for bg in self.interval_bg.values()]

    def _process(self,bar: BarData):
        function_list = self.get_function_list((bar.window,bar.interval))
        [function(bar) for function in function_list]


class BarFactoryEngine(BaseEngine):
    """
    Bar批量生成器，策略注册需要的bar和对应on_bar或on_minute_bar方法；BarFactoryEngine去生成bar，并推送给对应方法。
    BarFactoryEngine带有{品种-bar_productor实例} 字典存储对应不同品种和对应bar_productor实例，
    """

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine):
        """"""
        super().__init__(main_engine, event_engine, APP_NAME)

        self.symbol_barProdutors = {}

    def register_bar_function(
            self,
            vt_symbol,
            window: int = 0,
            on_window_bar: Callable = None,
            interval: Interval = Interval.MINUTE
    ):
        """"""
        bar_productor = self.get_symbol_barProdutors(vt_symbol)
        bar_productor.register_function((window,interval),on_window_bar)

    def get_symbol_barProdutors(self, vt_symbol: str):

        bp = self.symbol_barProdutors.get(vt_symbol, None)

        if not bp:
            bp = BarProductor(vt_symbol)
            self.symbol_barProdutors[vt_symbol] = bp
        return bp

    def register_event(self):
        """"""
        self.event_engine.register(EVENT_TICK, self.process_tick_event)

    def process_tick_event(self, event: Event):
        """"""
        tick = event.data
        for tick.vt_symbol in self.symbol_barProdutors:
            self.symbol_barProdutors[tick.vt_symbol].on_tick(tick)

    def update_bar(self, bar: BarData):
        """"""

        for bar.vt_symbol in self.symbol_barProdutors:
            self.symbol_barProdutors[bar.vt_symbol].on_bar(bar)