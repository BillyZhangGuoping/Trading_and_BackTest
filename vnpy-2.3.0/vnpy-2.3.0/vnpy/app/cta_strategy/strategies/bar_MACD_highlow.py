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


class BarMACDHighLowStrategy(CtaTemplate):
    """"""

    author = "BIlly Zhang"

    init_pos = 0
    init_entry_price = 0.0

    Kxian = 1
    HeYueJiaZhi = 100000
    HeYueChengShu = 10.0
    fixed_size = 1

    CLOSE_WINDOWS = 600
    OPEN_WINDOWS = 8
    Donchain_Windows = 120
    MACD_LIMIT = 1


    JUMP = 10
    STOP_TRADE = 0


    MARK_UP = 12
    MARK_DOWN = 40

    close_count_down = 0
    open_count_down = 0
    entry_price = 0

    high_close = 1000000
    low_close = 0

    bar_high = 1000000
    bar_low = 0
    bar_mean = 0
    macd = 0


    parameters = [
        "init_pos",
        "init_entry_price",
        "fixed_size",
        "HeYueJiaZhi",
        "HeYueChengShu",
        "CLOSE_WINDOWS",
        "OPEN_WINDOWS",
        "Donchain_Windows",
        "MACD_LIMIT",
        "Kxian",
        "JUMP",
        "MARK_DOWN",
        "MARK_UP"
    ]
    variables = [
        "entry_price",
        "close_count_down",
        "high_close",
        "low_close",
        "bar_high",
        "bar_mean",
        "bar_low",
        "macd"

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
        self.am = ArrayManager(self.Donchain_Windows+10)
        self.pricetick = 1
        self.contact = 0
        self.close_indicator = 0

        self.jump_price = 0
        self.Touch_JUMP = 0

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
            if self.macd > 0 or self.close_count_down <= 0 or self.check_not_trading_time(bar):
                self.close_indicator = 1
        elif self.pos < 0:
            if self.macd < 0 or self.close_count_down <= 0 or self.check_not_trading_time(bar):
                self.close_indicator = -1
        self.close_count_down -= 1
        self.bg.update_bar(bar)

    def on_time_bar(self, bar: BarData):
        am = self.am
        am.update_bar(bar)
        if not am.inited:
            return

        self.macd, signal, hist = am.macd(12,26,9,array=True)

        if self.open_count_down <= 0:
            if self.pos == 0:
                self.cancel_all()
            if bar.high_price > self.bar_high:
                self.Touch_JUMP = -1
                self.open_count_down = self.OPEN_WINDOWS
            elif bar.low_price < self.bar_low:
                self.Touch_JUMP = 1
                self.open_count_down = self.OPEN_WINDOWS
        else:
            if self.pos == 0 and not self.check_not_trading_time(bar):
                self.high_close = 1000000
                self.low_close = 0
                if self.Touch_JUMP == 1 and self.macd >= self.MACD_LIMIT:
                        self.buy(price=bar.close_price + self.pricetick, volume=self.fixed_size, stop=False)
                elif self.Touch_JUMP == -1 and self.macd <= -self.MACD_LIMIT:
                        self.short(price=bar.close_price - self.pricetick, volume=self.fixed_size, stop=False)

        self.bar_high, self.bar_low = am.donchian(self.Donchain_Windows)
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
