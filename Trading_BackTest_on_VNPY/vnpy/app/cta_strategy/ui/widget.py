import copy
import csv
from datetime import datetime, timedelta
from typing import Any

from PyQt5 import QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import *
from pandas import DataFrame
from tzlocal import get_localzone
from vnpy.app.cta_backtester.ui.widget import BacktesterChart
from vnpy.app.cta_strategy.backtesting import BacktestingEngine
from vnpy.event import Event, EventEngine
from vnpy.trader.constant import (
    Direction
)
from vnpy.trader.database import database_manager
from vnpy.trader.engine import MainEngine
from vnpy.trader.slip_summary.SlipSummary import SlipSummary
from vnpy.trader.ui import QtCore, QtWidgets
from vnpy.trader.ui.widget import (
    BaseCell,
    EnumCell,
    MsgCell,
    TimeCell,
    PnlCell,
    PercentCell,
    DatetimeCell,
    DirectionCell,
    BaseMonitor
)

from .rollover import RolloverTool
from ..base import (
    APP_NAME,
    EVENT_CTA_LOG,
    EVENT_CTA_STOPORDER,
    EVENT_CTA_DISPLAY_TRADE,
    EVENT_CTA_STRATEGY,
    EVENT_CTA_TRADE,
    EVENT_CTA_TRIGGERED_STOPORDER
)
from ..engine import CtaEngine


