import jqdatasdk as jq
import talib
import numpy as np
import pandas as pd
from vnpy.trader.mddata import mddata_client
from vnpy.trader.constant import Exchange
from collections import deque
from vnpy.trader.utility import load_json,get_folder_path
from datetime import datetime
import webbrowser
class TrendFutureAnalyzer:
    def __init__(self,  days=200):
        self.days = days
        setting = load_json("JQDataConfig.json")
        self.symbol_list = setting["Bar.Min"]


    def review_symbol_list(self):
        self.login_jq()
        tofile = []
        for symbol in self.symbol_list:
            df = self.calculate_emas(future_code = symbol,periods =[3,5,10,20,30,60])
            tofile.append(self.check_trend(df))

        # 获取当天日期并生成文件名
        today = datetime.today().strftime("%Y%m%d")
        fold_path = get_folder_path("trendquery")
        file_name = fold_path.joinpath(f"{today}.html")

        html_content = "<html><body>"

        for string in tofile:
            if string != "":
                if "均线向上" in string:
                    html_content += f"<p style='color:red;'>{string}</p>"
                elif "均线向下" in string:
                    html_content += f"<p style='color:green;'>{string}</p>"
                else:
                    html_content += f"<p>{string}</p>"

        html_content += "</body></html>"

        with open(file_name, 'w', encoding='UTF-8') as f:  # 指定编码写入文件
            f.write(html_content)

        # 自动打开网页
        webbrowser.open(file_name)

    def login_jq(self):
        # 登录聚宽数据
        mddata_client.init()

    def get_close_prices(self):
        # 获取指定期货合约最近指定天数的收盘价数据
        data = jq.get_price(self.future_code, end_date=datetime.now(), count=self.days, fields=['close'])
        return np.array(data['close'])

    def calculate_ema(self, close_prices, timeperiod):
        # 计算指定时间周期的移动均线
        ema = talib.EMA(close_prices, timeperiod=timeperiod)
        return ema

    def calculate_emas(self, future_code, periods):
        symbol, exchange = future_code.split('.')
        self.future_code = mddata_client.to_jq_symbol(symbol, Exchange(exchange))
        close_prices = self.get_close_prices()
        ema_results = [self.calculate_ema(close_prices, period) for period in periods]
        df = pd.DataFrame({period: result for period, result in zip(periods, ema_results)})

        # 在最左边添加一列
        df.insert(0, '1', close_prices)

        comparison_column = []
        for index in range(len(df)):  # 从第一行开始
            has_null = any(pd.isnull(df.loc[index, col]) for col in df.columns)  # 检查此行是否有任何空值
            if has_null:
                comparison_column.append(0)
                continue

            row_values = df.loc[index].values.tolist()
            queue = deque(row_values)
            is_increasing = all(queue[i] <= queue[i + 1] for i in range(len(queue) - 1))
            is_decreasing = all(queue[i] >= queue[i + 1] for i in range(len(queue) - 1))

            if is_increasing:
                comparison_column.append(-1)
            elif is_decreasing:
                comparison_column.append(1)
            else:
                comparison_column.append(0)
        df['Comparison_Result'] = comparison_column
        return df

    def check_trend(self, df):
        comparison_result = df['Comparison_Result'].values[::-1]  # 获取倒序的数组
        output = f"{mddata_client.to_vn_symbol(self.future_code)}:"

        if comparison_result[0] == 1:
            count = 1
            for i in range(1, len(comparison_result)):
                if comparison_result[i] == 1:
                    count += 1
                else:
                    break
            output = output + f"均线向上排列，已有{count}个交易日"
        elif comparison_result[0] == -1:
            count = 1
            for i in range(1, len(comparison_result)):
                if comparison_result[i] == -1:
                    count += 1
                else:
                    break
            output = output + f"均线向下排列，已有{count}个交易日"
        else:
            count = 0
            for value in comparison_result:
                if value!= 0:
                    break
                count += 1
            if comparison_result[count] == 1:
                output = output + f"在{count}个交易日之前，均线上"
            elif comparison_result[count] == -1:
                output = output + f"在{count}个交易日之前，均线下"
        return output

if __name__ == "__main__":
    futuretrend =TrendFutureAnalyzer()
    futuretrend.review_symbol_list()