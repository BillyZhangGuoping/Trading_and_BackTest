# encoding: UTF-8

from datetime import datetime, timedelta
import jqdatasdk as jq
import os
from vnpy.trader.supplyment import ConfigManager

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

		USERNAME = self.setting['jqdata.Username']
		PASSWORD = self.setting['jqdata.Password']
		self.check_days = self.setting["check_days"]
		self.check_symbol_dict = self.setting['symbol_list']

		if self.check_days < 1:
			self.check_days = 1
		self.dominant_change = False
		self.logger = configer.define_logger('check_dominant', self.filename_sequence)

		try:
			jq.auth(USERNAME, PASSWORD)
		except Exception as ex:
			print("jq auth fail:" + repr(ex))

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
				strLen = f"请注意 在{list(last_symbol_series.index)[-1]}日，{self.check_symbol_dict.get(symbol).get('name')}({symbol})主力合约切换:{last_symbol_series[-2]} {self.to_vn_symbol(last_symbol_series[-2])} -> {self.to_vn_symbol(last_symbol_series[-1])}. "
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

	def to_vn_symbol(self, symbol_exchange):
		"""
		CZCE product of RQData has symbol like "TA1905" while
		vt symbol is "TA905.CZCE" so need to add "1" in symbol.
		"""
		symbol,exchange = symbol_exchange.split(".")
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
		elif exchange == "XZCE":
			# 郑商所 的合约代码年份只有三位 需要特殊处理


			# noinspection PyUnboundLocalVariable
			count = 2
			product = symbol[:count]
			month = symbol[count + 1:]
			vt_symbol = f"{product}{month}.CZCE"

		return vt_symbol


if __name__ == '__main__':
	JQdata = JQDominantCheck()
	JQdata.query_dominant_symbols()
# JQdatacheck = JQDominantCheck()