class CtaManager(QtWidgets.QWidget):
    """"""

    signal_log = QtCore.pyqtSignal(Event)
    signal_strategy = QtCore.pyqtSignal(Event)
    signal_trade_strategy = QtCore.pyqtSignal(Event)
    signal_triggered_stoporder_strategy = QtCore.pyqtSignal(Event)

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine):
        super(CtaManager, self).__init__()

        self.main_engine = main_engine
        self.event_engine = event_engine
        self.cta_engine = main_engine.get_engine(APP_NAME)
        self.rowRecent = 1

        self.managergroup = {}
        self.managers = {}
        self.manager_locations = {}

        self.init_ui()
        self.register_event()
        self.cta_engine.init_engine()
        self.update_class_combo()
        self.currentStrategyName = "showRowInform"

    def init_ui(self):
        """"""
        self.setWindowTitle("CTA策略")

        # Create widgets
        self.class_combo = QtWidgets.QComboBox()

        account_button = QtWidgets.QPushButton("账户权益")
        account_button.clicked.connect(self.account_summary)

        slip_button = QtWidgets.QPushButton("滑点统计")
        slip_button.clicked.connect(self.slip_summary)

        deal_button = QtWidgets.QPushButton("交易统计")
        deal_button.clicked.connect(self.deal_summary)

        add_button = QtWidgets.QPushButton("添加策略")
        add_button.clicked.connect(self.add_strategy)

        init_button = QtWidgets.QPushButton("全部初始化")
        init_button.clicked.connect(self.cta_engine.init_all_strategies)

        start_button = QtWidgets.QPushButton("全部启动")
        start_button.clicked.connect(self.cta_engine.start_all_strategies)

        stop_button = QtWidgets.QPushButton("全部停止")
        stop_button.clicked.connect(self.cta_engine.stop_all_strategies)

        clear_button = QtWidgets.QPushButton("清空日志")
        clear_button.clicked.connect(self.clear_log)

        roll_button = QtWidgets.QPushButton("移仓助手")
        roll_button.clicked.connect(self.roll)

        self.scroll_layout = QtWidgets.QGridLayout()
        self.scroll_layout.setAlignment(QtCore.Qt.AlignTop)
        # self.scroll_layout.setHorizontalSpacing(1)

        # for rowI in range(self.rowRecent):
        #     for columnJ in range(10):
        #         label1 = QtWidgets.QFrame()
        #         label1.setMinimumSize(130,100)
        #         label1.setStyleSheet("background-color:black;")
        #         self.scroll_layout.addWidget(label1,rowI,columnJ,QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

        scroll_widget = QtWidgets.QWidget()
        scroll_widget.setLayout(self.scroll_layout)

        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll_widget)

        self.log_monitor = LogMonitor(self.main_engine, self.event_engine)

        self.stop_order_monitor = StopOrderMonitor(
            self.main_engine, self.event_engine
        )

        self.cta_trade_monitor = StrategyTradeMonitor(
            self.main_engine, self.event_engine
        )

        self.trigerred_stoporder_monitor = TriggeredStopOrderMonitor(
            self.main_engine, self.event_engine, self
        )
        self.main_engine.addWidgetForCSVExport("trigerred_stoporder", self.trigerred_stoporder_monitor)
        self.tw = QtWidgets.QTabWidget()
        self.tw.addTab(self.trigerred_stoporder_monitor, '触发委托')
        self.tw.addTab(self.cta_trade_monitor, '成交')
        self.tw.tabBarClicked.connect(lambda indexI: self.hideAllOtherRow())

        # Set layout
        hbox1 = QtWidgets.QHBoxLayout()
        hbox1.addWidget(self.class_combo)
        hbox1.addWidget(add_button)
        hbox1.addStretch()
        hbox1.addWidget(init_button)
        hbox1.addWidget(start_button)
        hbox1.addWidget(stop_button)
        hbox1.addWidget(clear_button)
        hbox1.addWidget(roll_button)
        hbox1.addWidget(slip_button)
        hbox1.addWidget(deal_button)
        hbox1.addWidget(account_button)
        labelRightTop = QtWidgets.QFrame()
        labelRightTop.setMinimumWidth(280)
        hbox1.addWidget(labelRightTop)
        # QtWidgets.QVBoxLayout()

        NewVQbox1 = QtWidgets.QVBoxLayout()
        NewVQbox1_widget = QtWidgets.QWidget()
        self.LeftInfromFrame = QtWidgets.QStackedWidget()
        self.LeftInfromFrame.setMinimumHeight(412)
        self.LeftInfromFrame.setMinimumWidth(300)
        self.tw.setFixedWidth(300)

        NewVQbox1.addWidget(self.LeftInfromFrame, QtCore.Qt.AlignTop)
        NewVQbox1.addWidget(self.tw, QtCore.Qt.AlignTop)
        NewVQbox1_widget.setLayout(NewVQbox1)
        NewVQbox1_widget.setMaximumWidth(302)

        NewHQbox1 = QtWidgets.QHBoxLayout()
        NewHQbox1.setAlignment(QtCore.Qt.AlignLeft)
        NewHQbox1.addWidget(NewVQbox1_widget)
        NewHQbox1.addWidget(scroll_area)

        labelRight = QtWidgets.QFrame()
        labelRight.setMinimumWidth(200)
        # NewVQbox1.addWidget(labelRight)

        VQbox1_widget = QtWidgets.QWidget()
        VQbox1_widget.setLayout(NewHQbox1)

        grid = QtWidgets.QGridLayout()
        grid.setSpacing(1)
        grid.addWidget(VQbox1_widget, 0, 0, 1, 2)
        grid.addWidget(self.stop_order_monitor, 1, 0, QtCore.Qt.AlignBottom)
        grid.addWidget(self.log_monitor, 1, 1, QtCore.Qt.AlignBottom)
        grid.addWidget(labelRight, 0, 2, 0, 2)

        vbox = QtWidgets.QVBoxLayout()
        vbox.addLayout(hbox1)
        vbox.addLayout(grid)
        self.setLayout(vbox)

    def addMonitorGroup(self):
        pass

    def update_class_combo(self):
        """"""
        self.class_combo.addItems(
            self.cta_engine.get_all_strategy_class_names()
        )

    def register_event(self):
        """"""
        self.signal_strategy.connect(self.process_strategy_event)
        self.signal_trade_strategy.connect(self.process_cta_trade_event)
        # self.signal_triggered_stoporder_strategy.connect(self.process_triggered_stoporder_event)

        self.event_engine.register(
            EVENT_CTA_STRATEGY, self.signal_strategy.emit
        )
        self.event_engine.register(
            EVENT_CTA_TRADE, self.signal_trade_strategy.emit
        )

    # self.event_engine.register(
    #   EVENT_CTA_TRIGGERED_STOPORDER, self.signal_trade_strategy.emit
    # )

    def process_strategy_event(self, event):
        """
        Update strategy status onto its monitor.
        """
        data = event.data
        strategy_name = data["strategy_name"]

        # rowInest = local//10
        # if rowInest+1 > self.rowRecent:
        #     for rowI in range(self.rowRecent,rowInest+1):
        #         for columnJ in range(10):
        #             label1 = QtWidgets.QFrame()
        #             label1.setFixedSize(130,100)
        #             label1.setStyleSheet("background-color:black;")
        #             self.scroll_layout.addWidget(label1, rowI, columnJ,QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        #     self.rowRecent = rowInest+1

        if strategy_name in self.managers and self.manager_locations[strategy_name] == data.get("vt_local"):
            manager = self.managers[strategy_name]
            manager.update_data(data)
        else:
            if strategy_name in self.managers:
                self.remove_strategy(strategy_name)

            manager = NewSampleDataMonitor(self, self.cta_engine, data)

            locallist = (data.get("vt_local")).split("-")
            group = locallist[0]
            local = locallist[1]
            if not (group in self.managergroup.keys()):
                self.managergroup[group] = SampleMonitorGroup(groupName=group)
                self.scroll_layout.addWidget(self.managergroup[group], int(group), 0,
                                             Qt.AlignTop)

            self.managergroup[group].add_strategy2group(int(local) - 1, manager)
            # manager.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
            # self.scroll_layout.addWidget(manager, rowInest,local%10,QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
            self.managers[strategy_name] = manager
            self.manager_locations[strategy_name] = data.get("vt_local")

    # self.hideAllOtherRow(self.currentStrategyName)

    def process_cta_trade_event(self, event):
        """
        Update strategy status onto its monitor.
        """
        data = event.data

        if data.date < datetime.now(get_localzone()) <= (data.date + timedelta(days=2, hours=8)):
            # self.managers[data.strategy].cells["pos"].setBackground(QtGui.QBrush(QtGui.QColor("blue")))
            self.managers[data.strategy].setStyleSheet("QTableWidget{border:6px solid aqua}")
        # if self.currentStrategyName == data.strategy:
        # data.date = data.date[-4:]
        self.event_engine.put(Event(EVENT_CTA_DISPLAY_TRADE, data))
        if self.currentStrategyName != data.strategy:
            self.hideAllOtherRow()

    def remove_strategy(self, strategy_name):
        """"""
        self.manager_locations.pop(strategy_name)
        manager = self.managers.pop(strategy_name)
        manager.deleteLater()

    def add_strategy(self):
        """"""
        class_name = str(self.class_combo.currentText())
        if not class_name:
            return

        parameters = self.cta_engine.get_strategy_class_parameters(class_name)
        editor = SettingEditor(parameters, class_name=class_name)
        n = editor.exec_()

        if n == editor.Accepted:
            setting = editor.get_setting()
            vt_symbol = setting.pop("vt_symbol")
            strategy_name = setting.pop("strategy_name")
            vt_local = setting.pop("vt_local")

            self.cta_engine.add_strategy(
                class_name, strategy_name, vt_symbol, vt_local, setting
            )

    def slip_summary(self):

        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "保存数据", "", "CSV(*.csv)")

        if not path:
            return
        slip_summary = SlipSummary()
        slip_summary_list = slip_summary.check_slip()

        with open(path, "w", encoding='utf-8-sig') as f:
            writer = csv.writer(f, lineterminator="\n")
            for row_data in slip_summary_list:
                writer.writerow(row_data)

    def deal_summary(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "保存数据", "", "xlsx(*.xlsx)")

        if not path:
            return

        deal_summary = self.main_engine.get_engine("csvExport")
        deal_summary.batchExport(days = 1000,path = path)

    def account_summary(self):
        accountdata_DF = self.cta_engine.get_dbaccount_data()

        if not accountdata_DF.empty:
            triggerd_view = AccountDataMonitor(self.main_engine, self.main_engine.event_engine)
            triggerd_view.set_df(accountdata_DF)
            triggerd_view.setMinimumHeight(400)
            triggerd_view.setMinimumWidth(600)


            objectDF = accountdata_DF.set_index("datetime")

            chart = BacktesterChart()
            chart.set_data(objectDF)

            analyz_dialog = QDialog()
            analyz_dialog.setWindowTitle("权益变动")
            analyz_dialog.setWindowModality(Qt.NonModal)
            analyz_dialog.setWindowFlags(Qt.Dialog | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)
            gbox = QtWidgets.QGridLayout()
            analyz_dialog.resize(1200, 800)

            gbox.addWidget(triggerd_view, 0, 0)
            gbox.addWidget(chart, 0, 1)
            analyz_dialog.setLayout(gbox)
            analyz_dialog.exec_()





    def clear_log(self):
        """"""
        self.log_monitor.setRowCount(0)

    def show(self):
        """"""
        self.showMaximized()

    def roll(self):
        """"""
        dialog = RolloverTool(self)
        # dialog.exec_()
        dialog.show()

    def hideAllOtherRow(self):
        for rowId in range(self.cta_trade_monitor.rowCount()):
            self.cta_trade_monitor.hideRow(rowId)
        items = self.cta_trade_monitor.findItems(self.currentStrategyName, Qt.MatchExactly)
        for item in items:
            itemrow = item.row()
            self.cta_trade_monitor.showRow(itemrow)
        # self.cta_trade_monitor.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)

        for rowId in range(self.trigerred_stoporder_monitor.rowCount()):
            self.trigerred_stoporder_monitor.hideRow(rowId)
        items_orders = self.trigerred_stoporder_monitor.findItems(self.currentStrategyName, Qt.MatchExactly)
        for item in items_orders:
            itemrow = item.row()
            self.trigerred_stoporder_monitor.showRow(itemrow)
            self.trigerred_stoporder_monitor.horizontalHeader().resizeSections(QtWidgets.QHeaderView.ResizeToContents)

    def tradeFilterbyStoporder(self, stopOrderId):
        for rowId in range(self.cta_trade_monitor.rowCount()):
            self.cta_trade_monitor.hideRow(rowId)
        items = self.cta_trade_monitor.findItems(stopOrderId, Qt.MatchExactly)
        for item in items:
            itemrow = item.row()
            self.cta_trade_monitor.showRow(itemrow)
        self.tw.setCurrentIndex(1)


