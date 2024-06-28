# encoding: UTF-8

import json
import time
from datetime import datetime, timedelta
from typing import List
import pandas as pd
import jqdatasdk as jq
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.mddata import mddata_client
from vnpy.trader.object import (
	BarData
)
from vnpy.addon.hotfutures import HotFuturesHandler


class JQDataService:
	"""
	Service for download market data from Joinquant
	"""

	def __init__(self):
		# 加载配置
		config = open('./JQDataConfig.json')
		self.setting = json.load(config)

		self.max_min_days = 0
		self.symbol_data_dict = {}

		mddata_client.init()


	def query_history(self, symbol, exchange, start, end, interval='1m',save_base = True):
		"""
		Query history bar data from JQData and update Database.
		"""

		jq_symbol = mddata_client.to_jq_symbol(symbol, exchange)
		# if jq_symbol not in self.symbols:
		#     return None

		# For querying night trading period data
		# end += timedelta(1)
		now =  datetime.now()
		if end >= now:
			end = now
		elif end.year == now.year and end.month == now.month and end.day == now.day:
			end = now

		df = jq.get_price(
			jq_symbol,
			frequency=interval,
			fields=['open','high','low','close','volume','money','high_limit',
					'low_limit','avg','open_interest'],
			start_date=start,
			end_date=end,
			skip_paused=True
		)

		# data: List[BarData] = []
		#
		# if df is not None:
		# 	for ix, row in df.iterrows():
		# 		bar = BarData(
		# 			symbol=symbol,
		# 			exchange=exchange,
		# 			interval=Interval.MINUTE,
		# 			datetime=row.name.to_pydatetime() - timedelta(minutes=1),
		# 			open_price=row["open"],
		# 			high_price=row["high"],
		# 			low_price=row["low"],
		# 			close_price=row["close"],
		# 			volume=row["volume"],
		# 			open_interest=row["open_interest"],
		# 			gateway_name="JQ"
		# 		)
		# 		data.append(bar)

		return df

	def downloadAllMinuteBar(self, days=0,startDt = 0):
		"""下载所有配置中的合约的分钟线数据"""
		if days == 0:
			days = self.setting["days"]
		if startDt == 0:
			startDt = datetime.today() - days * timedelta(1)
			enddt = datetime.today()
		else:
			enddt = startDt + days * timedelta(1)

		print('-' * 50)
		print(u'开始下载合约分钟线数据')
		print('-' * 50)

		if 'Bar.Min' in self.setting:
			l = self.setting["Bar.Min"]
			for VNSymbol in l:
				dt0 = time.process_time()
				symbol = VNSymbol.split(".")[0]
				exchange = Exchange(VNSymbol.split(".")[1])
				self.query_history(symbol, exchange, startDt, enddt, interval='1m')
				cost = (time.process_time() - dt0)
				print(u'合约%s的分钟K线数据下载完成%s - %s，耗时%s秒' % (symbol, startDt, enddt, cost))
				print(jq.get_query_count())
			print('-' * 50)
			print(u'合约数据下载完成')
			print('-' * 50)
		return

	def compareMaxMin(self,rangeday = 365, days = 3):
		startDt = (datetime.today() - rangeday * timedelta(1)).strftime("%Y-%m-%d")
		compareResult = ""
		self.downloadAllDayBar(rangeday)
		for key,value in self.symbol_data_dict.items():
			compareResult+=self.maxminCompare(value,key,startDt, rangeday, days)
		return compareResult

	def new_MaxMin(self,rangeday = 365, days = 1):
		startDt = (datetime.today() - days * timedelta(1)).strftime("%Y-%m-%d")
		compareResult = ""
		self.downloadAllDayBar(rangeday)
		for key,value in self.symbol_data_dict.items():
			compareResult += self.newCompare(value, key, startDt, days)
		return compareResult

	def downloadHotSymbol(self,hot_symbol,startDt = 0,enddt = 0):
		"""传入合约头两位，转为主力合约字典，然后使用query_history输出dataframe，
		再增加一行作为合约名称，最后用save_to_csv
		"""

		startDt  = startDt
		enddt = enddt
		hot_handler = HotFuturesHandler(hot_symbol)
		download_list = hot_handler.get_daily_contracts(startDt, enddt)
		# 生成空的 DataFrame
		hotdf_list = []
		for backtest_item in download_list:
			start = backtest_item['start_date']
			end = backtest_item['end_date']
			VNSymbol = backtest_item['contract_code']
			print(
				f"----------------------"
				f"从{backtest_item['start_date']} 到 {backtest_item['end_date']} 的"
				f"主力合约是 {backtest_item['contract_code']}")
			symbol = VNSymbol.split(".")[0]
			exchange = Exchange(VNSymbol.split(".")[1])
			df = self.query_history(symbol, exchange, start - timedelta(days= 15), end, interval='1d')
			df['pre_close'] = df['close'].shift(1)
			df = df.iloc[1:]  # 删除第一行
			df['symbol'] = VNSymbol
			col_a = df['symbol']
			df = df.drop('symbol', axis=1)
			df.insert(0, 'symbol', col_a)
			  # 请将此处替换为您实际的起始日期
			new_df = df[df.index >= start]

			hotdf_list.append(new_df)
		hot_daily_result = pd.concat(hotdf_list)
		self.save_csv_more(resultData=hot_daily_result,name= hot_symbol)

	def downloadAllDayBar(self, days=0,startDt = 0):
		"""下载所有配置中的合约的分钟线数据"""
		if days == 0:
			days = self.setting["days"]
		if startDt == 0:
			startDt = datetime.today() - days * timedelta(1)
			enddt = datetime.today()
		else:
			enddt = startDt + days * timedelta(1)

		print('-' * 50)
		print(u'开始下载日期日线数据')
		print('-' * 50)

		if 'Bar.Min' in self.setting:
			l = self.setting["Bar.Min"]
			for VNSymbol in l:
				dt0 = time.process_time()
				symbol = VNSymbol.split(".")[0]
				exchange = Exchange(VNSymbol.split(".")[1])
				df = self.query_history(symbol, exchange, startDt, enddt, interval='1d')

				cost = (time.process_time() - dt0)
				print(u'合约%s的日K线数据下载完成%s - %s，耗时%s秒' % (symbol, startDt, enddt, cost))
				print(jq.get_query_count())
				self.symbol_data_dict[VNSymbol] = df
			print('-' * 50)
			print(u'合约数据下载完成')
			print('-' * 50)

		return None

	def maxminCompare(self,bar_df,VNSymbol,startDt, rangeday, days):
		compareResult = ""
		bar_max = bar_df["high"]
		bar_min = bar_df["low"]
		if max(bar_max) == max(bar_max.tail(days)):
			compareResult += f"{VNSymbol} : 存在从{startDt}至今的{rangeday}天 最高价 在最近{days}日中.\n"
		elif min(bar_min) == min(bar_min.tail(days)):
			compareResult += f"{VNSymbol} : 存在从{startDt}至今的{rangeday}天 最低价 在最近{days}日中. \n"
		return compareResult

	def newCompare(self,bar_df,VNSymbol,startDt, days):
		compareResult = ""
		bar_max = bar_df["high"]
		bar_min = bar_df["low"]
		longdays = days*3
		if max(bar_max) == max(bar_max.tail(days)) and max(bar_max[:-days]) != max(bar_max[:-days].tail(longdays)):
			compareResult += f"{VNSymbol} : 存在从{startDt}至今的{days}天 最高价在最近{days}日中,且在之前{longdays}日没有最高点.\n"
		elif min(bar_min) == min(bar_min.tail(days)) and min(bar_min[:-days]) != min(bar_min[:-days].tail(longdays)):
			compareResult += f"{VNSymbol} : 存在从{startDt}至今的{days}天 最低价在最近{days}日中，且在之前{longdays}日没有最低高点 \n"
		return compareResult

	def downloadSymbol(self,vt_symbol,startDt,endDt,interval):

		print('-' * 50)
		print(u'开始下载%s线数据' %(interval))
		print('-' * 50)

		dt0 = time.process_time()
		symbol = vt_symbol.split(".")[0]
		exchange = Exchange(vt_symbol.split(".")[1])
		resultdata = self.query_history(symbol, exchange, startDt, endDt, interval=interval,save_base = False)
		cost = (time.process_time() - dt0)
		print(u'合约%s的下载完成%s - %s，耗时%s秒, 条数 %s' % (symbol, startDt, endDt, cost, len(resultdata)))
		print(jq.get_query_count())
		print('-' * 50)
		print(u'合约数据下载完成')
		print('-' * 50)

		return resultdata

	def downloadtick(self,vt_symbol,startDt,endDt):

		dt0 = time.process_time()
		symbol = vt_symbol.split(".")[0]
		exchange = Exchange(vt_symbol.split(".")[1])
		jq_symbol = mddata_client.to_jq_symbol(symbol, exchange)
		df = jq.get_ticks(jq_symbol, startDt, endDt, fields = None, skip=True,df=True)
		cost = (time.process_time() - dt0)
		print(u'合约%s的下载完成%s - %s，耗时%s秒, 条数 %s' % (symbol, startDt, endDt, cost, len(df)))

		return df


	def save_csv_more(self,resultData,name = "data") -> None:
		"""
        Save table data into a csv file
        """
		# path, _ = QtWidgets.QFileDialog.getSaveFileName(
		# 	self, "保存数据", "", "xls(*.xls)")
		path = "C:\\test_data\\" + name + ".csv"
		if not path:
			return
		# resultdata.to_excel(path)
		with open(path, "w", encoding='utf-8-sig') as f:
			resultData.to_csv(path)


if __name__ == '__main__':
	JQdata = JQDataService()
	date_str = '2014-1-15'
	date = datetime.strptime(date_str, '%Y-%m-%d')
	enddt = date.today()
	symol_list = mddata_client.get_all_symbol(date =enddt)
	filtered_symbols = [symbol for symbol in symol_list if '8888' in symbol]
	new_list = list(set([symbol.split('8888')[0] for symbol in filtered_symbols]))

	# JQdata.downloadHotSymbol("TA", startDt=date, enddt=enddt)
	starttime = datetime.now()
	for hot in new_list:
		print(hot)
		JQdata.downloadHotSymbol(hot,startDt=date,enddt = enddt)
	print("starttime: %s and fisish time: %s" %(starttime,datetime.now()))

	print("cost time : %s" %str(datetime.now()-starttime))

