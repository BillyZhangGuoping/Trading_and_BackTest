"""



"""
from vnpy.app.cta_strategy import (
    CtaTemplate,
    StopOrder,
    TickData,
    TradeData,
    OrderData,
    BarData,
    BarGenerator
)
import numpy as np
from datetime import datetime
from vnpy.trader.object import Offset, Direction, OrderType


class AvgTickStrategy(CtaTemplate):
    """"""

    author = "Billy Zhang"

    init_pos =0
    init_entry_price = 0.0

    HeYueJiaZhi = 100000
    HeYueChengShu = 10.0


    price_diff = 2
    min_volume = 100
    price_up = 3
    price_down = 4

    max_pos = 7
    order_amount = 1

    fix_loss = 1000

    day_minutes = 255
    night_minutes = 120

    ArrayLength = 12


    parameters = [
        "init_pos",
        "init_entry_price",
        "HeYueJiaZhi",
        "HeYueChengShu",
        "price_diff",
        "min_volume",
        "ArrayLength",
        "price_diff",
        "price_up",
        "price_down",
        "order_amount",
        "fix_loss"
    ]
    variables = [
                 ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, vt_local, setting):
        """"""
        super().__init__(cta_engine, strategy_name, vt_symbol, vt_local, setting)
        self.total_minute = self.day_minutes

        if datetime.now().hour > 18:
            self.total_minute = self.night_minutes
        self.close_min = self.total_minute -10
        self.current_min = 0
        self.contact = self.cta_engine.main_engine.get_contract(self.vt_symbol)
        self.close_order = ''
        self.minute = ""
        self.priceArray = np.zeros(self.ArrayLength)
        self.trade_price = 0

        self.closeOrderID = ""
        self.openShortOrderID = ""
        self.openLongOrderID = ""
        self.already_cancel = False

    def on_init(self):
        """
        Callback when strategy is inited.
        """


        self.write_log("策略初始化")

    def on_start(self):
        """
        Callback when strategy is started.
        """
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
        self.priceArray[:-1] = self.priceArray[1:]
        self.priceArray[-1] = tick.last_price
        if self.close_min > self.current_min > 1:
            avg_price = np.mean(self.priceArray)
            price_gap = tick.last_price - avg_price
            if self.pos == 0 and (tick.ask_price_1 - tick.bid_price_1) == 1:
                if price_gap <= -self.price_diff:
                    self.send_direct_order(
                        self.contact,
                        Direction.LONG,
                        Offset.OPEN,
                        tick.ask_price_1,
                        self.order_amount,
                        OrderType.FAK
                    )
                elif price_gap >= self.price_diff:
                    self.send_direct_order(
                        self.contact,
                        Direction.SHORT,
                        Offset.OPEN,
                        tick.bid_price_1,
                        self.order_amount,
                        OrderType.FAK
                    )
                self.already_cancel = False

            elif self.pos <0 and tick.last_price >= (self.trade_price + self.price_down) :
                if self.already_cancel or self.cta_engine.cancel_server_order(self, self.closeOrderID):
                    self.send_direct_order(
                        self.contact,
                        Direction.LONG,
                        Offset.CLOSE,
                        tick.ask_price_1,
                        abs(self.pos),
                        OrderType.FAK
                        )
                    self.already_cancel = True
            elif self.pos >0 and tick.last_price <= (self.trade_price - self.price_down):
                if self.already_cancel or self.cta_engine.cancel_server_order(self, self.closeOrderID):
                    self.closeOrderID = self.send_direct_order(
                        self.contact,
                        Direction.SHORT,
                        Offset.CLOSE,
                        tick.bid_price_1,
                        abs(self.pos),
                        OrderType.FAK
                        )
                    self.already_cancel = True

        elif self.pos > 0:
            if self.cta_engine.cancel_server_order(self, self.closeOrderID):
                self.closeOrderID = self.send_direct_order(
                    self.contact,
                    Direction.LONG,
                    Offset.CLOSE,
                    tick.ask_price_1,
                    abs(self.pos),
                    OrderType.LIMIT
                    )
        elif self.pos < 0:
            if self.cta_engine.cancel_server_order(self,self.closeOrderID):
                self.closeOrderID = self.send_direct_order(
                    self.contact,
                    Direction.SHORT,
                    Offset.CLOSE,
                    tick.bid_price_1,
                    abs(self.pos),
                    OrderType.LIMIT
                    )



        if self.minute != tick.datetime.minute:
            self.minute = tick.datetime.minute
            self.current_min +=1

    def on_order(self, order: OrderData):
        """
        Callback of new order data update.
        """
        pass

    def on_trade(self, trade: TradeData):
        """
        Callback of new trade data update.
        """
        self.trade_price = trade.price
        if self.pos >0:
            self.closeOrderID = self.send_direct_order(
                self.contact,
                Direction.SHORT,
                Offset.CLOSE,
                trade.price + self.price_up,
                abs(self.pos),
                OrderType.LIMIT
                )
        else:
            self.closeOrderID = self.send_direct_order(
                self.contact,
                Direction.LONG,
                Offset.CLOSE,
                trade.price - self.price_up,
                abs(self.pos),
                OrderType.LIMIT
                )


    def on_stop_order(self, stop_order: StopOrder):
        """
        :param stop_order:
        :return:
        """
        pass
