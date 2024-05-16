from datetime import time
import numpy as np
from vnpy.trader.object import Offset
from collections import defaultdict
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


class BILLY_DictTrendStrategy(CtaTemplate):
    """"""
    author = "Billy"
    fixed_size = 1
    AskBidRatioLimit  = 3
    PriceArry = 5
    Markup = 1
    OPIntRatioLimit = 40
    tickAskBidRatioLimit = 5


    PosPrice = 0
    OPIntRatio = 0
    AskBidRatio = 0
    tickIndictor = 0
    asksum = 0
    bidsum = 0
    buy_algoid = []
    sell_algoid = []
    short_algoid = []
    cover_algoid = []



    parameters = ["fixed_size","tickAskBidRatioLimit","AskBidRatioLimit","OPIntRatioLimit","Markup"]
    variables = ["PosPrice","OPIntRatio","AskBidRatio","asksum","bidsum","tickIndictor","buy_algoid","short_algoid"]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """"""
        super(BILLY_DictTrendStrategy, self).__init__(
            cta_engine, strategy_name, vt_symbol, setting
        )

        self.start_timePM = time(hour=9, minute=10)
        self.start_timeAM = time(hour=13, minute=35)
        self.start_timeNI = time(hour=21, minute=10)

        self.exit_timePM = time(hour=11, minute=25)
        self.exit_timeAM = time(hour=14, minute=50)
        self.exit_timeNI = time(hour=2, minute=50)

        self.PriceDict = defaultdict(int)
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
            self.PriceDict[tick.ask_price_1] = tick.ask_volume_1
            self.PriceDict[tick.bid_price_1] = tick.bid_volume_1
            self.OPIntRatio =  tick.volume - self.last_tick.volume


        if (tick.datetime.time() > self.start_timePM and tick.datetime.time() < self.exit_timeAM) or (
                tick.datetime.time() > self.start_timeNI or tick.datetime.time() < self.exit_timeNI):
            if self.pos == 0:
                self.cancel_all()
                if self.OPIntRatio > self.OPIntRatioLimit:
                    if min(self.PriceDict[tick.ask_price_1],self.PriceDict[tick.ask_price_1+1],self.PriceDict[tick.ask_price_1+2],
                           self.PriceDict[tick.bid_price_1], self.PriceDict[tick.bid_price_1 - 1],self.PriceDict[tick.bid_price_1 - 2])== 0:
                        self.last_tick = tick
                        return
                    self.asksum = sum([self.PriceDict[tick.ask_price_1],self.PriceDict[tick.ask_price_1+1],self.PriceDict[tick.ask_price_1+2]])
                    self.bidsum = sum([self.PriceDict[tick.bid_price_1],self.PriceDict[tick.bid_price_1-1],self.PriceDict[tick.bid_price_1-2]])
                    self.AskBidRatio = self.asksum / self.bidsum
                    if self.last_tick.last_price > tick.last_price and self.tickAskBidRatioLimit*tick.bid_volume_1 <  tick.ask_volume_1 and self.AskBidRatio > self.AskBidRatioLimit:
                        self.short_algoid = self.short(tick.bid_price_1, self.fixed_size, False)
                    elif self.last_tick.last_price < tick.last_price and tick.bid_volume_1 >  self.tickAskBidRatioLimit*tick.ask_volume_1 and self.bidsum/self.asksum  > self.AskBidRatioLimit:
                        self.buy_algoid = self.buy(tick.ask_price_1, self.fixed_size, False)

            elif self.pos > 0:
                if tick.last_price < self.PosPrice - self.Markup*2:
                    self.cancel_all()
                    self.sell(tick.last_price, abs(self.pos), stop=False)
            else:
                if tick.last_price > self.PosPrice + self.Markup*2:
                    self.cancel_all()
                    self.cover(tick.last_price, abs(self.pos), stop=False)
        else:
            if self.pos == 0:
                return
            elif self.pos > 0:
                self.cancel_all()
                self.sell(tick.bid_price_1, abs(self.pos), stop=False)
            else:
                self.cancel_all()
                self.cover(tick.ask_price_1, abs(self.pos), stop=False)
        self.last_tick = tick
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
            self.cancel_all()
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