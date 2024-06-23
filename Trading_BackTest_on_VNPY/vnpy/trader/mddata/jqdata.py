import jqdatasdk as jq

from datetime import timedelta, datetime
from typing import List

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.mddata.dataapi import MdDataApi
from vnpy.trader.object import BarData, HistoryRequest
from vnpy.trader.setting import SETTINGS
from tzlocal import get_localzone
INTERVAL_VT2JQ = {
    Interval.MINUTE: "1m",
    Interval.HOUR: "60m",
    Interval.DAILY: "1d",
}
from pytz import timezone
CHINA_TZ = timezone("Asia/Shanghai")
INTERVAL_ADJUSTMENT_MAP_JQ = {
    Interval.MINUTE: timedelta(minutes=1),
    Interval.HOUR: timedelta(hours=1),
    Interval.DAILY: timedelta()  # no need to adjust for daily bar
}


class JqdataClient(MdDataApi):
    """聚宽JQData客户端封装类"""

    def __init__(self):
        """"""
        self.username = SETTINGS["jqdata.username"]
        self.password = SETTINGS["jqdata.password"]
        self.jq = jq

        self.inited = False

    def init(self, username="", password=""):
        """"""
        if self.inited:
            return True

        if username and password:
            self.username = username
            self.password = password

        if not self.username or not self.password:
            return False

        try:
            jq.auth(self.username, self.password)
        except Exception as ex:
            print("jq auth fail:" + repr(ex))
            return False

        self.inited = True
        return True

    @staticmethod
    def to_vn_symbol(symbol_exchange):
        """
        CZCE product of RQData has symbol like "TA1905" while
        vt symbol is "TA905.CZCE" so need to add "1" in symbol.
        """
        symbol, exchange = symbol_exchange.split(".")
        if exchange in ["XSHG", "XSHE"]:
            if exchange == "XSHG":
                vt_symbol = f"{symbol}.SSE"  # 上海证券交易所
            else:
                vt_symbol = f"{symbol}.SZSE"  # 深圳证券交易所
        elif exchange == "XSGE":
            vt_symbol = f"{symbol.lower()}.SHFE"  # 上期所
        elif exchange == "CCFX":
            vt_symbol = f"{symbol}.CFFEX"  # 中金所
        elif exchange == "XDCE":
            vt_symbol = f"{symbol.lower()}.DCE"  # 大商所
        elif exchange == "XINE":
            vt_symbol = f"{symbol.lower()}.INE"  # 上海国际能源期货交易所
        elif exchange == "XINE":
            vt_symbol = f"{symbol.lower()}.INE"  # 上海国际能源期货交易所
        elif exchange == "GFEX":
            vt_symbol = f"{symbol.lower()}.GFEX"  # 广州能源期货交易所
        elif exchange == "XZCE":
            # 郑商所 的合约代码年份只有三位 需要特殊处理
            # 回测发现如果是201x的数据，会出现TA1405,转换成TA405情况，和TA2405的VN格式重复，为了避免冲突，
            # 如果是TA1开头，不改为三位，这个代码再203X年代需要再次修改
            # noinspection PyUnboundLocalVariable
            if symbol[2] != '2':
                vt_symbol = f"{symbol}.CZCE"

            else:
                count = 2
                product = symbol[:count]
                month = symbol[count + 1:]
                vt_symbol = f"{product}{month}.CZCE"
        else:
            print(f"{symbol_exchange} 没有对应vt_symbol")

        return vt_symbol

    @staticmethod
    def to_jq_symbol(symbol: str, exchange: Exchange):
        """
        CZCE product of RQData has symbol like "TA1905" while
        vt symbol is "TA905.CZCE" so need to add "1" in symbol.
        """
        if exchange in [Exchange.SSE, Exchange.SZSE]:
            if exchange == Exchange.SSE:
                jq_symbol = f"{symbol}.XSHG"  # 上海证券交易所
            else:
                jq_symbol = f"{symbol}.XSHE"  # 深圳证券交易所
        elif exchange == Exchange.SHFE:
            jq_symbol = f"{symbol}.XSGE"  # 上期所
        elif exchange == Exchange.CFFEX:
            jq_symbol = f"{symbol}.CCFX"  # 中金所
        elif exchange == Exchange.DCE:
            jq_symbol = f"{symbol}.XDCE"  # 大商所
        elif exchange == Exchange.INE:
            jq_symbol = f"{symbol}.XINE"  # 上海国际能源期货交易所
        elif exchange == Exchange.GFEX:
            jq_symbol = f"{symbol}.GFEX"  # 广州期货交易所
        elif exchange == Exchange.CZCE:
            # 郑商所 的合约代码年份只有三位 需要特殊处理
            # 回测发现如果是201x的数据，会出现TA1405,转换成TA405情况，和TA2405的VN格式重复，为了避免冲突，
            # 如果是TA1开头，不改为三位，这个代码再203X年代需要再次修改,此时有特殊处理,如果为4位则直接输出

            for count, word in enumerate(symbol):
                if word.isdigit():
                    break

            # Check for index symbol
            time_str = symbol[count:]
            if time_str in ["88", "888", "99", "8888"] or len(time_str) == 4:
                return f"{symbol}.XZCE"

            # noinspection PyUnboundLocalVariable
            product = symbol[:count]
            year = symbol[count]
            month = symbol[count + 1:]

            if year == "9":
                year = "1" + year
            else:
                year = "2" + year

            jq_symbol = f"{product}{year}{month}.XZCE"

        return jq_symbol.upper()

    def get_dominant_future(self, symbol: str):
        for count, word in enumerate(symbol):
            if word.isdigit():
                break
        # Check for index symbol
        char_str = symbol[:count]
        dominant_future = jq.get_dominant_future(char_str.upper())
        if dominant_future == jq.normalize_code(symbol.upper()):
            return f"{symbol} 是当前主力合约"
        else:
            return f"{symbol} 不是当前主力合约，主力合约是{dominant_future}"

    def get_all_symbol(self,date='2024-03-10'):
        futures = list(jq.get_all_securities(['futures'],date='2024-03-10').index)
        return futures


    def query_history(self, req: HistoryRequest):
        """
        Query history bar data from JQData.
        """
        symbol = req.symbol
        exchange = req.exchange
        interval = req.interval
        start = req.start
        end = req.end

        jq_symbol = self.to_jq_symbol(symbol, exchange)
        # if jq_symbol not in self.symbols:
        #     return None

        jq_interval = INTERVAL_VT2JQ.get(interval)
        if not jq_interval:
            return None

        # For adjust timestamp from bar close point (RQData) to open point (VN Trader)
        adjustment = INTERVAL_ADJUSTMENT_MAP_JQ.get(interval)

        # For querying night trading period data
        # end += timedelta(1)
        if start > end:
            return
        now = datetime.now(get_localzone())
        if end >= now:
            end = now
        elif end.year == now.year and end.month == now.month and end.day == now.day:
            end = now

        df = jq.get_price(
            jq_symbol,
            frequency=jq_interval,
            fields=['open','close','low','high','volume','money',"open_interest",
			'avg'],
            start_date=start,
            end_date=end,
            skip_paused=True
        )

        data: List[BarData] = []

        if df is not None:
            for ix, row in df.iterrows():
                dt = row.name.to_pydatetime() - adjustment
                dt = CHINA_TZ.localize(dt)
                bar = BarData(
                    symbol=symbol,
                    exchange=exchange,
                    interval=interval,
                    datetime=dt,
                    open_price=row["open"],
                    high_price=row["high"],
                    low_price=row["low"],
                    close_price=row["close"],
                    open_interest= row["open_interest"],
                    volume=row["volume"],
                    turnover= row['money'],
                    gateway_name="JQ"
                )
                data.append(bar)

        return data


jqdata_client = JqdataClient()