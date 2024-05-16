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


class BarJumpTrendDownStrategy(CtaTemplate):
    """"""

    author = "BIlly Zhang"

    init_pos = 0
    init_entry_price = 0.0

    Kxian = 1
    HeYueJiaZhi = 100000
    HeYueChengShu = 10.0
    fixed_size = 1

    CLOSE_WINDOWS = 50
    OPEN_WINDOWS = 100
    RATIO = 0.1
    RATIO2 = 0.1
    RATIO3 = 0.2

    JUMP = 10
    STOP_TRADE = 0

    MARK_UP = 50
    TURN_MARK_UP = 23
    TRUN_OPEN_LIMIT = 5
    TURN_CLOSE_LIMIT = 5

    MARK_DOWN = 40
    TURN_MARK_DOWN = 36

    close_count_down = 0
    open_count_down = 0
    entry_price = 0
    last_close_price = 0
    high_close = 1000000
    low_close = 0
    bar_high = 0
    bar_low = 0
    turn_count = 0

    trade_close = 0

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
        "Kxian",
        "JUMP",
        "RATIO",
        "RATIO2",
        "RATIO3",
        "MARK_DOWN",
        "MARK_UP"
    ]
    variables = [
        "entry_price",
        "trade_close",
        "close_count_down",
        "high_close",
        "low_close",
        "bar_high",
        "bar_low"

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

        self.pricetick = 1
        self.contact = 0
        self.close_indicator = 0

        self.Touch_JUMP = 0
        self.jump_price = 0
        self.touch_open_price = 0
        self.price_before_jump = 0

        self.turnoff_deal = 1

        self.jump_jump_price = 0
        self.turn_count = 0
        self.turn_close_count = 0

        self.start_timePM = time(hour=9, minute=0)
        self.start_timeNI = time(hour=21, minute=0)

        self.exit_timeAM = time(hour=14, minute=55)
        self.exit_timeNI = time(hour=22, minute=55)

    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.contact = self.cta_engine.main_engine.get_contract(self.vt_symbol)
        self.pricetick = self.contact.pricetick
        self.mark_up = self.pricetick * self.MARK_UP
        self.mark_down = self.pricetick * self.MARK_DOWN
        self.jump = self.pricetick * self.JUMP

        self.turn_mark_up = self.pricetick * self.TURN_MARK_UP
        self.turn_mark_down = self.pricetick * self.TURN_MARK_DOWN

        self.write_log("策略初始化")
        self.load_bar(2)

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
        if self.pos > 0 and (tick.last_price < self.low_close or self.close_indicator == 1):
            if self.cancel_all():
                self.sell(tick.bid_price_1, self.pos, False)

        elif self.pos < 0 and (tick.last_price > self.high_close or self.close_indicator == -1):
            if self.cancel_all():
                self.cover(tick.ask_price_1, abs(self.pos), False)

        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData):
        """
        Callback of new bar data update.
        """
        if self.pos > 0:
            if bar.high_price >= self.bar_high:
                self.bar_high = bar.high_price
                self.bar_low = bar.low_price
                self.turn_close_count = 0
            elif bar.close_price < self.bar_low:
                self.bar_low = bar.close_price
                self.turn_close_count = self.turn_close_count - 1
                if self.turn_close_count <= -self.TURN_CLOSE_LIMIT:
                    self.low_close = self.bar_low
            if self.close_count_down <= 0 or self.check_not_trading_time(bar):
                self.close_indicator = 1
        elif self.pos < 0:
            if bar.low_price <= self.bar_low:
                self.bar_high = bar.high_price
                self.bar_low = bar.low_price
                self.turn_close_count = 0
            elif bar.close_price > self.bar_high:
                self.bar_high = bar.close_price
                self.turn_close_count = self.turn_close_count - 1
                if self.turn_close_count <= -self.TURN_CLOSE_LIMIT:
                    self.high_close = self.bar_high
            if self.close_count_down <= 0 or self.check_not_trading_time(bar):
                self.close_indicator = -1
        self.close_count_down -= 1
        self.bg.update_bar(bar)

    def on_time_bar(self, bar: BarData):
        if self.last_close_price == 0:
            self.last_close_price = bar.close_price
            return

        if self.trading:
            self.write_log(
                f"Touch_JUMP : {self.Touch_JUMP}, self.open_count_down: {self.open_count_down},turn_count:{self.turn_count}, touch_open_price :{self.touch_open_price}, p jump_jump_price: {self.jump_jump_price}")

        if self.open_count_down <= 0:
            if self.pos == 0:
                self.cancel_all()
            self.Touch_JUMP = 0
            if bar.close_price - self.last_close_price > self.jump:
                actul_jump = bar.high_price - self.last_close_price
                self.Touch_JUMP = 1
                self.turn_count = 0
                self.open_count_down = self.OPEN_WINDOWS
                self.jump_price = bar.high_price + actul_jump * self.RATIO
                self.touch_open_price = bar.low_price
                self.price_before_jump = self.last_close_price - actul_jump * self.RATIO2
                self.jump_jump_price = bar.high_price + actul_jump * self.RATIO3
            elif self.last_close_price - bar.close_price > self.jump:
                actul_jump = self.last_close_price - bar.low_price
                self.Touch_JUMP = -1
                self.turn_count = 0
                self.open_count_down = self.OPEN_WINDOWS
                self.jump_price = bar.low_price - actul_jump * self.RATIO
                self.touch_open_price = bar.high_price
                self.price_before_jump = self.last_close_price + actul_jump * self.RATIO2
                self.jump_jump_price = bar.low_price - actul_jump * self.RATIO3
        else:
            if self.pos == 0 and not self.check_not_trading_time(bar):
                self.bar_high = bar.high_price
                self.bar_low = bar.low_price
                self.high_close = 1000000
                self.low_close = 0
                if self.Touch_JUMP == 1:
                    if bar.close_price < self.price_before_jump:
                        self.price_before_jump = bar.close_price
                        self.turn_count = self.turn_count - 1
                        if self.turn_count <= -(self.TRUN_OPEN_LIMIT +1):
                            self.cancel_all()
                            self.short(price=bar.close_price - self.pricetick, volume=self.fixed_size, stop=False)
                    if bar.low_price < self.touch_open_price:
                        self.cancel_all()
                        self.buy(price=self.jump_price, volume=self.fixed_size, stop=True)
                    elif bar.close_price > self.jump_jump_price:
                        self.jump_jump_price = bar.close_price
                        self.turn_count = self.turn_count + 1
                        if self.turn_count >= self.TRUN_OPEN_LIMIT:
                            self.cancel_all()
                            self.buy(price=bar.close_price + self.pricetick, volume=self.fixed_size, stop=False)
                elif self.Touch_JUMP == -1:
                    if bar.close_price > self.price_before_jump:
                        self.price_before_jump = bar.close_price
                        self.turn_count = self.turn_count + 1
                        if self.turn_count >= self.TRUN_OPEN_LIMIT + 1:
                            self.cancel_all()
                            self.buy(price=bar.close_price + self.pricetick, volume=self.fixed_size, stop=False)
                    if bar.high_price > self.touch_open_price:
                        self.cancel_all()
                        self.short(price=self.jump_price, volume=self.fixed_size, stop=True)
                    elif bar.close_price < self.jump_jump_price:
                        self.jump_jump_price = bar.close_price
                        self.turn_count = self.turn_count - 1
                        if self.turn_count <= -self.TRUN_OPEN_LIMIT:
                            self.cancel_all()
                            self.short(price=bar.close_price - self.pricetick, volume=self.fixed_size, stop=False)

        self.open_count_down = self.open_count_down - 1
        self.last_close_price = bar.close_price
        self.put_event()

    def check_not_trading_time(self, bar):
        if (self.start_timePM <= bar.datetime.time() < self.exit_timeAM) or (
                self.start_timeNI <= bar.datetime.time() < self.exit_timeNI):
            return False
        else:
            return True

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
            if trade.direction ==  Direction.LONG:
                self.high_close = trade.price + self.mark_up
                self.sell(self.high_close, trade.volume, False)
                self.low_close = trade.price - self.mark_down
            else:
                self.high_close = trade.price + self.mark_down
                self.low_close = trade.price - self.mark_up
                self.cover(self.low_close, trade.volume, False)

        self.put_event()

    def on_stop_order(self, stop_order: StopOrder):
        """
        :param stop_order:
        :return:
        """
        pass
