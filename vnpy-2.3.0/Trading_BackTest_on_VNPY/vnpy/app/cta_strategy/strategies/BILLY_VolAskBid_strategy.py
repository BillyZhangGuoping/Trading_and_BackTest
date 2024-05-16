from datetime import time
import queue
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


class BILLY_VolAskBidStrategy(CtaTemplate):
    """"""
    author = "Billy"
    fixed_size = 1
    ratio = 3
    tick_count_limit = 2
    Vol_Limit = 500
    price_dif_limit = 2

    Markup = 1

    PosPrice = 0
    Vol = 0

    price_dif = 0
    buy_algoid = []
    sell_algoid = []
    short_algoid = []
    cover_algoid = []



    parameters = ["fixed_size","ratio","tick_count_limit","price_dif_limit","Vol_Limit","Markup"]
    variables = ["PosPrice","Vol","price_dif","buy_algoid","short_algoid"]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """"""
        super(BILLY_VolAskBidStrategy, self).__init__(
            cta_engine, strategy_name, vt_symbol, setting
        )

        self.start_timePM = time(hour=9, minute=20)
        self.start_timeAM = time(hour=13, minute=35)
        self.start_timeNI = time(hour=21, minute=5)

        self.exit_timePM = time(hour=11, minute=25)
        self.exit_timeAM = time(hour=14, minute=50)
        self.exit_timeNI = time(hour=22, minute=50)
        self.last_tick = None
        self.tick_queue = queue.Queue(maxsize = self.tick_count_limit)
        self.last_bid = 0
        self.last_ask = 0

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
        if not self.tick_queue.full():
            self.tick_queue.put(tick)
            self.last_tick = tick
            return
        else:
            First_tick =self.tick_queue.get()
            self.Vol = tick.volume - First_tick.volume
            self.price_dif = tick.last_price - First_tick.last_price

            self.last_bid = self.last_tick.bid_price_1
            self.last_ask = self.last_tick.ask_price_1

            self.last_tick = tick
            self.tick_queue.put(tick)



        if (tick.datetime.time() > self.start_timePM and tick.datetime.time() < self.exit_timeAM) or (
                tick.datetime.time() > self.start_timeNI and tick.datetime.time() < self.exit_timeNI):
            if self.pos == 0:
                if self.Vol > self.Vol_Limit:
                    if tick.last_price == self.last_ask and self.price_dif >= self.price_dif_limit and tick.bid_volume_1 > self.ratio * tick.ask_volume_1:
                            self.buy_algoid = self.buy(tick.last_price, self.fixed_size,False)
                    elif tick.last_price == self.last_bid and self.price_dif <= -self.price_dif_limit and tick.ask_volume_1 > self.ratio * tick.bid_volume_1:
                            self.short_algoid = self.short(tick.last_price, self.fixed_size,False)
            elif self.pos > 0:
                if tick.last_price < self.PosPrice - self.Markup:
                    self.cancel_all()
                    self.sell(tick.last_price, abs(self.pos), stop=False)
            else:
                if tick.last_price > self.PosPrice + self.Markup:
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