from datetime import time
import numpy as np
from vnpy.trader.object import Offset
from vnpy.app.cta_strategy import (
    CtaTemplate,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData,
    BarGenerator,
    ArrayManager
)


class BILLY_HighLowLineStrategy(CtaTemplate):
    """"""
    author = "Billy"
    fixed_size = 1
    Countdown = 15
    range = 5
    Markup = 2

    PosPrice = 0
    Count = 0
    highprice = 0
    lowprice = 0
    buy_algoid = []
    sell_algoid = []
    short_algoid = []
    cover_algoid = []



    parameters = ["fixed_size","Countdown","range","Markup"]
    variables = ["PosPrice","Count","highprice","lowprice","buy_algoid","short_algoid"]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """"""
        super(BILLY_HighLowLineStrategy, self).__init__(
            cta_engine, strategy_name, vt_symbol, setting
        )

        self.start_timePM = time(hour=9, minute=20)
        self.start_timeAM = time(hour=13, minute=35)
        self.start_timeNI = time(hour=21, minute=5)

        self.exit_timePM = time(hour=11, minute=25)
        self.exit_timeAM = time(hour=14, minute=50)
        self.exit_timeNI = time(hour=2, minute=46)
        self.highprice = 0
        self.lowprice = 0

    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.write_log("策略初始化")

    def on_start(self):
        """
        Callback when strategy is started.
        """
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

        if (tick.datetime.time() > self.start_timePM and tick.datetime.time() < self.exit_timeAM) or (
                tick.datetime.time() > self.start_timeNI or tick.datetime.time() < self.exit_timeNI):
            self.Count = self.Count + 1

            if self.pos == 0:
                if self.Count >= self.Countdown:
                    self.cancel_all()
                    self.highprice = tick.last_price + self.range
                    self.lowprice = tick.last_price - self.range
                    self.Count = 0
                elif self.highprice !=0:
                    if tick.bid_price_1 <= self.lowprice:
                        self.buy_algoid = self.buy(tick.ask_price_1, self.fixed_size,False)
                    elif tick.ask_price_1 >= self.highprice:
                        self.short_algoid = self.short(tick.bid_price_1, self.fixed_size,False)
            elif self.pos > 0:
                if tick.last_price < self.PosPrice - self.Markup:
                    self.cancel_all()
                    self.sell(tick.bid_price_1, abs(self.pos), stop=False)
            else:
                if tick.last_price > self.PosPrice + self.Markup:
                    self.cancel_all()
                    self.cover(tick.ask_price_1, abs(self.pos), stop=False)
        else:
            if self.pos == 0:
                return
            elif self.pos > 0:
                self.cancel_all()
                self.sell(tick.bid_price_1, abs(self.pos), stop=False)
            else:
                self.cancel_all()
                self.cover(tick.ask_price_1, abs(self.pos), stop=False)

        self.put_event()

    def on_bar(self, bar: BarData):
        """
        Callback of new bar data update.
        """

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
            self.PosPrice = trade.price
            self.cancel_all()
            if self.pos > 0:
                self.sell(self.PosPrice + self.Markup,self.pos)
            else:
                self.cover(self.PosPrice - self.Markup,abs(self.pos))

        self.put_event()
    def on_stop_order(self, stop_order: StopOrder):
        """
        Callback of stop order update.
        """
        pass