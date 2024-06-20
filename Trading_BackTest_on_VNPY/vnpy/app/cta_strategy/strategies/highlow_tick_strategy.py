from datetime import time
import numpy as np
from vnpy.trader.object import Offset
from vnpy.app.cta_strategy import (
    CtaTemplate,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData,
    BarGenerator,
    ArrayManager,
)


class HighLowMulTickStrategy(CtaTemplate):
    """"""

    author = "Billy"

    fixed_size = 1
    # k1 = 0.4
    # k2 = 0.6
    #
    #
    # day_open = 0
    # day_high = 0
    # day_low = 0
    #
    # day_range = 0
    # long_entry = 0
    # short_entry = 0
    # exit_time = time(hour=14, minute=55)

    long_entered = False
    short_entered = False


    # 策略参数
    N = 1200
    Range = 160
    priceDiff = 5
    priceMargin = 4
    offPrice = 8
    initDays = 0

    # 策略变量
    Highprice = 0
    Lowprice = 0
    Medianprice = 0
    posPrice = 0
    keyPrice = 0
    KPrice = 0
    indictor = 0

    parameters = ["Range", "priceDiff", "priceMargin", "offPrice","fixed_size"]
    variables = ["indictor"]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        """Constructor"""
        self.start_timePM = time(hour=9, minute=20)
        self.start_timeAM = time(hour=13, minute=35)
        self.start_timeNI = time(hour=21, minute=5)

        self.exit_timePM = time(hour=11, minute=25)
        self.exit_timeAM = time(hour=14, minute=50)
        self.exit_timeNI = time(hour=22, minute=46)

        self.closeOrder = []

        self.priceList = np.zeros(self.Range)
        self.indictor = 0
        self.Ncount = 0
        self.Ncountdown = 0
        self.NoffPrice = self.offPrice
        self.NpriceMargin = self.priceMargin


    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.write_log("策略初始化")
        # self.load_bar(10)

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
        # 计算指标数值
        self.priceList[0:self.Range - 1] = self.priceList[1:self.Range]
        self.priceList[-1] = tick.last_price
        if self.Ncount <= self.N:
            self.Ncount += 1
            return

        if (tick.datetime.time() >= self.start_timePM and tick.datetime.time() < self.exit_timePM) \
                or (tick.datetime.time() >= self.start_timeAM and tick.datetime.time() < self.exit_timeAM) \
                or (tick.datetime.time() >= self.start_timeNI and tick.datetime.time() < self.exit_timeNI):
            self.Highprice = max(self.priceList)
            self.Lowprice = min(self.priceList)
            self.Medianprice = np.median(self.priceList)

            Diff = self.Highprice - self.Medianprice
            if min(self.priceList[-10:]) <= self.Medianprice and tick.last_price > self.priceList[-2] and self.priceList[
                -2] > self.priceList[-3] and self.priceList[-3] > self.priceList[-4] and max(
                self.priceList[-50:]) == self.Highprice and Diff > self.priceDiff:
                self.indictor = 1
            elif max(self.priceList[-10:]) >= self.Medianprice and tick.last_price < self.priceList[-2] and \
                    self.priceList[-2] <  self.priceList[-3] and self.priceList[-3] < self.priceList[-4] and min(
                self.priceList[-50:]) == self.Lowprice and Diff > self.priceDiff:
                self.indictor = -1
            else:
                self.indictor = 0

            if self.pos == 0:
                self.cancel_all()
                self.Ncountdown = 0
                self.KPrice = 0
                self.NoffPrice = self.offPrice
                self.NpriceMargin = self.priceMargin
                if self.indictor == 1:
                    self.buy(tick.ask_price_1, self.fixedSize, stop=False)
                elif self.indictor == -1:
                    self.short(tick.bid_price_1, self.fixedSize, stop=False)
            elif self.pos > 0:
                self.Ncountdown = self.Ncountdown + 1
                # self.sell(self.posPrice + self.priceMargin, self.pos, stop=False)
                if tick.ask_price_1 == self.KPrice or tick.last_price == self.KPrice:
                    self.cancel_all()
                    self.KPrice = self.KPrice + 1
                    self.sell(self.KPrice, abs(self.pos), stop=False)
                elif self.Ncountdown % 60 == 0:
                    self.cancel_all()
                    self.NpriceMargin = self.NpriceMargin - 1
                    self.sell(self.posPrice + self.NpriceMargin, self.pos, stop=False)
                #     self.NoffPrice = self.NoffPrice - 3
                if tick.last_price <= self.posPrice - self.NoffPrice:
                    self.cancel_all()
                    self.sell(tick.bid_price_1, self.pos, stop=False)

            elif self.pos < 0:
                # self.cover(self.posPrice - self.priceMargin, abs(self.pos), stop=False)
                self.Ncountdown = self.Ncountdown + 1
                if tick.bid_price_1 == self.KPrice or tick.last_price == self.KPrice:
                    self.cancel_all()
                    self.KPrice = self.KPrice - 1
                    self.cover(self.KPrice, abs(self.pos), stop=False)
                elif self.Ncountdown % 60 == 0:
                    self.cancel_all()
                    self.NpriceMargin = self.NpriceMargin - 1
                    self.cover(self.posPrice - self.NpriceMargin, abs(self.pos), stop=False)
                #     self.NoffPrice = self.NoffPrice - 3
                if tick.last_price >= self.posPrice + self.NoffPrice:
                    self.cancel_all()
                    self.cover(tick.ask_price_1, self.fixedSize, stop=False)
        else:
            self.cancel_all()
            if self.pos > 0:
                self.sell(tick.bid_price_1, abs(self.pos), stop=False)
            elif self.pos < 0:
                self.cover(tick.ask_price_1, abs(self.pos), stop=False)
        # 发出状态更新事件
        # self.putEvent()

    def on_bar(self, bar: BarData):
        """
        Callback of new bar data update.
        """
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
            self.posPrice = trade.price
            if self.pos > 0:
                self.KPrice = self.posPrice + self.NpriceMargin
                self.closeOrder = self.sell(self.KPrice, self.pos, stop=False)
            elif self.pos < 0:
                self.KPrice = self.posPrice - self.NpriceMargin
                self.closeOrder = self.cover(self.KPrice, abs(self.pos), stop=False)

        self.put_event()

    def on_stop_order(self, stop_order: StopOrder):
        """
        Callback of stop order update.
        """
        pass