class SampleMonitorGroup(QtWidgets.QGroupBox):
    def __init__(self, groupName):
        super(SampleMonitorGroup, self).__init__(groupName)
        self.groupName = groupName

        self.Managerlist = {}
        self.rowRecent = 0

        self.init_ui()

    def init_ui(self):
        self.gridbox = QtWidgets.QGridLayout()
        self.setLayout(self.gridbox)
        self.gridbox.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

        if not self.Managerlist:
            self.setHidden(True)

    def add_strategy2group(self, local, strategymanager):
        rowInest = local // 10
        if rowInest + 1 > self.rowRecent:
            for rowI in range(self.rowRecent, rowInest + 1):
                for columnJ in range(10):
                    label1 = QtWidgets.QFrame()
                    label1.setFixedSize(126, 60)
                    label1.setStyleSheet("background-color:black;")
                    self.gridbox.addWidget(label1, rowI, columnJ)
            self.rowRecent = rowInest + 1
        self.gridbox.addWidget(strategymanager, rowInest, local % 10)
        self.Managerlist[strategymanager._Strategy] = strategymanager
        self.setVisible(True)


class StrategyManager(QtWidgets.QFrame):
    """
    Manager for a strategy
    """

    def __init__(
            self, cta_manager: CtaManager, cta_engine: CtaEngine, data: dict
    ):
        """"""
        super(StrategyManager, self).__init__()

        self.cta_manager = cta_manager
        self.cta_engine = cta_engine

        self.strategy_name = data["strategy_name"]
        self._data = data

        self.init_ui()

    def init_ui(self):
        """"""

        self.init_button = QtWidgets.QPushButton("初始化")
        self.init_button.clicked.connect(self.init_strategy)

        self.start_button = QtWidgets.QPushButton("启动")
        self.start_button.clicked.connect(self.start_strategy)
        self.start_button.setEnabled(False)

        self.stop_button = QtWidgets.QPushButton("停止")
        self.stop_button.clicked.connect(self.stop_strategy)
        self.stop_button.setEnabled(False)

        self.edit_button = QtWidgets.QPushButton("编辑")
        self.edit_button.clicked.connect(self.edit_strategy)

        self.remove_button = QtWidgets.QPushButton("移除")
        self.remove_button.clicked.connect(self.remove_strategy)

        self.anaylze_button = QtWidgets.QPushButton("统计")
        self.anaylze_button.clicked.connect(self.analyze_strategy)

        self.clear_button = QtWidgets.QPushButton("清仓")
        self.clear_button.clicked.connect(self.clear_strategy)
        self.clear_button.setEnabled(False)

        strategy_name = self._data["strategy_name"]
        vt_symbol = self._data["vt_symbol"]
        class_name = self._data["class_name"]
        # author = self._data["author"]

        label_text = (
            f"({class_name}){strategy_name}-{vt_symbol}"
        )
        self.label = QtWidgets.QLabel(label_text)
        self.label.setAlignment(QtCore.Qt.AlignLeft)

        self.parameters_monitor = DataMonitor(self._data["parameters"])
        self.variables_monitor = DataMonitor(self._data["variables"])

        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.init_button)
        hbox.addWidget(self.start_button)
        hbox.addWidget(self.stop_button)
        hbox.addWidget(self.edit_button)
        hbox.addWidget(self.remove_button)
        hbox.addWidget(self.clear_button)
        hbox.addWidget(self.anaylze_button)


        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.label)
        vbox.addLayout(hbox)
        vbox.addWidget(self.parameters_monitor)
        vbox.addWidget(self.variables_monitor)
        self.setLayout(vbox)

    def update_data(self, data: dict):
        """"""
        self._data = data
        strategy_name = self._data["strategy_name"]
        vt_symbol = self._data["vt_symbol"]
        class_name = self._data["class_name"]
        # author = self._data["author"]

        self.label.setText(
            f"({class_name}) {strategy_name}-{vt_symbol}"
        )

        self.parameters_monitor.update_data(data["parameters"])
        self.variables_monitor.update_data(data["variables"])

        # Update button status
        variables = data["variables"]
        inited = variables["inited"]
        trading = variables["trading"]

        if not inited:
            self.init_button.setEnabled(True)
            self.start_button.setEnabled(False)
            self.anaylze_button.setEnabled(False)
            return
        self.init_button.setEnabled(False)
        self.anaylze_button.setEnabled(True)


        if trading:
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.edit_button.setEnabled(False)
            self.remove_button.setEnabled(False)
            self.clear_button.setEnabled(True)
        else:
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.edit_button.setEnabled(True)
            self.remove_button.setEnabled(True)
            self.clear_button.setEnabled(False)

    def init_strategy(self):
        """"""
        self.cta_engine.init_strategy(self.strategy_name)

    def start_strategy(self):
        """"""
        self.cta_engine.start_strategy(self.strategy_name)

    def stop_strategy(self):
        """"""
        self.cta_engine.stop_strategy(self.strategy_name)

    def edit_strategy(self):
        """"""
        strategy_name = self._data["strategy_name"]
        parameters = {}
        parameters["vt_local"] = self.cta_engine.strategies[self.strategy_name].vt_local
        parameters.update(self.cta_engine.get_strategy_parameters(strategy_name))
        editor = SettingEditor(parameters, strategy_name=strategy_name)
        n = editor.exec_()

        if n == editor.Accepted:
            setting = editor.get_setting()
            self.cta_engine.edit_strategy(strategy_name, setting)
            if ("init_pos" in setting) and ("init_entry_price" in setting):
                strategy = self.cta_engine.strategies[strategy_name]
                strategy.pos = setting["init_pos"]
                strategy.PosPrice = setting["init_entry_price"]
                self.cta_engine.sync_strategy_data(strategy)
                self.cta_engine.put_strategy_event(strategy)

    def remove_strategy(self):
        """"""
        reply = QtWidgets.QMessageBox.question(
            self,
            "删除",
            "确认删除？",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )

        if reply == QtWidgets.QMessageBox.Yes:
            result = self.cta_engine.remove_strategy(self.strategy_name)

            # Only remove strategy gui manager if it has been removed from engine
            if result:
                self.cta_manager.remove_strategy(self.strategy_name)

    def clear_strategy(self):
        """"""

        reply = QtWidgets.QMessageBox.question(
            self,
            "清仓",
            "确认清仓？",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )

        if reply == QtWidgets.QMessageBox.Yes:
            strategy = self.cta_engine.strategies[self.strategy_name]

            # Only remove strategy gui manager if it has been removed from engine
            if strategy:
                strategy.clear_position()


    def calculate_statistics(self, objectDF):
        """
        """
        data = {}
        # end_balance = df["balance"].iloc[-1]
        # max_drawdown = df["drawdown"].min()
        # max_ddpercent = df["ddpercent"].min()
        HeYueJiaZhi = self._data["parameters"]["HeYueJiaZhi"]
        data["capital"]  = HeYueJiaZhi
        data["total_net_pnl"] = objectDF["revenue"].sum()
        data["end_balance"] = objectDF["balance"].iloc[-1]
        data["total_return"] = data["total_net_pnl"]*100/max(HeYueJiaZhi,1)

        data["max_drawdown"] = objectDF["drawdown"].min()
        data["max_ddpercent"] = objectDF["ddpercent"].min()

        data["total_trade_count"] = len(objectDF)
        data["winningResult"] = len(objectDF[objectDF["revenue"] >0])
        data["losingResult"] = len(objectDF[objectDF["revenue"] <0])
        data["winningRate"] = data["winningResult"] *100/ data["total_trade_count"]
        data["totalWinning"] = objectDF[objectDF["revenue"] >0]["revenue"].sum()
        data["totalLosing"] = objectDF[objectDF["revenue"] <0]["revenue"].sum()
        data["averageWinning"] = data["totalWinning"]/max(1,data["winningResult"])
        data["averageLosing"] = data["totalLosing"]/max(1,data["losingResult"])
        data["perprofitLoss"] = data["total_net_pnl"] / data["total_trade_count"]
        data["profitLossRatio"] = data["averageWinning"] / max(1,abs(data["averageLosing"]))

        return data

    def analyze_strategy(self):
        """
        # use triggerrd_order to calculate the strategy
        objectDF = self.cta_engine.get_strategy_triggered_order(self.strategy_name)
        self.cta_engine.transprot_all_triggered_strategies_order()

        if not objectDF.empty:
            triggerd_statistics_monitor = Triggered_OrderStatisticsMonitor()
            triggerd_statistics_monitor.set_data(self.calculate_statistics(objectDF))
            triggerd_statistics_monitor.setMinimumHeight(400)
            triggerd_view = TriggeredMonitor(self.cta_manager.main_engine, self.cta_manager.main_engine.event_engine)
            triggerd_view.set_df(objectDF)
            triggerd_view.setMinimumHeight(400)
            triggerd_view.setMinimumWidth(600)

            objectDF["net_pnl"] = objectDF["revenue"]
            objectDF= objectDF.set_index("close_date")

            chart = BacktesterChart()
            chart.set_data(objectDF)


            analyz_dialog = QDialog()
            analyz_dialog.setWindowTitle(self.strategy_name)
            analyz_dialog.setWindowModality(Qt.NonModal)
            analyz_dialog.setWindowFlags(Qt.Dialog | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)
            gbox = QtWidgets.QGridLayout()
            analyz_dialog.resize(1200, 800)

            gbox.addWidget(triggerd_statistics_monitor,0,0)
            gbox.addWidget(triggerd_view,1,0)
            gbox.addWidget(chart,0,1,2,1)
            analyz_dialog.setLayout(gbox)
            analyz_dialog.exec_()
        """
        # use trader date in batabase to calcaute strategy
        trade_result = database_manager.load_cta_trade_data(strategy= self.strategy_name,start = datetime(2001,10,10), end = datetime(2100,10,10))
        if trade_result:
            backtester = BacktestingEngine()
            backtester.capital = self._data["parameters"]["HeYueJiaZhi"]
            backtester.size = self._data["parameters"]["HeYueChengShu"]

            tradeResultDict = copy.copy(backtester.calculateBacktestingResult(db_traders=trade_result))
            resultlist = copy.copy(tradeResultDict['resultList'])
            del backtester

            #define static_monitor
            statistics = {
                "损益": tradeResultDict['capital'],
                "最高收益": tradeResultDict['maxCapital'],
                "回撤": tradeResultDict['drawdown'],
                "最大回撤": tradeResultDict['maxDrawdown'],
                "总盈利": tradeResultDict['totalWinning'],
                "总亏损": tradeResultDict['totalLosing'],
                "总交易次数": tradeResultDict['totalResult'],
                "交易胜率": f"{tradeResultDict['winningRate']:,.2f}%",
                "盈利交易次数": tradeResultDict['winningResult'],
                "亏损交易次数": tradeResultDict['losingResult'],
                "平均每次交易": tradeResultDict['averageProfit'],
                "平均每次盈利": tradeResultDict['averageWinning'],
                "平均每次亏损": tradeResultDict['averageLosing'],
                "平均每次盈利/-平均每次亏损": tradeResultDict['profitLossRatio'],
                "最多连续赢几次": tradeResultDict['max_win_count'],
                "最多连续输几次": tradeResultDict['max_lose_count'],
                "总盈利/总亏损": -tradeResultDict['totalWinning'] / max(1, tradeResultDict['totalLosing']),
                "收益STD": tradeResultDict['returnStd'],

            }
            static_monitor = Trade_StatisticsMonitor()
            static_monitor.set_data(statistics)

            objectDF = self.converst_strategy_triggered_order(resultlist)

            #define triggerd_view
            triggerd_view = TriggeredMonitor(self.cta_manager.main_engine, self.cta_manager.main_engine.event_engine)
            triggerd_view.set_df(objectDF)
            triggerd_view.setMinimumHeight(400)

            #define chart
            objectDF["net_pnl"] = objectDF["revenue"]
            objectDF= objectDF.set_index("close_date")
            chart = BacktesterChart()
            chart.set_data(objectDF)

            analyz_dialog = QDialog()
            analyz_dialog.setWindowTitle(self.strategy_name)
            analyz_dialog.setWindowModality(Qt.NonModal)
            analyz_dialog.setWindowFlags(Qt.Dialog | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)
            gbox = QtWidgets.QGridLayout()
            analyz_dialog.resize(1200, 800)

            gbox.addWidget(static_monitor,0,0)
            gbox.addWidget(triggerd_view,1,0)
            gbox.addWidget(chart,0,1,2,1)
            analyz_dialog.setLayout(gbox)
            analyz_dialog.exec_()

            # trade_list = []
            # for trade in trade_result:
            #     trade_list.append(dict(trade))
            #
            # del trade_result
            #
            # trade_monitor = StrategyTradeMonitor(self.cta_manager.main_engine, self.cta_manager.main_engine.event_engine,event_type_required=False)
            # trade_monitor.set_df(trade_list)
            #
            # static_monitor.trade_table = trade_monitor
            #
            #
            # analyz_dialog = QDialog()
            # analyz_dialog.setWindowTitle("策略")
            # analyz_dialog.setWindowModality(Qt.NonModal)
            # analyz_dialog.setWindowFlags(Qt.Dialog | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)
            # gbox = QtWidgets.QGridLayout()
            # analyz_dialog.resize(1200, 800)
            #
            #
            # gbox.addWidget(static_monitor,0,0)
            # gbox.addWidget(trade_monitor,1,0)
            # # gbox.addWidget(chart,0,1,2,1)
            # analyz_dialog.setLayout(gbox)
            # analyz_dialog.exec_()

    def converst_strategy_triggered_order(self, result):
        # result = database_manager.load_close_triggered_stop_order_data(strategy_name)

        objectDF = DataFrame(data=None,
                             columns=["open_date", "close_date", "direction", "open_price", "volume", "close_price",
                                      "revenue"], dtype=object)
        if result:
            for close_data in result:
                close_data.direction = Direction.LONG if close_data.volume > 0 else Direction.SHORT
                objectDF.loc[len(objectDF) + 1] = [close_data.entryDt, close_data.exitDt, close_data.direction,
                                                   close_data.entryPrice, close_data.volume, close_data.exitPrice,
                                                   close_data.pnl]

            objectDF["UnitReturn"] = objectDF["revenue"] * 100 / objectDF['open_price']

            objectDF["balance"] = objectDF["revenue"].cumsum()

            objectDF["returnRatio"] = objectDF["revenue"]

            objectDF.loc[0, "balance"] = 0

            objectDF["highlevel"] = (
                objectDF["balance"].rolling(
                    min_periods=1, window=len(objectDF), center=False).max()
            )

            objectDF.drop(index=0, inplace=True)

            objectDF["drawdown"] = objectDF["balance"] - objectDF["highlevel"]
            objectDF["ddpercent"] = objectDF["drawdown"] / objectDF["highlevel"] * 100

        return objectDF




