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


class BILLY_CrashTrendStrategy(CtaTemplate):
    """"""
    author = "Billy"
    fixed_size = 1
    ArrayLength = 20
    SendOrderLast = 4
    Markup = 1

    PosPrice = 0
    tickIndictor = 0

    buy_algoid = []
    sell_algoid = []
    short_algoid = []
    cover_algoid = []



    parameters = ["fixed_size","ArrayLength","Markup","SendOrderLast"]
    variables = ["PosPrice","tickIndictor","buy_algoid","short_algoid"]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """"""
        super(BILLY_CrashTrendStrategy, self).__init__(
            cta_engine, strategy_name, vt_symbol, setting
        )

        self.start_timePM = time(hour=9, minute=10)
        self.start_timeAM = time(hour=13, minute=35)
        self.start_timeNI = time(hour=21, minute=10)

        self.exit_timePM = time(hour=11, minute=25)
        self.exit_timeAM = time(hour=14, minute=50)
        self.exit_timeNI = time(hour=2, minute=50)

        self.PriceArray = np.zeros(self.ArrayLength)
        self.SendOrderCount = self.SendOrderLast
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
            if tick.last_price > self.last_tick.ask_price_1:
                self.tickIndictor = 1
            elif tick.last_price < self.last_tick.bid_price_1:
                self.tickIndictor = -1
            else:
                self.tickIndictor = 0
            self.PriceArray[0:self.ArrayLength - 1] = self.PriceArray[1:self.ArrayLength]
            self.PriceArray[-1] = tick.last_price

        if (tick.datetime.time() > self.start_timePM and tick.datetime.time() < self.exit_timeAM) or (
                tick.datetime.time() > self.start_timeNI or tick.datetime.time() < self.exit_timeNI):
            if self.pos == 0:
                if self.buy_algoid or self.short_algoid:
                    self.SendOrderCount = self.SendOrderCount - 1
                if self.tickIndictor == 1 and self.SendOrderCount == self.SendOrderLast and max(self.PriceArray) == tick.last_price:
                    self.short_algoid = self.short(tick.ask_price_1, self.fixed_size, False)

                elif self.tickIndictor == -1 and self.SendOrderCount == self.SendOrderLast and min(self.PriceArray) == tick.last_price:
                    self.buy_algoid = self.buy(tick.bid_price_1, self.fixed_size, False)

                elif self.SendOrderCount == 0:
                    self.cancel_all()
                    self.buy_algoid = []
                    self.short_algoid = []
                    self.SendOrderCount = self.SendOrderLast
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