# encoding: UTF-8
import json
from datetime import datetime
from vnpy.app.cta_strategy.base import Direction
from vnpy.trader.database import database_manager
from vnpy.trader.utility import load_json
import csv
class SlipSummary:
    """
    Check the slip summary from the triggered stop orders in database.
    """

    def __init__(self):
        # 加载配置
        configfile = "ZhuLiQieHuan/JQDominantConfig.json"
        self.setting = load_json(configfile)
        self.start_date = datetime.strptime(self.setting["start_date"], "%Y%m%d")
        self.check_symbol_dict = self.setting['symbol_list']
        self.symbol_slip_dict = {}


    def get_dbstop_orders(self):
        end = datetime.now()
        dbstop_orders = database_manager.load_triggered_all_stop_order_data(self.start_date, end)
        return dbstop_orders

    def get_symbol_slip(self,symbol):
        underlying_symbol = self.to_underlying_symbol(symbol)
        symbol_slip = self.symbol_slip_dict.get(underlying_symbol, None)
        if not symbol_slip:
            self.symbol_slip_dict[underlying_symbol] = [underlying_symbol,self.check_symbol_dict.get(underlying_symbol,{"name":underlying_symbol}).get("name"),self.check_symbol_dict.get(underlying_symbol,{"PriceTick":1}).get("PriceTick"),
                                                        0,0,0,0]
        return self.symbol_slip_dict[underlying_symbol]

    def get_symbol_order_list(self,underlying_symbol):
        dbstop_orders = self.get_dbstop_orders()
        symbol_order_list = [["品种","策略名","触发时间","多空","开平","挂单价","手数","触发价","均价","首单价"]]
        for stop_order in dbstop_orders:
            if self.to_underlying_symbol(stop_order.vt_symbol)== underlying_symbol:
                symbol_order_list.extend([stop_order.vt_symbol,stop_order.strategy_name,stop_order.datetime,
                                          stop_order.direction.value,stop_order.offset.value,stop_order.price,
                                          stop_order.volume,stop_order.triggered_price,stop_order.average_price,stop_order.first_price])

        return symbol_order_list


    def check_slip(self):
        dbstop_orders = self.get_dbstop_orders()
        for stop_order in dbstop_orders:
            if stop_order.triggered_price == 0:
                pass
            else:
                details = self.get_symbol_slip(stop_order.vt_symbol)
                details[3] = details[3] + stop_order.completed_volume
                if stop_order.direction == Direction.LONG:
                    slipAmout = max(0,stop_order.average_price - stop_order.triggered_price)*stop_order.completed_volume
                elif stop_order.direction == Direction.SHORT:
                    slipAmout = max(0, stop_order.triggered_price - stop_order.average_price) * stop_order.completed_volume
                details[4] = details[4] + slipAmout
                details[5] = round(details[4] /details[3],3)
                details[6] = round(details[5] /details[2],3)

        order_list = [ ["合约", "合约名称", "合约最小变动价格", "总成交手数", "总滑点金额", "平均滑点金额", "平均滑点点位"]]
        order_list.extend(self.symbol_slip_dict.values())
        return order_list


    def exportCSV(self,exportPath, output_data):
        with open(exportPath, "w", encoding='utf-8-sig') as f:
            writer = csv.writer(f, lineterminator="\n")
            if output_data:
                for dborder in output_data:
                    writer.writerow(dborder)

                writer.writerow("")
                writer.writerow("\n")


    def to_underlying_symbol(self, symbol_exchange):
        """
        return underlying_symbol
        """
        symbol, exchange = symbol_exchange.split(".")
        if '2' in symbol[:2]:
            underlying_symbol = symbol[:1]
        else:
            underlying_symbol = symbol[:2]

        return underlying_symbol


if __name__ == '__main__':
    JQdata = SlipSummary()
    output_list = JQdata.get_symbol_order_list("j")
    exportPath = "j_order_list.csv"
    JQdata.exportCSV(exportPath,output_list)
