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


class BarBBIBOLLBAKStrategy(CtaTemplate):
    """"""

    author = "BIlly Zhang"

    init_pos = 0
    init_entry_price = 0.0

    Kxian = 1
    HeYueJiaZhi = 100000
    HeYueChengShu = 10.0
    fixed_size = 1

    OPEN_WINDOWS = 10
    CLOSE_WINDOWS = 20

    TRUN_OPEN_LIMIT = 3
    TURN_CLOSE_LIMIT = 4

    JUMP = 6
    MARK_UP = 5
    MARK_DOWN = 5

    BBI_WINDOWS = 26
    BBI_DEV = 2.8

    STOP_TRADE = 0

    bbi_mid = 0
    bbi_high = 0
    bbi_low = 0

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
        "OPEN_WINDOWS",
        "TRUN_OPEN_LIMIT",
        "TURN_CLOSE_LIMIT",
        "JUMP",
        "BBI_WINDOWS",
        "BBI_DEV",
        "Kxian",
        "MARK_DOWN",
        "MARK_UP"
    ]
    variables = [
        "entry_price",
        "close_count_down",
        "high_close",
        "low_close",
        "bbi_high",
        "bbi_low"

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
        self.long_open_request = []
        self.short_open_request = []

        self.not_trading_time = False

        self.start_timePM = time(hour=9, minute=5)
        self.start_timeNI = time(hour=21, minute=5)

        self.exit_timeAM = time(hour=14, minute=55)
        self.exit_timeNI = time(hour=22, minute=55)

        self.exit_open_timeAM = time(hour=14, minute=48)
        self.exit_open_timeNI = time(hour=22, minute=48)

    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.jump = self.pricetick * self.JUMP
        self.mark_up = self.pricetick * self.MARK_UP
        self.mark_down = self.pricetick * self.MARK_DOWN

        self.write_log("策略初始化")
        self.load_bar(5)

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

    def send_open_short_deal(self, price):
        self.openLongOrderID = self.send_direct_order(
            self.contact,
            Direction.SHORT,
            Offset.OPEN,
            price,
            self.fixed_size,
            OrderType.FOK
        )

    def send_open_long_deal(self, price):
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
        if self.high_limit == 0:
            self.high_limit = tick.limit_up - self.pricetick
            self.low_limit = tick.limit_down + self.pricetick

        if self.pos > 0:
            # self.low_close = max((tick.last_price - self.mark_down), self.low_close)
            if tick.last_price < self.low_close or self.close_indicator == 1:
                self.cancel_all()
                self.close_request = self.sell(tick.bid_price_1, self.pos, False)

        elif self.pos < 0:
            # self.high_close = min((tick.last_price + self.mark_down), self.high_close)
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
        if self.trading:
            self.write_log(
                f"Touch_JUMP : {self.Touch_JUMP}, self.open_count_down: {self.open_count_down},turn_count:{self.turn_count}, touch_open_price :{self.touch_open_price},  jump_jump_price: {self.jump_jump_price}")

        if self.open_count_down <= 0:
            if self.pos == 0:
                self.cancel_all()
            self.Touch_JUMP = 0
            self.bbi_high, mid, self.bbi_low = am.bbiboll(self.BBI_WINDOWS, self.BBI_DEV)
            self.jump = self.bbi_high - mid
            # self.diff = (self.bbi_high - self.bbi_mid)
            if bar.high_price > self.bbi_high:
                self.Touch_JUMP = 1
                self.turn_count = 0
                self.open_count_down = self.OPEN_WINDOWS
                self.jump_price = bar.close_price
                self.jump_jump_price = bar.high_price
                self.touch_open_price = bar.close_price
            elif bar.low_price  < self.bbi_low:
                self.Touch_JUMP = -1
                self.turn_count = 0
                self.jump_price = bar.close_price
                self.open_count_down = self.OPEN_WINDOWS
                self.jump_jump_price = bar.low_price
                self.touch_open_price = bar.close_price

        else:
            if self.pos == 0 and not self.not_trading_time:
                self.high_close = 1000000
                self.low_close = 0
                if self.Touch_JUMP == 1:
                    if bar.close_price > self.jump_price:
                        self.jump_jump_price = bar.high_price
                        self.jump_price = bar.close_price
                        self.turn_count = self.turn_count + 1
                        if self.turn_count >= self.TRUN_OPEN_LIMIT:
                            self.buy(price=self.touch_open_price + self.jump, volume=self.fixed_size, stop=True)
                elif self.Touch_JUMP == -1:
                    if bar.close_price < self.jump_price:
                        self.jump_jump_price = bar.low_price
                        self.jump_price = bar.close_price
                        self.turn_count = self.turn_count - 1
                        if self.turn_count <= -self.TRUN_OPEN_LIMIT:
                            self.short(price=self.touch_open_price - self.jump, volume=self.fixed_size, stop=True)
        self.open_count_down = self.open_count_down - 1
        self.last_close_price = bar.close_price
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
        self.turn_count = 0
        self.turn_close_count = 0
        self.close_indicator = 0
        self.open_count_down = 0
        if trade.offset == Offset.OPEN:
            self.Touch_JUMP = 0
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
