"""
短线策略1
1、先判断大趋势方向，做成GUI页面打钩，例如多头、中性、空头。或者分别有1、0、-1替代都可以。判断大方向我觉得估计还是用人工判断，因为需要参考升贴水以及K线和均线形态。长期趋势看涨的品种，只做多。长期趋势看跌的品种，只做空。
   策略参数long_trend 表示长期趋势，默认为0
2、所有品种按照不同板块录入数据库，选出一部分可以交易的活跃品种。类似母库与子库，只能交易子库的品种。
    未在策略踢醒
3、入场选择用30分钟K作为信号，然后20-120天均线作为参数，届时在GUI界面选择或者填都可以。
    bar_time_length 代表k线时间周期，默认30，为30分钟K线
    MA_windows 表示均线计算周期，默认60，
4、起初不持有任何头寸，某品种主趋势是看涨的，小趋势下跌回调，然后30分K对应的macd金叉，即diff大于dea，则入场做多。当实时30分K线（T时刻）的dea小于前一根30分K线（T1时刻）的dea则平多出场。之后，当实时30分K线（T时刻）的dea大于前一根30分K线（T1时刻）的dea，并且同时满足diff大于dea，则再次入场做多。（入场必须满足2个条件，diff大于dea，并且实时30分K线（T时刻）的dea大于前一根30分K线（T1时刻）的dea）。
5、起初不持有任何头寸，某品种主趋势是看跌的，小趋势上涨反弹，然后30分K对应的macd死叉，即diff小于dea，则入场做空。当实时30分K线（T时刻）的dea大于前一根30分K线（T1时刻）的dea则平空出场。之后，当实时30分K线（T时刻）的dea小于前一根30分K线（T1时刻）的dea，并且同时满足diff小于dea，则再次入场做空。（入场必须满足2个条件，diff小于dea，并且实时30分K线（T时刻）的dea小于前一根30分K线（T1时刻）的dea）。
6、如果某品种属于中性品种，则多和空都可以操作。按照上面第4和5的操作方式入场和出场。

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
from copy import copy
import talib
from vnpy.trader.object import Offset


class TwoMAMACDBarStrategy(CtaTemplate):
	""""""

	author = "BIlly Zhang"

	long_trend = 0
	bar_time_length = 30
	MA_Windows = 30

	MACD_short = 12
	MACD_long = 26
	MACD_signal = 9

	fixed_size = 1

	fix_loss = 8

	triger_profit_1 = 3
	triger_profit_2 = 5
	triger_profit_3 = 10
	triger_profit_4 = 20

	move_loss_1 = 2
	move_loss_2 = 3
	move_loss_3 = 4
	move_loss_4 = 6
	OPEN_MACD_RATE = 0
	CLOSE_MACD_RATE = 3

	MA_value = 0
	MACD_DIFF = 0
	MACD_DEA = 0
	MACD_BAR = 0
	MACD_RATE = 0
	open_price = 0
	price_rate = 0

	intra_trade_high = 0
	intra_trade_low = 0
	long_stop = 0
	short_stop = 0

	long_vt_orderids = []
	short_vt_orderids = []
	vt_orderids = []

	parameters = ["long_trend",
	              "fixed_size",
	              "bar_time_length",
	              "MA_Windows",
	              "OPEN_MACD_RATE",
	              "CLOSE_MACD_RATE",
	              "fix_loss",
	              "triger_profit_1",
	              "triger_profit_2",
	              "triger_profit_3",
	              "triger_profit_4",
	              "move_loss_1",
	              "move_loss_2",
	              "move_loss_3",
	              "move_loss_4"
	              ]
	variables = ["MA_value",
	             "MACD_DIFF",
	             "MACD_DEA",
	             "MACD_BAR",
	             "open_price",
	             "price_rate",
	             "intra_trade_high",
	             "intra_trade_low",
	             "long_stop",
	             "short_stop"
	             ]

	def __init__(self, cta_engine, strategy_name, vt_symbol,vt_local, setting):
		""""""

		super().__init__(cta_engine, strategy_name, vt_symbol,vt_local, setting)

		self.bg = BarGenerator(self.on_bar, self.bar_time_length, self.on_time_bar)
		self.am = ArrayManager(self.MA_Windows + 50)

	def on_init(self):
		"""
        Callback when strategy is inited.
        """
		self.write_log("策略初始化")
		self.load_bar(20)
		self.OPEN_MACD_RATE = self.OPEN_MACD_RATE  * 0.01
		self.CLOSE_MACD_RATE = self.OPEN_MACD_RATE * 0.001

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

		self.bg.update_tick(tick)

	def calcuale_MACD_rate(self,DIFF_value, DEA_value):
		if DIFF_value >= DEA_value:
			rate =  abs((DIFF_value - DEA_value)/ DIFF_value)
		else:
			rate = -abs((DIFF_value - DEA_value)/DIFF_value)
		return rate


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

		self.MA_value = talib.SMA(local_close_array, self.MA_Windows)[-1]
		macd, signal, hist = talib.MACD(
			local_close_array, self.MACD_short, self.MACD_long, self.MACD_signal
		)
		self.MACD_DIFF = macd[-1]
		last_MACD_DIFF = macd[-2]
		self.MACD_DEA = signal[-1]
		self.MACD_BAR = hist[-1]
		self.MACD_RATE = self.calcuale_MACD_rate(self.MACD_DIFF,self.MACD_DEA)
		if self.pos == 0:
			self.intra_trade_high = bar.high_price
			self.intra_trade_low = bar.low_price

			self.open_price = 0

			self.price_rate = 0
			self.cancel_all()

			if bar.close_price > self.MA_value and self.MACD_RATE > self.OPEN_MACD_RATE and self.MACD_DIFF > last_MACD_DIFF and self.long_trend != -1:
				self.buy(bar.close_price + 2, self.fixed_size, False)
			elif bar.close_price < self.MA_value and self.MACD_RATE < -self.OPEN_MACD_RATE and self.MACD_DIFF < last_MACD_DIFF and self.long_trend != 1:
				self.short(bar.close_price - 2, self.fixed_size, False)

		elif self.pos > 0:
			if self.MACD_RATE < - self.CLOSE_MACD_RATE:
				self.cancel_all()
				self.sell(bar.close_price - 2, self.pos, False)
			else:
				self.intra_trade_high = max(self.intra_trade_high, bar.high_price)
				self.intra_trade_low = bar.low_price

				self.price_rate = (self.intra_trade_high - self.open_price) / self.open_price

				if self.price_rate < self.triger_profit_1:
					self.long_stop = self.open_price * (1 - self.fix_loss * 0.01)
				elif self.price_rate >= self.triger_profit_1 and self.price_rate < self.triger_profit_2:
					self.long_stop = self.intra_trade_high - self.open_price * self.move_loss_1 * 0.01
				elif self.price_rate >= self.triger_profit_2 and self.price_rate < self.triger_profit_3:
					self.long_stop = self.intra_trade_high - self.open_price * self.move_loss_2 * 0.01
				elif self.price_rate >= self.triger_profit_3 and self.price_rate < self.triger_profit_4:
					self.long_stop = self.intra_trade_high - self.open_price * self.move_loss_3 * 0.01
				elif self.price_rate >= self.triger_profit_4:
					self.long_stop = self.intra_trade_high - self.open_price * self.move_loss_4 * 0.01

				self.cancel_all()
				self.sell(self.long_stop, abs(self.pos), True)



		elif self.pos < 0:
			if self.MACD_RATE > self.CLOSE_MACD_RATE:
				self.cancel_all()
				self.cover(bar.close_price + 2, abs(self.pos), False)
			else:
				self.intra_trade_high = bar.high_price
				self.intra_trade_low = min(self.intra_trade_low, bar.low_price)

				self.price_rate = (self.open_price - self.intra_trade_low) / self.open_price

				if self.price_rate < self.triger_profit_1:
					self.short_stop = self.open_price * (1 + self.fix_loss * 0.01)
				elif self.price_rate >= self.triger_profit_1 and self.price_rate < self.triger_profit_2:
					self.short_stop = self.intra_trade_low + self.open_price * self.move_loss_1 * 0.01
				elif self.price_rate >= self.triger_profit_2 and self.price_rate < self.triger_profit_3:
					self.short_stop = self.intra_trade_low + self.open_price * self.move_loss_2 * 0.01
				elif self.price_rate >= self.triger_profit_3 and self.price_rate < self.triger_profit_4:
					self.short_stop = self.intra_trade_low + self.open_price * self.move_loss_3 * 0.01
				elif self.price_rate >= self.triger_profit_4:
					self.short_stop = self.intra_trade_low + self.open_price * self.move_loss_4 * 0.01

				self.cancel_all()
				self.cover(self.short_stop, abs(self.pos), True)

		self.bg.update_bar(bar)

	def on_time_bar(self, bar: BarData):
		am = self.am
		am.update_bar(bar)
		if not am.inited:
			return
		self.MA_value = am.sma(self.MA_Windows, False)

		macd, signal, hist = am.macd(self.MACD_short, self.MACD_long, self.MACD_signal, True)
		self.MACD_DIFF = macd[-1]
		last_MACD_DIFF = macd[-2]
		self.MACD_DEA = signal[-1]
		self.MACD_BAR = hist[-1]
		self.MACD_RATE = self.calcuale_MACD_rate(self.MACD_DIFF, self.MACD_DEA)
		if self.pos == 0:
			self.cancel_all()
			if bar.close_price > self.MA_value and self.MACD_RATE > self.OPEN_MACD_RATE and self.MACD_DIFF > last_MACD_DIFF and self.long_trend != -1:
				self.buy(bar.close_price + 2, self.fixed_size, False)
			elif bar.close_price < self.MA_value and self.MACD_RATE < -self.OPEN_MACD_RATE and self.MACD_DIFF < last_MACD_DIFF and self.long_trend != 1:
				self.short(bar.close_price - 2, self.fixed_size, False)
		elif self.pos > 0 and self.MACD_RATE < - self.CLOSE_MACD_RATE:
			self.cancel_all()
			self.sell(bar.close_price - 2, self.pos, False)

		elif self.pos < 0 and self.MACD_RATE > self.CLOSE_MACD_RATE:
			self.cancel_all()
			self.cover(bar.close_price + 2, abs(self.pos), False)

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
			self.open_price = trade.price
		self.put_event()

	def on_stop_order(self, stop_order: StopOrder):
		"""
        Callback of stop order update.
        """
		pass
