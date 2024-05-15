""""""

import importlib
import os
import traceback
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from copy import copy
from tzlocal import get_localzone
from datetime import datetime, time
from pandas import DataFrame
from vnpy.event import Event, EventEngine
from vnpy.trader.engine import BaseEngine, MainEngine
from vnpy.trader.object import (
    OrderRequest,
    SubscribeRequest,
    HistoryRequest,
    LogData,
    TickData,
    BarData,
    ContractData
)

from vnpy.trader.event import (
    EVENT_TICK,
    EVENT_ORDER,
    EVENT_TRADE,
    EVENT_POSITION,
    EVENT_ACCOUNT
)
from vnpy.trader.constant import (
    Direction,
    OrderType,
    Interval,
    Exchange,
    Offset,
    Status
)
from vnpy.trader.utility import load_json, save_json, extract_vt_symbol, round_to, get_folder_path
from vnpy.trader.setting import SETTINGS
from vnpy.trader.mddata import mddata_client
from vnpy.trader.converter import OffsetConverter
from vnpy.trader.database import database_manager

from .base import (
    APP_NAME,
    EVENT_CTA_LOG,
    EVENT_CTA_STRATEGY,
    EVENT_CTA_STOPORDER,
    EVENT_CTA_TRADE,
    EVENT_CTA_TRIGGERED_STOPORDER,
    EngineType,
    StopOrder,
    StopOrderStatus,
    STOPORDER_PREFIX
)
from .template import CtaTemplate

STOP_STATUS_MAP = {
    Status.SUBMITTING: StopOrderStatus.WAITING,
    Status.NOTTRADED: StopOrderStatus.WAITING,
    Status.PARTTRADED: StopOrderStatus.TRIGGERED,
    Status.ALLTRADED: StopOrderStatus.TRIGGERED,
    Status.CANCELLED: StopOrderStatus.CANCELLED,
    Status.REJECTED: StopOrderStatus.CANCELLED
}

LOCAL_TZ = get_localzone()


