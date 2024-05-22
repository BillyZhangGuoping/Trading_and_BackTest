""""""
from datetime import datetime, time, date
from typing import List

from mongoengine import (
    Document,
    DateTimeField,
    FloatField,
    StringField,
    BooleanField,
    IntField,
    connect,
    QuerySet,
    ListField
)
from mongoengine.errors import DoesNotExist

from vnpy.trader.constant import Exchange, Interval, Direction, Offset
from vnpy.trader.object import BarData, TickData, TradeData,StopOrder
from vnpy.trader.constant import StopOrderStatus
from vnpy.trader.database import (
    BaseDatabase,
    BarOverview,
    DB_TZ,
    convert_tz
)
from vnpy.trader.setting import SETTINGS

class DbTradeData(Document):
    """
    Trade data contains information of a fill of an order. One order
    can have several trade fills.
    """

    symbol: str = StringField()
    exchange: str = StringField()
    orderid: str = StringField()
    tradeid: str = StringField()
    direction: str = StringField()
    strategy: str = StringField()

    offset: str = StringField()
    price: float = FloatField()
    volume: float = FloatField()
    datetime: datetime = DateTimeField()
    date: datetime = DateTimeField()
    meta = {
        "indexes": [
            {
                "fields": ("symbol", "strategy", "tradeid", "datetime"),
                "unique": True,
            }
        ]
    }

    def keys(self):
        '''当对实例化对象使用dict(obj)的时候, 会调用这个方法,这里定义了字典的键, 其对应的值将以obj['name']的形式取,
		但是对象是不可以以这种方式取值的, 为了支持这种取值, 可以为类增加一个方法'''
        return (
        "strategy",
        "symbol",
        "tradeid",
        "orderid",
        "datetime",
        "price",
        "volume",
        "direction",
        "offset"
        )

    def __getitem__(self, item):
        '''内置方法, 当使用obj['name']的形式的时候, 将调用这个方法, 这里返回的结果就是值'''
        return getattr(self, item)



class DbAccountData(Document):
    accountid: str = StringField()
    balance: float = FloatField()
    frozen: float = FloatField()
    PositionProfit: float = FloatField()
    CurrentProfit: float = FloatField()
    CurrMarginPrecent: float = FloatField()
    CurrMargin: float = FloatField()
    gateway_name: str = StringField()
    Commission: float = FloatField()
    available: float = FloatField()
    BankTransfer: float = FloatField()
    datetime: datetime = DateTimeField()
    meta = {
        "indexes": [
            {
                "fields": ("accountid", "datetime","gateway_name"),
                "unique": True,
            }
        ]
    }

class DbTriStopOrderData(Document):
    """
    stop order
    """
    vt_symbol: str = StringField()
    stop_orderid: str = StringField()
    strategy_name: str = StringField()
    direction: str = StringField()
    offset: str = StringField()
    datetime: datetime = DateTimeField()
    lock: bool = BooleanField()
    net: bool = BooleanField()
    price: float = FloatField()
    volume: float = FloatField()
    completed_volume: float = FloatField()
    average_price: float = FloatField()
    first_price: float = FloatField()
    triggered_price: float = FloatField()
    open_price: float = FloatField()
    vt_orderids: list = ListField()
    status: str = StringField()

    meta = {
        "indexes": [
            {
                "fields": ("vt_symbol", "stop_orderid", "datetime","strategy_name"),
                "unique": True,
            }
        ]
    }

class DbTriCloseStopOrderData(Document):

    vt_symbol: str = StringField()
    strategy_name: str = StringField()
    strategy_class: str = StringField()
    HeYueJiaZhi : float = FloatField()
    HeYueChengShu : float = FloatField()
    open_date : datetime = DateTimeField()
    close_date: datetime = DateTimeField()
    open_price: float = FloatField()
    direction: str = StringField()
    close_price: float = FloatField()
    volume: float = FloatField()
    revenue: float = FloatField()
    UnitReturn: float = FloatField()
    returnRatio : float = FloatField()
    balance : float = FloatField()
    highlevel: float = FloatField()
    drawdown : float = FloatField()
    ddpercent: float = FloatField()
    meta = {
        "indexes": [
            {
                "fields": ("vt_symbol","open_date","strategy_name"),
                "unique": True,
            }
        ]
    }




