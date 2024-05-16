"""
https://github.com/DYSIM/Avellaneda-Stoikov-Implementation
            # limited time horizon
            reserve_price[step] = prices[step] - inventory[step] * gamma * (sigma ** 2) * (T-dt*step)
            reserve_spread = (2/gamma) * np.log(1 + gamma/k)

            if mode == 'symmetric':
                # symmetric strategy (fixed around mid-price)
                r_optimal_ask[step] = prices[step] + reserve_spread / 2
                r_optimal_bid[step] = prices[step] - reserve_spread / 2


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
from queue import Empty, Queue
from datetime import datetime
from vnpy.trader.object import Offset, Direction, OrderType


class TenMoveTickStrategy(CtaTemplate):
    """"""

    author = "Billy Zhang"

    init_pos =0
    init_entry_price = 0.0

    HeYueJiaZhi = 100000
    HeYueChengShu = 10.0


    price_diff = 1
    min_volume = 100
    price_up = 1
    price_down = 3

    max_pos = 7
    order_amount = 1

    fix_loss = 1000

    day_minutes = 255
    night_minutes = 120


    parameters = [
        "init_pos",
        "init_entry_price",
        "HeYueJiaZhi",
        "HeYueChengShu",
        "price_diff",
        "min_volume",
        "price_up",
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
        self.ArrayLength = 9
        self.tickQueue = Queue(self.ArrayLength)
        self.trade_price = 0

        self.last_volume_diff = -1
        self.closeOrderID = ""
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
        if self.close_min > self.current_min > 1:
            if not self.tickQueue.full():
                self.tickQueue.put(tick)
                return
            pre_tick = self.tickQueue.get()

            if self.last_volume_diff == -1:
                self.last_volume_diff = tick.volume - pre_tick.volume
                self.tickQueue.put(tick)
                return
            volume_dif = tick.volume - pre_tick.volume

            if self.pos == 0 and self.last_volume_diff < 160 and volume_dif > 250:
                price_diff = tick.last_price - pre_tick.last_price
                if price_diff <= -1:
                    self.send_direct_order(
                        self.contact,
                        Direction.LONG,
                        Offset.OPEN,
                        tick.ask_price_1,
                        self.order_amount,
                        OrderType.FAK
                    )
                elif price_diff >= 1:
                    self.send_direct_order(
                        self.contact,
                        Direction.SHORT,
                        Offset.OPEN,
                        tick.bid_price_1,
                        self.order_amount,
                        OrderType.FAK
                    )
                self.already_cancel = False

            elif self.pos <0 and tick.last_price > self.trade_price + self.price_down :
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
            elif self.pos >0 and tick.last_price < self.trade_price - self.price_down:
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
            self.last_volume_diff = volume_dif
            self.tickQueue.put(tick)
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
        elif self.pos < 0  :
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
