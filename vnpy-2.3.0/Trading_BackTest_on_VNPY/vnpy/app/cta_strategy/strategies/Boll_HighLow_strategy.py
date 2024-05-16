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


class BollHighLowStrategy(CtaTemplate):
    """"""
    author = "Billy"
    init_pos = 0
    init_entry_price = 0.0

    HeYueJiaZhi = 100000
    HeYueChengShu = 10.0

    fixed_size = 1

    bar_time = 5

    std_array_length = 3
    boll_window = 28
    boll_dev = 2.8

    Markup = 2
    price_up = 2
    price_down = 6

    trade_price = 0
    close_long_price = 0
    close_short_price = 0
    high = 100000000
    low = -1
    isAG = 0
    increment_limit = 7

    lose_count = 0
    lose_count_number = 15

    real_Markup = 0
    priceArray_sum = 0
    std_limitation =6
    std = 0
    tick_touch_count = 10
    tick_touch = 0
    touch_start_low_point = False
    touch_start_high_point = False
    boll_up = 0
    boll_down = 0
    old_bar_pass = 0




    parameters = ["fixed_size", "bar_time", "std_array_length", "Markup", "price_up", "price_down", "boll_window", "boll_dev", "isAG",
                  "lose_count_number","std_limitation","tick_touch_count","increment_limit"]
    variables = ["real_price_up","real_price_down", "std", "high","low","trade_price", "close_long_price", "close_short_price","std", "lose_count","boll_up","boll_down"]

    def __init__(self, cta_engine, strategy_name, vt_symbol, vt_local, setting):
        """"""
        super(BollHighLowStrategy, self).__init__(
            cta_engine, strategy_name, vt_symbol, vt_local, setting
        )

        self.start_timePM = time(hour=9, minute=13)
        self.start_timeAM = time(hour=13, minute=13)
        self.start_timeNI = time(hour=21, minute=13)

        self.start_time_mind_moring = time(hour=10,minute=29)
        self.exit_time_mid_morning = time(hour=10,minute=(15- self.bar_time-1))

        self.exit_timePM = time(hour=11, minute=15)
        self.exit_timeAM = time(hour=14, minute=45)
        self.exit_timeNI = time(hour=22, minute=45)
        self.exit_timeNI_ag = time(hour=2, minute=10)

        self.bg = BarGenerator(self.on_bar, self.bar_time, self.on_min_bar)
        self.am = ArrayManager()
        self.std = 0
        self.start = True
        self.touch_start_low_point = False
        self.touch_start_high_point = False
        self.tick_touch = 0
        self.profit_price = 0
        self.force_profit_price = 0
        self.old_bar_pass =0





        self.closeOrderID = ""
        self.already_cancel = False

        self.openShortOrderID = ""
        self.openLongOrderID = ""
        self.trading_time = False
        self.real_Markup = 0
        self.real_price_up = 0
        self.real_price_down = 0
        self.last_tick = 0

    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.contact = self.cta_engine.main_engine.get_contract(self.vt_symbol)
        self.load_bar(10)
        self.write_log("策略初始化")

    def on_start(self):
        """
        Callback when strategy is started.
        """
        self.high = 100000000
        self.low = -1


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

        # limited time horizon
        if self.pos == 0 and self.start:

            if tick.last_price >= self.boll_up:
                self.tick_touch -= 1
                self.touch_start_high_point = True
            elif tick.last_price <= self.boll_down:
                self.tick_touch -= 1
                self.touch_start_low_point = True
            if self.tick_touch <= 0:
                if self.touch_start_high_point:
                    self.send_open_long_deal(tick.ask_price_1)
                    self.start = False
                elif self.touch_start_low_point:
                    self.send_open_short_deal(tick.bid_price_1)
                    self.start = False

        elif self.pos < 0:
            if tick.last_price < self.profit_price:
                self.profit_price = tick.last_price
                self.close_short_price = self.profit_price + self.real_price_down

            elif tick.last_price >= self.close_short_price or tick.last_price <= self.force_profit_price:
                    self.cta_engine.cancel_server_order(self, self.closeOrderID)
                    self.closeOrderID = self.send_direct_order(
                        self.contact,
                        Direction.LONG,
                        Offset.CLOSE,
                        tick.last_price,
                        -self.pos,
                        OrderType.LIMIT
                    )

        elif self.pos > 0:
            if tick.last_price > self.profit_price:
                self.profit_price = tick.last_price
                self.close_long_price = self.profit_price - self.real_price_down


            elif tick.last_price <= self.close_long_price or tick.last_price >= self.force_profit_price:
                    self.cta_engine.cancel_server_order(self, self.closeOrderID)
                    self.closeOrderID = self.send_direct_order(
                        self.contact,
                        Direction.SHORT,
                        Offset.CLOSE,
                        tick.last_price,
                        self.pos,
                        OrderType.LIMIT
                    )


        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData):
        """
        Callback of new bar data update.
        """
        self.tick_touch = self.tick_touch_count
        self.touch_start_low_point = False
        self.touch_start_high_point = False

        self.bg.update_bar(bar)
        self.put_event()

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


    def check_trading_time(self, bar):
        if self.isAG:
            if (bar.datetime.time() > self.start_timePM and bar.datetime.time() < self.exit_time_mid_morning) or \
                    (bar.datetime.time() > self.start_time_mind_moring and bar.datetime.time() < self.exit_timePM) or \
                    (bar.datetime.time() > self.start_timeAM and bar.datetime.time() < self.exit_timeAM) or (
                    bar.datetime.time() > self.start_timeNI or bar.datetime.time() < self.exit_timeNI_ag):
                return True
            else:
                return False
        else:
            if (bar.datetime.time() > self.start_timePM and bar.datetime.time() < self.exit_timePM) or \
                (bar.datetime.time() > self.start_time_mind_moring and bar.datetime.time() < self.exit_timePM) or \
                    (bar.datetime.time() > self.start_timeAM and bar.datetime.time() < self.exit_timeAM) or (
                    bar.datetime.time() > self.start_timeNI and bar.datetime.time() < self.exit_timeNI):
                return True
            else:
                return False

    def on_min_bar(self, bar: BarData):
        """"""
        am = self.am
        am.update_bar(bar)
        if not am.inited:
            return
        std_array = am.std(self.boll_window,1,array= True)
        self.std = std_array [-1]
        ma = am.sma(self.boll_window)
        self.boll_up,self.boll_down = am.boll(self.boll_window,self.boll_dev)
        self.start = False
        if self.check_trading_time(bar) and self.trading:
            # self.write_log("trading_time")
            self.lose_count = self.lose_count - 1


            if self.pos == 0 and self.lose_count <= 0 and std_array[-1] > std_array[-2]> std_array[-3] > self.std_limitation:
                    self.closeOrderID = ""
                    self.cancel_all()
                    self.start = True
                    self.write_log(f"trading_time {self.boll_up} and {self.boll_down}")
                    self.real_price_up = (self.boll_up - ma)/2
                    self.real_price_down = self.real_price_up

        else:
            # self.write_log("close_time")
            if self.pos == 0:
                self.cancel_all()
            else:
                if self.pos < 0:
                        self.cta_engine.cancel_server_order(self, self.closeOrderID)
                        self.closeOrderID = self.send_direct_order(
                            self.contact,
                            Direction.LONG,
                            Offset.CLOSE,
                            bar.close_price + 2*self.contact.pricetick,
                            -self.pos,
                            OrderType.LIMIT
                        )

                elif self.pos > 0:
                        self.cta_engine.cancel_server_order(self, self.closeOrderID)
                        self.closeOrderID = self.send_direct_order(
                            self.contact,
                            Direction.SHORT,
                            Offset.CLOSE,
                            bar.close_price - 2*self.contact.pricetick,
                            self.pos,
                            OrderType.LIMIT
                        )

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
            self.trade_price = trade.price
            if self.pos > 0:
                self.profit_price = trade.price
                self.force_profit_price = trade.price + self.real_price_up
                self.close_long_price = trade.price - self.real_price_down
                # self.cta_engine.cancel_server_order(self, self.openLongOrderID)

            elif self.pos < 0:
                self.profit_price = trade.price
                self.force_profit_price = trade.price - self.real_price_up
                self.close_short_price = trade.price + self.real_price_down


                # self.cta_engine.cancel_server_order(self, self.openShortOrderID)
        else:
            if trade.direction == Direction.LONG and self.trade_price < trade.price:
                self.lose_count = self.lose_count_number
            elif trade.direction == Direction.SHORT and self.trade_price > trade.price:
                self.lose_count = self.lose_count_number
            else:
                self.lose_count = 2



