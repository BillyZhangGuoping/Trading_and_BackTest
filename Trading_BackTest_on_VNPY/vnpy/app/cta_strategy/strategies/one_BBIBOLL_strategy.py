"""
短线策略1
1、先判断大趋势方向，做成GUI页面打钩，例如多头、中性、空头。或者分别有1、0、-1替代都可以。判断大方向我觉得估计还是用人工判断，因为需要参考升贴水以及K线和均线形态。长期趋势看涨的品种，只做多。长期趋势看跌的品种，只做空。
   策略参数long_trend 表示长期趋势，默认为0
2、所有品种按照不同板块录入数据库，选出一部分可以交易的活跃品种。类似母库与子库，只能交易子库的品种。
    未在策略踢醒
3、入场选择用30分钟K作为信号，然后20-120天均线作为参数，届时在GUI界面选择或者填都可以。
    bar_time_length 代表k线时间周期，默认30，为30分钟K线
    MA_windows 表示均线计算周期，默认60，
4、起初不持有任何头寸，某品种主趋势是看涨的，小趋势下跌回调，然后30分K实时价格突破所选择的MA参数的实时价格（可选择多个MA参数，只要突破其中一个即可），
    同时满足当时macd能量柱是红色，即diff大于dea，则入场做多。30分K的macd死叉马上平仓多头离场，如果是隔夜跳空翻转的，diff小于dea也要离场。
    之后，macd再次金叉，并且30分K实时价格突破或者大于所选择的MA参数的实时价格（可选择多个MA参数，只要突破其中一个即可），则再次入场做多。
    （入场必须满足2个条件，diff大于dea，并且30分K实时价格大于所选择的MA参数的实时价格）。
    策略在on_tick 方法中，每10秒中按照临时合成数据判断，在on_time_bar在每个K线结束时候判断
5、起初不持有任何头寸，某品种主趋势是看跌的，小趋势上涨反弹，然后30分K实时价格跌穿所选择的MA参数的实时价格（可选择多个MA参数，只要突破其中一个即可），
    同时满足当时macd能量柱是绿色，diff小于dea，则入场做空。30分K的macd金叉马上平仓空头离场，如果是隔夜跳空翻转的，diff大于dea也要离场。
    之后，macd再次死叉，并且30分K实时价格跌破或者小于所选择的MA参数的实时价格（可选择多个MA参数，只要突破其中一个即可），则再次入场做空。
    （入场必须满足2个条件，diff小于dea，并且30分K实时价格小于所选择的MA参数的实时价格）。
     策略在on_tick 方法中，每10秒中按照临时合成数据判断，在on_time_bar在每个K线结束时候判断
6、如果某品种属于中性品种，则多和空都可以操作。按照上面第4和5的操作方式入场和出场。
（一般不要选择此类品种，因为行情比较反复，交易频率比较高）
   策略参数long_trend 表示长期趋势，默认为0，可开多/空单，1为只开多单，-1为只开空单
7、单笔设置最大8%止损。当合约产生利润P，若3%<P<5%，则自动设置移动止损，回撤2%平仓；若5%<P<10%，则自动设置移动止损，回撤3%平仓；若10%<P<20%，则自动设置移动止损，回撤4%平仓。
    策略参数 fix_loss 表示固定止损, 默认值8%，计算方法为
    多头： (现价 - 买入价）/ 买入价，此时止损价为 买入价*（1- 8%）
    空头： （现价 - 买入）/ 买入价， 此时止损价为 买入价*（1 + 8%）
    策略参数 triger_profit_1 默认值3，triger_profit_2, 默认值5 ， triger_profit_3, 默认值10， triger_profit_4, 默认值20 ；对应盈利指标
    策略参数 move_loss_1 默认值 2, move_loss_2, 默认值3 ， move_loss_3, 默认值4， move_loss_4, 默认值6%
    多头： 当买入后 (最高价 - 买入价)/买入价 为正计算收益率，如大于triger_profit_1 2%后，按照 （最高价 -  买入价*2%）作为止损价格。
    空头： 当买入后 （买入价 - 最低价）/ 买入价 为正计算收益率，如大于triger_profit_1 2%后，按照 （最低价 + 买入价*2%）作为止损价格。
    后面类似递增


"""
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
from vnpy.trader.constant import Interval
import numpy as np
from copy import copy
import talib
from vnpy.trader.object import Offset