class fullDatetimeCell(BaseCell):
    """
    Cell used for showing pnl data.
    """
    def __init__(self, content: Any, data: Any):
        """"""
        super(fullDatetimeCell, self).__init__(content, data)

    def set_content(self, content: Any, data: Any) -> None:
        """"""
        if content is None:
            return
        timestamp = content.strftime("%Y-%m-%d %H:%M:%S")

        self.setText(timestamp)
        self._data = data



class TriggeredMonitor(BaseMonitor):
    """
    Monitor for log data.
    """

    event_type = ""
    data_key = ""
    sorting = False
    # ["平仓日期", "方向", "开仓价", "手数", "平仓价", "收益"]
    headers = {
        "open_date": {"display": "开仓日期", "cell": fullDatetimeCell, "update": False},
        "close_date": {"display": "平仓日期", "cell": fullDatetimeCell, "update": False},
        "direction": {"display": "开仓方向", "cell": DirectionCell, "update": False},
        "open_price": {"display": "开仓价", "cell": BaseCell, "update": False},
        "volume": {"display": "手数", "cell": BaseCell, "update": False},
        "close_price": {"display": "平仓价", "cell": BaseCell, "update": False},
        "revenue": {"display": "收益", "cell": PnlCell, "update": False},
        "returnRatio": {"display": "收益率", "cell": PercentCell, "update": False},
        "UnitReturn": {"display": "单位收益率", "cell": PercentCell, "update": False},
        "balance": {"display": "当前资金", "cell": BaseCell, "update": False},
        "drawdown": {"display": "回撤", "cell": BaseCell, "update": False}
    }


    def set_df(self,objectDF):
        if not isinstance(objectDF,list):
            objectDF = objectDF.to_dict(orient='records')
        for record_item in objectDF:
            self.insert_data(record_item)

    def insert_data(self, data):
        """
        Insert a new row at the top of table.
        """
        self.insertRow(0)

        for column, header in enumerate(self.headers.keys()):
            setting = self.headers[header]
            content = data[header]
            cell = setting["cell"](content, data)
            self.setItem(0, column, cell)

    def __del__(self) -> None:
        """"""
        pass

