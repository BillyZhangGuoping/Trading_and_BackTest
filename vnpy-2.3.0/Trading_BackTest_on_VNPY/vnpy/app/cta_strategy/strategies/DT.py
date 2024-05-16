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
from vnpy.trader.utility import load_json


class DT_x(CtaTemplate):
    """"""

    author = "用Python的交易员"

    init_pos = 0
    init_entry_price = 0.0
    Kxian = ''
    beishu = 0.0
    Length = 0
    stoploss_percent = 0.0
    HeYueJiaZhi = 0
    HeYueChengShu = 0

    entry_price = 0.0
    long_entry = 0.0
    short_entry = 0.0

    parameters = ["init_pos", "init_entry_price","Kxian","beishu","Length","stoploss_percent","HeYueJiaZhi","HeYueChengShu"]
    variables = ["entry_price", "long_entry", "short_entry"]

    def __init__(self, cta_engine, strategy_name, vt_symbol, vt_local, setting):
        """"""
        super().__init__(cta_engine, strategy_name, vt_symbol, vt_local, setting)

        self.long_entry_no = 0
        self.short_entry_no =0
    # self.canshu = self.canshuDict[strategy_name]
    # self.Kxian = self.canshu[0]
    # self.beishu = self.canshu[1]
    # self.Length = self.canshu[2]
    # self.stoploss_percent = self.canshu[3]
    # self.HeYueJiaZhi = self.canshu[4]
    # self.HeYueChengShu = self.canshu[5]

    # # self.cansshu = load_json(self.inside_setting_filename)
    # # self.cansshu[strategy_name] = self.canshu
    # # save_json(self.inside_setting_filename, self.cansshu)

    # if self.Kxian == "1h":
    #     self.bg = BarGenerator(self.on_bar, 1, self.on_window_bar, Interval.HOUR)
    # elif self.Kxian == "4h":
    #     self.bg = BarGenerator(self.on_bar, 4, self.on_window_bar, Interval.HOUR)
    # elif self.Kxian == "30m":
    #     self.bg = BarGenerator(self.on_bar, 30, self.on_window_bar)

    # self.am = ArrayManager()

    def on_init(self):
        """
        Callback when strategy is inited.
        """
        # Billy move to on_init
        # self.canshuDict = load_json(self.inside_setting_filename)
        # self.canshu = self.canshuDict[self.strategy_name]
        # self.Kxian = self.canshu[0]
        # self.beishu = self.canshu[1]
        # self.Length = self.canshu[2]
        # self.stoploss_percent = self.canshu[3]
        # self.HeYueJiaZhi = self.canshu[4]
        # self.HeYueChengShu = self.canshu[5]

        # self.cansshu = load_json(self.inside_setting_filename)
        # self.cansshu[strategy_name] = self.canshu
        # save_json(self.inside_setting_filename, self.cansshu)
        self.Length = int(self.Length)
        if self.Kxian == "1h":
            self.bg = BarGenerator(self.on_bar, 1, self.on_window_bar, Interval.HOUR)
        if self.Kxian == "3h":
            self.bg = BarGenerator(self.on_bar, 3, self.on_window_bar, Interval.HOUR)
        elif self.Kxian == "4h":
            self.bg = BarGenerator(self.on_bar, 4, self.on_window_bar, Interval.HOUR)
        elif self.Kxian == "30m":
            self.bg = BarGenerator(self.on_bar, 30, self.on_window_bar)

        self.am = ArrayManager()
        # end

        self.pos = self.init_pos
        self.entry_price = self.init_entry_price
        self.PosPrice = self.entry_price
        self.load_bar(30)

    # self.write_log("策略初始化")

    def on_start(self):
        """
        Callback when strategy is started.
        """
        if self.HeYueJiaZhi == 0 or self.HeYueJiaZhi == 0:
            return
        if self.pos == 0:
            self.buy(self.long_entry, self.trading_size_long, stop=True, net=True)
            self.short(self.short_entry, self.trading_size_short, stop=True, net=True)

        elif self.pos > 0:
            self.long_stop = self.entry_price * (1 - self.stoploss_percent)
            if self.long_stop > self.short_entry:
                self.sell(self.long_stop, abs(self.pos), stop=True, net=True)
            else:
                self.sell(self.short_entry, abs(self.pos), stop=True, net=True)
            self.short(self.short_entry, self.trading_size_short, stop=True, net=True)

        elif self.pos < 0:
            self.short_stop = self.entry_price * (1 + self.stoploss_percent)
            if self.short_stop < self.long_entry:
                self.cover(self.short_stop, abs(self.pos), stop=True, net=True)
            else:
                self.cover(self.long_entry, abs(self.pos), stop=True, net=True)
            self.buy(self.long_entry, self.trading_size_long, stop=True, net=True)

    # self.write_log("策略启动")

    def on_stop(self):
        """
        Callback when strategy is stopped.
        """
        self.write_log("策略停止")

    def on_tick(self, tick: TickData):
        """
        Callback of new tick data update.
        """
        # self.write_log(tick)
        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData):
        """
        Callback of new bar data update.
        """
        self.LastPrice = bar.close_price
        self.bg.update_bar(bar)
        self.put_event()

    def on_window_bar(self, bar: BarData):
        """
        Callback of new bar data update.
        """
        # self.write_log(bar)
        self.cancel_all()

        self.am.update_bar(bar)
        if not self.am.inited:
            return

        self.HH = self.am.high[-self.Length:].max()
        self.HC = self.am.close[-self.Length:].max()
        self.LL = self.am.low[-self.Length:].min()
        self.LC = self.am.close[-self.Length:].min()
        self.Range = max(self.HH - self.LC, self.HC - self.LL)
        self.Trig = self.beishu * self.Range
        if self.Trig == 0:
            self.Trig = bar.close_price / 50

        self.long_entry = round(bar.close_price + self.Trig, 1)
        self.long_entry_no = bar.close_price + self.Trig
        self.short_entry = round(bar.close_price - self.Trig, 1)
        self.short_entry_no = bar.close_price - self.Trig
        self.trading_size_long = round((self.HeYueJiaZhi / self.HeYueChengShu) / self.long_entry)
        self.trading_size_short = round((self.HeYueJiaZhi / self.HeYueChengShu) / self.short_entry)
        if self.HeYueJiaZhi == 0 or self.HeYueJiaZhi == 0:
            self.put_event()
            return

        if self.pos == 0:
            self.buy(self.long_entry, self.trading_size_long, stop=True, net=True)
            self.short(self.short_entry, self.trading_size_short, stop=True, net=True)

        elif self.pos > 0:
            self.long_stop = self.entry_price * (1 - self.stoploss_percent)
            if self.long_stop > self.short_entry:
                self.sell(self.long_stop, abs(self.pos), stop=True, net=True)
            else:
                self.sell(self.short_entry, abs(self.pos), stop=True, net=True)
            self.short(self.short_entry, self.trading_size_short, stop=True, net=True)

        elif self.pos < 0:
            self.short_stop = self.entry_price * (1 + self.stoploss_percent)
            if self.short_stop < self.long_entry:
                self.cover(self.short_stop, abs(self.pos), stop=True, net=True)
            else:
                self.cover(self.long_entry, abs(self.pos), stop=True, net=True)
            self.buy(self.long_entry, self.trading_size_long, stop=True, net=True)
        # self.cta_engine.write_log(f"window close price{bar}")
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
        # move to cta_template.on_cta_trade
        # self.entry_price = trade.price
        # self.write_log(f"{trade.direction}数量{trade.volume}价格{trade.price},策略持仓{self.pos}价格{self.entry_price}")
        # # Sync strategy setting to setting file
        # self.setting = {'init_pos':self.pos,'init_entry_price': self.entry_price}
        # self.sync_setting(self.strategy_name,self.setting)
        self.cancel_all()
        if self.pos > 0:
            self.long_stop = self.entry_price * (1 - self.stoploss_percent)
            self.sell(self.long_stop, abs(self.pos), stop=True, net=True)
            # self.short(self.short_entry, self.trading_size_short, stop=True, net=True)
        elif self.pos < 0:
            self.short_stop = self.entry_price * (1 + self.stoploss_percent)
            self.cover(self.short_stop, abs(self.pos), stop=True, net=True)

            # self.buy(self.long_entry, self.trading_size_long, stop=True, net=True)
        self.put_event()

    def on_stop_order(self, stop_order: StopOrder):
        """
        Callback of stop order update.
        """
        pass