class CtaEngine(BaseEngine):
    """"""

    engine_type = EngineType.LIVE  # live trading engine

    setting_filename = "cta_strategy_setting.json"
    data_filename = "cta_strategy_data.json"
    commodities_filename = "cta_commodities.json"

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine):
        """"""
        super(CtaEngine, self).__init__(
            main_engine, event_engine, APP_NAME)

        self.strategy_setting = {}  # strategy_name: dict
        self.strategy_data = {}  # strategy_name: dict
        self.symbol_attr = {} # symbol_name: dict

        self.classes = {}  # class_name: stategy_class
        self.strategies = {}  # strategy_name: strategy

        self.symbol_strategy_map = defaultdict(
            list)  # vt_symbol: strategy list
        self.orderid_strategy_map = {}  # vt_orderid: strategy
        self.strategy_orderid_map = defaultdict(
            set)  # strategy_name: orderid list

        self.stop_order_count = 0  # for generating stop_orderid
        self.stop_orders = {}  # stop_orderid: stop_order

        self.symbol_time = {}

        # Billy added
        self.triggered_stop_orders = {}
        self.vt_orderid_triggered_stop_order = {}
        # End Billy added

        self.init_executor = ThreadPoolExecutor(max_workers=1)

        self.rq_client = None
        self.rq_symbols = set()

        self.vt_tradeids = set()  # for filtering duplicate trade

        self.offset_converter = OffsetConverter(self.main_engine)

        self.day_trade_time = False
        if time(hour=16) > datetime.now().time() > time(hour = 3):
            self.day_trade_time = True

        self.CurrMarginPrecent = 0
        self.main_engine.add_method_sched(self.daily_strategy_setting_backup)

    def init_engine(self):
        """
        """
        self.init_rqdata()
        self.load_symbol_attr()
        self.load_strategy_class()
        self.load_strategy_setting()
        self.load_strategy_data()
        self.register_event()
        self.write_log("CTA策略引擎初始化成功")

    def close(self):
        """"""
        self.stop_all_strategies()

    def register_event(self):
        """"""
        self.event_engine.register(EVENT_TICK, self.process_tick_event)
        self.event_engine.register(EVENT_ORDER, self.process_order_event)
        self.event_engine.register(EVENT_TRADE, self.process_trade_event)
        self.event_engine.register(EVENT_POSITION, self.process_position_event)
        self.event_engine.register(EVENT_ACCOUNT,self.process_account_event)

    def init_rqdata(self):
        """
        Init RQData client.
        """
        result = mddata_client.init()
        md_data_api = SETTINGS["mddata.api"]
        if result:
            self.write_log(f"{md_data_api}数据接口初始化成功")

    def query_bar_from_rq(
            self, symbol: str, exchange: Exchange, interval: Interval, start: datetime, end: datetime
    ):
        """
        Query bar data from RQData.
        """

        req = HistoryRequest(
            symbol=symbol,
            exchange=exchange,
            interval=interval,
            start=start,
            end=end
        )
        bar_start = None
        bar_end = None
        bar_overview_list = database_manager.get_bar_overview()
        for bar_overview in bar_overview_list:
            if bar_overview.symbol == symbol and bar_overview.exchange == exchange and bar_overview.interval == interval:
                bar_start = bar_overview.start.astimezone(LOCAL_TZ)
                bar_end = bar_overview.end.astimezone(LOCAL_TZ)
                if bar_start <= start:
                    req = HistoryRequest(
                        symbol=symbol,
                        exchange=exchange,
                        interval=interval,
                        start=bar_end + timedelta(minutes=2),
                        end=end + timedelta(minutes=1)
                    )

        data = mddata_client.query_history(req)
        if data:
            database_manager.save_bar_data(data)
            if bar_end:
                self.write_log(f"{symbol}，数据库已有 {self.convertTime(bar_start)} 到 {bar_end}数据，从 {self.convertTime(bar_end + timedelta(minutes=1))} 到{self.convertTime(end)}历史数据下载完成")
            else:
                self.write_log(
                    f"{symbol}，从 {self.convertTime(start)} 到{self.convertTime(end)}历史数据下载完成")
        else:
            if bar_end:
                self.write_log(
                    f"{symbol}，数据库已有 {self.convertTime(bar_start)} 到 {self.convertTime(bar_end)}数据，从 {self.convertTime(bar_end + timedelta(minutes=1))} 到{self.convertTime(end)}或无历史数据")
            else:
                self.write_log(f"{symbol}，从 {self.convertTime(start)} 到{self.convertTime(end)}历史数据下载失败")
        return data

    def convertTime(self, timestamp):
        return timestamp.strftime('%Y%m%d %H:%M:%S')

    def process_tick_event(self, event: Event):
        """"""
        tick = event.data
        trade_time = False

        if self.day_trade_time:
            if time(hour = 9, minute=0, second= 0 ) >= tick.datetime.time() >= time(hour=11, minute=30, second=0) or time(hour=13, minute=30, second=0) >= tick.datetime.time() >= time(hour=15, minute=0, second=0):
                trade_time = True
        else:
            if tick.datetime.time()<= time(hour=2, minute=30, second=0) or tick.datetime.time() >= time(21, 00):
                trade_time = True


        # if time(9, 0, 0) > tick.datetime.time()> time(hour=2, minute=30, second=0):
        #     return
        # elif tick.datetime.time() > time(hour=11, minute=30, second=0) and tick.datetime.time() < time(13, 30):
        #     return
        # elif self.day_trade_time and (tick.datetime.time()>time(hour=15,minute=15) or tick.datetime.time() < time(hour =3)):
        #     return
        # elif tick.datetime.time() > time(hour=15, minute=0, second=0) and tick.datetime.time() < time(21, 00):
        #     return

        if trade_time:
            strategies = self.symbol_strategy_map[tick.vt_symbol]
            if not strategies:
                return

            self.check_stop_order(tick)

            for strategy in strategies:
                if strategy.inited:
                    self.call_strategy_func(strategy, strategy.on_tick, tick)

    def process_order_event(self, event: Event):
        """"""
        order = event.data

        self.offset_converter.update_order(order)

        strategy = self.orderid_strategy_map.get(order.vt_orderid, None)
        if not strategy:
            return

        # Remove vt_orderid if order is no longer active.
        vt_orderids = self.strategy_orderid_map[strategy.strategy_name]
        if order.vt_orderid in vt_orderids and not order.is_active():
            vt_orderids.remove(order.vt_orderid)

        # For server stop order, call strategy on_stop_order function
        if order.type == OrderType.STOP:
            so = StopOrder(
                vt_symbol=order.vt_symbol,
                direction=order.direction,
                offset=order.offset,
                price=order.price,
                volume=order.volume,
                stop_orderid=order.vt_orderid,
                strategy_name=strategy.strategy_name,
                datetime=order.datetime,
                status=STOP_STATUS_MAP[order.status],
                vt_orderids=[order.vt_orderid],
            )
            self.call_strategy_func(strategy, strategy.on_stop_order, so)

        # Call strategy on_order function
        self.call_strategy_func(strategy, strategy.on_order, order)

    def process_trade_event(self, event: Event):
        """"""
        trade = event.data

        # Filter duplicate trade push
        if trade.vt_tradeid in self.vt_tradeids:
            return
        self.vt_tradeids.add(trade.vt_tradeid)

        self.offset_converter.update_trade(trade)

        strategy = self.orderid_strategy_map.get(trade.vt_orderid, None)

        if not strategy:
            # Sync strategy variables to data file
            return

        # Update strategy pos before calling on_trade method
        if trade.direction == Direction.LONG:
            strategy.pos += trade.volume
        else:
            strategy.pos -= trade.volume

        self.call_strategy_func(strategy, strategy.on_trade, trade)

        # Billy added, update triggered_stop_order
        cta_trade = copy(trade)
        # current_triggered_stop_order = None

        allComplete = False
        if cta_trade.vt_orderid in self.vt_orderid_triggered_stop_order:
            triggered_stop_order = self.vt_orderid_triggered_stop_order[cta_trade.vt_orderid]
            if triggered_stop_order.first_price == 0:
                triggered_stop_order.first_price = cta_trade.price
            triggered_stop_order.completed_volume += cta_trade.volume
            triggered_stop_order.average_price += cta_trade.volume * cta_trade.price
            # change orderid to stop_orderid
            cta_trade.orderid = triggered_stop_order.stop_orderid
            # current_triggered_stop_order = triggered_stop_order
            if triggered_stop_order.completed_volume == triggered_stop_order.volume:
                allComplete = True


        self.call_strategy_func(strategy, strategy.on_cta_trade, cta_trade)

        if allComplete:
            # Sync strategy variables to data file
            self.sync_strategy_data(strategy)
            triggered_stop_order.average_price = round(
                triggered_stop_order.average_price / triggered_stop_order.completed_volume, 2)
            self.put_cta_triggered_stoporder_event(triggered_stop_order)
            self.call_strategy_func(strategy, strategy.on_completed_order, triggered_stop_order)

            database_manager.save_triggered_stop_order_data(copy(triggered_stop_order))
            for k in triggered_stop_order.vt_orderids:
                self.vt_orderid_triggered_stop_order.pop(k)
            self.call_strategy_func(strategy, strategy.save_setting_file)

        # Update GUI
        self.put_strategy_event(strategy)

    def process_position_event(self, event: Event):
        """"""
        position = event.data

        self.offset_converter.update_position(position)

    def process_account_event(self,event: Event):
        """
        收到账户事件推送
        """
        data = event.data
        self.CurrMarginPrecent = data.CurrMargin / data.balance

    def check_stop_order(self, tick: TickData):
        """"""
        for stop_order in list(self.stop_orders.values()):
            if stop_order.vt_symbol != tick.vt_symbol:
                continue

            long_triggered = (
                    stop_order.direction == Direction.LONG and tick.last_price >= stop_order.price
            )
            short_triggered = (
                    stop_order.direction == Direction.SHORT and tick.last_price <= stop_order.price
            )

            if long_triggered or short_triggered:
                strategy = self.strategies[stop_order.strategy_name]

                # To get excuted immediately after stop order is
                # triggered, use limit price if available, otherwise
                # use ask_price_5 or bid_price_5
                if stop_order.direction == Direction.LONG:
                    if tick.limit_up:
                        price = tick.limit_up
                    else:
                        price = tick.ask_price_5
                else:
                    if tick.limit_down:
                        price = tick.limit_down
                    else:
                        price = tick.bid_price_5

                contract = self.main_engine.get_contract(stop_order.vt_symbol)

                vt_orderids = self.send_limit_order(
                    strategy,
                    contract,
                    stop_order.direction,
                    stop_order.offset,
                    price,
                    stop_order.volume,
                    stop_order.lock,
                    stop_order.net
                )

                # Update stop order status if placed successfully
                if vt_orderids:
                    # Remove from relation map.
                    if vt_orderids == 1:
                        # self.write_log(f"取消挂单，{strategy.strategy_name} {stop_order.stop_orderid}")
                        self.cancel_order(strategy,stop_order.stop_orderid)
                        return

                    self.stop_orders.pop(stop_order.stop_orderid)

                    strategy_vt_orderids = self.strategy_orderid_map[strategy.strategy_name]
                    if stop_order.stop_orderid in strategy_vt_orderids:
                        strategy_vt_orderids.remove(stop_order.stop_orderid)

                    # Change stop order status to cancelled and update to strategy.
                    stop_order.status = StopOrderStatus.TRIGGERED

                    stop_order.vt_orderids = vt_orderids

                    # Billy add to triggerred_stop_order dict
                    triggered_stop_order = copy(stop_order)
                    # triggered_stop_order.vt_orderids = list(map(lambda name: name.split(".")[1], triggered_stop_order.vt_orderids))
                    triggered_stop_order.stop_orderid = triggered_stop_order.stop_orderid + "." + stop_order.strategy_name + "." + '.'.join(
                        vt_orderids)
                    triggered_stop_order.datetime = copy(tick.datetime)
                    triggered_stop_order.completed_volume = 0
                    triggered_stop_order.average_price = 0
                    triggered_stop_order.first_price = 0
                    triggered_stop_order.open_price = 0
                    triggered_stop_order.triggered_price = tick.last_price
                    # self.triggered_stop_orders[triggered_stop_order.stop_orderid] = triggered_stop_order
                    for vt_orderid in vt_orderids:
                        self.vt_orderid_triggered_stop_order[vt_orderid] = triggered_stop_order
                    # self.put_cta_triggered_stoporder_event(triggered_stop_order)
                    # end Billy add

                    self.write_log(f"{strategy.strategy_name}触发停止挂单 {stop_order.stop_orderid}")

                    self.call_strategy_func(
                        strategy, strategy.on_stop_order, stop_order
                    )
                    self.put_stop_order_event(stop_order)

    def send_server_order(
            self,
            strategy: CtaTemplate,
            contract: ContractData,
            direction: Direction,
            offset: Offset,
            price: float,
            volume: float,
            type: OrderType,
            lock: bool,
            net: bool
    ):
        """
        Send a new order to server.
        """
        # Create request and send order.
        original_req = OrderRequest(
            symbol=contract.symbol,
            exchange=contract.exchange,
            direction=direction,
            offset=offset,
            type=type,
            price=price,
            volume=volume,
            reference=f"{APP_NAME}_{strategy.strategy_name}"
        )

        # Convert with offset converter
        req_list = self.offset_converter.convert_order_request(original_req, lock, net)

        # if marign rate > 95% and Offset.OPEN, req_list = []

        if self.CurrMarginPrecent >= 0.90:
            for req in req_list:
                if req.offset == Offset.OPEN:
                    self.write_log(f"保证金已经大于等于90%，{strategy.strategy_name}无法开新仓")
                    return 1

        # Send Orders
        vt_orderids = []

        for req in req_list:
            vt_orderid = self.main_engine.send_order(req, contract.gateway_name)

            # Check if sending order successful
            if not vt_orderid:
                continue

            vt_orderids.append(vt_orderid)

            self.offset_converter.update_order_request(req, vt_orderid)

            # Save relationship between orderid and strategy.
            self.orderid_strategy_map[vt_orderid] = strategy
            self.strategy_orderid_map[strategy.strategy_name].add(vt_orderid)

        return vt_orderids

    def send_direct_server_order(
            self,
            strategy: CtaTemplate,
            contract: ContractData,
            direction: Direction,
            offset: Offset,
            price: float,
            volume: float,
            type: OrderType,
    ):
        """
        Send a new order to server.
        """
        if offset == Offset.CLOSE and contract.exchange in [Exchange.SHFE, Exchange.INE]:
            offset = Offset.CLOSETODAY
        # Create request and send order.
        original_req = OrderRequest(
            symbol=contract.symbol,
            exchange=contract.exchange,
            direction=direction,
            offset=offset,
            type=type,
            price=price,
            volume=volume,
            reference=f"{APP_NAME}_{strategy.strategy_name}"
        )


        # Convert with offset converter
        vt_orderid = self.main_engine.send_order(original_req, contract.gateway_name)


            # Save relationship between orderid and strategy.
        self.orderid_strategy_map[vt_orderid] = strategy
        self.strategy_orderid_map[strategy.strategy_name].add(vt_orderid)

        return vt_orderid

    def send_limit_order(
            self,
            strategy: CtaTemplate,
            contract: ContractData,
            direction: Direction,
            offset: Offset,
            price: float,
            volume: float,
            lock: bool,
            net: bool
    ):
        """
        Send a limit order to server.
        """
        return self.send_server_order(
            strategy,
            contract,
            direction,
            offset,
            price,
            volume,
            OrderType.LIMIT,
            lock,
            net
        )

    def send_server_stop_order(
            self,
            strategy: CtaTemplate,
            contract: ContractData,
            direction: Direction,
            offset: Offset,
            price: float,
            volume: float,
            lock: bool,
            net: bool
    ):
        """
        Send a stop order to server.

        Should only be used if stop order supported
        on the trading server.
        """
        return self.send_server_order(
            strategy,
            contract,
            direction,
            offset,
            price,
            volume,
            OrderType.STOP,
            lock,
            net
        )

    def send_local_stop_order(
            self,
            strategy: CtaTemplate,
            direction: Direction,
            offset: Offset,
            price: float,
            volume: float,
            lock: bool,
            net: bool
    ):
        """
        Create a new local stop order.
        """
        self.stop_order_count += 1
        stop_orderid = f"{STOPORDER_PREFIX}.{self.stop_order_count}"

        stop_order = StopOrder(
            vt_symbol=strategy.vt_symbol,
            direction=direction,
            offset=offset,
            price=price,
            volume=volume,
            stop_orderid=stop_orderid,
            strategy_name=strategy.strategy_name,
            datetime=datetime.now(LOCAL_TZ),
            lock=lock,
            net=net
        )

        self.stop_orders[stop_orderid] = stop_order

        vt_orderids = self.strategy_orderid_map[strategy.strategy_name]
        vt_orderids.add(stop_orderid)

        self.call_strategy_func(strategy, strategy.on_stop_order, stop_order)
        self.put_stop_order_event(stop_order)

        return [stop_orderid]

    def cancel_server_order(self, strategy: CtaTemplate, vt_orderid: str):
        """
        Cancel existing order by vt_orderid.
        """
        order = self.main_engine.get_order(vt_orderid)
        if not order:
            self.write_log(f"撤单失败，找不到委托{vt_orderid}", strategy)
            return False

        req = order.create_cancel_request()
        self.main_engine.cancel_order(req, order.gateway_name)
        return True

    def cancel_local_stop_order(self, strategy: CtaTemplate, stop_orderid: str):
        """
        Cancel a local stop order.
        """
        stop_order = self.stop_orders.get(stop_orderid, None)
        if not stop_order:
            return
        strategy = self.strategies[stop_order.strategy_name]

        # Remove from relation map.
        self.stop_orders.pop(stop_orderid)

        vt_orderids = self.strategy_orderid_map[strategy.strategy_name]
        if stop_orderid in vt_orderids:
            vt_orderids.remove(stop_orderid)

        # Change stop order status to cancelled and update to strategy.
        stop_order.status = StopOrderStatus.CANCELLED

        self.call_strategy_func(strategy, strategy.on_stop_order, stop_order)
        self.put_stop_order_event(stop_order)
        return

    def send_order(
            self,
            strategy: CtaTemplate,
            direction: Direction,
            offset: Offset,
            price: float,
            volume: float,
            stop: bool,
            lock: bool,
            net: bool
    ):
        """
        """
        contract = self.main_engine.get_contract(strategy.vt_symbol)
        if not contract:
            self.write_log(f"委托失败，找不到合约：{strategy.vt_symbol}", strategy)
            return ""

        # Round order price and volume to nearest incremental value
        price = round_to(price, contract.pricetick)
        volume = round_to(volume, contract.min_volume)

        if stop:
            if contract.stop_supported:
                return self.send_server_stop_order(
                    strategy, contract, direction, offset, price, volume, lock, net
                )
            else:
                return self.send_local_stop_order(
                    strategy, direction, offset, price, volume, lock, net
                )
        else:
            return self.send_limit_order(
                strategy, contract, direction, offset, price, volume, lock, net
            )

    def cancel_order(self, strategy: CtaTemplate, vt_orderid: str):
        """
        """
        if vt_orderid.startswith(STOPORDER_PREFIX):
            self.cancel_local_stop_order(strategy, vt_orderid)
            return True
        else:
            return self.cancel_server_order(strategy, vt_orderid)
        # self.write_log(f"策略 {strategy.strategy_name} 撤销停止挂单{vt_orderid}")

    def cancel_all(self, strategy: CtaTemplate):
        """
        Cancel all active orders of a strategy.
        """
        vt_orderids = self.strategy_orderid_map[strategy.strategy_name]
        if not vt_orderids:
            return True

        returnValue = True
        for vt_orderid in copy(vt_orderids):
            returnValue = returnValue & self.cancel_order(strategy, vt_orderid)
        return returnValue

    def get_engine_type(self):
        """"""
        return self.engine_type

    def get_pricetick(self, strategy: CtaTemplate):
        """
        Return contract pricetick data.
        """
        contract = self.main_engine.get_contract(strategy.vt_symbol)

        if contract:
            return contract.pricetick
        else:
            return None


    def load_bar(
            self,
            vt_symbol: str,
            days: int,
            interval: Interval,
            callback: Callable[[BarData], None],
            use_database: bool
    ):
        """"""
        symbol, exchange = extract_vt_symbol(vt_symbol)
        end = datetime.now(LOCAL_TZ)
        start = end - timedelta(days)
        bars = []

        # Pass gateway and RQData if use_database set to True
        if not use_database:
            # Query bars from gateway if available
            contract = self.main_engine.get_contract(vt_symbol)

            if contract and contract.history_data:
                req = HistoryRequest(
                    symbol=symbol,
                    exchange=exchange,
                    interval=interval,
                    start=start,
                    end=end
                )
                bars = self.main_engine.query_history(req, contract.gateway_name)

            # Try to query bars from RQData, if not found, load from database.
            else:
                # bars = self.query_bar_from_rq(symbol, exchange, interval, start, end)
                if vt_symbol in self.symbol_time and self.symbol_time[vt_symbol] >= end:
                    self.write_log(
                        f"{vt_symbol}数据已在数据库")
                else:
                    any_bars = self.query_bar_from_rq(symbol, exchange, interval, start, end)
                    self.symbol_time[vt_symbol] = end +  timedelta(minutes=3)

                bars = database_manager.load_bar_data(
                    symbol=symbol,
                    exchange=exchange,
                    interval=interval,
                    start=start,
                    end=end,
                )


        for bar in bars:
            callback(bar)

    def load_tick(
            self,
            vt_symbol: str,
            days: int,
            callback: Callable[[TickData], None]
    ):
        """"""
        symbol, exchange = extract_vt_symbol(vt_symbol)
        end = datetime.now(LOCAL_TZ)
        start = end - timedelta(days)

        ticks = database_manager.load_tick_data(
            symbol=symbol,
            exchange=exchange,
            start=start,
            end=end,
        )

        for tick in ticks:
            callback(tick)

    def call_strategy_func(
            self, strategy: CtaTemplate, func: Callable, params: Any = None
    ):
        """
        Call function of a strategy and catch any exception raised.
        """
        try:
            if params:
                func(params)
            else:
                func()
        except Exception:
            strategy.trading = False
            strategy.inited = False

            msg = f"触发异常已停止\n{traceback.format_exc()}"
            self.write_log(msg, strategy)

    def add_strategy(
            self, class_name: str, strategy_name: str, vt_symbol: str, vt_local, setting: dict
    ):
        """
        Add a new strategy.
        """
        if strategy_name in self.strategies:
            self.write_log(f"创建策略失败，存在重名{strategy_name}")
            return

        strategy_class = self.classes.get(class_name, None)
        if not strategy_class:
            self.write_log(f"创建策略失败，找不到策略类{class_name}")
            return

        if "." not in vt_symbol:
            self.write_log("创建策略失败，本地代码缺失交易所后缀")
            return

        _, exchange_str = vt_symbol.split(".")
        if exchange_str not in Exchange.__members__:
            self.write_log("创建策略失败，本地代码的交易所后缀不正确")
            return

        parameterList = [strategy_setting.vt_local for strategy_setting in list(self.strategies.values())]
        if vt_local in parameterList:
            self.write_log(f"创建策略失败，位置{vt_local}已经存在策略")
            return

        strategy = strategy_class(self, strategy_name, vt_symbol, vt_local, setting)
        self.strategies[strategy_name] = strategy

        # Add vt_symbol to strategy map.
        strategies = self.symbol_strategy_map[vt_symbol]
        strategies.append(strategy)

        # Update to setting file.
        self.update_strategy_setting(strategy_name, setting)

        self.put_strategy_event(strategy)

    def init_strategy(self, strategy_name: str):
        """
        Init a strategy.
        """
        self.init_executor.submit(self._init_strategy, strategy_name)

    def _init_strategy(self, strategy_name: str):
        """
        Init strategies in queue.
        """
        strategy = self.strategies[strategy_name]

        if strategy.inited:
            self.write_log(f"{strategy_name}已经完成初始化，禁止重复操作")
            return
        if strategy.STOP_TRADE:
            strategy.inited = True
            self.write_log(f"{strategy_name}已经停用")
            return
        self.write_log(f"{strategy_name}开始执行初始化")

        # Call on_init function of strategy
        self.call_strategy_func(strategy, strategy.on_init)

        # Restore strategy data(variables)
        data = self.strategy_data.get(strategy_name, None)
        if data:
            for name in strategy.variables:
                value = data.get(name, None)
                if value:
                    setattr(strategy, name, value)

        # Subscribe market data
        contract = self.main_engine.get_contract(strategy.vt_symbol)
        if contract:
            req = SubscribeRequest(
                symbol=contract.symbol, exchange=contract.exchange)
            self.main_engine.subscribe(req, contract.gateway_name)
        else:
            self.write_log(f"行情订阅失败，找不到合约{strategy.vt_symbol}", strategy)

        # Put event to update init completed status.
        strategy.inited = True
        self.put_strategy_event(strategy)
        self.write_log(f"{strategy_name}初始化完成")

    def start_strategy(self, strategy_name: str):
        """
        Start a strategy.
        """
        strategy = self.strategies[strategy_name]

        if not strategy.inited:
            self.write_log(f"策略{strategy.strategy_name}启动失败，请先初始化")
            return

        if strategy.trading:
            self.write_log(f"{strategy_name}已经启动，请勿重复操作")
            return


        strategy.trading = True

        self.call_strategy_func(strategy, strategy.on_start)
        # if commit, the stop botton disable
        # strategy.trading = True

        self.put_strategy_event(strategy)

    def stop_strategy(self, strategy_name: str):
        """
        Stop a strategy.
        """
        strategy = self.strategies[strategy_name]
        if not strategy.trading:
            return

        # Call on_stop function of the strategy
        self.call_strategy_func(strategy, strategy.on_stop)

        # Change trading status of strategy to False
        strategy.trading = False

        # Cancel all orders of the strategy
        self.cancel_all(strategy)

        # Sync strategy variables to data file
        self.sync_strategy_data(strategy)

        # Update GUI
        self.put_strategy_event(strategy)

    def edit_strategy(self, strategy_name: str, setting: dict):
        """
        Edit parameters of a strategy.
        """
        strategy = self.strategies[strategy_name]
        if "vt_local" in setting.keys():
            vt_local = setting["vt_local"]
            parameterList = [strategy_setting.vt_local for strategy_setting in list(self.strategies.values())]
            if vt_local in parameterList and strategy.vt_local != vt_local:
                self.write_log(f"更新策略失败，位置{vt_local}已经存在策略")
                return
        strategy.inited = False
        strategy.update_setting(setting)

        self.update_strategy_setting(strategy_name, setting)
        # comment inited for editon parameter during trading
        # strategy.inited = False
        self.put_strategy_event(strategy)

    def remove_strategy(self, strategy_name: str):
        """
        Remove a strategy.
        """
        strategy = self.strategies[strategy_name]
        if strategy.trading:
            self.write_log(f"策略{strategy.strategy_name}移除失败，请先停止")
            return

        # Remove setting
        self.remove_strategy_setting(strategy_name)

        # Remove from symbol strategy map
        strategies = self.symbol_strategy_map[strategy.vt_symbol]
        strategies.remove(strategy)

        # Remove from active orderid map
        if strategy_name in self.strategy_orderid_map:
            vt_orderids = self.strategy_orderid_map.pop(strategy_name)

            # Remove vt_orderid strategy map
            for vt_orderid in vt_orderids:
                if vt_orderid in self.orderid_strategy_map:
                    self.orderid_strategy_map.pop(vt_orderid)

        # Remove from strategies
        self.strategies.pop(strategy_name)

        self.write_log(f"策略{strategy.strategy_name}移除移除成功")
        return True

    def load_strategy_class(self):
        """
        Load strategy class from source code.
        """
        path1 = Path(__file__).parent.joinpath("strategies")
        self.load_strategy_class_from_folder(
            path1, "vnpy.app.cta_strategy.strategies")

        path2 = Path.cwd().joinpath("strategies")
        self.load_strategy_class_from_folder(path2, "strategies")

    def load_strategy_class_from_folder(self, path: Path, module_name: str = ""):
        """
        Load strategy class from certain folder.
        """
        for dirpath, dirnames, filenames in os.walk(str(path)):
            for filename in filenames:
                if filename.split(".")[-1] in ("py", "pyd", "so"):
                    strategy_module_name = ".".join([module_name, filename.split(".")[0]])
                    self.load_strategy_class_from_module(strategy_module_name)

    def load_strategy_class_from_module(self, module_name: str):
        """
        Load strategy class from module file.
        """
        try:
            module = importlib.import_module(module_name)

            for name in dir(module):
                value = getattr(module, name)
                if (isinstance(value, type) and issubclass(value, CtaTemplate) and value is not CtaTemplate):
                    self.classes[value.__name__] = value
        except:  # noqa
            msg = f"策略文件{module_name}加载失败，触发异常：\n{traceback.format_exc()}"
            self.write_log(msg)

    def load_strategy_data(self):
        """
        Load strategy data from json file.
        """
        self.strategy_data = load_json(self.data_filename)

    def load_symbol_attr(self):
        """
        Load strategy data from json file.
        """
        self.symbol_attr = load_json(self.commodities_filename)

    def sync_strategy_data(self, strategy: CtaTemplate):
        """
        Sync strategy data into json file.
        """
        data = strategy.get_variables()
        data.pop("inited")  # Strategy status (inited, trading) should not be synced.
        data.pop("trading")

        self.strategy_data[strategy.strategy_name] = data
        save_json(self.data_filename, self.strategy_data)

    def get_all_strategy_class_names(self):
        """
        Return names of strategy classes loaded.
        """
        return list(self.classes.keys())

    def get_strategy_class_parameters(self, class_name: str):
        """
        Get default parameters of a strategy class.
        """
        strategy_class = self.classes[class_name]

        parameters = {}
        for name in strategy_class.parameters:
            parameters[name] = getattr(strategy_class, name)

        return parameters

    def get_strategy_parameters(self, strategy_name):
        """
        Get parameters of a strategy.
        """
        strategy = self.strategies[strategy_name]
        return strategy.get_parameters()

    def convert_strategy_triggered_order(self,strategy_name,open_date = datetime(2001,10,10), close_date = datetime(2100,10,10)):
        result = database_manager.load_triggered_stop_order_data(strategy_name,open_date,close_date)
        if result:
            matchedOrderList = []
            last_order = None
            for order in result:
                if order.offset == Offset.OPEN:
                    last_order = copy(order)


                elif last_order != None and order.offset == Offset.CLOSE:
                    if last_order.vt_symbol != order.vt_symbol:
                        last_order = None
                        continue
                    order.vt_orderids = [last_order.datetime]
                    order.open_price = last_order.average_price
                    matchedOrderList.append(copy(order))
                    last_order = None
            return matchedOrderList


    def transprot_all_triggered_strategies_order(self,open_date = datetime(2001,10,10), close_date = datetime(2100,10,10)):
        for strategy in self.strategies:
            objectDF = self.get_strategy_triggered_order(strategy,open_date, close_date)
            database_manager.save_closetriggered_stop_order_data(objectDF.to_dict("records"))


    def get_dbaccount_data(self, start = datetime(2001,10,10), end = datetime(2100,10,10)):

        account_data_list = database_manager.load_account_data(start, end)
        account_data_DF = DataFrame(data=None,
                             columns=["accountid","datetime", "balance", "Commission","CurrMargin", "CurrMarginPrecent","available","BankTransfer"], dtype=object)
        if account_data_list:
            for account_data in account_data_list:
                account_data_DF.loc[len(account_data_DF) + 1] =[account_data.accountid, account_data.datetime.replace(tzinfo=None),account_data.balance,account_data.Commission,account_data.CurrMargin,
                                                            account_data.CurrMarginPrecent,account_data.available, account_data.BankTransfer]

            account_data_DF["net_pnl"] = round(account_data_DF["balance"].diff(periods=1) - account_data_DF["BankTransfer"],2)

            account_data_DF["total_pnl"] = account_data_DF["net_pnl"].cumsum()
            account_data_DF["total_pnl_percent"] = account_data_DF["total_pnl"]*100.0/account_data_DF["balance"]

            account_data_DF["highlevel"] = (
                account_data_DF["total_pnl"].rolling(
                    min_periods=1, window=len(account_data_DF), center=False).max()
            )

            account_data_DF["drawdown"] = account_data_DF["total_pnl"] - account_data_DF["highlevel"]
            account_data_DF = account_data_DF.fillna(0)

        return account_data_DF



    def get_strategy_triggered_order(self,strategy_name,open_date = datetime(2001,10,10), close_date = datetime(2100,10,10)):
        # result = database_manager.load_close_triggered_stop_order_data(strategy_name)
        result = self.convert_strategy_triggered_order(strategy_name,open_date,close_date)

        objectDF = DataFrame(data=None,columns=["HeYueJiaZhi","HeYueChengShu","vt_symbol","strategy_name","strategy_class","open_date","close_date", "direction", "open_price", "volume", "close_price", "revenue"],dtype=object)
        if result:
            strategy = self.strategies[strategy_name]
            parameters = self.get_strategy_parameters(strategy_name)
            HeYueJiaZhi = parameters["HeYueJiaZhi"]
            HeYueChengShu = parameters["HeYueChengShu"]
            strategy_name = strategy.strategy_name
            strategy_class = type(strategy).__name__

            for close_data in result:
                close_data.direction = Direction.LONG if close_data.direction == Direction.SHORT else Direction.SHORT
                objectDF.loc[len(objectDF) + 1] = [HeYueJiaZhi,HeYueChengShu,close_data.vt_symbol,strategy_name,strategy_class,
                                                   close_data.vt_orderids[0].replace(tzinfo=None),close_data.datetime.replace(tzinfo=None), close_data.direction, close_data.open_price,close_data.volume, close_data.average_price,0.0]

            objectDF["revenue"] = objectDF.apply(lambda x: x['open_price'] - x['close_price'] if x['direction'] == Direction.SHORT else x['close_price'] - x['open_price'],
                                        axis=1)

            objectDF["UnitReturn"] = objectDF["revenue"] * 100 / objectDF['open_price']

            objectDF["revenue"] = objectDF["revenue"]*HeYueChengShu*objectDF["volume"]

            objectDF["balance"] = objectDF["revenue"].cumsum() + HeYueJiaZhi

            objectDF["returnRatio"] = objectDF["revenue"]*100/HeYueJiaZhi


            objectDF.loc[0] = copy(objectDF.iloc[0])
            objectDF = objectDF.sort_index()
            objectDF.loc[0,"balance"] = HeYueJiaZhi

            objectDF["highlevel"] = (
                objectDF["balance"].rolling(
                    min_periods=1, window=len(objectDF), center=False).max()
            )

            objectDF.drop(index=0, inplace=True)

            objectDF["drawdown"] = objectDF["balance"] - objectDF["highlevel"]
            objectDF["ddpercent"] = objectDF["drawdown"] / objectDF["highlevel"] * 100

        return objectDF



    def init_all_strategies(self):
        """
        """
        for strategy_name in self.strategies.keys():
            self.init_strategy(strategy_name)

    def start_all_strategies(self):
        """
        """
        self.write_log(self.symbol_strategy_map)
        for strategy_name in self.strategies.keys():
            self.start_strategy(strategy_name)

    def stop_all_strategies(self):
        """
        """
        for strategy_name in self.strategies.keys():
            self.stop_strategy(strategy_name)

    def load_strategy_setting(self):
        """
        Load setting file.
        """
        self.strategy_setting = load_json(self.setting_filename)

        for strategy_name, strategy_config in self.strategy_setting.items():
            self.add_strategy(
                strategy_config["class_name"],
                strategy_name,
                strategy_config["vt_symbol"],
                strategy_config["vt_local"],
                strategy_config["setting"]
            )

    def update_strategy_setting(self, strategy_name: str, setting: dict):
        """
        Update setting file.
        """
        strategy = self.strategies[strategy_name]
        if "vt_local" in setting:
            vt_local = setting.pop("vt_local")
            strategy.vt_local = vt_local

        self.strategy_setting[strategy_name] = {
            "class_name": strategy.__class__.__name__,
            "vt_symbol": strategy.vt_symbol,
            "vt_local": strategy.vt_local,
            "setting": setting,
        }
        save_json(self.setting_filename, self.strategy_setting)

    def daily_strategy_setting_backup(self):
        today_date = datetime.now().strftime("%Y_%m_%d")
        filename = f"vt_{today_date}" + "_cta_strategy_setting.json"
        bak_path = get_folder_path("cta_strategy_bak\\" + f"{today_date}")
        file_path = bak_path.joinpath(filename)

        # exportPath = "cta_strategy_bak\\"+ filename + "_cta_strategy_setting.json"
        save_json(file_path,self.strategy_setting)
        # (self, subject: str, content: str, receiver: str = "", attch_dir = "", filename = "")
        self.main_engine.send_email_attchment(subject=filename, content=filename,
                                              attch_dir=file_path, filename=filename)

        # py_path = r"C:\ProgramData\Anaconda3\Lib\site-packages\vnpy\app\cta_strategy\strategies"
        # py_file ="bar_jumpdown_trend.py"
        # self.main_engine.send_email(subject=f"vt_{today_date}" + py_file, content=py_file,
        #                                       attch_dir=py_path, filename=py_file)

    def remove_strategy_setting(self, strategy_name: str):
        """
        Update setting file.
        """
        if strategy_name not in self.strategy_setting:
            return

        self.strategy_setting.pop(strategy_name)
        save_json(self.setting_filename, self.strategy_setting)

    def put_stop_order_event(self, stop_order: StopOrder):
        """
        Put an event to update stop order status.
        """
        event = Event(EVENT_CTA_STOPORDER, stop_order)
        self.event_engine.put(event)

    def put_cta_triggered_stoporder_event(self, triggered_stop_order):
        """
        Put an event to update stop order status.
        """
        event = Event(EVENT_CTA_TRIGGERED_STOPORDER, triggered_stop_order)
        self.event_engine.put(event)

    def put_cta_trade_event(self, cta_trade):
        """
        Put an event to update stop order status.
        """
        event = Event(EVENT_CTA_TRADE, cta_trade)
        self.event_engine.put(event)

    def put_strategy_event(self, strategy: CtaTemplate):
        """
        Put an event to update strategy status.
        """
        data = strategy.get_data()
        event = Event(EVENT_CTA_STRATEGY, data)
        self.event_engine.put(event)

    def write_log(self, msg: str, strategy: CtaTemplate = None):
        """
        Create cta engine log event.
        """
        if strategy:
            msg = f"[{strategy.strategy_name}]  {msg}"

        log = LogData(msg=msg, gateway_name=APP_NAME)
        event = Event(type=EVENT_CTA_LOG, data=log)
        self.event_engine.put(event)

    def send_email(self, msg: str, strategy: CtaTemplate = None):
        """
        Send email to default receiver.
        """
        if strategy:
            subject = f"{strategy.strategy_name}"
        else:
            subject = "CTA策略引擎"

        self.main_engine.send_email(subject, msg)