class AccountDataMonitor(TriggeredMonitor):
    """["datetime", "balance", "Commission", "CurrMargin", "CurrMarginPrecent","available"]"""
    headers = {
        "accountid": {"display": "账户", "cell": BaseCell, "update": False},
        "datetime": {"display": "日期", "cell": fullDatetimeCell, "update": False},
        "balance": {"display": "权益", "cell": BaseCell, "update": False},
        "Commission": {"display": "手续费", "cell": BaseCell, "update": False},
        "net_pnl": {"display": "权益变动", "cell": PnlCell, "update": False},
        "total_pnl": {"display": "累计变动", "cell": PnlCell, "update": False},
        "total_pnl_percent": {"display": "累计变动比率", "cell": PercentCell, "update": False},
        "drawdown": {"display": "最高点回撤", "cell": PnlCell, "update": False},
        "BankTransfer": {"display": "出入金", "cell": BaseCell, "update": False},
        "CurrMargin": {"display": "保证金", "cell": BaseCell, "update": False},
        "CurrMarginPrecent": {"display": "保证金占比", "cell": PercentCell, "update": False},
        "available": {"display": "可用余额", "cell": BaseCell, "update": False}

    }


class Triggered_OrderStatisticsMonitor(QtWidgets.QTableWidget):
    """"""
    KEY_NAME_MAP = {
        "capital": "策略定义资金",
        "end_balance": "历史结算资金",
        "total_net_pnl": "总盈亏",
        "total_return": "总收益率",

        "total_trade_count": "总成交笔数",
        "winningResult": "盈利次数",
        "losingResult" : "亏损次数",
        "winningRate": "笔数胜率",
        "max_drawdown": "最大回撤",
        "max_ddpercent": "最大回撤比率",

        "totalWinning": "总盈利金额",
        "totalLosing": "总亏损金额",
        "perprofitLoss": "平均单笔损益",
        "averageWinning": "盈利平均每笔",
        "averageLosing" : "亏损平均每笔",
        "profitLossRatio" : "盈亏比"

    }

    def __init__(self):
        """"""
        super().__init__()

        self.cells = {}

        self.trade_table = None

        self.init_ui()

    def init_ui(self):
        """"""
        self.setRowCount(len(self.KEY_NAME_MAP))
        self.setVerticalHeaderLabels(list(self.KEY_NAME_MAP.values()))

        self.setColumnCount(1)
        self.horizontalHeader().setVisible(False)
        self.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch
        )
        self.setEditTriggers(self.NoEditTriggers)

        for row, key in enumerate(self.KEY_NAME_MAP.keys()):
            cell = QtWidgets.QTableWidgetItem()
            self.setItem(row, 0, cell)
            self.cells[key] = cell

        self.init_menu()

    def clear_data(self):
        """"""
        for cell in self.cells.values():
            cell.setText("")

    def set_data(self, data: dict):
        """
        :param data:
        :return:
        """
        data["capital"] = f"{data['capital']:,.2f}"
        data["end_balance"] = f"{data['end_balance']:,.2f}"
        data["total_return"] = f"{data['total_return']:,.2f}%"
        data["annual_return"] = f"{data['annual_return']:,.2f}%"
        data["max_drawdown"] = f"{data['max_drawdown']:,.2f}"
        data["max_ddpercent"] = f"{data['max_ddpercent']:,.2f}%"
        data["total_net_pnl"] = f"{data['total_net_pnl']:,.2f}"
        data["total_commission"] = f"{data['total_commission']:,.2f}"
        data["total_slippage"] = f"{data['total_slippage']:,.2f}"
        data["total_turnover"] = f"{data['total_turnover']:,.2f}"
        data["daily_net_pnl"] = f"{data['daily_net_pnl']:,.2f}"
        data["daily_commission"] = f"{data['daily_commission']:,.2f}"
        data["daily_slippage"] = f"{data['daily_slippage']:,.2f}"
        data["daily_turnover"] = f"{data['daily_turnover']:,.2f}"
        data["daily_trade_count"] = f"{data['daily_trade_count']:,.2f}"
        data["daily_return"] = f"{data['daily_return']:,.2f}%"
        data["return_std"] = f"{data['return_std']:,.2f}%"
        data["sharpe_ratio"] = f"{data['sharpe_ratio']:,.2f}"
        data["return_drawdown_ratio"] = f"{data['return_drawdown_ratio']:,.2f}"


        for key, cell in self.cells.items():
            value = data.get(key, "")
            cell.setText(str(value))

    def init_menu(self) -> None:
        """
        Create right click menu.
        """
        self.menu = QtWidgets.QMenu(self)

        save_action = QtWidgets.QAction("保存数据", self)
        save_action.triggered.connect(self.save_csv)
        self.menu.addAction(save_action)

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent) -> None:
        """
        Show menu with right click.
        """
        self.menu.popup(QtGui.QCursor.pos())

    def save_csv(self) -> None:
        """
        Save table data into a csv file
        """
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "保存数据", "", "CSV(*.csv)")

        if not path:
            return

        with open(path, "w", encoding='utf-8-sig') as f:
            writer = csv.writer(f, lineterminator="\n")

            headers = list(self.KEY_NAME_MAP.values())

            for row in range(self.rowCount()):
                if self.isRowHidden(row):
                    continue

                row_data = []
                row_data.append(headers[row])
                for column in range(self.columnCount()):
                    item = self.item(row, column)
                    if item:
                        row_data.append(str(item.text()))
                    else:
                        row_data.append("")
                writer.writerow(row_data)

            writer.writerow([""])

            if self.trade_table:
                headers = [d["display"] for d in self.trade_table.headers.values()]
                writer.writerow(headers)

                for row in range(self.trade_table.rowCount()):
                    if self.trade_table.isRowHidden(row):
                        continue

                    row_data = []
                    for column in range(self.trade_table.columnCount()):
                        item = self.trade_table.item(row, column)
                        if item:
                            row_data.append(str(item.text()))
                        else:
                            row_data.append("")
                    writer.writerow(row_data)


