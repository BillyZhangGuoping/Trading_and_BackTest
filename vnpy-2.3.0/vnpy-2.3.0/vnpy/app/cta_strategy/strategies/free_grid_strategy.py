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
from vnpy.trader.constant import Interval,Direction,Status
import numpy as np
from copy import copy
import talib
from vnpy.trader.object import Offset


class FreeGridStrategy(CtaTemplate):
    """"""

    author = "BIlly Zhang"

    init_pos =0
    init_entry_price = 0.0

    Kxian = 60
    HighLow_Windows = 40
    HeYueJiaZhi = 100000
    HeYueChengShu = 10.0
    current_HeYueJiaZhi = 100000
    Markup = 2
    lose_limit = 0.3

    interval_balRatio = 0.2
    current_balRatio = 0.6

    Trend = 0

    fixed_size = 1
    close_fixed_size = 1


    OPEN_HOLD_BAR = 6
    CLOSE_HOLD_BAR = 4


    MA_value = 0
    real_Markup = 0
    real_lose_rate = 0

    price_rate = 0
    entry_price = 0
    close_bar_count = 0


    high = 0
    low = 100000
    long_stop = 0
    short_stop = 0
    Open_close = 0

    long_vt_orderids = []
    short_vt_orderids = []

    interval_balRatio = 0.2
    current_balRatio = 0.6
    leverage = 1
    real_leverage = 1


    parameters = [
        "init_pos",
        "init_entry_price",
        "fixed_size",
        "close_fixed_size",
        "HeYueJiaZhi",
        "HeYueChengShu",
        "leverage",
        "Kxian",
        "lose_limit",
        "HighLow_Windows",
        "Markup",
        "Trend",
        "Open_close",
        "OPEN_HOLD_BAR",
        "CLOSE_HOLD_BAR"
    ]
    variables = [
        "entry_price",
        "price_rate",
        "close_bar_count",
        "real_leverage",
        "real_Markup",
        "real_lose_rate",
        "high",
        "low"

    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, vt_local, setting):
        """"""
        super().__init__(cta_engine, strategy_name, vt_symbol, vt_local, setting)

        if self.Kxian >= 240 :
            self.bg = BarGenerator(self.on_bar, 4, self.on_time_bar, Interval.HOUR)
        elif 240>self.Kxian >= 180:
            self.bg = BarGenerator(self.on_bar, 3, self.on_time_bar, Interval.HOUR)
        elif 180>self.Kxian >= 60:
            self.bg = BarGenerator(self.on_bar, 1, self.on_time_bar, Interval.HOUR)
        else:
            self.bg = BarGenerator(self.on_bar, self.Kxian, self.on_time_bar)

        self.contact = None

        self.am = ArrayManager(self.HighLow_Windows + 40)
        self.mid  = 0


    def on_init(self):
        """
        Callback when strategy is inited.
        """

        self.write_log("策略初始化")
        self.load_bar(30)


    def on_start(self):
        """
        Callback when strategy is started.
        """
        self.contact = self.cta_engine.main_engine.get_contract(self.vt_symbol)
        self.real_Markup = self.Markup * self.contact.pricetick
        self.real_leverage = min(self.leverage,1/ self.contact.LongMarginRatioByMoney)

        self.pos = self.init_pos
        self.entry_price = self.init_entry_price
        self.PosPrice = self.entry_price
        if self.Trend == 1 and self.pos == 0:
            self.PosPrice = 1000000
        self.write_log(f"pos price is {self.PosPrice}, high price is {self.high} low price is {self.low}")
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
        if self.close_bar_count <=0:
            if tick.last_price >= self.high:
                if self.Trend == -1 and self.Open_close !=-1:
                    self.short(price=self.high, volume=self.fixed_size, stop=False)
                    self.close_bar_count = 1
                if self.pos >0 and self.Open_close != 1:
                    self.sell(price=self.high, volume=min(self.close_fixed_size, self.pos), stop=False)
                    self.close_bar_count = 1
            elif tick.last_price <= self.low:
                if self.Trend == 1 and self.Open_close !=-1:
                    self.buy(price=self.low, volume=self.fixed_size, stop=False)
                    self.close_bar_count = 1
                if self.pos<0 and self.Open_close != 1:
                    self.cover(price=self.low, volume=min(self.close_fixed_size, abs(self.pos)), stop=False)
                    self.close_bar_count = 1
        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData):
        """
        Callback of new bar data update.

        """
        # self.fixed_size = int(self.HeYueChengShu * self.real_leverage / (bar.close_price * self.contact.size))
        if self.trading:
            try:
                if self.pos > 0:
                    self.price_rate = (bar.close_price - self.entry_price)  / (self.entry_price * self.contact.LongMarginRatioByMoney)
                    if self.price_rate < -self.lose_limit:
                        self.sell(price=bar.low_price, volume=self.pos, stop=False)
                elif self.pos < 0:
                    self.price_rate = (self.entry_price - bar.close_price ) / (self.entry_price * self.contact.ShortMarginRatioByMoney)
                    if self.price_rate < -self.lose_limit:
                        self.cover(price=bar.high_price,volume=abs(self.pos), stop=False)
            except:
                print("entry_price is zero")

        self.bg.update_bar(bar)

        self.put_event()

    def on_time_bar(self, bar: BarData):
        am = self.am
        am.update_bar(bar)
        if not am.inited:
            return

        high, low = am.donchian(self.HighLow_Windows)

        self.close_bar_count = self.close_bar_count - 1
        self.cancel_all()
        self.high = high + self.real_Markup
        self.low = low - self.real_Markup
        if self.PosPrice != 0:
            if self.PosPrice > high:
                self.high = self.PosPrice + self.real_Markup
            elif self.PosPrice < low:
                self.low = self.PosPrice - self.real_Markup

        if self.trading:
            self.write_log(f"当前bar信息 开始时间：{bar.datetime.strftime('%Y%m%d %H:%M:%S.%f')};开始价格 {bar.open_price}，结束价格{bar.close_price}")
            self.write_log(f"pos price is {self.PosPrice}, high price is {self.high} low price is {self.low}")
        self.sync_data()
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

            self.close_bar_count = self.OPEN_HOLD_BAR
        else:
            self.close_bar_count = self.CLOSE_HOLD_BAR

        self.put_event()

    def on_stop_order(self, stop_order: StopOrder):
        """
        :param stop_order:
        :return:
        """
        pass
