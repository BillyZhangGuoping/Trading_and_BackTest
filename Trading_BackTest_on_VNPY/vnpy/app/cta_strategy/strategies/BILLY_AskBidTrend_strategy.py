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


class BILLY_AskBidTrendStrategy(CtaTemplate):
    """"""
    author = "Billy"
    fixed_size = 1
    ArrayLength = 3
    Markup = 1

    PosPrice = 0
    Count = 0

    buy_algoid = []
    sell_algoid = []
    short_algoid = []
    cover_algoid = []



    parameters = ["fixed_size","ArrayLength","Markup"]
    variables = ["PosPrice","Count","buy_algoid","short_algoid"]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """"""
        super(BILLY_AskBidTrendStrategy, self).__init__(
            cta_engine, strategy_name, vt_symbol, setting
        )

        self.start_timePM = time(hour=9, minute=20)
        self.start_timeAM = time(hour=13, minute=35)
        self.start_timeNI = time(hour=21, minute=5)

        self.exit_timePM = time(hour=11, minute=25)
        self.exit_timeAM = time(hour=14, minute=50)
        self.exit_timeNI = time(hour=2, minute=46)

        self.AskbidArray = np.zeros(self.ArrayLength)
        self.last_tick = None

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
        if not self.last_tick:
            self.last_tick = tick
            return
        else:
            if tick.last_price == self.last_tick.ask_price_1:
                tickIndictor = -1
            elif tick.last_price == self.last_tick.bid_price_1:
                tickIndictor = 1
            else:
                tickIndictor = 0
            self.AskbidArray[0:self.ArrayLength - 1] = self.AskbidArray[1:self.ArrayLength]
            self.AskbidArray[-1] = tickIndictor
            self.last_tick = tick

        if (tick.datetime.time() > self.start_timePM and tick.datetime.time() < self.exit_timeAM) or (
                tick.datetime.time() > self.start_timeNI or tick.datetime.time() < self.exit_timeNI):
            if self.pos == 0:
                self.Count = sum(self.AskbidArray)
                if self.Count  >= self.ArrayLength:
                    if not self.buy_algoid:
                        self.buy_algoid = self.buy(tick.bid_price_1, self.fixed_size,False)
                elif self.Count  <= -self.ArrayLength:
                    if not self.short_algoid:
                        self.short_algoid = self.short(tick.ask_price_1, self.fixed_size)
                else:
                    self.cancel_all()
                    self.buy_algoid = []
                    self.short_algoid = []
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