class Trade_StatisticsMonitor(Triggered_OrderStatisticsMonitor):
    KEY_NAME_MAP = {
        "损益": "损益",
        "最高收益": "最高收益",
        "回撤": "回撤",
        "最大回撤": "最大回撤",
        "总盈利": "总盈利",
        "总亏损": "总亏损",
        "总交易次数": "总交易次数",
        "交易胜率": "交易胜率",
        "盈利交易次数": "盈利交易次数",
        "亏损交易次数": "亏损交易次数",
        "平均每次交易": "平均每次交易",
        "平均每次盈利": "平均每次盈利",
        "平均每次亏损": "平均每次亏损",
        "平均每次盈利/-平均每次亏损": "平均每次盈利/-平均每次亏损",
        "最多连续赢几次": "最多连续赢几次",
        "最多连续输几次": "最多连续输几次",
        "总盈利/总亏损": "总盈利/总亏损",
        "收益STD": "收益STD"
    }
    def set_data(self, data: dict):
        """
        :param data:
        :return:
        """
        data["损益"] = f"{data['损益']:,.2f}"
        data["最高收益"] = f"{data['最高收益']}"
        data["回撤"] = f"{data['回撤']}"
        data["最大回撤"] = f"{data['最大回撤']}"
        data["总盈利"] = f"{data['总盈利']:,.2f}"
        data["总亏损"] = f"{data['总亏损']:,.2f}"
        data["总交易次数"] = data['总交易次数']
        data["交易胜率"] = data['交易胜率']
        data["盈利交易次数"] = f"{data['盈利交易次数']}"
        data["亏损交易次数"] = f"{data['亏损交易次数']}"
        data["平均每次交易"] = f"{data['平均每次交易']:,.2f}"
        data["平均每次盈利"] = f"{data['平均每次盈利']:,.2f}"
        data["平均每次亏损"] = f"{data['平均每次亏损']:,.2f}"
        data["平均每次盈利/-平均每次亏损"] = f"{data['平均每次盈利/-平均每次亏损']:,.2f}"
        data["最多连续赢几次"] = f"{data['最多连续赢几次']:}"
        data["最多连续输几次"] = f"{data['最多连续输几次']}"
        data["总盈利/总亏损"] = f"{data['总盈利/总亏损']:,.2f}"
        data["收益STD"] = f"{data['收益STD']:,.2f}"


        for key, cell in self.cells.items():
            value = data.get(key, "")
            cell.setText(str(value))

class DataMonitor(QtWidgets.QTableWidget):
    """
    Table monitor for parameters and variables.
    """

    def __init__(self, data: dict):
        """"""
        super(DataMonitor, self).__init__()

        if "inited" in data:
            data = data.copy()
            data.pop("inited")
            data.pop("trading")
            # data.pop("pos")
            # data.pop("PosPrice")
        self._data = data
        self.cells = {}

        self.init_ui()

    def init_ui(self):
        """"""
        labels = list(self._data.keys())
        self.setRowCount(len(labels))
        # self.setHorizontalHeaderLabels(labels)
        self.setVerticalHeaderLabels(labels)
        # self.setMaximumWidth(100)
        self.setFixedHeight(180)

        self.setColumnCount(1)
        self.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch
        )
        self.horizontalHeader().setVisible(False)
        self.setEditTriggers(self.NoEditTriggers)

        # self.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.verticalHeader().setDefaultSectionSize(10)

        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)


        for column, name in enumerate(self._data.keys()):
            value = self._data[name]
            cell = QtWidgets.QTableWidgetItem(roundTwoDecimal(value))
            cell.setTextAlignment(Qt.AlignCenter)
            self.setItem(column, 0, cell)
            self.cells[name] = cell
        if "pos" in self._data:
            self.hideRow(0)
            self.hideRow(2)
        #     self.setFixedHeight(32 * (len(self._data) - 2))
        # else:
        #     self.setFixedHeight(32 * (len(self._data)))


    def update_data(self, data: dict):
        """"""

        if "inited" in data:
            data = data.copy()
            data.pop("inited")
            data.pop("trading")
            # data.pop("pos")
            # data.pop("PosPrice")
        for name, value in data.items():
            cell = self.cells[name]
            cell.setText(roundTwoDecimal(value))
        self._data = data
        # if "pos" in self._data:
        #     self.setFixedHeight(32 * (len(self._data) - 2))
        # else:
        #     self.setFixedHeight(32 * (len(self._data)))

