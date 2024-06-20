from vnpy.trader.utility import load_json
import datetime

def find_closest_dates(json_data, exchange, symbol, start_date, end_date):
    # 将开始日期和结束日期转换为日期对象
    start_date = datetime.datetime.strptime(start_date, '%Y%m%d').date()
    if end_date:
        end_date = datetime.datetime.strptime(end_date, '%Y%m%d').date()
    else:
        end_date = datetime.date.today()

    # 初始化结果队列
    hot_detail_result = []

    # 遍历 JSON 数据
    for index, item in enumerate(json_data[exchange][symbol]):
        item_date = datetime.datetime.strptime(str(item['date']), '%Y%m%d').date()

        # 如果当前日期大于开始日期且是第一个大于开始日期的
        if item_date > start_date and (len(hot_detail_result) == 0 or item_date > datetime.datetime.strptime(str(hot_detail_result[-1][('date')]), '%Y%m%d').date()):
            hot_detail_result.append(json_data[exchange][symbol][index -1])

        # 如果当前日期大于结束日期且是第一个大于结束日期的
        if item_date > end_date:
            break

    return hot_detail_result

if __name__ == '__main__':
    hot_json_data = load_json("hots.json")
    symbol, variant ,exhcnage = "i.hot.DCE".split(".")
    real_symbol_list = find_closest_dates(hot_json_data,exhcnage,symbol,"20220304","20230408")
    print(real_symbol_list)