class DbBarData(Document):
    """"""

    symbol: str = StringField()
    exchange: str = StringField()
    datetime: datetime = DateTimeField()
    interval: str = StringField()

    volume: float = FloatField()
    turnover: float = FloatField()
    open_interest: float = FloatField()
    open_price: float = FloatField()
    high_price: float = FloatField()
    low_price: float = FloatField()
    close_price: float = FloatField()

    meta = {
        "indexes": [
            {
                "fields": ("symbol", "exchange", "interval", "datetime"),
                "unique": True,
            }
        ]
    }


class DbTickData(Document):
    """"""

    symbol: str = StringField()
    exchange: str = StringField()
    datetime: datetime = DateTimeField()

    name: str = StringField()
    volume: float = FloatField()
    turnover: float = FloatField()
    open_interest: float = FloatField()
    last_price: float = FloatField()
    last_volume: float = FloatField()
    limit_up: float = FloatField()
    limit_down: float = FloatField()

    open_price: float = FloatField()
    high_price: float = FloatField()
    low_price: float = FloatField()
    close_price: float = FloatField()
    pre_close: float = FloatField()

    bid_price_1: float = FloatField()
    bid_price_2: float = FloatField()
    bid_price_3: float = FloatField()
    bid_price_4: float = FloatField()
    bid_price_5: float = FloatField()

    ask_price_1: float = FloatField()
    ask_price_2: float = FloatField()
    ask_price_3: float = FloatField()
    ask_price_4: float = FloatField()
    ask_price_5: float = FloatField()

    bid_volume_1: float = FloatField()
    bid_volume_2: float = FloatField()
    bid_volume_3: float = FloatField()
    bid_volume_4: float = FloatField()
    bid_volume_5: float = FloatField()

    ask_volume_1: float = FloatField()
    ask_volume_2: float = FloatField()
    ask_volume_3: float = FloatField()
    ask_volume_4: float = FloatField()
    ask_volume_5: float = FloatField()

    localtime: datetime = DateTimeField()

    meta = {
        "indexes": [
            {
                "fields": ("symbol", "exchange", "datetime"),
                "unique": True,
            }
        ],
    }


class DbBarOverview(Document):
    """"""

    symbol: str = StringField()
    exchange: str = StringField()
    interval: str = StringField()
    count: int = IntField()
    start: datetime = DateTimeField()
    end: datetime = DateTimeField()

    meta = {
        "indexes": [
            {
                "fields": ("symbol", "exchange", "interval"),
                "unique": True,
            }
        ],
    }


