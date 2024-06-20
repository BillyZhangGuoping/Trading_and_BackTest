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
from vnpy.trader.utility import round_to,floor_to


class BarMaTrendStrategy(CtaTemplate):
    """"""

    author = "BIlly Zhang"

    init_pos = 0
    init_entry_price = 0.0

    Kxian = 1
    HeYueJiaZhi = 100000
    HeYueChengShu = 10.0
    fixed_size = 1


    PERIOD_LENGTH = 5
    MARK_UP = 20
    MARK_DOWN = 10
    CLOSE_WINDOWS = 10


    close_count_down = 0
    entry_price = 0

    high_close = 1000000
    low_close = 0
    cut_min = 0
    OPEN_RATIO = 0.5
    CLOSE_RATIO = 0

    pricetick = 1

    parameters = [
        "init_pos",
        "init_entry_price",
        "fixed_size",
        "HeYueJiaZhi",
        "HeYueChengShu",
        "pricetick",
        "Kxian",
        "CLOSE_WINDOWS",
        "PERIOD_LENGTH",
        "MARK_DOWN",
        "OPEN_RATIO",
        "CLOSE_RATIO",
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


        self.close_indicator = 0

        self.high_limit = 1000000
        self.low_limit = 0

        self.period_list = [5,10,20,30,60,90,120]

        self.am = ArrayManager(self.period_list[self.PERIOD_LENGTH-1]+20)
        self.period_list = self.period_list[:self.PERIOD_LENGTH]
        self.close_period_list = self.period_list[1:]
        self.trend = 0
        self.last_trend = 0


        self.Touch_JUMP = 0
        self.jump_price = 0
        self.touch_open_price = 0
        self.price_before_jump = 0
        self.jump_jump_price = 0
        self.start_close_price = 0

        self.mark_up = 1
        self.mark_down = 1
        self.jump = 1
        self.turn_mark_up = 1
        self.turn_mark_down =1


        self.turn_close_count = 0

        self.not_trading_time = False

        if self.cut_min == 0:
            self.start_timePM = time(hour=9, minute=5)
            self.start_timeNI = time(hour=21, minute=5)
        else:
            self.start_timePM = time(hour=8, minute=59)
            self.start_timeNI = time(hour=20, minute=59)

        self.exit_timeAM = time(hour=14, minute=45)
        self.exit_timeNI = time(hour=22, minute=45)

        self.exit_open_timeAM = time(hour=14, minute=45)
        self.exit_open_timeNI = time(hour=22, minute=45)


    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.gap = self.pricetick*self.OPEN_RATIO
        self.mark_up = self.pricetick * self.MARK_UP
        self.mark_down = self.pricetick * self.MARK_DOWN

        self.write_log("策略初始化")
        self.load_bar(12)

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
        # for real deal
        # if self.not_trading_time:
        #     if self.pos > 0:
        #         self.close_indicator = 1
        #     elif self.pos < 0:
        #         self.close_indicator = -1
        #     else:
        #         self.cancel_all()
        # else:
        #     if self.pos > 0:
        #         if self.close_count_down <= 0 or self.trend != 1:
        #             self.close_indicator = 1
        #         if not self.get_orderids():
        #             self.sell(self.high_close, self.pos, False)
        #     elif self.pos < 0:
        #         if self.close_count_down <= 0 or self.trend != -1:
        #             self.close_indicator = -1
        #         if not self.get_orderids():
        #             self.cover(self.low_close, abs(self.pos), False)

        ## for backtest
        if self.not_trading_time:
            if self.pos > 0:
                # self.close_indicator = 1
                self.cancel_all()
                self.close_request = self.sell(bar.close_price - self.pricetick, self.pos, False)
            elif self.pos < 0:
                # self.close_indicator = -1
                self.cancel_all()
                self.close_request = self.cover(bar.close_price + self.pricetick, abs(self.pos), False)
            else:
                self.cancel_all()
        else:
            if self.pos > 0:
                if self.close_count_down <= 0:
                    # self.close_indicator = 1
                    self.cancel_all()
                    self.close_request = self.sell(bar.close_price - self.pricetick, self.pos, False)
                elif bar.low_price < self.low_close:
                    self.cancel_all()
                    self.sell(bar.close_price - self.pricetick, self.pos, False)
            elif self.pos < 0:
                if self.close_count_down <= 0:
                    # self.close_indicator = -1
                    self.cancel_all()
                    self.close_request = self.cover(bar.close_price + self.pricetick, abs(self.pos), False)
                elif bar.high_price > self.high_close:
                    self.cancel_all()
                    self.close_request = self.cover(bar.close_price + self.pricetick, abs(self.pos), False)

        self.close_count_down -= 1
        self.bg.update_bar(bar)

    def check_sequence(self,sequence):
        is_increasing = all(sequence[i] + self.gap <=sequence[i + 1] for i in range(len(sequence) - 1))
        is_decreasing = all(sequence[i] >= sequence[i + 1] + self.gap for i in range(len(sequence) - 1))

        if is_increasing:

            return -1
        elif is_decreasing:
            return 1
        else:
            return 0

    def on_time_bar(self, bar: BarData):
        am = self.am
        am.update_bar(bar)
        if not am.inited:
            return

        ema_result = []
        if self.pos == 0:
            period_list = self.period_list
        else:
            period_list =self.close_period_list
        for ema_length in period_list:
            ema_result.append(am.ema(ema_length))
        self.trend = self.check_sequence(ema_result)

        if not self.not_trading_time:
                if self.trend == 1 and self.last_trend == 0:
                    if self.pos == 0:
                        self.buy(price=bar.close_price + self.pricetick, volume=self.fixed_size, stop=False)
                elif self.trend == -1 and self.last_trend == 0:
                    if self.pos == 0:
                        self.short(price=bar.close_price + self.pricetick, volume=self.fixed_size, stop=False)
                if self.pos > 0 :
                    if self.close_count_down <= 0:
                        # self.close_indicator = 1
                        self.cancel_all()
                        self.close_request = self.sell(bar.close_price - self.pricetick, self.pos, False)
                elif self.pos < 0:
                    if self.close_count_down <= 0:
                        # self.close_indicator = -1
                        self.cancel_all()
                        self.close_request = self.cover(bar.close_price + self.pricetick, abs(self.pos), False)

        self.last_trend = self.trend
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
        self.turn_close_count = 0
        self.close_indicator = 0

        if trade.offset == Offset.OPEN:
            self.Touch_JUMP = 0
            self.entry_price = trade.price
            self.close_count_down = self.CLOSE_WINDOWS
            self.gap = self.pricetick *self.CLOSE_RATIO
            if trade.direction ==  Direction.LONG:
                self.high_close = min(trade.price + self.mark_up,self.high_limit)
                self.sell(self.high_close, trade.volume, False)
                self.low_close = trade.price - self.mark_down
            else:
                self.high_close = trade.price + self.mark_down
                self.low_close = max(trade.price - self.mark_up, self.low_limit)
                self.cover(self.low_close, trade.volume, False)
        else:
            self.gap = self.pricetick * self.OPEN_RATIO


    def on_stop_order(self, stop_order: StopOrder):
        """
        :param stop_order:
        :return:
        """
        pass
