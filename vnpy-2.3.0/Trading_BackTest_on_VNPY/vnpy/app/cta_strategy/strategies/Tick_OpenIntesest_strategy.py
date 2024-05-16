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


class TickOpenIntesestStrategy(CtaTemplate):
    """"""
    author = "Billy"
    init_pos = 0
    init_entry_price = 0.0

    HeYueJiaZhi = 100000
    HeYueChengShu = 10.0

    fixed_size = 1


    Markup = 2
    price_up = 2
    price_down = 6

    trade_price = 0
    close_long_price = 0
    close_short_price = 0
    high = 100000000
    low = -1
    isAG = 0

    lose_count = 0
    lose_count_number = 8
    deal_open_count_number = 3
    deal_open_count = 3
    real_Markup = 0
    priceArray_sum = 0
    std_limitation =2.6
    std = 0
    tick_touch_count = 6
    tick_touch = 0
    open_interest_limit = 150





    parameters = ["fixed_size", "price_up", "price_down", "isAG","open_interest_limit"]
    variables = ["real_Markup"]

    def __init__(self, cta_engine, strategy_name, vt_symbol, vt_local, setting):
        """"""
        super(TickOpenIntesestStrategy, self).__init__(
            cta_engine, strategy_name, vt_symbol, vt_local, setting
        )




        self.tick_touch = 0
        self.contact = ""
        self.open_price = 0
        self.open = 0




        self.closeOrderID = ""
        self.already_cancel = False

        self.openShortOrderID = ""
        self.openLongOrderID = ""
        self.trading_time = False
        self.real_Markup = 0
        self.real_price_up = 0
        self.real_price_down = 0
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
        self.high = 100000000
        self.low = -1
        self.contact = self.cta_engine.main_engine.get_contract(self.vt_symbol)

        self.real_Markup = self.Markup *self.contact.pricetick
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
        if self.last_tick is None:
            self.last_tick = tick
            return

        # limited time horizon
        if self.pos == 0:
            if (tick.open_interest - self.last_tick.open_interest) >= self.open_interest_limit:
                if tick.bid_price_1 >= self.last_tick.ask_price_1:
                    self.send_open_long_deal(tick.last_price)
                    self.open_price = tick.last_price
                    self.open = 1

                elif tick.ask_price_1 <= self.last_tick.bid_price_1:
                    self.open_price = tick.last_price
                    self.open = -1
            if self.open_price == tick.last_price:
                if self.open == 1:
                    self.send_open_long_deal(self.open_price)
                elif self.open_price == -1:
                    self.send_open_short_deal(self.open_price)
                else:
                    self.open_price = 0


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



    def on_order(self, order: OrderData):
        """
        Callback of new order data update.
        """
        pass

    def on_trade(self, trade: TradeData):
        """
        Callback of new trade data update.
        """
        self.open_price = 0
        if trade.offset == Offset.OPEN:
            self.trade_price = trade.price
            if self.pos > 0 and self.pos == self.fixed_size:
                self.closeOrderID = self.send_direct_order(
                    self.contact,
                    Direction.SHORT,
                    Offset.CLOSE,
                    trade.price + self.real_price_up,
                    self.fixed_size,
                    OrderType.LIMIT
                )
                self.close_long_price = trade.price - self.real_price_down


            elif self.pos < 0 and self.pos == -self.fixed_size:
                self.closeOrderID = self.send_direct_order(
                    self.contact,
                    Direction.LONG,
                    Offset.CLOSE,
                    trade.price - self.real_price_up,
                    self.fixed_size,
                    OrderType.LIMIT
                )
                self.close_short_price = trade.price + self.real_price_down