class MongodbDatabase(BaseDatabase):
    """"""

    def __init__(self) -> None:
        """"""
        database = SETTINGS["database.database"]
        host = SETTINGS["database.host"]
        port = SETTINGS["database.port"]
        username = SETTINGS["database.user"]
        password = SETTINGS["database.password"]
        authentication_source = SETTINGS["database.authentication_source"]

        if not username:
            username = None
            password = None
            authentication_source = None

        connect(
            db=database,
            host=host,
            port=port,
            username=username,
            password=password,
            authentication_source=authentication_source,
        )

    def save_bar_data(self, bars: List[BarData]) -> bool:
        """"""
        # Store key parameters
        bar = bars[0]
        symbol = bar.symbol
        exchange = bar.exchange
        interval = bar.interval

        # Upsert data into mongodb
        for bar in bars:
            bar.datetime = convert_tz(bar.datetime)

            d = bar.__dict__
            d["exchange"] = d["exchange"].value
            d["interval"] = d["interval"].value
            d.pop("gateway_name")
            d.pop("vt_symbol")
            param = to_update_param(d)

            DbBarData.objects(
                symbol=d["symbol"],
                exchange=d["exchange"],
                interval=d["interval"],
                datetime=d["datetime"],
            ).update_one(upsert=True, **param)

        # Update bar overview
        try:
            overview: DbBarOverview = DbBarOverview.objects(
                symbol=symbol,
                exchange=exchange.value,
                interval=interval.value
            ).get()
        except DoesNotExist:
            overview: DbBarOverview = DbBarOverview(
                symbol=symbol,
                exchange=exchange.value,
                interval=interval.value
            )

        if not overview.start:
            overview.start = bars[0].datetime
            overview.end = bars[-1].datetime
            overview.count = len(bars)
        else:
            overview.start = min(bars[0].datetime, overview.start)
            overview.end = max(bars[-1].datetime, overview.end)
            overview.count = DbBarData.objects(
                symbol=symbol,
                exchange=exchange.value,
                interval=interval.value
            ).count()

        overview.save()

    def save_tick_data(self, ticks: List[TickData]) -> bool:
        """"""
        for tick in ticks:
            tick.datetime = convert_tz(tick.datetime)

            d = tick.__dict__
            d["exchange"] = d["exchange"].value
            d.pop("gateway_name")
            d.pop("vt_symbol")
            param = to_update_param(d)

            DbTickData.objects(
                symbol=d["symbol"],
                exchange=d["exchange"],
                datetime=d["datetime"],
            ).update_one(upsert=True, **param)

    def load_bar_data(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
        start: datetime,
        end: datetime
    ) -> List[BarData]:
        """"""
        s: QuerySet = DbBarData.objects(
            symbol=symbol,
            exchange=exchange.value,
            interval=interval.value,
            datetime__gte=convert_tz(start),
            datetime__lte=convert_tz(end),
        )

        vt_symbol = f"{symbol}.{exchange.value}"
        bars: List[BarData] = []
        for db_bar in s:
            bar = BarData(
                symbol=db_bar.symbol,
                exchange=Exchange(db_bar.exchange),
                datetime=db_bar.datetime.astimezone(DB_TZ),
                interval=Interval(db_bar.interval),
                volume=db_bar.volume,
                turnover=db_bar.turnover,
                open_interest=db_bar.open_interest,
                open_price=db_bar.open_price,
                high_price=db_bar.high_price,
                low_price=db_bar.low_price,
                close_price=db_bar.close_price,
                gateway_name="DB"
            )
            bars.append(bar)

        return bars

    def load_tick_data(
        self,
        symbol: str,
        exchange: Exchange,
        start: datetime,
        end: datetime
    ) -> List[TickData]:
        """"""
        s: QuerySet = DbTickData.objects(
            symbol=symbol,
            exchange=exchange.value,
            datetime__gte=convert_tz(start),
            datetime__lte=convert_tz(end),
        )

        vt_symbol = f"{symbol}.{exchange.value}"
        ticks: List[TickData] = []
        for db_tick in s:
            tick = TickData(
                symbol=db_tick.symbol,
                exchange=Exchange(db_tick.exchange),
                datetime=db_tick.datetime.astimezone(DB_TZ),
                name=db_tick.name,
                volume=db_tick.volume,
                turnover=db_tick.turnover,
                open_interest=db_tick.open_interest,
                last_price=db_tick.last_price,
                last_volume=db_tick.last_volume,
                limit_up=db_tick.limit_up,
                limit_down=db_tick.limit_down,
                open_price=db_tick.open_price,
                high_price=db_tick.high_price,
                low_price=db_tick.low_price,
                pre_close=db_tick.pre_close,
                bid_price_1=db_tick.bid_price_1,
                bid_price_2=db_tick.bid_price_2,
                bid_price_3=db_tick.bid_price_3,
                bid_price_4=db_tick.bid_price_4,
                bid_price_5=db_tick.bid_price_5,
                ask_price_1=db_tick.ask_price_1,
                ask_price_2=db_tick.ask_price_2,
                ask_price_3=db_tick.ask_price_3,
                ask_price_4=db_tick.ask_price_4,
                ask_price_5=db_tick.ask_price_5,
                bid_volume_1=db_tick.bid_volume_1,
                bid_volume_2=db_tick.bid_volume_2,
                bid_volume_3=db_tick.bid_volume_3,
                bid_volume_4=db_tick.bid_volume_4,
                bid_volume_5=db_tick.bid_volume_5,
                ask_volume_1=db_tick.ask_volume_1,
                ask_volume_2=db_tick.ask_volume_2,
                ask_volume_3=db_tick.ask_volume_3,
                ask_volume_4=db_tick.ask_volume_4,
                ask_volume_5=db_tick.ask_volume_5,
                localtime=db_tick.localtime,
                gateway_name="DB"
            )
            ticks.append(tick)

        return ticks

    def delete_bar_data(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval
    ) -> int:
        """"""
        count = DbBarData.objects(
            symbol=symbol,
            exchange=exchange.value,
            interval=interval.value
        ).delete()

        # Delete bar overview
        DbBarOverview.objects(
            symbol=symbol,
            exchange=exchange.value,
            interval=interval.value
        ).delete()

        return count

    def delete_tick_data(
        self,
        symbol: str,
        exchange: Exchange
    ) -> int:
        """"""
        count = DbTickData.objects(
            symbol=symbol,
            exchange=exchange.value
        ).delete()
        return count

    def get_bar_overview(self) -> List[BarOverview]:
        """
        Return data avaible in database.
        """
        # Init bar overview for old version database
        data_count = DbBarData.objects.count()
        overview_count = DbBarOverview.objects.count()
        if data_count and not overview_count:
            self.init_bar_overview()

        s: QuerySet = DbBarOverview.objects()
        overviews = []
        for overview in s:
            overview.exchange = Exchange(overview.exchange)
            overview.interval = Interval(overview.interval)
            overviews.append(overview)
        return overviews

    def init_bar_overview(self) -> None:
        """
        Init overview table if not exists.
        """
        s: QuerySet = (
            DbBarData.objects.aggregate({
                "$group": {
                    "_id": {
                        "symbol": "$symbol",
                        "exchange": "$exchange",
                        "interval": "$interval",
                    },
                    "count": {"$sum": 1}
                }
            })
        )

        for d in s:
            id_data = d["_id"]

            overview = DbBarOverview()
            overview.symbol = id_data["symbol"]
            overview.exchange = id_data["exchange"]
            overview.interval = id_data["interval"]
            overview.count = d["count"]

            start_bar: DbBarData = (
                DbBarData.objects(
                    symbol=id_data["symbol"],
                    exchange=id_data["exchange"],
                    interval=id_data["interval"],
                )
                .order_by("+datetime")
                .first()
            )
            overview.start = start_bar.datetime

            end_bar: DbBarData = (
                DbBarData.objects(
                    symbol=id_data["symbol"],
                    exchange=id_data["exchange"],
                    interval=id_data["interval"],
                )
                .order_by("-datetime")
                .first()
            )
            overview.end = end_bar.datetime

            overview.save()
    # Billy added Methoed
    def save_cta_trade_data(self,cta_trade) -> bool:
        """
        Save cta_trade data into database.
        """

        cta_trade.datetime = convert_tz(cta_trade.datetime)
        cta_trade.date = convert_tz(cta_trade.date)
        d = cta_trade.__dict__
        d["exchange"] = d["exchange"].value
        d["direction"] = d["direction"].value
        d["offset"] = d["offset"].value
        d.pop("vt_orderid")
        d.pop("vt_symbol")
        d.pop("vt_tradeid")
        d.pop("gateway_name")
        param = to_update_param(d)

        DbTradeData.objects(
            symbol=d["symbol"],
            strategy=d["strategy"],
            tradeid = d["tradeid"],
            datetime=d["datetime"],
        ).update_one(upsert=True, **param)

    # Billy added Methoed
    def load_cta_trade_data(
        self,
        # symbol: str,
        strategy: str,
        start: datetime,
        end: datetime
    ):
        """
        Load cta_trade data from database.
        """
        s: QuerySet = DbTradeData.objects(
            # symbol=symbol,
            strategy = strategy,
            datetime__gte=convert_tz(start),
            datetime__lte=convert_tz(end),
        ).order_by('datetime')

        dbtrades: List[TradeData] = []
        for db_trade in s:
            db_trade.datetime = DB_TZ.localize(db_trade.datetime)
            db_trade.exchange = Exchange(db_trade.exchange)
            db_trade.direction = Direction(db_trade.direction)
            db_trade.offset = Offset(db_trade.offset)
            db_trade.price = round(db_trade.price,3)
            db_trade.gateway_name = "DataBase"
            db_trade.date = DB_TZ.localize(db_trade.date)
            dbtrades.append(db_trade)
        return dbtrades



    def save_triggered_stop_order_data(self,triggered_stop_order ) -> bool:
        """
        Save triggered_stop_order data into database.
        """

        triggered_stop_order.datetime = convert_tz(triggered_stop_order.datetime)
        d = triggered_stop_order .__dict__
        d["direction"] = d["direction"].value
        d["offset"] = d["offset"].value
        d["status"] = d["status"].value
        param = to_update_param(d)

        DbTriStopOrderData.objects(
            vt_symbol=d["vt_symbol"],
            strategy_name=d["strategy_name"],
            stop_orderid = d["stop_orderid"],
            datetime=d["datetime"],
        ).update_one(upsert=True, **param)

    def save_account_data(self,accountDataList:List[object] ) -> bool:
        """
        """
        currentTime = datetime.combine(date.today(), time(15,10,0))

        for accountData in accountDataList:
            d = accountData.__dict__
            d["datetime"] = currentTime
            d.pop("vt_accountid")
            param = to_update_param(d)

            DbAccountData.objects(
                accountid=d["accountid"],
                datetime=d["datetime"],
                gateway_name = d["gateway_name"]
            ).update_one(upsert=True, **param)

    def load_account_data(
            self,
            start: datetime,
            end: datetime):
        """
        """

        s: QuerySet = DbAccountData.objects(
            datetime__gte=convert_tz(start),
            datetime__lte=convert_tz(end),
        ).order_by('datetime')

        account_orders: List[StopOrder] = []
        for account_order in s:
            account_order.datetime = DB_TZ.localize(account_order.datetime)
            account_orders.append(account_order)
        return account_orders

    def save_closetriggered_stop_order_data(self,records:List[object] ) -> bool:
        """
        Save triggered_stop_order data into database.
        """

        for triggered_stop_order in records:
            # triggered_stop_order["open_date"] = convert_tz(triggered_stop_order["open_date"] )
            # triggered_stop_order["close_date"] = convert_tz(triggered_stop_order["close_date"])
            d = triggered_stop_order
            d["direction"] = d["direction"].value
            param = to_update_param(d)

            DbTriCloseStopOrderData.objects(
                vt_symbol=d["vt_symbol"],
                strategy_name=d["strategy_name"],
                open_date=d["open_date"]
            ).update_one(upsert=True, **param)

    # Billy added Methoed
    def load_triggered_stop_order_data(
        self,
        # symbol: str,
        strategy_name: str,
        start: datetime,
        end: datetime
    ):

        s: QuerySet = DbTriStopOrderData.objects(
            # symbol=symbol,
            strategy_name = strategy_name,
            datetime__gte=convert_tz(start),
            datetime__lte=convert_tz(end),
        ).order_by('datetime')


        stop_orders: List[StopOrder] = []
        for db_stop_order in s:
            db_stop_order.datetime = DB_TZ.localize(db_stop_order.datetime)
            db_stop_order.direction = Direction(db_stop_order.direction)
            db_stop_order.offset = Offset(db_stop_order.offset)
            db_stop_order.status = StopOrderStatus(db_stop_order.status)
            db_stop_order.volume= abs(db_stop_order.volume)
            db_stop_order.first_price = round(db_stop_order.first_price,2)
            db_stop_order.average_price = round(db_stop_order.average_price, 2)
            stop_orders.append(db_stop_order)
        return stop_orders

    # Billy added Methoed
    def load_close_triggered_stop_order_data(
        self,
        # symbol: str,
        strategy_name: str,
    ):

        s: QuerySet = DbTriStopOrderData.objects(
            strategy_name = strategy_name,
            offset = Offset.CLOSE.value,
            open_price__ne = 0.0
        ).order_by('datetime')


        stop_orders: List[StopOrder] = []
        for db_stop_order in s:
            db_stop_order.datetime = DB_TZ.localize(db_stop_order.datetime)
            db_stop_order.direction = Direction(db_stop_order.direction)
            db_stop_order.offset = Offset(db_stop_order.offset)
            db_stop_order.status = StopOrderStatus(db_stop_order.status)
            db_stop_order.first_price = round(db_stop_order.first_price,2)
            db_stop_order.average_price = round(db_stop_order.average_price, 2)
            stop_orders.append(db_stop_order)
        return stop_orders
    # Billy added Methoed
    def load_triggered_all_stop_order_data(
        self,
        # symbol: str,
        start: datetime,
        end: datetime
    ):

        s: QuerySet = DbTriStopOrderData.objects(
            # symbol=symbol,
            datetime__gte=convert_tz(start),
            datetime__lte=convert_tz(end),
        ).order_by('datetime')


        stop_orders: List[StopOrder] = []
        for db_stop_order in s:
            db_stop_order.datetime = DB_TZ.localize(db_stop_order.datetime)
            db_stop_order.direction = Direction(db_stop_order.direction)
            db_stop_order.offset = Offset(db_stop_order.offset)
            db_stop_order.status = StopOrderStatus(db_stop_order.status)
            db_stop_order.first_price = round(db_stop_order.first_price,2)
            db_stop_order.average_price = round(db_stop_order.average_price, 2)
            stop_orders.append(db_stop_order)
        return stop_orders

def to_update_param(d: dict) -> dict:
    """
    Convert data dict to update parameters.
    """
    param = {f"set__{k}": v for k, v in d.items()}
    return param


database_manager = MongodbDatabase()
