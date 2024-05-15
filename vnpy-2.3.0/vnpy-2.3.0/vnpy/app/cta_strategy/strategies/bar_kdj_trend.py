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
    ArrayManager
)
from vnpy.trader.object import Offset, Direction, OrderType, Interval
from datetime import time


class BarKDJTrendStrategy(CtaTemplate):
    """"""

    author = "BIlly Zhang"

    init_pos = 0
    init_entry_price = 0.0

    Kxian = 1
    HeYueJiaZhi = 100000
    HeYueChengShu = 10.0
    fixed_size = 1

    OPEN_WINDOWS = 10
    CLOSE_WINDOWS = 5

    FAST_WINDOWS = 5
    SLOW_WINDOWS = 20


    JUMP = 6
    MARK_UP = 4
    MARK_DOWN = 4

    close_count_down = 0
    open_count_down = 0
    entry_price = 0

    high_close = 1000000
    low_close = 0
    bar_high = 0


    parameters = [
        "init_pos",
        "init_entry_price",
        "fixed_size",
        "HeYueJiaZhi",
        "HeYueChengShu",
        "CLOSE_WINDOWS",
        "FAST_WINDOWS",
        "SLOW_WINDOWS",
        "Kxian",
        "MARK_DOWN",
        "MARK_UP"
    ]
    variables = [
        "entry_price",
        "close_count_down",
        "high_close",
        "low_close"
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, vt_local, setting):
        """"""
        super().__init__(cta_engine, strategy_name, vt_symbol, vt_local, setting)

        if 360 > self.Kxian >= 240:
            self.bg = BarGenerator(self.on_bar, 4, self.on_time_bar, Interval.HOUR)
        elif 240 > self.Kxian >= 180:
            self.bg = BarGenerator(self.on_bar, 3, self.on_time_bar, Interval.HOUR)
        elif 180 > self.Kxian >= 60:
            self.bg = BarGenerator(self.on_bar, 1, self.on_time_bar, Interval.HOUR)
        elif self.Kxian >= 360:
            self.bg = BarGenerator(self.on_bar, 1, self.on_time_bar, Interval.DAILY)
        else:
            self.bg = BarGenerator(self.on_bar, self.Kxian, self.on_time_bar, Interval.MINUTE)
        self.am = ArrayManager()

        self.contact = 0
        self.close_indicator = 0

        self.high_limit = 0
        self.low_limit = 10000000000

        self.Touch_JUMP = 0
        self.jump_price = 0
        self.touch_open_price = 0
        self.price_before_jump = 0

        self.diff = 0

        self.jump_jump_price = 0
        self.turn_count = 0
        self.turn_close_count = 0

        self.close_request = []

        self.not_trading_time = False


        self.start_timePM = time(hour=9, minute=10)
        self.start_timeNI = time(hour=21, minute=10)

        self.exit_timeAM = time(hour=14, minute=55)
        self.exit_timeNI = time(hour=22, minute=55)

        self.exit_open_timeAM = time(hour=14, minute=45)
        self.exit_open_timeNI = time(hour=22, minute=45)

    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.jump = self.pricetick * self.JUMP
        self.mark_up = self.pricetick * self.MARK_UP
        self.mark_down = self.pricetick * self.MARK_DOWN

        self.write_log("策略初始化")
        self.load_bar(3)

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
        if self.high_limit == 0:
            self.high_limit = tick.limit_up - self.pricetick
            self.low_limit = tick.limit_down + self.pricetick

        if self.pos > 0:
            if tick.last_price < self.low_close or self.close_indicator == 1:
                self.cancel_all()
                self.close_request = self.sell(tick.bid_price_1, self.pos, False)

        elif self.pos < 0:
            if tick.last_price > self.high_close or self.close_indicator == -1:
                self.cancel_all()
                self.close_request = self.cover(tick.ask_price_1, abs(self.pos), False)

        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData):
        """
        Callback of new bar data update.
        """
        self.not_trading_time = self.check_not_trading_time(bar)
        if self.not_trading_time:
            self.Touch_JUMP = 0
            if self.pos > 0:
                self.close_indicator = 1
            elif self.pos < 0:
                self.close_indicator = -1
            else:
                self.cancel_all()
        else:
            if self.pos > 0:
                if self.close_count_down <= 0:
                    self.close_indicator = 1
                if not self.get_orderids():
                    self.sell(self.high_close, self.pos, False)
            elif self.pos < 0:
                if self.close_count_down <= 0:
                    self.close_indicator = -1
                if not self.get_orderids():
                    self.cover(self.low_close, abs(self.pos), False)

        self.close_count_down -= 1
        self.bg.update_bar(bar)

    def on_time_bar(self, bar: BarData):
        am = self.am
        am.update_bar(bar)
        if not am.inited:
            return
        # if self.trading:
        #     self.write_log(
        #         f"k : {self.k}, self.d: {self.d},  self.j: {self.j}")
        fast_array = am.ema(self.FAST_WINDOWS,True)
        slow_arry = am.ema(self.SLOW_WINDOWS,True)
        if self.trading:
            self.write_log(
                f"fast_array : {fast_array[-1]}, slow_arry : {slow_arry [-1]}")
        if not self.not_trading_time:
            if self.pos == 0:
                self.high_close = 1000000
                self.low_close = 0
                self.cancel_all()
                if fast_array[-1] > slow_arry[-1] and fast_array[-2] < slow_arry[-2] and (fast_array[-2] - slow_arry[-2]) > (fast_array[-5] - slow_arry [-5]) > (fast_array[-10] - slow_arry[-10]):
                    self.cancel_all()
                    self.buy(price=bar.close_price +  2* self.pricetick, volume=self.fixed_size, stop=False)
                elif fast_array[-1] < slow_arry[-1] and fast_array[-2] > slow_arry[-2] and (fast_array[-2] - slow_arry[-2]) < (fast_array[-5] - slow_arry [-5]) < (fast_array[-10] - slow_arry[-10]):
                    self.cancel_all()
                    self.short(price=bar.close_price - 2 * self.pricetick, volume=self.fixed_size, stop=False)
            elif self.pos > 0:
                if fast_array[-1] < slow_arry[-1]:
                    self.close_indicator = 1
            else:
                if fast_array[-1] > slow_arry[-1]:
                    self.close_indicator = -1

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
        # self.turn_count = 0
        # self.turn_close_count = 0

        # self.open_count_down = 0
        if trade.offset == Offset.OPEN:
            # self.Touch_JUMP = 0
            self.close_indicator = 0
            self.entry_price = trade.price
            self.close_count_down = self.CLOSE_WINDOWS
            if trade.direction == Direction.LONG:
                self.high_close = min(trade.price + self.mark_up, self.high_limit)
                self.sell(self.high_close, trade.volume, False)
                self.low_close = trade.price - self.mark_down
            else:
                self.high_close = trade.price + self.mark_down
                self.low_close = max(trade.price - self.mark_up, self.low_limit)
                self.cover(self.low_close, trade.volume, False)

    def on_stop_order(self, stop_order: StopOrder):
        """
        :param stop_order:
        :return:
        """
        pass
