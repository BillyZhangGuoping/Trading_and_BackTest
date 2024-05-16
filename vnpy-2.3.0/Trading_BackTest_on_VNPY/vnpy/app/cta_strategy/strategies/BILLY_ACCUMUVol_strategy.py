from datetime import time
import numpy as np
from vnpy.trader.object import Offset
from collections import defaultdict

from vnpy.app.cta_strategy import (
	CtaTemplate,
	StopOrder,
	TickData,
	BarData,
	TradeData,
	OrderData
)


class BILLY_ACCUMUVolStrategy(CtaTemplate):
	""""""
	author = "Billy"
	fixed_size = 1
	AskBidRatioLimit = 3
	VolListLength = 60
	Markup = 10
	MarkDown = 6
	VolLimit = 60
	OPILimit = 0
	divcount =12000
	VolLimitSum = 121
	KeyPrice = 0

	AskBidRatio = 0
	VolIndictor = 0
	Volsum = 0
	buy_algoid = []
	sell_algoid = []
	short_algoid = []
	cover_algoid = []

	parameters = ["fixed_size", "VolListLength", "AskBidRatioLimit",  "Markup","VolLimit", "divcount",
	              "MarkDown"]
	variables = ["KeyPrice", "VolLimitSum", "OPILimit", "AskBidRatio", "Volsum", "VolIndictor", "buy_algoid", "short_algoid"]

	def __init__(self, cta_engine, strategy_name, vt_symbol,vt_local, setting):
		""""""
		super(BILLY_ACCUMUVolStrategy, self).__init__(
			cta_engine, strategy_name, vt_symbol,vt_local, setting
		)

		self.start_timePM = time(hour=9, minute=10)
		self.start_timeAM = time(hour=13, minute=35)
		self.start_timeNI = time(hour=21, minute=10)

		self.exit_timePM = time(hour=11, minute=25)
		self.exit_timeAM = time(hour=14, minute=50)
		self.exit_timeNI = time(hour=2, minute=50)

		self.VolList = np.zeros(self.VolListLength)
		self.PosOPintList = np.zeros(self.VolListLength)
		self.NegOPintList = np.zeros(self.VolListLength)
		self.PriceList = np.zeros(self.VolListLength)
		self.last_tick = None

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
		if not self.last_tick:
			self.last_tick = tick
			self.OPILimit = int(tick.open_interest*self.VolListLength*0.1 / self.divcount)
			self.VolLimitSum = int(self.OPILimit *self.VolListLength / 2.8)
			return
		else:
			self.VolList[0:self.VolListLength - 1] = self.VolList[1:self.VolListLength]
			self.NegOPintList[0:self.VolListLength - 1] = self.NegOPintList[1:self.VolListLength]
			self.PosOPintList[0:self.VolListLength - 1] = self.PosOPintList[1:self.VolListLength]
			self.PriceList[0:self.VolListLength - 1] = self.PriceList[1:self.VolListLength]
			VolDiff = tick.volume - self.last_tick.volume
			self.PriceList[-1] = tick.last_price - self.last_tick.last_price
			if VolDiff > self.VolLimit:
				OPint = tick.open_interest - self.last_tick.open_interest
				if tick.last_price >= self.last_tick.ask_price_1:
					self.VolList[-1] = VolDiff
					if OPint > 0:
						self.PosOPintList[-1] = OPint
						self.NegOPintList[-1] = 0
					elif OPint < 0:
						self.PosOPintList[-1] = 0
						self.NegOPintList[-1] = OPint

				elif tick.last_price <= self.last_tick.bid_price_1:
					self.VolList[-1] = -VolDiff
					if OPint > 0:
						self.PosOPintList[-1] = 0
						self.NegOPintList[-1] = OPint
					elif OPint < 0:
						self.PosOPintList[-1] = OPint
						self.NegOPintList[-1] = 0
				else:
					self.VolList[-1] = 0
					self.PosOPintList[-1] = 0
					self.NegOPintList[-1] = 0
			else:
				self.VolList[-1] = 0
				self.PosOPintList[-1] = 0
				self.NegOPintList[-1] = 0


		if (tick.datetime.time() > self.start_timePM and tick.datetime.time() < self.exit_timeAM) or (
				tick.datetime.time() > self.start_timeNI or tick.datetime.time() < self.exit_timeNI):
			if self.pos == 0:
				self.cancel_all()
				self.Volsum = sum(self.VolList)
				if self.Volsum > self.VolLimitSum and sum(self.PosOPintList) > self.OPILimit and sum(self.PriceList[-6:])>3 and tick.bid_volume_1 > self.AskBidRatioLimit *tick.ask_volume_1:
					self.buy_algoid = self.buy(tick.ask_price_1, self.fixed_size, False)
				elif self.Volsum < -self.VolLimitSum and sum(self.NegOPintList) > self.OPILimit and sum(self.PriceList[-6:])<-3 and tick.ask_volume_1 > self.AskBidRatioLimit *tick.bid_volume_1:
					self.short_algoid = self.short(tick.bid_price_1, self.fixed_size, False)

			elif self.pos > 0:
				if tick.last_price <= self.KeyPrice - self.MarkDown:
					self.cancel_all()
					self.sell(tick.bid_price_1, abs(self.pos), stop=False)
			else:
				if tick.last_price >= self.KeyPrice + self.MarkDown:
					self.cancel_all()
					self.cover(tick.ask_price_1, abs(self.pos), stop=False)
		else:
			if self.pos == 0:
				return
			elif self.pos > 0:
				self.cancel_all()
				self.sell(tick.bid_price_1, abs(self.pos), stop=False)
			else:
				self.cancel_all()
				self.cover(tick.ask_price_1, abs(self.pos), stop=False)
		self.last_tick = tick
		self.put_event()

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
			self.cancel_all()
			self.VolList = np.zeros(self.VolListLength)
			self.PosPrice = trade.price
			self.KeyPrice = self.PosPrice
			if self.pos > 0:
				self.sell(self.KeyPrice + self.Markup, self.pos)
			else:
				self.cover(self.KeyPrice - self.Markup, abs(self.pos))
		self.put_event()

	def on_stop_order(self, stop_order: StopOrder):
		"""
        Callback of stop order update.
        """
		pass