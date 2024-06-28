import json
import jqdatasdk as jq
from vnpy.trader.mddata import mddata_client
from datetime import datetime

class HotFuturesHandler:

    def __init__(self, hot_code):
        """"""
        self.hot_code = hot_code.upper()
        mddata_client.init()

    def get_daily_contracts(self, start_date, end_date):
        """使用 jqdatasdk 获取每日合约的方法"""
        self.end = end_date
        data = jq.get_dominant_future(self.hot_code, start_date, end_date)
        # 将数据转换为 Series

        return self.process_series(data)


    def process_series(self, series):
        """处理系列数据得到结果队列的方法"""
        result = []
        current_contract = None
        start_date = None

        for date, contract in series.items():
            if contract!= current_contract:
                if current_contract:
                    result.append({
                        "start_date": datetime.strptime(start_date, '%Y-%m-%d'),
                        "end_date": datetime.strptime(date, '%Y-%m-%d'),
                        "contract_code": mddata_client.to_vn_symbol(current_contract)
                    })
                current_contract = contract
                start_date = date


        if current_contract:
            result.append({
                "start_date": datetime.strptime(start_date, '%Y-%m-%d'),
                "end_date":  self.end,
                "contract_code": mddata_client.to_vn_symbol(current_contract)
            })

        return result

    def output_to_json(self, file, data):
        """将数据输出到 JSON 文件的方法"""
        ##TODO: change to vnpy.trader.utility import load_json,save_json
        try:
            with open('output.json', 'r') as f:
                existing_data = json.load(f)
        except FileNotFoundError:
            existing_data = {}


        existing_data[self.hot_code] = data

        with open('output.json', 'w') as f:
            json.dump(existing_data, f)

    def read_json_queue(self, key):
        """根据键读取 JSON 并获取队列的方法"""
        ##TODO: change to vnpy.trader.utility import load_json,save_json
        try:
            with open('output.json', 'r') as f:
                data = json.load(f)
                if key in data:
                    return data[key]
                else:
                    return None
        except FileNotFoundError:
            return None

if __name__=='__main__':
    hot_handler = HotFuturesHandler('IC')
    hotlist = hot_handler.get_daily_contracts(datetime.strptime("2024-1-12", '%Y-%m-%d'),datetime.strptime("2024-1-31" , '%Y-%m-%d'))
    print(hotlist)