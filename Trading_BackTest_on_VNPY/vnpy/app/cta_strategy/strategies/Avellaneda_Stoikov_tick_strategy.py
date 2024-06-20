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
from vnpy.trader.constant import Interval
import numpy as np
from datetime import datetime
from vnpy.trader.object import Offset, Direction, OrderType


class ASTickStrategy(CtaTemplate):
    """"""

    author = "Billy Zhang"

    init_pos =0
    init_entry_price = 0.0

    HeYueJiaZhi = 100000
    HeYueChengShu = 10.0

    # Volatility
    sigma = 8
    # inventory Risk aversion
    gamma = 0.4
    # order book liquidity
    k = 1.5

    max_pos = 7
    order_amount = 1
    min_spread = 1

    fix_loss = 1000

    day_minutes = 275
    night_minutes = 110


    parameters = [
        "init_pos",
        "init_entry_price",
        "HeYueJiaZhi",
        "HeYueChengShu",
        "sigma",
        "gamma",
        "k",
        "max_pos",
        "order_amount",
        "min_spread",
        "fix_loss"
    ]
    variables = [
                 ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, vt_local, setting):
        """"""
        super().__init__(cta_engine, strategy_name, vt_symbol, vt_local, setting)
        self.inventory = 0
        self.reserve_spread = (2 / self.gamma) * np.log(1 + self.gamma / self.k)/2
        self.temp_state = self.gamma * (self.sigma ** 2)
        self.total_minute = self.day_minutes

        if datetime.now().hour > 18:
            self.total_minute = self.night_minutes
        self.close_min = self.total_minute -5
        self.bg = BarGenerator(self.on_bar)
        self.current_min = 0
        self.time_left_fraction = 1
        self.contact = self.cta_engine.main_engine.get_contract(self.vt_symbol)

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
            reserve_price = tick.last_price - self.pos * self.temp_state * self.time_left_fraction
            r_optimal_ask = max(reserve_price  + self.reserve_spread / 2, tick.last_price + 1)
            r_optimal_bid = min(reserve_price  - self.reserve_spread / 2,tick.last_price -1)

            self.send_FAK_Order(
                Direction.LONG,
                r_optimal_bid,
                self.order_amount
                )

            self.send_FAK_Order(
                Direction.SHORT,
                r_optimal_ask,
                self.order_amount
                )
        elif self.pos > self.max_pos:
            self.send_FAK_Order(
                Direction.SHORT,
                tick.bid_price_1,
                self.pos
                )
        elif self.pos < -self.max_pos:
            self.send_FAK_Order(
                Direction.LONG,
                tick.ask_price_1,
                abs(self.pos)
                )
            # reserve_spread = (2 / gamma) * np.log(1 + gamma / k)

            # if mode == 'symmetric':
            #     # symmetric strategy (fixed around mid-price)
            #     r_optimal_ask[step] = prices[step] + reserve_spread / 2
            #     r_optimal_bid[step] = prices[step] - reserve_spread / 2
            #     optimal_distance_ask = r_optimal_ask[step] - prices[step]
            #     optimal_distance_bid = prices[step] - r_optimal_bid[step]
            # elif mode == 'inventory':
            #     # i nventory strategy (fixed around reservation price)
            #     r_optimal_ask[step] = reserve_price[step] + reserve_spread / 2
            #     r_optimal_bid[step] = reserve_price[step] - reserve_spread / 2
            #     optimal_distance_ask = -gamma * inventory[step] * (sigma ** 2) + (1 / gamma) * np.log(1 + (gamma / k))
            #     optimal_distance_bid = gamma * inventory[step] * (sigma ** 2) + (1 / gamma) * np.log(1 + (gamma / k))

        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData):
        self.current_min +=1
        self.time_left_fraction = min(0,1 - self.current_min/self.total_minute)

    def send_FAK_Order(self,direction,price,fixedSize):
        self.cta_engine.send_server_order(
            self,
            self.contact,
            direction,
            Offset.OPEN,
            price,
            fixedSize,
            OrderType.FAK,
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
        pass

    def on_stop_order(self, stop_order: StopOrder):
        """
        :param stop_order:
        :return:
        """
        pass
