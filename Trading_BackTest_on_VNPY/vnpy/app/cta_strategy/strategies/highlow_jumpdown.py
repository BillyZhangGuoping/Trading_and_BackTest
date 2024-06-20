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


class HighLowJumpDownStrategy(CtaTemplate):
    """"""

    author = "BIlly Zhang"

    init_pos =0
    init_entry_price = 0.0

    Kxian = 60
    HeYueJiaZhi = 100000
    HeYueChengShu = 10.0
    fixed_size = 1

    CLOSE_WINDOWS = 10
    OPEN_WINDOWS = 10

    JUMP = 10

    MARK_UP = 50

    MARK_DOWN = 12

    close_count_down = 0
    open_count_down = 0
    entry_price = 0
    last_close_price = 0


    parameters = [
        "init_pos",
        "init_entry_price",
        "fixed_size",
        "HeYueJiaZhi",
        "HeYueChengShu",
        "CLOSE_WINDOWS",
        "OPEN_WINDOWS",
        "Kxian",
        "JUMP",
        "MARK_DOWN",
        "MARK_UP"
    ]
    variables = [
        "entry_price",
        "open_count_down",
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

        self.high_close = 100000
        self.low_close = 0
        self.pricetick = 1
        self.contact = 0

        self.Touch_JUMP = 0
        self.jump_price = 0
        self.touch_open_price = 0




    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.contact = self.cta_engine.main_engine.get_contract(self.vt_symbol)
        self.pricetick = self.contact.pricetick

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

    def on_tick(self, tick: TickData):
        """
        Callback of new tick data update.
        """
        if self.pos > 0 and (tick.last_price > self.high_close or tick.last_price < self.low_close):
            self.sell(tick.bid_price_1, self.pos, False)

        elif self.pos < 0 and (tick.last_price > self.high_close or tick.last_price < self.low_close):
            self.cover(tick.ask_price_1, abs(self.pos), False)


        self.bg.update_tick(tick)


    def on_bar(self, bar: BarData):
        """
        Callback of new bar data update.

        """
        if self.last_close_price == 0:
            self.last_close_price = bar.close_price
            return

        if self.trading:
            self.write_log(f"bar time {bar.datetime}, open :{bar.open_price}, close: {bar.close_price}")

        if self.pos == 0:
            if bar.high_price - self.last_close_price > self.JUMP:
                self.Touch_JUMP = 1
                self.open_count_down = self.OPEN_WINDOWS
                self.jump_price = max(self.last_close_price + self.JUMP,bar.open_price, bar.close_price)
                self.touch_open_price = min(bar.close_price, bar.open_price)
            elif self.last_close_price - bar.low_price > self.JUMP:
                self.Touch_JUMP = -1
                self.open_count_down = self.OPEN_WINDOWS
                self.jump_price = min(self.last_close_price - self.JUMP,bar.open_price, bar.close_price)
                self.touch_open_price = max(bar.open_price,bar.close_price)
            elif self.open_count_down >0:
                if self.Touch_JUMP == 1 and bar.low_price < self.touch_open_price:
                    self.cancel_all()
                    self.buy(price = self.jump_price,volume = self.fixed_size, stop = True)
                elif self.Touch_JUMP == -1 and bar.high_price > self.touch_open_price:
                    self.cancel_all()
                    self.short(price = self.jump_price, volume=self.fixed_size, stop = True)
            elif self.open_count_down <= 0:
                self.cancel_all()

            self.open_count_down = self.open_count_down -1



        if self.close_count_down <=0:
            if self.pos > 0:
                self.cancel_all()
                self.sell(bar.close_price-self.pricetick, abs(self.pos), False)
            elif self.pos <0:
                self.cancel_all()
                self.cover(bar.close_price+self.pricetick, abs(self.pos), False)

        self.close_count_down -= 1
        self.last_close_price = bar.close_price
        self.put_event()



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
            self.open_count_down = 0
            self.Touch_JUMP = 0
            if self.pos>0:
                self.high_close = trade.price + self.MARK_UP
                self.low_close = trade.price - self.MARK_DOWN
            else:
                self.high_close = trade.price + self.MARK_DOWN
                self.low_close = trade.price - self.MARK_UP


        self.put_event()

    def on_stop_order(self, stop_order: StopOrder):
        """
        :param stop_order:
        :return:
        """
        pass
