""""""
from abc import ABC
from copy import copy
from typing import Any, Callable

from vnpy.trader.constant import Interval, Direction, Offset
from vnpy.trader.object import BarData, TickData, OrderData, TradeData
from vnpy.trader.utility import virtual
from datetime import datetime
from .base import StopOrder, EngineType
from vnpy.trader.utility import load_json
from vnpy.trader.database import database_manager,DB_TZ


class CtaTemplate(ABC):
    """"""

    author = ""
    inside_setting_filename = "cta_strategy_inside_setting.json"
    current_balRatio = 0.6
    interval_balRatio = 0.2
    next_up_profit = 2.0
    next_down_profit = 0.3
    # JiaoYiKongzhi_setting_filename = "JiaoYiKongzhi_setting.json"
    parameters = ["up_profit","down_profit"]
    variables = []

    def __init__(
        self,
        cta_engine: Any,
        strategy_name: str,
        vt_symbol: str,
        vt_local = 0,
        setting = {}
    ):
        """"""
        self.cta_engine = cta_engine
        self.strategy_name = strategy_name
        self.vt_symbol = vt_symbol
        self.vt_local = vt_local

        self.inited = False
        self.trading = False
        self.pos = 0
        self.PosPrice = 0
        self.LastPrice = 0
        self.LastOrderId = ""

        # Copy a new variables list here to avoid duplicate insert when multiple
        # strategy instances are created with the same strategy class.
        self.variables = copy(self.variables)
        self.variables.insert(0, "inited")
        self.variables.insert(1, "trading")
        self.variables.insert(2, "pos")
        self.variables.insert(4, "PosPrice")
        self.variables.insert(5, "LastPrice")
        self.canshuDict = load_json(self.inside_setting_filename)
        # self.stop_open_symbols = load_json(self.JiaoYiKongzhi_setting_filename)["Stop_Open_Symbols"]
        self.parameters = copy(self.parameters)
        self.parameters.extend(["next_up_profit","next_down_profit"])
        self.update_setting(setting)

    def update_setting(self, setting: dict):
        """
        Update strategy parameter wtih value in setting dict.
        """
        for name in self.parameters:
            if name in setting:
                setattr(self, name, setting[name])

    def sync_setting(self,strategy_name,setting):
        self.cta_engine.update_strategy_setting(strategy_name,setting)

    @classmethod
    def get_class_parameters(cls):
        """
        Get default parameters dict of strategy class.
        """
        class_parameters = {}
        for name in cls.parameters:
            class_parameters[name] = getattr(cls, name)
        return class_parameters

    def calculation_fixedSize(self):
        """
        only works for the strategy with parameters HeYueJiaZhi interval_balRatio HeYueChengShu
        :param up:
        :param down:
        :return:
        """


        contract = self.cta_engine.main_engine.get_contract(self.vt_symbol)
        if contract:
            self.fixed_size = max(0, int(self.current_HeYueJiaZhi * self.current_balRatio / (
                        self.LastPrice * 1.05 * self.HeYueChengShu * contract.LongMarginRatioByMoney)))

    def get_parameters(self):
        """
        Get strategy parameters dict.
        """
        strategy_parameters = {}
        for name in self.parameters:
            strategy_parameters[name] = getattr(self, name)
        return strategy_parameters

    def get_variables(self):
        """
        Get strategy variables dict.
        """
        strategy_variables = {}
        for name in self.variables:
            strategy_variables[name] = getattr(self, name)
        return strategy_variables

    def get_data(self):
        """
        Get strategy data.
        """
        strategy_data = {
            "strategy_name": self.strategy_name,
            "vt_symbol": self.vt_symbol,
            "vt_local":self.vt_local,
            "class_name": self.__class__.__name__,
            "author": self.author,
            "parameters": self.get_parameters(),
            "variables": self.get_variables(),
        }
        return strategy_data

    @virtual
    def on_init(self):
        """
        Callback when strategy is inited.
        """
        pass

    @virtual
    def on_start(self):
        """
        Callback when strategy is started.
        """
        pass

    @virtual
    def on_stop(self):
        """
        Callback when strategy is stopped.
        """
        pass

    @virtual
    def on_tick(self, tick: TickData):
        """
        Callback of new tick data update.
        """
        pass

    @virtual
    def on_bar(self, bar: BarData):
        """
        Callback of new bar data update.
        """
        pass

    @virtual
    def on_trade(self, trade: TradeData):
        """
        Callback of new trade data update.
        """
        pass
    #Billy Add

    def on_completed_order(self,on_completed_order):
        # update setting

        # 取stop_order 成交的价格
        self.entry_price = on_completed_order.average_price

        if on_completed_order.offset == Offset.CLOSE:
            if on_completed_order.direction == Direction.SHORT:
                lastDeal = (on_completed_order.average_price - self.init_entry_price) * 100.0 / self.init_entry_price
                self.current_HeYueJiaZhi = self.current_HeYueJiaZhi + (
                            on_completed_order.average_price - self.init_entry_price) * self.HeYueChengShu * self.init_pos
            elif on_completed_order.direction == Direction.LONG:
                lastDeal = (self.init_entry_price - on_completed_order.price) * 100.0 / self.init_entry_price
                self.current_HeYueJiaZhi = self.current_HeYueJiaZhi + (
                             on_completed_order.average_price - self.init_entry_price) * self.init_pos * self.HeYueChengShu

            if lastDeal > self.next_up_profit:
                self.current_balRatio = self.interval_balRatio
            elif lastDeal < -self.next_down_profit:
                self.current_balRatio = min(self.current_balRatio + self.interval_balRatio, 1.4)
            self.calculation_fixedSize()
        self.save_setting_file()

    def on_cta_trade(self, cta_trade: TradeData):

        self.write_log(f"{cta_trade.direction}数量{cta_trade.volume}: 价格{cta_trade.price}; 策略持仓{self.pos}: 价格{self.entry_price}")
        # 如果持仓为空，价格为空
        if self.pos == 0:
            self.entry_price = 0.0
        self.PosPrice = self.entry_price
        # # Sync strategy setting to setting file
        # setting = self.get_parameters()
        # setting['init_pos'] = self.pos
        # setting['init_entry_price'] = self.entry_price
        # # self.update_setting(setting)
        # self.sync_setting(self.strategy_name, setting)


        # saving to db
        cta_trade.strategy = self.strategy_name
        cta_trade.date = datetime.now().strftime("%Y%m%d")
        timestamp: str = f"{cta_trade.date} {cta_trade.datetime.strftime('%H:%M:%S')}"
        cta_trade.datetime = datetime.strptime(timestamp, "%Y%m%d %H:%M:%S")
        cta_trade.date = DB_TZ.localize(datetime.strptime(cta_trade.date, "%Y%m%d"))
        cta_trade.datetime = DB_TZ.localize(cta_trade.datetime)
        database_manager.save_cta_trade_data(copy(cta_trade))
        self.cta_engine.put_cta_trade_event(cta_trade)

    def save_setting_file(self):
        # Sync strategy setting to setting file
        setting = self.get_parameters()
        setting['init_pos'] = self.pos
        setting['init_entry_price'] = self.entry_price
        setting['current_balRatio'] = self.current_balRatio
        setting['current_HeYueJiaZhi'] = self.current_HeYueJiaZhi
        self.update_setting(setting)
        self.sync_setting(self.strategy_name, setting)
        self.put_event()
        # self.cta_engine.put_strategy_event(self)

    # End Billy add

    @virtual
    def on_order(self, order: OrderData):
        """
        Callback of new order data update.
        """
        pass

    @virtual
    def on_stop_order(self, stop_order: StopOrder):
        """
        Callback of stop order update.
        """
        pass

    def buy(
        self,
        price: float,
        volume: float,
        stop: bool = False,
        lock: bool = False,
        net: bool = False
    ):
        """
        Send buy order to open a long position.
        """
        return self.send_order(
            Direction.LONG,
            Offset.OPEN,
            price,
            volume,
            stop,
            lock,
            net
        )

    def sell(
        self,
        price: float,
        volume: float,
        stop: bool = False,
        lock: bool = False,
        net: bool = False
    ):
        """
        Send sell order to close a long position.
        """
        return self.send_order(
            Direction.SHORT,
            Offset.CLOSE,
            price,
            volume,
            stop,
            lock,
            net
        )

    def short(
        self,
        price: float,
        volume: float,
        stop: bool = False,
        lock: bool = False,
        net: bool = False
    ):
        """
        Send short order to open as short position.
        """
        return self.send_order(
            Direction.SHORT,
            Offset.OPEN,
            price,
            volume,
            stop,
            lock,
            net
        )

    def cover(
        self,
        price: float,
        volume: float,
        stop: bool = False,
        lock: bool = False,
        net: bool = False
    ):
        """
        Send cover order to close a short position.
        """
        return self.send_order(
            Direction.LONG,
            Offset.CLOSE,
            price,
            volume,
            stop,
            lock,
            net
        )

    def send_order(
        self,
        direction: Direction,
        offset: Offset,
        price: float,
        volume: float,
        stop: bool = False,
        lock: bool = False,
        net: bool = False
    ):
        """
        Send a new order.
        """
        if self.trading:
            # Billy added, 如果是在停止开单合约中，并且是开单请求，返回为空队列
            # if self.vt_symbol in self.stop_open_symbols and offset == Offset.OPEN:
            #     return []
            # End Billy added
            vt_orderids = self.cta_engine.send_order(
                self, direction, offset, price, volume, stop, lock, net
            )
            return vt_orderids
        else:
            return []

    def cancel_order(self, vt_orderid: str):
        """
        Cancel an existing order.
        """
        if self.trading:
            return self.cta_engine.cancel_order(self, vt_orderid)

    def cancel_all(self):
        """
        Cancel all orders sent by strategy.
        """
        if self.trading:
            return self.cta_engine.cancel_all(self)

    def write_log(self, msg: str):
        """
        Write a log message.
        """
        self.cta_engine.write_log(msg, self)

    def get_engine_type(self):
        """
        Return whether the cta_engine is backtesting or live trading.
        """
        return self.cta_engine.get_engine_type()

    def get_pricetick(self):
        """
        Return pricetick data of trading contract.
        """
        return self.cta_engine.get_pricetick(self)

    def load_bar(
        self,
        days: int,
        interval: Interval = Interval.MINUTE,
        callback: Callable = None,
        use_database: bool = False
    ):
        """
        Load historical bar data for initializing strategy.
        """
        if not callback:
            callback = self.on_bar

        self.cta_engine.load_bar(
            self.vt_symbol,
            days,
            interval,
            callback,
            use_database
        )

    def load_tick(self, days: int):
        """
        Load historical tick data for initializing strategy.
        """
        self.cta_engine.load_tick(self.vt_symbol, days, self.on_tick)

    def put_event(self):
        """
        Put an strategy data event for ui update.
        """
        if self.inited:
            self.cta_engine.put_strategy_event(self)

    def send_email(self, msg):
        """
        Send email to default receiver.
        """
        if self.inited:
            self.cta_engine.send_email(msg, self)

    def sync_data(self):
        """
        Sync strategy variables value into disk storage.
        """
        if self.trading:
            self.cta_engine.sync_strategy_data(self)


