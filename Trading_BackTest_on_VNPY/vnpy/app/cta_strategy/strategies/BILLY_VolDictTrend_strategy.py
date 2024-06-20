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


class BILLY_VolDictTrendStrategy(CtaTemplate):
	""""""
	author = "Billy"
	fixed_size = 1
	AskBidRatioLimit = 5
	VolListLength = 15
	Markup = 2
	MarkDown = 3
	tickVolLimit = 3
	VolLimit = 121
	OPILimit = 0

	PosPrice = 0
	OPIntRatio = 0
	AskBidRatio = 0
	VolIndictor = 0
	Volsum = 0
	buy_algoid = []
	sell_algoid = []
	short_algoid = []
	cover_algoid = []

	parameters = ["fixed_size", "VolLimit", "tickVolLimit", "VolListLength", "AskBidRatioLimit", "OPILimit", "Markup",
	              "MarkDown"]
	variables = ["PosPrice", "OPIntRatio", "AskBidRatio", "Volsum", "VolIndictor", "buy_algoid", "short_algoid"]

	def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
		""""""
		super(BILLY_VolDictTrendStrategy, self).__init__(
			cta_engine, strategy_name, vt_symbol, setting
		)

		self.start_timePM = time(hour=9, minute=10)
		self.start_timeAM = time(hour=13, minute=35)
		self.start_timeNI = time(hour=21, minute=10)

		self.exit_timePM = time(hour=11, minute=25)
		self.exit_timeAM = time(hour=14, minute=50)
		self.exit_timeNI = time(hour=2, minute=50)

		self.VolList = np.zeros(self.VolListLength)
		self.NetVolList = np.zeros(self.VolListLength)
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
			return
		else:
			if tick.volume - self.last_tick.volume > self.VolLimit:
				if tick.last_price >= self.last_tick.ask_price_1:
					self.VolIndictor = 1
				elif tick.last_price <= self.last_tick.bid_price_1:
					self.VolIndictor = -1
				else:
					self.VolIndictor = 0
			else:
				self.VolIndictor = 0
		self.VolList[0:self.VolListLength - 1] = self.VolList[1:self.VolListLength]
		self.VolList[-1] = self.VolIndictor

		self.NetVolList[0:self.VolListLength - 1] = self.NetVolList[1:self.VolListLength]
		if  tick.open_interest - self.last_tick.open_interest > self.OPILimit:
			self.NetVolList[-1] = self.VolIndictor
		else:
			self.NetVolList[-1] = 0

		if (tick.datetime.time() > self.start_timePM and tick.datetime.time() < self.exit_timeAM) or (
				tick.datetime.time() > self.start_timeNI or tick.datetime.time() < self.exit_timeNI):
			if self.pos == 0:
				self.cancel_all()
				self.Volsum = sum(self.NetVolList)
				if self.Volsum >= self.tickVolLimit and (not -1 in self.VolList) and tick.last_price >= self.last_tick.ask_price_1 and tick.bid_volume_1 > self.AskBidRatioLimit * tick.ask_volume_1:
					self.buy_algoid = self.buy(tick.ask_price_1, self.fixed_size, False)
				elif self.Volsum <= -self.tickVolLimit and (not 1 in self.VolList) and tick.last_price <= self.last_tick.bid_price_1 and tick.ask_volume_1 > self.AskBidRatioLimit * tick.bid_volume_1:
					self.short_algoid = self.short(tick.bid_price_1, self.fixed_size, False)

			elif self.pos > 0:
				if tick.last_price <= self.PosPrice - self.MarkDown:
					self.cancel_all()
					self.sell(tick.bid_price_1, abs(self.pos), stop=False)
			else:
				if tick.last_price >= self.PosPrice + self.MarkDown:
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
			self.PosPrice = trade.price
			if self.pos > 0:
				self.sell(self.PosPrice + max(self.Markup, self.Volsum), self.pos)
			else:
				self.cover(self.PosPrice - max(self.Markup, abs(self.Volsum)), abs(self.pos))
		self.put_event()

	def on_stop_order(self, stop_order: StopOrder):
		"""
        Callback of stop order update.
        """
		pass