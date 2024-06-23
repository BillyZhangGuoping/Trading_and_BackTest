# encoding: UTF-8
import json
import ast
import time
import traceback
from datetime import datetime, date,timedelta
import pandas as pd
from pandas import DataFrame
from vnpy.app.cta_strategy.backtesting import BacktestingEngine, OptimizationSetting
from vnpy.trader import optimize
# 策略类是用字符串格式记录的，然后用eval方法关联类，所以必须引用，虽然编辑器提示未使用
from vnpy.app.cta_strategy.strategies.bar_jump_trend_bt import BT_BarJumpTrendDownStrategy
from vnpy.app.cta_strategy.strategies.bar_ma_trend import BarMaTrendStrategy
from vnpy.app.cta_strategy.strategies.king_keltner_strategy import KingKeltnerStrategy
from vnpy.app.cta_strategy.strategies.turtle_signal_strategy import TurtleSignalStrategy
from vnpy.app.cta_strategy.strategies.double_ma_strategy import DoubleMaStrategy
from vnpy.app.cta_strategy.strategies.bar_ema_trend import BarEMaTrendStrategy
from vnpy.app.cta_strategy.strategies.bar_ema_trend_actual import BarEMaTrendActaulStrategy
from vnpy.app.cta_strategy.strategies.atr_rsi_strategy import (
    AtrRsiStrategy,
)
from vnpy.app.cta_strategy.strategies.bt_bar_bbiboll_trend import (
    BT_BarBBIBOLLStrategy
)
from vnpy.app.cta_strategy.strategies.bar_jump_trend_bt import BT_BarJumpTrendDownStrategy
class BatchCTABackTest:
	"""
	提供批量CTA策略回测，输出结果到excel或pdf，和CTA策略批量优化，输出结果到excel或pdf，
	"""

	def __init__(self, vtSymbolconfig="SymbolSize.json", exportpath="C:\\test_data\\OPNEW\\"):
		"""
		加载配置路径
		"""
		config = open(vtSymbolconfig)
		self.setting = json.load(config)
		self.exportpath = exportpath
		self.engine =BacktestingEngine()

	def addParameters(self, engine, vt_symbol: str, startDate, endDate, interval="1m", capital=1000000):
		"""
		从vtSymbol.json文档读取品种的交易属性，比如费率，交易每跳，比率，滑点
		"""
		vt_symbol_short = vt_symbol[:2]
		if vt_symbol_short in self.setting:
			engine.set_parameters(
				vt_symbol=vt_symbol,
				interval=interval,
				start=startDate,
				end=endDate,
				rate=self.setting[vt_symbol_short]["rate"],
				slippage=self.setting[vt_symbol_short]["slippage"],
				size=self.setting[vt_symbol_short]["size"],
				pricetick=self.setting[vt_symbol_short]["pricetick"],
				capital=capital
			)
		else:
			print("symbol %s hasn't be maintained in config file" % vt_symbol)
		return engine

	def runBatchTestMultiple(self, strategy_setting, startDate, endDate):
		"""
		进行回测
		"""
		resultDf = DataFrame()
		vt_symbol = strategy_setting[0]["symbol"]
		class_name = strategy_setting[0]["class_name"]
		param_settings = []

		for strategy_name, strategy_config in strategy_setting.items():
			param_settings.append(ast.literal_eval(strategy_config["setting"]))

		self.engine.clear_data()
		self.engine = self.addParameters(self.engine, vt_symbol, startDate,
										 endDate)
		self.engine.add_strategy(eval(class_name),"1-1",{})
		setting = OptimizationSetting()
		setting.set_target("sharpe_ratio")
		setting.settings = param_settings

		result = self.engine.run_bf_optimization(setting,output=False)

		return result

	def runBatchTest(self, strategy_setting, startDate, endDate, portfolio = False):
		"""
		进行回测
		"""
		resultDf = DataFrame()
		dfportfolio = None
		for strategy_name, strategy_config in strategy_setting.items():
			self.engine.clear_data()
			vt_symbol = strategy_config["symbol"]
			self.engine = self.addParameters(self.engine, vt_symbol, startDate, endDate)
			if type(strategy_config["setting"]) is str:
				print(eval(strategy_config["setting"]))
				self.engine.add_strategy(
					eval(strategy_config["class_name"]),
					"2-2",
					# json.loads(strategy_config["setting"])
					ast.literal_eval(strategy_config["setting"])
				)
			else:
				self.engine.add_strategy(
					json.loads(strategy_config["class_name"]),
					ast.literal_eval(strategy_config["setting"])
				)
			self.engine.load_data()
			self.engine.run_backtesting()
			df = self.engine.calculate_result()
			if portfolio == True:
				if dfportfolio is None:
					dfportfolio = df
				else:
					dfportfolio = dfportfolio + df
			resultDict = self.engine.calculate_statistics()
			resultDict["0strategy_name"] = strategy_name
			resultDict["1class_name"] = strategy_config["class_name"]
			resultDict["3setting"] = strategy_config["setting"]
			resultDict["2vt_symbol"] = strategy_config["symbol"]
			resultDf = resultDf.append(resultDict, ignore_index=True)

		if portfolio == True:
			# dfportfolio = dfportfolio.dropna()
			self.engine = BacktestingEngine()
			self.engine.calculate_statistics(dfportfolio)
			self.engine.show_chart(dfportfolio)

		return resultDf

	def runBatchTestJson(self, jsonpath="ctaStrategy.json", startDate=datetime(2022, 9, 1),
	                     endDate=datetime(2023, 3, 1), exporpath=None, portfolio=False):
		"""
		从ctaStrategy.json去读交易策略和参数，进行回测
		"""
		with open(jsonpath, mode="r", encoding="UTF-8") as f:
			strategy_setting = json.load(f)
		resultDf = self.runBatchTest(strategy_setting, startDate, endDate, portfolio)
		self.ResultExcel(resultDf, exporpath)
		return strategy_setting

	def runBatchOptimationJson(self,jsonpath = 'Optimization.json', OpApproach = "bf",target ="sharpe_ratio",startDate=datetime(2023,6, 1), endDate=datetime(2023, 11, 15) ,exporpath=None):
		with open(jsonpath, mode="r", encoding="UTF-8") as f:
			Optimze_setting_list = json.load(f)
		for optimaztionName, optimzation_Setting in Optimze_setting_list.items():
			result = self.Optimize(optimzation_Setting,OpApproach,target,startDate, endDate)
			optimaztionNameTest = optimzation_Setting["class_name"] + "+" + optimzation_Setting["vt_symbol"]
			self.ResultExcel(result,optimaztionNameTest,exporpath)



	def Optimize(self,optimzation_Setting, OpApproach = "bf",target ="sharpe_ratio",startDate=datetime(2021, 3, 1), endDate=datetime(2021, 9, 1)):

		self.engine.clear_data()
		vt_symbol = optimzation_Setting["vt_symbol"]
		opimization_setting = optimzation_Setting["setting"]
		self.engine = self.addParameters(self.engine, vt_symbol, datetime.strptime(optimzation_Setting["startDate"],"%Y-%m-%d"),
										 datetime.strptime(optimzation_Setting["endDate"],"%Y-%m-%d"))
		self.engine.add_strategy(eval(optimzation_Setting["class_name"]),"1-1",{})
		setting = OptimizationSetting()
		setting.set_target(target)
		for key, params in opimization_setting.items():
			if isinstance(params,list):
				setting.add_parameter(key, params[0], params[1], params[2])
			else:
				setting.add_parameter(key, params)
		if OpApproach == "GA":
			result = self.engine.run_ga_optimization(setting,output=False)
		else:
			result = self.engine.run_bf_optimization(setting,output=False)

		return result[:2000]


	def runBatchTestExcecl(self, path="ctaStrategy.xlsx",startDate=datetime(2019,6,8),
	                     endDate=datetime(2019, 12, 1), vt_symbol = None, exporpath=None, mutiple = False):
		"""
		从ctaStrategy.excel去读交易策略和参数，进行回测
		"""
		df = pd.read_excel(path)
		strategy_setting = df.to_dict(orient='index')
		if vt_symbol:
			# strategy_setting["vt_symbol"] = vt_symbol
			for strategy_name, strategy_config in strategy_setting.items():
				strategy_config["symbol"] = vt_symbol
		if mutiple:
			resultDf = self.runBatchTestMultiple(strategy_setting, startDate, endDate)
		else:
			resultDf = self.runBatchTest(strategy_setting, startDate, endDate)

		exportname = "BatchTestExcel_" + strategy_setting[0]['class_name'] +"+" + vt_symbol
		self.ResultExcel(resultDf, exportname, exporpath)
		return strategy_setting

	def ResultExcel(self, result, exportfileName = "CTABatch",export=None):
		"""
		输出交易结果到excel
		"""
		if export != None:
			exportpath = export
		else:
			exportpath = self.exportpath
		try:
			path = exportpath + exportfileName + datetime.now().strftime("%Y%m%d_%H%M")+ ".xlsx"
			if isinstance(result,list):
				resultdf = DataFrame()
				className = exportfileName.split("+")[0]
				symbol= exportfileName.split("+")[1]
				for resultItem in result:
					itemDict = {}
					itemDict["class_name"] = className
					itemDict["symbol"] = symbol
					itemDict["setting"] = resultItem[0]
					itemDict["Target"] = resultItem[1]
					itemDict.update(resultItem[2])
					resultdf = resultdf.append(itemDict, ignore_index=True)
			else:
				resultdf = result

			resultdf.to_excel(path, index=False)
			# path = exportpath + exportfileName + datetime.now().strftime("%Y%m%d_%H%M") + ".csv"
			# resultdf.to_csv(path_or_buf = path,index = False)
			print("CTA Batch result is export to %s" % path)
		except:
			print(traceback.format_exc())

		return None

	def runSingleBackTesting(self,vt_symbol,class_name,strategy_setting, startDate=datetime(2022, 6, 4),
	                       endDate=datetime(2022, 11, 9),showGraph = True):
		self.engine = self.addParameters(self.engine, vt_symbol, startDate, endDate)
		self.engine.clear_data()
		self.engine.add_strategy(class_name,"1-1",strategy_setting)
		self.engine.load_data()
		self.engine.run_backtesting()
		self.engine.calculate_result()
		self.engine.calculate_statistics()

		if showGraph == True:
			self.engine.show_chart()


if __name__ == '__main__':
	
	starttime = datetime.now()

	bts = BatchCTABackTest()
	bts.runBatchOptimationJson()

	print("starttime: %s and fisish time: %s" %(starttime,datetime.now()))

	print("cost time : %s" %str(datetime.now()-starttime))

	# strategy_setting = {'init_pos': 0, 'init_entry_price': 0, 'fixed_size': 1, 'HeYueJiaZhi': 100000, 'HeYueChengShu': 10.0, 'CLOSE_WINDOWS': 40, 'OPEN_WINDOWS': 30, 'TRUN_OPEN_LIMIT': 4, 'TURN_CLOSE_LIMIT': 4, 'Kxian': 1, 'STOP_TRADE': 0, 'JUMP': 6, 'RATIO': 0, 'RATIO2': 0.2, 'RATIO3': 0.4, 'MARK_DOWN': 10, 'MARK_UP': 4}
	# bts.runSingleBackTesting("fu2403.SHFE",BT_BarJumpTrendDownStrategy,strategy_setting)





