from vnpy.trader.utility import BarGenerator, ArrayManager
from datetime import datetime, time
from vnpy.trader.utility import round_to
from vnpy.trader.constant import Status
from vnpy.app.spread_trading import (
    SpreadStrategyTemplate,
    SpreadAlgoTemplate,
    SpreadData,
    OrderData,
    TradeData,
    TickData,
    BarData
)


class AGBILStatisticalSpreadStrategy(SpreadStrategyTemplate):
    """"""

    author = "BILLY"


    boll_window = 300
    boll_dev = 1.5
    boll_plus = 1
    max_pos = 1
    payup = 1
    interval = 30
    check_Ratio = 3

    spread_pos = 0.0
    boll_up = 0.0
    boll_down = 0.0
    boll_mid = 0.0

    buy_price = 0.0
    sell_price = 0.0
    cover_price = 0.0
    short_price = 0.0
    start_indictor = False

    update_time = None
    buy_algoid = ""
    sell_algoid = ""
    short_algoid = ""
    cover_algoid = ""
    PosPrice = 0

    parameters = [
        "boll_window",
        "boll_dev",
        "boll_plus",
        "check_Ratio",
        "max_pos",
        "payup",
        "interval"
    ]
    variables = [
        "spread_pos",
        "PosPrice",
        "buy_price",
        "sell_price",
        "cover_price",
        "short_price",
        "update_time",
        "buy_algoid",
        "sell_algoid",
        "short_algoid",
        "cover_algoid",
        "start_indictor"
    ]

    def __init__(
        self,
        strategy_engine,
        strategy_name: str,
        spread: SpreadData,
        setting: dict
    ):
        """"""
        super().__init__(
            strategy_engine, strategy_name, spread, setting
        )
        self.start_indictor = False
        self.start_timePM = time(hour=9, minute=5)
        self.start_timeAM = time(hour=13, minute=35)
        self.start_timeNI = time(hour=21, minute=5)

        self.exit_timePM = time(hour=11, minute=25)
        self.exit_timeAM = time(hour=14, minute=55)
        self.exit_timeNI = time(hour=0, minute=15)


        self.bg = BarGenerator(self.on_spread_bar)
        self.am = ArrayManager(self.boll_window + 10)
        self.PosPrice = 0.0

    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.write_log("策略初始化")
        self.localPriceTick = self.getSymbolSize()
        self.load_bar(8)

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

        self.put_event()

    def on_spread_data(self):
        """
        Callback when spread price is updated.
        """

        # Trading is only allowed within given start/end time range
        self.update_time = self.spread.datetime.time()
        if not ((self.update_time > self.start_timePM and self.update_time <self.exit_timeAM) or (self.update_time > self.start_timeNI or self.update_time <self.exit_timeNI)):
            self.spread_pos = self.get_spread_pos()
            if self.spread_pos != 0:
                # Go through all legs to calculate price
                for n, leg in enumerate(self.spread.legs.values()):
                    if leg.net_pos > 0:
                        self.sell(leg.vt_symbol,leg.bid_price - self.localPriceTick,abs(leg.net_pos),False)
                    elif leg.net_pos < 0:
                        self.cover(leg.vt_symbol, leg.ask_price + self.localPriceTick, abs(leg.net_pos), False)
            else:
                self.stop_open_algos()
                self.stop_close_algos()
            self.put_event()
            return

        self.spread_pos = self.get_spread_pos()

        # No position
        if self.spread_pos == 0.0 and self.start_indictor:
            self.stop_close_algos()
            self.PosPrice = 0.0
            # Start open algos
            if not self.buy_algoid:
                self.buy_algoid = self.start_long_algo(
                    self.buy_price, self.max_pos, self.payup, self.interval
                )

            if not self.short_algoid:
                self.short_algoid = self.start_short_algo(
                    self.short_price, self.max_pos, self.payup, self.interval
                )

        # Long position
        elif self.spread_pos > 0:
            self.stop_open_algos()

            # Start sell close algo
            if not self.sell_algoid:
                if self.PosPrice != 0.0:
                    self.sell_price = min(self.PosPrice + (self.check_Ratio+1)*self.localPriceTick, self.sell_price)

                self.sell_algoid = self.start_short_algo(
                    self.sell_price, self.spread_pos, self.payup, self.interval
                )

        # Short position
        elif self.spread_pos < 0:
            self.stop_open_algos()

            # Start cover close algo
            if not self.cover_algoid:
                if self.PosPrice != 0.0:
                    self.cover_price = max(self.PosPrice - (self.check_Ratio+1)*self.localPriceTick, self.cover_price)
                self.cover_algoid = self.start_long_algo(
                    self.cover_price, abs(
                        self.spread_pos), self.payup, self.interval
                )

        self.put_event()

    def on_spread_tick(self, tick: TickData):
        """
        Callback when new spread tick data is generated.
        """
        self.bg.update_tick(tick)

    def on_spread_bar(self, bar: BarData):
        """
        Callback when spread bar data is generated.
        """
        self.stop_all_algos()

        self.am.update_bar(bar)
        if not self.am.inited:
            return


        self.boll_mid = self.am.sma(self.boll_window)
        self.boll_up, self.boll_down = self.am.boll(
            self.boll_window, self.boll_dev)

        self.buy_price = round_to(self.boll_down, self.localPriceTick)
        self.sell_price = round_to(self.boll_mid - self.boll_plus,self.localPriceTick)
        self.cover_price = round_to(self.boll_mid + self.boll_plus, self.localPriceTick)
        self.short_price = round_to(self.boll_up,self.localPriceTick)
        if self.sell_price - self.buy_price > self.check_Ratio*self.localPriceTick:
            self.start_indictor = True
        else:
            self.start_indictor = False

        self.put_event()

    def on_spread_pos(self):
        """
        Callback when spread position is updated.
        """
        self.spread_pos = self.get_spread_pos()
        self.put_event()

    def on_spread_algo(self, algo: SpreadAlgoTemplate):
        """
        Callback when algo status is updated.
        """
        if not algo.is_active():
            if self.buy_algoid == algo.algoid:
                if algo.status == Status.ALLTRADED:
                    self.PosPrice = algo.traded_price
                self.buy_algoid = ""
            elif self.sell_algoid == algo.algoid:
                self.sell_algoid = ""
            elif self.short_algoid == algo.algoid:
                if algo.status == Status.ALLTRADED:
                    self.PosPrice = algo.traded_price
                self.short_algoid = ""
            else:
                self.cover_algoid = ""

        self.put_event()

    def on_order(self, order: OrderData):
        """
        Callback when order status is updated.
        """
        pass

    def on_trade(self, trade: TradeData):
        """
        Callback when new trade data is received.
        """
        pass

    def stop_open_algos(self):
        """"""
        if self.buy_algoid:
            self.stop_algo(self.buy_algoid)

        if self.short_algoid:
            self.stop_algo(self.short_algoid)

    def stop_close_algos(self):
        """"""
        if self.sell_algoid:
            self.stop_algo(self.sell_algoid)

        if self.cover_algoid:
            self.stop_algo(self.cover_algoid)
