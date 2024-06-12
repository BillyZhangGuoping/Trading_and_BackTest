from vnpy.app.cta_backtester.engine import BacktesterEngine
from datetime import datetime
from vnpy.trader.engine import EventEngine, MainEngine
from vnpy.app.cta_strategy.strategies.ABR import (
    ABR
)

event_engine = EventEngine()
main_engine = MainEngine(event_engine)
print("主引擎创建成功")

backtester_engine = BacktesterEngine(main_engine = main_engine,event_engine=event_engine)
backtester_engine.init_engine()

strategy_setting = {
    "Kxian":"30m",
    "beishu" : 1.5,
    "Length" : 35,
    "stoploss_percent": 0.00125,
    "HeYueJiaZhi": 1000000,
    "HeYueChengShu": 10
}
backtester_engine.run_backtesting(
    class_name = 'ABR',
    vt_symbol="fu.HOT",
    interval="1m",
    start=datetime(2019, 1, 1),
    end=datetime(2023, 4, 30),
    rate=0.3/10000,
    slippage=0.2,
    size=10,
    pricetick=1,
    capital=1_000_000,
    inverse = False,
    setting = strategy_setting
)
engine = backtester_engine.backtesting_engine
# engine.load_data()
# engine.run_backtesting()
# df = engine.calculate_result()
# engine.calculate_statistics()
engine.show_chart()