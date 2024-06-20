from datetime import time
import numpy as np
from vnpy.trader.object import Offset, Direction, OrderType
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


class BarTrendStrategy(CtaTemplate):
    """"""
    author = "Billy"
    init_pos = 0
    init_entry_price = 0.0

    HeYueJiaZhi = 100000
    HeYueChengShu = 10.0

    fixed_size = 1
    bar_time = 5

    bar_array_length = 3

    bar_width = 2
    price_up = 1
    price_down = 2

    trade_price = 0
    close_long_price = 0
    close_short_price = 0
    high = 100000000
    low = -1
    isAG = 0
    lose_count = 0
    lose_count_number = 2
    deal_open_count_number = 2
    deal_open_count = 2
    real_Markup = 0

    parameters = ["fixed_size", "bar_time", "bar_array_length", "bar_width", "price_up", "price_down", "isAG",
                  "lose_count_number","deal_open_count_number"]
    variables = ["real_Markup","trade_price", "close_long_price", "close_short_price", "lose_count","deal_open_count"]

    def __init__(self, cta_engine, strategy_name, vt_symbol, vt_local, setting):
        """"""
        super(BarTrendStrategy, self).__init__(
            cta_engine, strategy_name, vt_symbol, vt_local, setting
        )

        self.start_timePM = time(hour=9, minute=4)
        self.start_timeAM = time(hour=13, minute=34)
        self.start_timeNI = time(hour=21, minute=4)

        self.exit_timePM = time(hour=11, minute=15)
        self.exit_timeAM = time(hour=14, minute=45)
        self.exit_timeNI = time(hour=22, minute=45)
        self.exit_timeNI_ag = time(hour=2, minute=10)

        self.bg = BarGenerator(self.on_bar, self.bar_time, self.on_min_bar)
        self.priceArray = np.zeros(self.bar_array_length)

        self.bar_trend = 0


        self.closeOrderID = ""
        self.already_cancel = False
        self.start_check = 0
        self.openShortOrderID = ""
        self.openLongOrderID = ""
        self.trading_time = False

    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.write_log("策略初始化")

    def on_start(self):
        """
        Callback when strategy is started.
        """
        self.high = 100000000
        self.low = -1
        self.contact = self.cta_engine.main_engine.get_contract(self.vt_symbol)

        self.real_bar_width = self.bar_width *self.contact.pricetick
        self.real_price_up = self.price_up *self.contact.pricetick
        self.real_price_down = self.price_down *self.contact.pricetick

        self.lose_cout = 0
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

        # limited time horizon
        if self.pos < 0 and tick.last_price >= self.close_short_price:
            if self.cta_engine.cancel_server_order(self, self.closeOrderID):
                self.closeOrderID = self.send_direct_order(
                    self.contact,
                    Direction.LONG,
                    Offset.CLOSE,
                    tick.ask_price_1,
                    -self.pos,
                    OrderType.LIMIT
                )
                self.lose_count = self.lose_count_number


        elif self.pos > 0 and tick.last_price <= self.close_long_price:
            if self.cta_engine.cancel_server_order(self, self.closeOrderID):
                self.closeOrderID = self.send_direct_order(
                    self.contact,
                    Direction.SHORT,
                    Offset.CLOSE,
                    tick.bid_price_1,
                    self.pos,
                    OrderType.LIMIT
                )
                self.lose_count = self.lose_count_number

        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData):
        """
        Callback of new bar data update.
        """
        # self.open_count += 1
        # if self.open_count < self.open_count_limit:
        # 	return
        self.deal_open_count -= 1
        if self.pos == 0:
            if self.bar_trend == 1 and bar.close_price > bar.open_price:
                self.send_open_long_deal()
            elif self.bar_trend == -1 and bar.close_price < bar.open_price:
                pas



        if self.pos !=0 and self.deal_open_count <= 0:
            if self.pos < 0:
                if self.cta_engine.cancel_server_order(self, self.closeOrderID):
                    self.closeOrderID = self.send_direct_order(
                        self.contact,
                        Direction.LONG,
                        Offset.CLOSE,
                        bar.close_price + self.contact.pricetick,
                        -self.pos,
                        OrderType.LIMIT
                    )
                    if bar.close_price >= self.trade_price:
                        self.lose_count = self.lose_count_number
            elif self.pos > 0:
                if self.cta_engine.cancel_server_order(self, self.closeOrderID):
                    self.closeOrderID = self.send_direct_order(
                        self.contact,
                        Direction.SHORT,
                        Offset.CLOSE,
                        bar.close_price - self.contact.pricetick,
                        self.pos,
                        OrderType.LIMIT
                    )
                    if bar.close_price <= self.trade_price:
                        self.lose_count = self.lose_count_number


        self.bg.update_bar(bar)
        self.put_event()

    def send_open_short_deal(self):
        self.openLongOrderID = self.send_direct_order(
            self.contact,
            Direction.SHORT,
            Offset.OPEN,
            self.high,
            self.fixed_size,
            OrderType.LIMIT
        )

    def send_open_long_deal(self):
        self.openShortOrderID = self.send_direct_order(
            self.contact,
            Direction.LONG,
            Offset.OPEN,
            self.low,
            self.fixed_size,
            OrderType.LIMIT
        )

    def close_all_deal(self,sell_price,cover_price):
        if self.pos < 0:
            if self.cta_engine.cancel_server_order(self, self.closeOrderID):
                self.closeOrderID = self.send_direct_order(
                    self.contact,
                    Direction.LONG,
                    Offset.CLOSE,
                    cover_price,
                    -self.pos,
                    OrderType.LIMIT
                )

        elif self.pos > 0:
            if self.cta_engine.cancel_server_order(self, self.closeOrderID):
                self.closeOrderID = self.send_direct_order(
                    self.contact,
                    Direction.SHORT,
                    Offset.CLOSE,
                    sell_price,
                    self.pos,
                    OrderType.LIMIT
                )

    def check_trading_time(self, bar):
        if self.isAG:
            if (bar.datetime.time() > self.start_timePM and bar.datetime.time() < self.exit_timePM) or \
                    (bar.datetime.time() > self.start_timeAM and bar.datetime.time() < self.exit_timeAM) or (
                    bar.datetime.time() > self.start_timeNI or bar.datetime.time() < self.exit_timeNI_ag):
                return True
            else:
                return False
        else:
            if (bar.datetime.time() > self.start_timePM and bar.datetime.time() < self.exit_timePM) or \
                    (bar.datetime.time() > self.start_timeAM and bar.datetime.time() < self.exit_timeAM) or (
                    bar.datetime.time() > self.start_timeNI and bar.datetime.time() < self.exit_timeNI):
                return True
            else:
                return False

    def on_min_bar(self, bar: BarData):
        """"""
        if bar.open_price > bar.close_price:
            price_trend = -1
        elif bar.open_price < bar.close_price:
            price_trend = 1
        else:
            price_trend = 0

        self.priceArray[:-1] = self.priceArray[1:]
        self.priceArray[-1] = price_trend

        if self.check_trading_time(bar):
            self.write_log("trading_time")
            self.high = bar.high_price + self.real_Markup
            self.low = bar.low_price - self.real_Markup
            self.write_log(f"trading_time {self.high} and {self.low}")
            self.lose_count = self.lose_count - 1

            if self.pos == 0 and self.lose_count <= 0:
                self.closeOrderID = ""
                self.cancel_all()
                if bar.high_price > max(bar.close_price, bar.open_price) and min(bar.close_price,
                                                                                 bar.open_price) > bar.low_price \
                        and abs(sum(self.priceArray)) < self.bar_array_length:
                    self.send_open_long_deal()
                    self.send_open_short_deal()


        else:
            self.write_log("close_time")

            if self.pos == 0:
                self.cancel_all()
            else:
                self.close_all_deal(bar.close_price - self.contact.pricetick,bar.close_price + self.contact.pricetick)

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
            self.start_check = 0
            self.deal_open_count  = self.deal_open_count_number
            self.trade_price = trade.price
            if self.pos > 0 and self.pos == self.fixed_size:
                self.closeOrderID = self.send_direct_order(
                    self.contact,
                    Direction.SHORT,
                    Offset.CLOSE,
                    trade.price + self.real_price_up,
                    self.pos,
                    OrderType.LIMIT
                )
                self.close_long_price = trade.price - self.real_price_down
                self.cta_engine.cancel_server_order(self, self.openLongOrderID)
            elif self.pos < 0 and self.pos == -self.fixed_size:
                self.closeOrderID = self.send_direct_order(
                    self.contact,
                    Direction.LONG,
                    Offset.CLOSE,
                    trade.price - self.real_price_up,
                    -self.pos,
                    OrderType.LIMIT
                )
                self.close_short_price = trade.price + self.real_price_down
                self.cta_engine.cancel_server_order(self, self.openShortOrderID)

