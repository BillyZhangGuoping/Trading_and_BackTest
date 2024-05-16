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

class MinTrendMaxStrategy(CtaTemplate):
    """"""

    author = "BIlly Zhang"

    init_pos =0
    init_entry_price = 0.0

    Kxian = 60
    MA_Windows = 40
    HeYueJiaZhi = 100000
    HeYueChengShu = 10.0
    fixed_size = 1




    CLOSE_BAR = 2
    close_count = 2

    MA_value = 0



    parameters = [
        "init_pos",
        "init_entry_price",
        "fixed_size",
        "HeYueJiaZhi",
        "HeYueChengShu",
        "Kxian",
        "MA_Windows"
    ]
    variables = [
        "entry_price",
        "price_rate",
        "MA_value"
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
        self.pos = self.init_pos
        self.entry_price = self.init_entry_price
        self.PosPrice = self.entry_price

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
        if self.trading:
            self.write_log(f"{self.strategy_name} coming bar: {bar.datetime}")
        am = self.am
        am.update_bar(bar)
        if not am.inited:
            return


        self.cancel_all()
        if (bar.datetime.time() in [time(9,0),time(21,0)] ) and self.MA_value !=0:
            if 1.015 > am.close_array[-2]/bar.open_price > 1.005 and 1.01>am.close_array[-2]/am.sma(self.MA_Windows) > 0.99:
                self.buy(price=bar.close_price + 2, volume=self.fixed_size,stop = False)
                self.close_count = self.CLOSE_BAR
            elif 1.015 > bar.open_price/am.close_array[-2] > 1.005 and 1.01>am.sma(self.MA_Windows)/am.close_array[-2] > 0.99:
                self.short(price=bar.close_price -2, volume= self.fixed_size, stop = False)
                self.close_count = self.CLOSE_BAR
        if self.close_count <=0 and self.pos != 0:
            if self.pos >0:
                self.sell(price=bar.close_price -2,volume=self.pos, stop= False)
            else:
                self.cover(price=bar.close_price + 2, volume= abs(self.pos), stop= False)
        self.close_count -= 1

        self.MA_value = self.am.sma(self.MA_Windows)
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
        self.put_event()

    def on_stop_order(self, stop_order: StopOrder):
        """
        :param stop_order:
        :return:
        """
        pass
