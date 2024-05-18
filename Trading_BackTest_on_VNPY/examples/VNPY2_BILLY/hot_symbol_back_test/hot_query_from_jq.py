import json
import jqdatasdk as jq
from vnpy.addon.supplyment import ConfigManager
from vnpy.trader.mddata import mddata_client
class FuturesHandler:

    def __init__(self, hot_code):
        self.hot_code = hot_code.upper()
        configer = ConfigManager()
        configfile = "JQDominantConfig.json"
        mddata_client.init()
        self.setting = configer.read_config(configfile)

    def get_daily_contracts(self, start_date, end_date):
        """使用 jqdatasdk 获取每日合约的方法"""
        # 使用 jqdatasdk 获取主力合约数据
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
                if current_contract is not None:
                    result.append({
                        "start_date": start_date,
                        "end_date": date,
                        "contract_code": mddata_client.to_vn_symbol(current_contract)
                    })
                current_contract = contract
                start_date = date

        if current_contract is not None:
            result.append({
                "start_date": start_date,
                "end_date": "None",
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
    hot_handler = FuturesHandler('i')
    hotlist = hot_handler.get_daily_contracts("2021-5-12","2024-4-1")
    print(hotlist)