def roundTwoDecimal(inputvalue):
    if isinstance(inputvalue, float):
        inputvalue = round(inputvalue, 3)
    return str(inputvalue)


class NewSampleDataMonitor(QtWidgets.QTableWidget):
    """
    Table monitor for parameters and variables.
    """

    def __init__(self, cta_manager: CtaManager, cta_engine: CtaEngine, data: dict):
        """"""
        super(NewSampleDataMonitor, self).__init__()
        self._full_symbol = data["vt_symbol"]
        self._Symbol = self._full_symbol.split(".")[0]

        self._Strategy = data["strategy_name"]
        self.subkey = ['inited', 'trading', 'pos', 'PosPrice']
        self.end = datetime.now()
        self.start = self.end.replace(hour=0, minute=0) - timedelta(days=2)
        self.cta_manager = cta_manager
        self.cta_engine = cta_engine
        self.inited = False
        self.trading = False
        self.StrategyManagerFrame = StrategyManager(self.cta_manager, self.cta_engine, data)
        self.cta_manager.LeftInfromFrame.addWidget(self.StrategyManagerFrame)
        self.cells = {}

        self.init_ui(data)

    def getSampleVariables(self, data: dict) -> dict:
        variables = data["variables"]
        return dict([(key, variables[key]) for key in self.subkey])

    def init_ui(self, data: dict):
        """"""

        # self.setSizePolicy()
        labels = list([self._Symbol, self._Strategy])
        self.setColumnCount(len(labels))
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.setHorizontalHeaderLabels(labels)
        self.horizontalHeader().setHighlightSections(False)
        self.setFixedHeight(60)
        self.setFixedWidth(128)

        self.setRowCount(1)
        # self.setColumnCount(2)
        self.verticalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch
        )
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(self.NoEditTriggers)
        self.clicked.connect(self.StrategyManagerChoose)
        self.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)

        sample_variables = self.getSampleVariables(data)
        for iterable, name in enumerate(['pos', 'PosPrice']):
            value = sample_variables[name]
            cell = QtWidgets.QTableWidgetItem(roundTwoDecimal(value))
            cell.setTextAlignment(QtCore.Qt.AlignCenter)

            self.setItem(0, iterable, cell)
            self.cells[name] = cell

        if not (sample_variables['inited'] or sample_variables['trading']):
            self.cells["pos"].setBackground(QtGui.QColor("red"))
            self.cells["PosPrice"].setBackground(QtGui.QColor("red"))

    def update_data(self, data: dict):
        """"""
        labels = list([self._Symbol, self._Strategy])
        self.setHorizontalHeaderLabels(labels)

        self.StrategyManagerFrame.update_data(data)
        sample_variables = self.getSampleVariables(data)

        if sample_variables['inited'] and (self.inited == False):
            self.loadTradeDatafromDB()

        if not (sample_variables['inited'] or sample_variables['trading']):
            self.cells["pos"].setBackground(QtGui.QColor("red"))
            self.cells["PosPrice"].setBackground(QtGui.QColor("red"))
        elif sample_variables['inited'] != sample_variables['trading']:
            self.cells["pos"].setBackground(QtGui.QColor("yellow"))
            self.cells["PosPrice"].setBackground(QtGui.QColor("yellow"))
        elif sample_variables['inited'] and sample_variables['trading']:
            self.cells["pos"].setBackground(QtGui.QColor("transparent"))
            self.cells["PosPrice"].setBackground(QtGui.QColor("transparent"))

        self.inited = sample_variables['inited']
        self.trading = sample_variables['trading']

        self.cells["pos"].setText(roundTwoDecimal(sample_variables["pos"]))
        self.cells["PosPrice"].setText(roundTwoDecimal(sample_variables["PosPrice"]))

        if self.cells["pos"]:
            if float(self.cells['pos'].text()) > 0:
                self.cells["pos"].setForeground(QtGui.QColor("red"))
            elif float(self.cells['pos'].text()) < 0:
                self.cells["pos"].setForeground(QtGui.QColor("lime"))
            else:
                self.cells["pos"].setForeground(QtGui.QColor("white"))

    def loadTradeDatafromDB(self):
        dbtrades = database_manager.load_cta_trade_data(self._Strategy, self.start, self.end)
        for trade in dbtrades:
            self.cta_manager.event_engine.put(Event(EVENT_CTA_TRADE, trade))

        dbstop_orders = database_manager.load_triggered_stop_order_data(self._Strategy, self.start, self.end)
        for dbstop_order in dbstop_orders:
            self.cta_manager.event_engine.put(Event(EVENT_CTA_TRIGGERED_STOPORDER, dbstop_order))

    def StrategyManagerChoose(self):
        """"""
        # update the LastPrice when click
        # local_strategy = self.cta_engine.strategies[self._Strategy]
        # if hasattr(local_strategy, "bg") and local_strategy.bg.last_tick:
        #     local_strategy.LastPrice = local_strategy.bg.last_tick.last_price
        #     local_strategy.put_event()
        local_strategy = self.cta_engine.strategies[self._Strategy]
        tick = self.cta_engine.main_engine.get_tick(self._full_symbol)
        if tick:
            local_strategy.LastPrice = tick.last_price
            local_strategy.put_event()
        # if self.cta_manager.currentStrategyName == self._Strategy:
        #   return
        self.cta_manager.currentStrategyName = self._Strategy
        self.cta_manager.LeftInfromFrame.setCurrentWidget(self.StrategyManagerFrame)
        self.cta_manager.hideAllOtherRow()


class StopOrderMonitor(BaseMonitor):
    """
    Monitor for local stop order.
    """

    event_type = EVENT_CTA_STOPORDER
    data_key = "stop_orderid"
    sorting = True

    headers = {
        "stop_orderid": {
            "display": "停止委托号",
            "cell": BaseCell,
            "update": False,
        },
        "vt_orderids": {"display": "限价委托号", "cell": BaseCell, "update": True},
        "vt_symbol": {"display": "本地代码", "cell": BaseCell, "update": False},
        "direction": {"display": "方向", "cell": EnumCell, "update": False},
        "offset": {"display": "开平", "cell": EnumCell, "update": False},
        "price": {"display": "价格", "cell": BaseCell, "update": False},
        "volume": {"display": "数量", "cell": BaseCell, "update": False},
        "status": {"display": "状态", "cell": EnumCell, "update": True},
        "datetime": {"display": "时间", "cell": TimeCell, "update": False},
        "lock": {"display": "锁仓", "cell": BaseCell, "update": False},
        "net": {"display": "净仓", "cell": BaseCell, "update": False},
        "strategy_name": {"display": "策略名", "cell": BaseCell, "update": False},
    }


