"""



"""
from vnpy.app.cta_strategy import (
    CtaTemplate,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData,
    BarGenerator,
    ArrayManager,
)
from vnpy.trader.constant import Interval
import numpy as np
from copy import copy
import talib
from vnpy.trader.object import Offset
from datetime import time

class JumpTrendStrategy(CtaTemplate):
    """"""

    author = "BIlly Zhang"

    init_pos =0
    init_entry_price = 0.0

    Kxian = 60
    MA_Windows = 30
    HeYueJiaZhi = 100000
    HeYueChengShu = 10.0
    fixed_size = 1

    OPEN_WINDOWS = 30

    JUMP_PRECENTAGE = 0.45
    OPEN_PRECENTAGE = 0.5

    last_precentage = 0
    MA_precentage = 0

    MA_value = 0
    open_count = 0
    open_direction = 0

    MARK_UP = 10
    open_bar_price = 0



    parameters = [
        "init_pos",
        "init_entry_price",
        "fixed_size",
        "HeYueJiaZhi",
        "HeYueChengShu",
        "OPEN_WINDOWS",
        "Kxian",
        "MA_Windows",
        "JUMP_PRECENTAGE",
        "OPEN_PRECENTAGE",
        "MARK_UP"
    ]
    variables = [
        "entry_price",
        "price_rate",
        "MA_value",
        "open_count",
        "last_precentage",
        "MA_precentage",
        "open_direction",
        "open_bar_price"
                 ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, vt_local, setting):
        """"""
        super().__init__(cta_engine, strategy_name, vt_symbol, vt_local, setting)

        if  360>self.Kxian >= 240 :
            self.bg = BarGenerator(self.on_bar, 4, self.on_time_bar, Interval.HOUR)
        elif 240>self.Kxian >= 180:
            self.bg = BarGenerator(self.on_bar, 3, self.on_time_bar, Interval.HOUR)
        elif 180>self.Kxian >= 60:
            self.bg = BarGenerator(self.on_bar, 1, self.on_time_bar, Interval.HOUR)
        elif self.Kxian >= 360:
            self.bg = BarGenerator(self.on_bar, 1, self.on_time_bar, Interval.DAILY)
        else:
            self.bg = BarGenerator(self.on_bar, self.Kxian, self.on_time_bar,Interval.MINUTE)


        self.am = ArrayManager(self.MA_Windows + 50)

    def on_init(self):
        """
        Callback when strategy is inited.
        """

        self.write_log("策略初始化")
        self.load_bar(15)

    def on_start(self):
        """
        Callback when strategy is started.
        """
        self.pos = self.init_pos
        self.entry_price = self.init_entry_price
        self.PosPrice = self.entry_price
        self.write_log("策略启动")


    def on_stop(self):
        """
        Callback when strategy is stopped.
        """
        self.write_log("策略停止")

    def on_tick(self, tick: TickData):
        """
        Callback of new tick data update.
        """

        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData):
        """
        Callback of new bar data update.

        """
        # if self.trading:
        #     self.write_log(f"{self.strategy_name} coming bar: {bar.datetime}")
        am = self.am
        am.update_bar(bar)
        if not am.inited:
            return
        MA_value_array = self.am.sma(n=self.MA_Windows,array=True)
        self.MA_value = MA_value_array[-1]
        self.last_precentage = (bar.close_price - am.close_array[-2])*100.0/am.close_array[-2]
        self.MA_precentage = abs(self.MA_value - bar.close_price)*100.0/bar.close_price
        last_MA_precentage = (MA_value_array[-2] - am.close_array[-2])*100.0/am.close_array[-2]

        self.cancel_all()
        if self.last_precentage >= self.JUMP_PRECENTAGE and last_MA_precentage <= self.OPEN_PRECENTAGE:
            self.open_count = self.OPEN_WINDOWS
            self.open_bar_price = bar.close_price
            self.open_direction =1

        elif self.last_precentage <= -self.JUMP_PRECENTAGE and last_MA_precentage <= self.OPEN_PRECENTAGE:
            self.open_count = self.OPEN_WINDOWS
            self.open_bar_price = bar.close_price
            self.open_direction = -1

        if self.open_count >=0 and self.pos == 0 and self.MA_precentage < self.OPEN_PRECENTAGE:
            if bar.close_price > self.open_bar_price:
                self.buy(price=bar.close_price + 1, volume=self.fixed_size, stop=False)
            elif bar.close_price < self.open_bar_price:
                self.short(price=bar.close_price - 1, volume=self.fixed_size, stop=False)
            else:
                self.open_count = 0

        if self.pos > 0:
            self.sell(self.entry_price + self.MARK_UP, abs(self.pos), False)
            self.sell(self.entry_price - self.MARK_UP, abs(self.pos), True)
        elif self.pos <0:
            self.cover(self.entry_price - self.MARK_UP, abs(self.pos), False)
            self.cover(self.entry_price + self.MARK_UP, abs(self.pos), True)



        self.open_count -= 1
        self.put_event()




    def on_time_bar(self, bar: BarData):

        self.put_event()

    def on_order(self, order: OrderData):
        """
        Callback of new order data update.
        """
        pass

    def on_trade(self, trade: TradeData):
        """
        Callback of new trade data update.
        """
        if trade.offset == Offset.OPEN:
            self.entry_price = trade.price
        else:
            self.open_direction = 0
            self.open_count = 0

        self.put_event()

    def on_stop_order(self, stop_order: StopOrder):
        """
        :param stop_order:
        :return:
        """
        pass
