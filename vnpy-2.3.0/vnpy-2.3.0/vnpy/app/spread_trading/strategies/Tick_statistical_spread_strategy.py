from vnpy.trader.utility import BarGenerator, ArrayManager
from datetime import datetime, time
from scipy import stats
from vnpy.trader.utility import round_to
import numpy as np
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


class TickStatisticalSpreadStrategy(SpreadStrategyTemplate):
	""""""

	author = "BILLY"

	max_pos = 1
	payup = 1
	interval = 30
	check_Ratio = 0.3
	Range = 2000
	timeslot = 20

	spread_pos = 0.0
	boll_up = 0.0
	boll_down = 0.0
	boll_mid = 0.0

	buy_price = 0.0
	sell_price = 0.0
	cover_price = 0.0
	short_price = 0.0
	std = 0.0
	start_indictor = False

	update_time = None
	buy_algoid = ""
	sell_algoid = ""
	short_algoid = ""
	cover_algoid = ""
	priceSlip = 0
	PosPrice = 0

	parameters = [
		"check_Ratio",
		"max_pos",
		"payup",
		"interval",
		"Range",
		"timeslot"
	]
	variables = [
		"spread_pos",
		"PosPrice",
		"std",
		"boll_mid",
		"buy_price",
		"sell_price",
		"cover_price",
		"short_price",
		"update_time",
		"priceSlip",
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
		self.exit_timeNI = time(hour=2, minute=50)

		self.priceList = np.zeros(self.Range)
		self.PosPrice = 0.0
		self.N = self.Range + 10
		self.Ncount = 0
		self.act_sell_price = 0
		self.act_cover_price = 0
		self.distance = 0
		self.priceSlip = 0
		self.priceSlipInit = False

	def on_init(self):
		"""
        Callback when strategy is inited.
        """
		self.write_log("策略初始化")
		self.localPriceTick = self.getSymbolSize()

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
		self.priceList[0:self.Range - 1] = self.priceList[1:self.Range]
		self.priceList[-1] = (self.spread.ask_price + self.spread.bid_price) / 2
		if self.Ncount <= self.N:
			self.Ncount += 1
			return

		self.update_time = self.spread.datetime.time()
		self.spread_pos = self.get_spread_pos()
		if not ((self.update_time > self.start_timePM and self.update_time < self.exit_timeAM) or (
				self.update_time > self.start_timeNI or self.update_time < self.exit_timeNI)):
			if self.spread_pos != 0:
				# Go through all legs to calculate price
				for n, leg in enumerate(self.spread.legs.values()):
					if leg.net_pos > 0:
						self.sell(leg.vt_symbol, leg.bid_price, abs(leg.net_pos), False)
					elif leg.net_pos < 0:
						self.cover(leg.vt_symbol, leg.ask_price, abs(leg.net_pos), False)
			else:
				self.stop_open_algos()
				self.stop_close_algos()
			self.put_event()
			return

		if self.update_time.minute % self.timeslot == 0 and self.update_time.second == 1:
			self.boll_mid = np.average(self.priceList)
			self.std = np.std(self.priceList) * 2
			if self.std >= self.check_Ratio:
				self.distance = self.localPriceTick * round(self.std)
				self.boll_mid = round_to(self.boll_mid, self.localPriceTick)
				self.buy_price = self.boll_mid - self.distance
				self.sell_price = self.boll_mid
				self.cover_price = self.boll_mid
				self.short_price = self.boll_mid + self.distance
				self.start_indictor = True
			elif self.spread_pos != 0:
				self.boll_mid = round_to(self.boll_mid, self.localPriceTick)
				# self.buy_price = self.boll_mid - distance
				self.sell_price = self.boll_mid
				self.cover_price = self.boll_mid
				# self.short_price = self.boll_mid + distance
				self.start_indictor = False
			else:
				self.start_indictor = False

		# No position
		if self.spread_pos == 0.0 and self.update_time.second == 30:
			self.stop_close_algos()
			self.PosPrice = 0.0
			self.priceSlip = 0
			self.priceSlipInit = False
			# Start open algos

			if self.start_indictor == True and (not self.buy_algoid):
				self.buy_algoid = self.start_long_algo(
					self.buy_price, self.max_pos, self.payup, self.interval
				)

			if self.start_indictor == True and (not self.short_algoid):
				self.short_algoid = self.start_short_algo(
					self.short_price, self.max_pos, self.payup, self.interval
				)

		# Long position
		elif self.spread_pos > 0:
			self.stop_open_algos()

			# Start sell close algo
			if not self.sell_algoid:
				if (not self.priceSlipInit) and self.PosPrice != 0:
					self.priceSlip = self.PosPrice - self.buy_price
					self.priceSlipInit = True
				self.act_sell_price = self.sell_price + self.priceSlip
				self.sell_algoid = self.start_short_algo(
					self.act_sell_price, self.spread_pos, self.payup, self.interval
				)
			# elif self.act_sell_price  > self.sell_price +  self.priceSlip:
			#     self.stop_close_algos()


		# Short position
		elif self.spread_pos < 0:
			self.stop_open_algos()

			# Start cover close algo
			if not self.cover_algoid:
				if (not self.priceSlipInit) and self.PosPrice != 0:
					self.priceSlip = self.short_price - self.PosPrice
					self.priceSlipInit = True
				self.act_cover_price = self.cover_price - self.priceSlip
				self.cover_algoid = self.start_long_algo(
					self.act_cover_price, abs(
						self.spread_pos), self.payup, self.interval
				)
			# elif self.act_cover_price < self.cover_price - self.priceSlip:
			#     self.stop_close_algos()

		self.put_event()

	def on_spread_tick(self, tick: TickData):
		"""
        Callback when new spread tick data is generated.
        """
		pass

	def on_spread_bar(self, bar: BarData):
		"""
        Callback when spread bar data is generated.
        """

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