class CtaSignal(ABC):
    """"""

    def __init__(self):
        """"""
        self.signal_pos = 0

    @virtual
    def on_tick(self, tick: TickData):
        """
        Callback of new tick data update.
        """
        pass

    @virtual
    def on_bar(self, bar: BarData):
        """
        Callback of new bar data update.
        """
        pass

    def set_signal_pos(self, pos):
        """"""
        self.signal_pos = pos

    def get_signal_pos(self):
        """"""

        return self.signal_pos


class TargetPosTemplate(CtaTemplate):
    """"""
    tick_add = 1

    last_tick = None
    last_bar = None
    target_pos = 0

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        self.active_orderids = []
        self.cancel_orderids = []

        self.variables.append("target_pos")

    @virtual
    def on_tick(self, tick: TickData):
        """
        Callback of new tick data update.
        """
        self.last_tick = tick

        if self.trading:
            self.trade()

    @virtual
    def on_bar(self, bar: BarData):
        """
        Callback of new bar data update.
        """
        self.last_bar = bar

    @virtual
    def on_order(self, order: OrderData):
        """
        Callback of new order data update.
        """
        vt_orderid = order.vt_orderid

        if not order.is_active():
            if vt_orderid in self.active_orderids:
                self.active_orderids.remove(vt_orderid)

            if vt_orderid in self.cancel_orderids:
                self.cancel_orderids.remove(vt_orderid)

    def check_order_finished(self):
        """"""
        if self.active_orderids:
            return False
        else:
            return True

    def set_target_pos(self, target_pos):
        """"""
        self.target_pos = target_pos
        self.trade()

    def trade(self):
        """"""
        if not self.check_order_finished():
            self.cancel_old_order()
        else:
            self.send_new_order()

    def cancel_old_order(self):
        """"""
        for vt_orderid in self.active_orderids:
            if vt_orderid not in self.cancel_orderids:
                self.cancel_order(vt_orderid)
                self.cancel_orderids.append(vt_orderid)

    def send_new_order(self):
        """"""
        pos_change = self.target_pos - self.pos
        if not pos_change:
            return

        long_price = 0
        short_price = 0

        if self.last_tick:
            if pos_change > 0:
                long_price = self.last_tick.ask_price_1 + self.tick_add
                if self.last_tick.limit_up:
                    long_price = min(long_price, self.last_tick.limit_up)
            else:
                short_price = self.last_tick.bid_price_1 - self.tick_add
                if self.last_tick.limit_down:
                    short_price = max(short_price, self.last_tick.limit_down)

        else:
            if pos_change > 0:
                long_price = self.last_bar.close_price + self.tick_add
            else:
                short_price = self.last_bar.close_price - self.tick_add

        if self.get_engine_type() == EngineType.BACKTESTING:
            if pos_change > 0:
                vt_orderids = self.buy(long_price, abs(pos_change))
            else:
                vt_orderids = self.short(short_price, abs(pos_change))
            self.active_orderids.extend(vt_orderids)

        else:
            if self.active_orderids:
                return

            if pos_change > 0:
                if self.pos < 0:
                    if pos_change < abs(self.pos):
                        vt_orderids = self.cover(long_price, pos_change)
                    else:
                        vt_orderids = self.cover(long_price, abs(self.pos))
                else:
                    vt_orderids = self.buy(long_price, abs(pos_change))
            else:
                if self.pos > 0:
                    if abs(pos_change) < self.pos:
                        vt_orderids = self.sell(short_price, abs(pos_change))
                    else:
                        vt_orderids = self.sell(short_price, abs(self.pos))
                else:
                    vt_orderids = self.short(short_price, abs(pos_change))
            self.active_orderids.extend(vt_orderids)