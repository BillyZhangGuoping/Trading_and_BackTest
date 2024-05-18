# encoding: UTF-8
import os
from datetime import datetime, timedelta

import jqdatasdk as jq
from vnpy.addon.supplyment import ConfigManager
from vnpy.trader.mddata import mddata_client


class JQDominantCheck:
    """
    Service for download market data from Joinquant
    """

    def __init__(self):
        # 加载配置

        configer = ConfigManager()
        configfile = "JQDominantConfig.json"
        self.filename = configer.build_path("zhuliheyueqiehuan.log")
        self.filename_sequence = configer.build_path("zhuliheyueqiehuan_sequence.log")

        self.setting = configer.read_config(configfile)
        mddata_client.init()

        self.check_days = self.setting["check_days"]
        self.check_symbol_dict = self.setting['symbol_list']

        if self.check_days < 1:
            self.check_days = 1
        self.dominant_change = False
        self.logger = configer.define_logger('check_dominant', self.filename_sequence)


    def check_dominant(self,symbol,startdate,enddate) -> str:
        """
        传入合约名，返回str
        :param symbol:
        :return:
        """
        dominant_symbol_list = jq.get_dominant_future(symbol.upper(),startdate,enddate)

        if dominant_symbol_list is not None:
            last_symbol_series = dominant_symbol_list.tail(self.check_days+1).drop_duplicates()
            if len(last_symbol_series)>1:
                self.dominant_change =True
                strLen = f"请注意 在{list(last_symbol_series.index)[-1]}日，{self.check_symbol_dict.get(symbol).get('name')}({symbol})主力合约切换:{last_symbol_series[-2]} {mddata_client.to_vn_symbol(last_symbol_series[-2])} -> {mddata_client.to_vn_symbol(last_symbol_series[-1])}. "
                self.logger.info(strLen)
        else:
            self.logger.info("主力合约无法确定，检查合约代码")


    def query_dominant_symbols(self):
        """
        Query history bar data from JQData and update Database.
        """

        startdate = datetime.now() - timedelta(days=self.check_days + 10)
        endDate = datetime.now()
        symbol_list = self.check_symbol_dict.keys()
        for symbol in symbol_list:
            self.check_dominant(symbol, startdate, endDate)
        if self.dominant_change == True:
            if not os.path.exists(self.filename):
                # 创建文件
                open(self.filename, 'w').close()
            if self.dominant_change == True:
                with open(self.filename_sequence, encoding="utf-8") as f, open(self.filename, encoding="utf-8",
                                                                               mode='w') as fout:
                    fout.writelines(reversed(f.readlines()))
                os.startfile(self.filename)




if __name__ == '__main__':
    JQdata = JQDominantCheck()
    JQdata.query_dominant_symbols()
# hot_list = jq.get_dominant_future('AU','2018-05-06','2024-05-06')
# print(hot_list[:100])
# JQdatacheck = JQDominantCheck()