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
)
from vnpy.trader.object import Offset, Direction, OrderType, Interval
from datetime import time
import numpy as np

class BarJumpStepCloseStrategy(CtaTemplate):
    """"""

    author = "BIlly Zhang"

    init_pos =0
    init_entry_price = 0.0

    Kxian = 60
    HeYueJiaZhi = 100000
    HeYueChengShu = 10.0
    fixed_size = 1

    CLOSE_WINDOWS = 10
    JUMP = 10

    MARK_UP = 50
    MARK_DOWN = 12

    close_count_down = 0
    entry_price = 0
    last_close_price = 0


    parameters = [
        "init_pos",
        "init_entry_price",
        "fixed_size",
        "HeYueJiaZhi",
        "HeYueChengShu",
        "CLOSE_WINDOWS",
        "Kxian",
        "JUMP",
        "MARK_DOWN",
        "MARK_UP"
    ]
    variables = [
        "entry_price",
        "close_count_down"
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

        self.high_close = 100000
        self.low_close = 0
        self.pricetick = 1
        self.contact = 0
        self.waitNextBar = 0
        self.tick_price_list= np.zeros(self.CLOSE_WINDOWS)
        self.WAIT_CLOSE_BAR = self.CLOSE_WINDOWS*2


    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.contact = self.cta_engine.main_engine.get_contract(self.vt_symbol)
        self.pricetick = self.contact.pricetick

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


    def send_open_short_deal(self,price):
        self.openLongOrderID = self.send_direct_order(
            self.contact,
            Direction.SHORT,
            Offset.OPEN,
            price,
            self.fixed_size,
            OrderType.FOK
        )

    def send_open_long_deal(self,price):
        self.openShortOrderID = self.send_direct_order(
            self.contact,
            Direction.LONG,
            Offset.OPEN,
            price,
            self.fixed_size,
            OrderType.FOK
        )

    def on_tick(self, tick: TickData):
        """
        Callback of new tick data update.
        """
        self.tick_price_list[:-1] = self.tick_price_list[1:]
        self.tick_price_list[-1] = tick.last_price
        if min(self.tick_price_list) == 0:
            return

        if self.pos == 0 and self.waitNextBar <= 0:
            if tick.last_price - min(self.tick_price_list) > self.JUMP:
                self.send_open_long_deal(tick.ask_price_1)
            elif tick.last_price - max(self.tick_price_list) < -self.JUMP:
                self.send_open_short_deal(tick.bid_price_1)

        elif self.pos > 0:
            if tick.last_price <= self.low_close:
                if self.cancel_all():
                    self.sell(tick.bid_price_1, self.pos, False)
            if self.close_count_down <=0:
                self.cancel_all()
                self.sell(tick.bid_price_1, self.pos, False)

        elif self.pos < 0:
            if tick.last_price >= self.high_close:
                if self.cancel_all():
                    self.cover(tick.ask_price_1, abs(self.pos), False)
            if self.close_count_down <=0:
                self.cancel_all()
                self.cover(tick.ask_price_1, abs(self.pos), False)
        self.close_count_down -= 1
        self.waitNextBar -= 1
        # self.bg.update_tick(tick)


    def on_bar(self, bar: BarData):
        """
        Callback of new bar data update.

        """
        pass
        # self.last_close_price = bar.close_price
        # if self.check_not_trading_time(bar):
        #     self.waitNextBar = 1
        # else:
        #     self.waitNextBar = 0
        # self.put_event()

    def on_time_bar(self, bar: BarData):
        self.put_event()

    def on_order(self, order: OrderData):
        """
        Callback of new order data update.
        """
        pass

    def check_not_trading_time(self, bar):
        if (self.start_timePM <= bar.datetime.time() < self.exit_timeAM) or (
                self.start_timeNI <= bar.datetime.time() < self.exit_timeNI):
            return False
        else:
            return True

    def on_trade(self, trade: TradeData):
        """
        Callback of new trade data update.
        """
        if trade.offset == Offset.OPEN:
            self.entry_price = trade.price
            self.waitNextBar = self.WAIT_CLOSE_BAR
            self.close_count_down = self.CLOSE_WINDOWS
            if self.pos>0:
                self.high_close = trade.price + self.MARK_UP
                self.sell(self.high_close, abs(self.pos), False)
                self.low_close = trade.price - self.MARK_DOWN
            else:
                self.high_close = trade.price + self.MARK_DOWN
                self.low_close = trade.price - self.MARK_UP
                self.cover(self.low_close, abs(self.pos), False)

        self.put_event()

    def on_stop_order(self, stop_order: StopOrder):
        """
        :param stop_order:
        :return:
        """
        pass
