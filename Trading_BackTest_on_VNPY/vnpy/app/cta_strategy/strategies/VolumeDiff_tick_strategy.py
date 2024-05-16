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

from datetime import datetime
from vnpy.trader.object import Offset, Direction, OrderType


class VolumeDiffTickStrategy(CtaTemplate):
    """"""

    author = "Billy Zhang"

    init_pos =0
    init_entry_price = 0.0

    HeYueJiaZhi = 100000
    HeYueChengShu = 10.0


    bid_ratio = 2.0
    min_volume = 10
    price_up = 1

    max_pos = 7
    order_amount = 3

    fix_loss = 1000

    day_minutes = 275
    night_minutes = 110


    parameters = [
        "init_pos",
        "init_entry_price",
        "HeYueJiaZhi",
        "HeYueChengShu",
        "bid_ratio",
        "min_volume",
        "price_up",
        "max_pos",
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
        self.close_min = self.total_minute -5
        self.bg = BarGenerator(self.on_bar)
        self.current_min = 0
        self.contact = self.cta_engine.main_engine.get_contract(self.vt_symbol)
        self.ask_ratio = 1/self.bid_ratio
        self.close_order = ''

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
        if self.close_min > self.current_min > 0 and abs(self.pos) < self.max_pos:
            bidask_ratio = tick.bid_volume_1/tick.ask_volume_1
            if bidask_ratio > self.bid_ratio and self.pos <=0:
                self.cancel_all()
                self.send_FAK_Order(
                    Direction.LONG,
                    tick.ask_price_1,
                    max(self.order_amount,-self.pos),
                    OrderType.FAK
                    )
            elif bidask_ratio < self.ask_ratio and self.pos >=0:
                self.cancel_all()
                self.send_FAK_Order(
                    Direction.SHORT,
                    tick.bid_price_1,
                    max(self.pos, self.order_amount),
                    OrderType.FAK
                    )
        elif self.pos > self.max_pos:
            self.send_FAK_Order(
                Direction.SHORT,
                tick.bid_price_1,
                self.pos,
                OrderType.LIMIT
                )
        elif self.pos < -self.max_pos:
            self.send_FAK_Order(
                Direction.LONG,
                tick.ask_price_1,
                abs(self.pos),
                OrderType.LIMIT
                )
            # reserve_spread = (2 / gamma) * np.log(1 + gamma / k)


        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData):
        self.current_min +=1

    def send_FAK_Order(self,direction,price,fixedSize,orderType):
        self.cta_engine.send_server_order(
            self,
            self.contact,
            direction,
            Offset.NONE,
            price,
            fixedSize,
            orderType,
            lock=False,
            net=True
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
        if self.pos>0:
            self.send_FAK_Order(
                                Direction.SHORT,
                                trade.price + self.price_up,
                                self.pos,
                                OrderType.LIMIT
                                )
        else:
            self.send_FAK_Order(
                Direction.LONG,
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
