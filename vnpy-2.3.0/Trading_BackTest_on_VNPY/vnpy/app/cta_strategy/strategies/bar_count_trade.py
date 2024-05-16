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


class BarCountStrategy(CtaTemplate):
    """"""

    author = "BIlly Zhang"

    init_pos = 0
    init_entry_price = 0.0

    Kxian = 1
    HeYueJiaZhi = 100000
    HeYueChengShu = 10.0
    fixed_size = 1

    bar_count = 0
    BAR_COUNT = 3
    PRICE_JUMP = 2
    STOP_COUNT  = 2

    MARK_UP = 5
    MARK_DOWN = 5

    entry_price = 0
    last_close_price = 0
    high_close = 1000000
    low_close = 0

    parameters = [
        "init_pos",
        "init_entry_price",
        "fixed_size",
        "HeYueJiaZhi",
        "HeYueChengShu",
        "BAR_COUNT",
        "PRICE_JUMP",
        "MARK_DOWN",
        "MARK_UP"
    ]
    variables = [
        "entry_price",
        "bar_count"

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
        self.close_indicator = 0

        self.start_timePM = time(hour=9, minute=0)
        self.start_timeNI = time(hour=21, minute=0)

        self.exit_timeAM = time(hour=14, minute=55)
        self.exit_timeNI = time(hour=23, minute=55)

    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.contact = self.cta_engine.main_engine.get_contract(self.vt_symbol)
        self.pricetick = self.contact.pricetick
        self.mark_up = self.pricetick * self.MARK_UP
        self.mark_down = self.pricetick * self.MARK_DOWN
        self.price_jump = self.pricetick * self.PRICE_JUMP

        self.write_log("策略初始化")

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
        if self.pos > 0 and (tick.last_price < self.low_close or self.close_indicator == self.STOP_COUNT):
            if self.cancel_all():
                self.sell(tick.bid_price_1, self.pos, False)

        elif self.pos < 0 and (tick.last_price < self.low_close or self.close_indicator == -self.STOP_COUNT):
            if self.cancel_all():
                self.cover(tick.ask_price_1, abs(self.pos), False)

        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData):
        """
        Callback of new bar data update.
        """
        if self.pos == 0 and not self.check_not_trading_time(bar):
            if bar.close_price - bar.open_price >= self.price_jump:
                if self.bar_count <= 0:
                    self.bar_count = 1
                else:
                    self.bar_count += 1
            elif bar.close_price - bar.open_price <= -self.price_jump:
                if self.bar_count >= 0:
                    self.bar_count = -1
                else:
                    self.bar_count -= 1
            else:
                self.bar_count = 0
            if self.bar_count >= self.BAR_COUNT:
                self.send_open_long_deal(bar.close_price + 2*self.pricetick)
            elif self.bar_count <= -self.BAR_COUNT:
                self.send_open_short_deal(bar.close_price - 2*self.pricetick)
        elif self.pos > 0:
            self.close_indicator += 1
        elif self.pos < 0:
            self.close_indicator -= 1
        self.put_event()

    def on_time_bar(self, bar: BarData):
        pass

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
        self.bar_count = 0
        self.close_indicator = 0
        if trade.offset == Offset.OPEN:
            if trade.direction == Direction.LONG:
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