class OneBBIBOLLStrategy(CtaTemplate):
    """"""

    author = "BIlly Zhang"

    init_pos =0
    init_entry_price = 0.0

    Kxian = 30
    HeYueJiaZhi = 40000
    HeYueChengShu = 10.0


    fixed_size = 1

    BBI_dev = 3.5
    BBI_Windows = 30

    fix_loss = 0.8
    CLOSE_BAR = 40
    triger_profit_1 = 2.5
    triger_profit_2 = 5.0
    triger_profit_3 = 8.0
    triger_profit_4 = 12.0

    move_loss_1 = 1.3
    move_loss_2 = 1.8
    move_loss_3 = 2.0
    move_loss_4 = 2.0


    BBI_mid = 0
    BBI_hgih = 0
    BBI_low = 0

    price_rate = 0
    entry_price = 0
    close_bar_count = 0

    intra_trade_high = 0
    intra_trade_low = 1000
    long_stop = 0
    short_stop = 0
    interval_balRatio = 0.2
    current_balRatio = 0.6

    parameters = [
        "init_pos",
        "init_entry_price",
        "fixed_size",
        "HeYueJiaZhi",
        "HeYueChengShu",
        "interval_balRatio",
        "current_balRatio",
        "Kxian",
        "BBI_dev",
        "BBI_Windows",
        "fix_loss",
        "CLOSE_BAR",
        "triger_profit_1",
        "triger_profit_2",
        "triger_profit_3",
        "triger_profit_4",
        "move_loss_1",
        "move_loss_2",
        "move_loss_3",
        "move_loss_4"
    ]
    variables = [
        "entry_price",
        "price_rate",
        "BBI_mid",
        "BBI_hgih",
        "BBI_low",
        "close_bar_count",
        "intra_trade_high",
        "intra_trade_low",
        "long_stop",
        "short_stop"
                 ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, vt_local, setting):
        """"""
        super().__init__(cta_engine, strategy_name, vt_symbol, vt_local, setting)


        if self.Kxian >= 240 :
            self.bg = BarGenerator(self.on_bar, 4, self.on_time_bar, Interval.HOUR)
        elif 240>self.Kxian >= 180:
            self.bg = BarGenerator(self.on_bar, 3, self.on_time_bar, Interval.HOUR)
        elif 180>self.Kxian >= 60:
            self.bg = BarGenerator(self.on_bar, 1, self.on_time_bar, Interval.HOUR)
        else:
            self.bg = BarGenerator(self.on_bar, self.Kxian, self.on_time_bar)



        self.am = ArrayManager(self.BBI_Windows + 50)


    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.pos = self.init_pos
        self.entry_price = self.init_entry_price
        self.PosPrice = self.entry_price

        self.write_log("策略初始化")
        self.load_bar(30)

    def on_start(self):
        """
        Callback when strategy is started.
        """
        self.pos = self.init_pos
        self.entry_price = self.init_entry_price
        self.PosPrice = self.entry_price
        self.write_log("策略启动")

        # self.calculation_fixedSize()


        if self.pos > 0:
            self.close_bar_count = 0
            self.new_time_bar = False
            self.cancel_all()
            self.sell(max(self.BBI_mid, self.long_stop), abs(self.pos), True,lock=False,net=True)

        elif self.pos < 0:
            self.close_bar_count = 0
            self.new_time_bar = False
            self.cancel_all()
            self.cover(min(self.BBI_mid, self.short_stop), abs(self.pos),True,lock=False,net=True)

    def on_stop(self):
        """
        Callback when strategy is stopped.
        """
        self.write_log("策略停止")

    def on_tick(self, tick: TickData):
        """
        Callback of new tick data update.
        """

        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData):
        """
        Callback of new bar data update.

        """
        if not self.am.inited:
            self.bg.update_bar(bar)
            return
        local_close_array = copy(self.am.close_array)
        local_close_array[:-1] = local_close_array[1:]
        local_close_array[-1] = bar.close_price

        # mid = (self.sma(3, True) + self.sma(6, True) + self.sma(12, True) + self.sma(24, True))/4
        # std = talib.STDDEV(mid, n, 1)
        #
        # up = mid + std * dev
        # down = mid - std * dev


        mid = (talib.SMA(local_close_array, 3) + talib.SMA(local_close_array, 6) + talib.SMA(local_close_array, 12) + talib.SMA(local_close_array, 24))/4
        std = talib.STDDEV(mid, self.BBI_Windows, 1)

        BBI_hgih = self.BBI_mid + std*self.BBI_dev
        BBI_low = self.BBI_mid - std * self.BBI_dev
        self.BBI_hgih = BBI_hgih[-1]
        self.BBI_low = BBI_low[-1]

        self.BBI_mid = mid[-1]


        if self.pos == 0:
            self.intra_trade_high = bar.high_price
            self.intra_trade_low = bar.low_price
            self.close_bar_count = self.close_bar_count + 1
            self.entry_price = 0
            self.price_rate = 0
            self.cancel_all()
            if mid[-1] > mid[-2] and self.close_bar_count >= self.CLOSE_BAR and self.new_time_bar == True:
                self.buy(self.BBI_hgih, self.fixed_size, True,lock=False,net=True)
            elif mid[-1] < mid[-2] and self.close_bar_count >= self.CLOSE_BAR and self.new_time_bar == True:
                self.short(self.BBI_low, self.fixed_size, True,lock=False,net=True)

        elif self.pos > 0:
            self.close_bar_count = 0
            self.new_time_bar = False

            self.intra_trade_high = max(self.intra_trade_high, bar.high_price)
            self.intra_trade_low = bar.low_price

            self.price_rate = (self.intra_trade_high - self.entry_price) * 100.0 / self.entry_price

            if self.price_rate < self.triger_profit_1:
                self.long_stop = self.intra_trade_high - self.fix_loss * 0.01*self.entry_price
            elif self.price_rate >= self.triger_profit_1 and self.price_rate < self.triger_profit_2:
                self.long_stop = self.intra_trade_high - self.entry_price * self.move_loss_1 * 0.01
            elif self.price_rate >= self.triger_profit_2 and self.price_rate < self.triger_profit_3:
                self.long_stop = self.intra_trade_high - self.entry_price * self.move_loss_2 * 0.01
            elif self.price_rate >= self.triger_profit_3 and self.price_rate < self.triger_profit_4:
                self.long_stop = self.intra_trade_high - self.entry_price * self.move_loss_3 * 0.01
            elif self.price_rate >= self.triger_profit_4:
                self.long_stop = self.intra_trade_high - self.entry_price * self.move_loss_4 * 0.01

            self.cancel_all()
            self.sell(max(self.BBI_mid, self.long_stop), abs(self.pos), True,lock=False,net=True)



        elif self.pos < 0:
            self.close_bar_count = 0
            self.new_time_bar = False

            self.intra_trade_high = bar.high_price
            self.intra_trade_low = min(self.intra_trade_low, bar.low_price)

            self.price_rate = (self.entry_price - self.intra_trade_low) * 100.0 / self.entry_price

            if self.price_rate < self.triger_profit_1:
                self.short_stop = self.intra_trade_low  + self.entry_price*self.fix_loss * 0.01
            elif self.price_rate >= self.triger_profit_1 and self.price_rate < self.triger_profit_2:
                self.short_stop = self.intra_trade_low + self.entry_price * self.move_loss_1 * 0.01
            elif self.price_rate >= self.triger_profit_2 and self.price_rate < self.triger_profit_3:
                self.short_stop = self.intra_trade_low + self.entry_price * self.move_loss_2 * 0.01
            elif self.price_rate >= self.triger_profit_3 and self.price_rate < self.triger_profit_4:
                self.short_stop = self.intra_trade_low + self.entry_price * self.move_loss_3 * 0.01
            elif self.price_rate >= self.triger_profit_4:
                self.short_stop = self.intra_trade_low + self.entry_price * self.move_loss_4 * 0.01

            self.cancel_all()
            self.cover(min(self.short_stop,  self.BBI_mid), abs(self.pos), True,lock=False,net=True)
        self.LastPrice = bar.close_price
        self.bg.update_bar(bar)
        self.sync_data()
        self.put_event()

    def on_time_bar(self, bar: BarData):
        am = self.am
        am.update_bar(bar)
        if not am.inited:
            return
        self.new_time_bar = True
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
            self.close_bar_count = 0
        self.put_event()

    def on_stop_order(self, stop_order: StopOrder):
        """
        :param stop_order:
        :return:
        """
        pass