class TriggeredStopOrderMonitor(BaseMonitor):
    """
    Monitor for local stop order.
    """

    event_type = EVENT_CTA_TRIGGERED_STOPORDER
    data_key = "stop_orderid"
    sorting = True

    headers = {
        "strategy_name": {"display": "策略名", "cell": BaseCell, "update": False},
        "vt_symbol": {"display": "合约代码", "cell": BaseCell, "update": False},
        "stop_orderid": {"display": "挂单号", "cell": BaseCell, "update": False},
        "datetime": {"display": "时间", "cell": DatetimeCell, "update": False},
        "direction": {"display": "方", "cell": DirectionCell, "update": False},
        "offset": {"display": "开", "cell": EnumCell, "update": False},
        "completed_volume": {"display": "完成", "cell": BaseCell, "update": True},
        "first_price": {"display": "首价", "cell": BaseCell, "update": True},
        "average_price": {"display": "均价", "cell": BaseCell, "update": True},
        "triggered_price": {"display": "触发价", "cell": BaseCell, "update": True},
        "price": {"display": "价格", "cell": BaseCell, "update": False},
        "volume": {"display": "数量", "cell": BaseCell, "update": False},
        # "date": {"display": "日期", "cell": BaseCell, "update": False},
        # "tradeid": {"display": "成交号 ", "cell": BaseCell, "update": False},
        # "orderid": {"display": "委托号", "cell": BaseCell, "update": False},
        # "exchange": {"display": "交易所", "cell": EnumCell, "update": False},
        # "gateway_name": {"display": "接口", "cell": BaseCell, "update": False},
    }

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine, ctaManager):
        super(TriggeredStopOrderMonitor, self).__init__(main_engine, event_engine)
        self.ctaManager = ctaManager

    def init_ui(self):
        """
        Stretch last column.
        """
        super(TriggeredStopOrderMonitor, self).init_ui()
        self.hideColumn(0)
        self.hideColumn(1)
        self.hideColumn(2)

        self.itemDoubleClicked.connect(self.sync_table_double_clicked)
        self.horizontalHeader().setFont(QtGui.QFont("", 8))
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)

    def sync_table_double_clicked(self, item):
        self.ctaManager.tradeFilterbyStoporder(item._data.stop_orderid)

    def process_event(self, event: Event):
        super(TriggeredStopOrderMonitor, self).process_event(event)
        self.horizontalHeader().resizeSections(QtWidgets.QHeaderView.ResizeToContents)

    def readyforExport(self,days = 1):
        end = datetime.now()
        start = end - timedelta(days)
        dbstop_orders = database_manager.load_triggered_all_stop_order_data(start, end)
        return dbstop_orders


class StrategyTradeMonitor(BaseMonitor):
    """
    Monitor for local stop order.
    """

    event_type = EVENT_CTA_DISPLAY_TRADE
    data_key = "tradeid"
    sorting = True

    headers = {
        "strategy": {"display": "策略名", "cell": BaseCell, "update": False},
        "symbol": {"display": "代码", "cell": BaseCell, "update": False},
        "tradeid": {"display": "成交号 ", "cell": BaseCell, "update": False},
        "orderid": {"display": "委托号", "cell": BaseCell, "update": False},
        "datetime": {"display": "时间", "cell": DatetimeCell, "update": False},
        "price": {"display": "价格", "cell": BaseCell, "update": False},
        "volume": {"display": "数量", "cell": BaseCell, "update": False},
        "direction": {"display": "方向", "cell": DirectionCell, "update": False},
        "offset": {"display": "开平", "cell": EnumCell, "update": False}
    }

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine,event_type_required = True):
        """"""
        if event_type_required == False:
	        self.event_type = None
        super(StrategyTradeMonitor, self).__init__(main_engine,event_engine)

    def init_ui(self):
        """
        Stretch last column.
        """
        super(StrategyTradeMonitor, self).init_ui()
        self.hideColumn(0)
        self.hideColumn(1)
        self.hideColumn(2)
        self.hideColumn(3)
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)

    def set_df(self, objectDF):
        if not isinstance(objectDF, list):
	        objectDF = objectDF.to_dict(orient='records')
        for record_item in objectDF:
	        self.insert_data(record_item)

    def insert_data(self, data):
        """
		Insert a new row at the top of table.
		"""
        self.insertRow(0)

        for column, header in enumerate(self.headers.keys()):
	        setting = self.headers[header]
	        content = data[header]
	        cell = setting["cell"](content, data)
	        self.setItem(0, column, cell)

    def __del__(self) -> None:
        """"""
        pass

class LogMonitor(BaseMonitor):
    """
    Monitor for log data.
    """

    event_type = EVENT_CTA_LOG
    data_key = ""
    sorting = False

    headers = {
        "time": {"display": "时间", "cell": TimeCell, "update": False},
        "msg": {"display": "信息", "cell": MsgCell, "update": False},
    }

    def init_ui(self):
        """
        Stretch last column.
        """
        super(LogMonitor, self).init_ui()

        self.horizontalHeader().setSectionResizeMode(
            1, QtWidgets.QHeaderView.Stretch
        )

    def insert_new_row(self, data):
        """
        Insert a new row at the top of table.
        """
        super(LogMonitor, self).insert_new_row(data)
        self.resizeRowToContents(0)


class SettingEditor(QtWidgets.QDialog):
    """
    For creating new strategy and editing strategy parameters.
    """

    def __init__(
            self, parameters: dict, strategy_name: str = "", class_name: str = ""
    ):
        """"""
        super(SettingEditor, self).__init__()

        self.parameters = parameters
        self.strategy_name = strategy_name
        self.class_name = class_name

        self.edits = {}

        self.init_ui()

    def init_ui(self):
        """"""
        form = QtWidgets.QFormLayout()

        # Add vt_symbol and name edit if add new strategy
        if self.class_name:
            self.setWindowTitle(f"添加策略：{self.class_name}")
            button_text = "添加"
            parameters = {"strategy_name": "", "vt_symbol": "", "vt_local": ""}
            parameters.update(self.parameters)
        else:
            self.setWindowTitle(f"参数编辑：{self.strategy_name}")
            button_text = "确定"
            parameters = self.parameters

        for name, value in parameters.items():
            type_ = type(value)

            edit = QtWidgets.QLineEdit(str(value))
            if type_ is int:
                validator = QtGui.QIntValidator()
                edit.setValidator(validator)
            elif type_ is float:
                validator = QtGui.QDoubleValidator()
                edit.setValidator(validator)
            if name == "vt_local":
                regExp1 = QtCore.QRegExp("^\d{1,3}-\d{1,3}$")
                edit.setValidator(QtGui.QRegExpValidator(regExp1))

            form.addRow(f"{name} {type_}", edit)

            self.edits[name] = (edit, type_)

        button = QtWidgets.QPushButton(button_text)
        button.clicked.connect(self.accept)
        form.addRow(button)

        widget = QtWidgets.QWidget()
        widget.setLayout(form)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)

        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(scroll)
        self.setLayout(vbox)

    def get_setting(self):
        """"""
        setting = {}

        if self.class_name:
            setting["class_name"] = self.class_name

        for name, tp in self.edits.items():
            edit, type_ = tp
            value_text = edit.text()

            if type_ == bool:
                if value_text == "True":
                    value = True
                else:
                    value = False
            else:
                value = type_(value_text)

            setting[name] = value

        return setting
