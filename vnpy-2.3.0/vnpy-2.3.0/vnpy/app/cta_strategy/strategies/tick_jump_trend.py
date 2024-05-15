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


class TickJumpTrendStrategy(CtaTemplate):
    """"""

    author = "BIlly Zhang"

    init_pos =0
    init_entry_price = 0.0

    Kxian = 60
    MA_Windows = 30
    HeYueJiaZhi = 100000
    HeYueChengShu = 10.0
    fixed_size = 1

    CLOSE_WINDOWS = 2

    JUMP_PRECENTAGE = 0.1

    MARK_UP = 10

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
        "JUMP_PRECENTAGE",
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

        self.real_up_precentage = 1 + self.JUMP_PRECENTAGE /100.0
        self.real_down_precentage = 1- self.JUMP_PRECENTAGE /100.0

    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.contact = self.cta_engine.main_engine.get_contract(self.vt_symbol)
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

    def on_tick(self, tick: TickData):
        """
        Callback of new tick data update.
        """
        if self.pos ==0:
            if tick.last_price / self.last_close_price >= self.real_up_precentage:
                self.send_open_long_deal(tick.ask_price_1)
            elif tick.last_price / self.last_close_price <= self.real_down_precentage:
                self.send_open_short_deal(tick.bid_price_1)
        self.last_close_price = tick.last_price
        self.bg.update_tick(tick)


    def on_bar(self, bar: BarData):
        """
        Callback of new bar data update.

        """
        self.last_close_price = bar.close_price

        if self.close_count_down <=0:
            self.cancel_all()
            if self.pos > 0:
                self.sell(bar.close_price-1, abs(self.pos), False)

            elif self.pos <0:
                self.cover(bar.close_price+1, abs(self.pos), False)

        self.close_count_down -= 1
        self.put_event()


    def send_open_short_deal(self,price):
        self.openLongOrderID = self.send_direct_order(
            self.contact,
            Direction.SHORT,
            Offset.OPEN,
            price,
            self.fixed_size,
            OrderType.LIMIT
        )

    def send_open_long_deal(self,price):
        self.openShortOrderID = self.send_direct_order(
            self.contact,
            Direction.LONG,
            Offset.OPEN,
            price,
            self.fixed_size,
            OrderType.LIMIT
        )

    def on_time_bar(self, bar: BarData):

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
            self.entry_price = trade.price
            self.close_count_down = self.CLOSE_WINDOWS
            if abs(self.pos) == self.fixed_size:
                if self.pos > 0:
                    self.sell(trade.price + self.MARK_UP, self.pos, False)
                    self.sell(trade.price - self.MARK_UP + 1, self.pos, True)

                elif self.pos < 0:
                    self.cover(trade.price - self.MARK_UP, abs(self.pos), False)
                    self.cover(trade.price + self.MARK_UP -1, abs(self.pos), True)



        self.put_event()

    def on_stop_order(self, stop_order: StopOrder):
        """
        :param stop_order:
        :return:
        """
        pass
