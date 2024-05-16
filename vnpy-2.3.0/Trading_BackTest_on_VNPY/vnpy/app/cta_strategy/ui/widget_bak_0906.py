from vnpy.event import Event, EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
from vnpy.trader.database import database_manager
from datetime import datetime, timedelta
from vnpy.trader.ui.widget import (
    BaseCell,
    EnumCell,
    MsgCell,
    TimeCell,
    DirectionCell,
    BaseMonitor
)
from ..base import (
    APP_NAME,
    EVENT_CTA_LOG,
    EVENT_CTA_STOPORDER,
    EVENT_CTA_DISPLAY_TRADE,
    EVENT_CTA_STRATEGY,
    EVENT_CTA_TRADE
)
from ..engine import CtaEngine
from .rollover import RolloverTool


class CtaManager(QtWidgets.QWidget):
    """"""

    signal_log = QtCore.pyqtSignal(Event)
    signal_strategy = QtCore.pyqtSignal(Event)

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine):
        super(CtaManager, self).__init__()

        self.main_engine = main_engine
        self.event_engine = event_engine
        self.cta_engine = main_engine.get_engine(APP_NAME)
        self.rowRecent = 7
        self.managers = {}

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
        # self.scroll_layout.addStretch()
        # self.scroll_layout.setSpacing(1)
        # self.scroll_layout.setVerticalSpacing(2)
        # self.scroll_layout.setHorizontalSpacing(2)

        for rowI in range(self.rowRecent):
            for columnJ in range(10):
                label1 = QtWidgets.QFrame()
                label1.setMinimumSize(130,100)
                label1.setStyleSheet("background-color:black;")
                self.scroll_layout.addWidget(label1,rowI,columnJ,QtCore.Qt.AlignTop | QtCore.Qt.AlignCenter)

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
        labelRightTop = QtWidgets.QFrame()
        labelRightTop.setMinimumWidth(280)
        hbox1.addWidget(labelRightTop)
        # QtWidgets.QVBoxLayout()

        NewVQbox1 = QtWidgets.QVBoxLayout()
        NewVQbox1_widget = QtWidgets.QWidget()
        self.LeftInfromFrame = QtWidgets.QStackedWidget()
        self.LeftInfromFrame.setMinimumWidth(280)
        self.cta_trade_monitor.setMaximumWidth(280)

        NewVQbox1.addWidget(self.LeftInfromFrame,QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        # displayAllTrade_button = QtWidgets.QPushButton("所有成交显示")
        # displayAllTrade_button.clicked.connect(lambda : self.hideAllOtherRow("showRowInform"))
        # NewVQbox1.addWidget(displayAllTrade_button)
        NewVQbox1.addWidget(self.cta_trade_monitor,QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        NewVQbox1_widget.setLayout(NewVQbox1)
        NewVQbox1_widget.setMaximumWidth(281)


        NewHQbox1 = QtWidgets.QHBoxLayout()
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
        grid.addWidget(self.stop_order_monitor, 1,0,QtCore.Qt.AlignBottom)
        grid.addWidget(self.log_monitor, 1, 1,QtCore.Qt.AlignBottom)
        grid.addWidget(labelRight,0,2,0,2)

        vbox = QtWidgets.QVBoxLayout()
        vbox.addLayout(hbox1)
        vbox.addLayout(grid)
        self.setLayout(vbox)

    def update_class_combo(self):
        """"""
        self.class_combo.addItems(
            self.cta_engine.get_all_strategy_class_names()
        )

    def register_event(self):
        """"""
        self.signal_strategy.connect(self.process_strategy_event)

        self.event_engine.register(
            EVENT_CTA_STRATEGY, self.signal_strategy.emit
        )
        self.event_engine.register(
            EVENT_CTA_TRADE, self.process_cta_trade_event
        )
    def process_strategy_event(self, event):
        """
        Update strategy status onto its monitor.
        """
        data = event.data
        strategy_name = data["strategy_name"]
        local = int(data.get("vt_local"))
        rowInest = local//10
        if rowInest+1 > self.rowRecent:
            for rowI in range(self.rowRecent,rowInest+1):
                for columnJ in range(10):
                    label1 = QtWidgets.QFrame()
                    label1.setMinimumSize(130,100)
                    label1.setStyleSheet("background-color:black;")
                    self.scroll_layout.addWidget(label1, rowI, columnJ,QtCore.Qt.AlignTop | QtCore.Qt.AlignCenter)
            self.rowRecent = rowInest+1

        if strategy_name in self.managers:
            manager = self.managers[strategy_name]
            manager.update_data(data)

        else:
            manager = NewSampleDataMonitor(self, self.cta_engine, data)
            # manager.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
            self.scroll_layout.addWidget(manager, rowInest,local%10,QtCore.Qt.AlignTop | QtCore.Qt.AlignCenter)
            self.managers[strategy_name] = manager

        # self.hideAllOtherRow(self.currentStrategyName)
    def process_cta_trade_event(self, event):
        """
        Update strategy status onto its monitor.
        """
        data = event.data
        if data.date == datetime.today().strftime("%Y%m%d"):
            self.managers[data.strategy].cells["pos"].setBackground(QtGui.QBrush(QtGui.QColor(0,0,255)))
        # if self.currentStrategyName == data.strategy:
        data.date = data.date[-4:]
        self.event_engine.put(Event(EVENT_CTA_DISPLAY_TRADE,data))
        self.hideAllOtherRow()



    def remove_strategy(self, strategy_name):
        """"""
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

    def clear_log(self):
        """"""
        self.log_monitor.setRowCount(0)

    def show(self):
        """"""
        self.showMaximized()

    def roll(self):
        """"""
        dialog = RolloverTool(self)
        dialog.exec_()

    def hideAllOtherRow(self):

        for rowId in range(self.cta_trade_monitor.rowCount()):
            self.cta_trade_monitor.hideRow(rowId)
        items = self.cta_trade_monitor.findItems(self.currentStrategyName, Qt.MatchExactly)
        for item in items:
            itemrow = item.row()
            self.cta_trade_monitor.showRow(itemrow)
        self.cta_trade_monitor.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)


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
        # self.setFixedHeight(280)
        # self.setMaximumWidth(280)
        # self.setFrameShape(self.Box)
        # self.setLineWidth(0)

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

        strategy_name = self._data["strategy_name"]
        vt_symbol = self._data["vt_symbol"]
        class_name = self._data["class_name"]
        # author = self._data["author"]

        label_text = (
            f"{strategy_name}-{vt_symbol}({class_name})"
        )
        label = QtWidgets.QLabel(label_text)
        label.setAlignment(QtCore.Qt.AlignLeft)


        self.parameters_monitor = DataMonitor(self._data["parameters"])
        self.variables_monitor = DataMonitor(self._data["variables"])

        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.init_button)
        hbox.addWidget(self.start_button)
        hbox.addWidget(self.stop_button)
        hbox.addWidget(self.edit_button)
        hbox.addWidget(self.remove_button)

        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(label)
        vbox.addLayout(hbox)
        vbox.addWidget(self.parameters_monitor)
        vbox.addWidget(self.variables_monitor)
        self.setLayout(vbox)


    def update_data(self, data: dict):
        """"""
        self._data = data

        self.parameters_monitor.update_data(data["parameters"])
        self.variables_monitor.update_data(data["variables"])

        # Update button status
        variables = data["variables"]
        inited = variables["inited"]
        trading = variables["trading"]

        if not inited:
            return
        self.init_button.setEnabled(False)

        if trading:
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.edit_button.setEnabled(False)
            self.remove_button.setEnabled(False)
        else:
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.edit_button.setEnabled(True)
            self.remove_button.setEnabled(True)

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

        parameters = self.cta_engine.get_strategy_parameters(strategy_name)
        editor = SettingEditor(parameters, strategy_name=strategy_name)
        n = editor.exec_()

        if n == editor.Accepted:
            setting = editor.get_setting()
            self.cta_engine.edit_strategy(strategy_name, setting)

    def remove_strategy(self):
        """"""
        result = self.cta_engine.remove_strategy(self.strategy_name)

        # Only remove strategy gui manager if it has been removed from engine
        if result:
            self.cta_manager.remove_strategy(self.strategy_name)




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
            data.pop("pos")
            data.pop("PosPrice")
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


        self.setColumnCount(1)
        self.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch
        )
        self.horizontalHeader().setVisible(False)
        self.setEditTriggers(self.NoEditTriggers)

        self.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        # self.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        for column, name in enumerate(self._data.keys()):
            value = self._data[name]
            cell = QtWidgets.QTableWidgetItem(roundTwoDecimal(value))
            cell.setTextAlignment(QtCore.Qt.AlignCenter)
            self.setItem(column, 0, cell)
            self.cells[name] = cell


    def update_data(self, data: dict):
        """"""

        if "inited" in data:
            data = data.copy()
            data.pop("inited")
            data.pop("trading")
            data.pop("pos")
            data.pop("PosPrice")
        for name, value in data.items():
            cell = self.cells[name]
            cell.setText(roundTwoDecimal(value))

def roundTwoDecimal(inputvalue):
    if isinstance(inputvalue, float):
        inputvalue = round(inputvalue,2)
    return str(inputvalue)


class NewSampleDataMonitor(QtWidgets.QTableWidget):
    """
    Table monitor for parameters and variables.
    """

    def __init__(self, cta_manager: CtaManager, cta_engine: CtaEngine, data: dict):
        """"""
        super(NewSampleDataMonitor, self).__init__()


        self._Symbol = data["vt_symbol"]
        self._Strategy = data["strategy_name"]
        self.subkey = ['inited', 'trading', 'pos', 'PosPrice']
        self.end = datetime.now()
        self.start = self.end - timedelta(2)
        self.cta_manager = cta_manager
        self.cta_engine = cta_engine
        self.alldata = data
        self.StrategyManagerFrame = StrategyManager(self.cta_manager,self.cta_engine,self.alldata)
        self.cta_manager.LeftInfromFrame.addWidget(self.StrategyManagerFrame)

        variables = data["variables"]
        sample_variables = (dict([(key, variables[key]) for key in self.subkey]))
        self._data = sample_variables
        # self._data = data
        self.cells = {}

        self.init_ui()


    def init_ui(self):
        """"""

        # self.setSizePolicy()
        labels = list([self._Symbol,self._Strategy])
        self.setColumnCount(len(labels))
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.setHorizontalHeaderLabels(labels)
        self.horizontalHeader().setHighlightSections(False)
        # self.setMaximumHeight(100)


        self.setRowCount(2)
        # self.setColumnCount(2)
        self.verticalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch
        )
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(self.NoEditTriggers)
        self.clicked.connect(self.StrategyManagerChoose)
        self.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)


        for iterable, name in enumerate(self._data.keys()):
            value = self._data[name]

            cell = QtWidgets.QTableWidgetItem(roundTwoDecimal(value))
            cell.setTextAlignment(QtCore.Qt.AlignCenter)

            if str(value) == "True":
                cell.setBackground(QtGui.QBrush(QtGui.QColor(0,255,0)))
            elif str(value) == "False":
                cell.setBackground(QtGui.QBrush(QtGui.QColor(255, 0, 0)))
            self.setItem(iterable//2, iterable%2, cell)
            self.cells[name] = cell



    def update_data(self, data: dict):
        """"""
        self.StrategyManagerFrame.update_data(data)
        variables = data["variables"]
        sample_variables = (dict([(key, variables[key]) for key in self.subkey]))

        if variables['inited'] and (self.cells['inited'].text() == "False"):
            self.loadTradeDatafromDB()

        for name, value in sample_variables.items():
            cell = self.cells[name]

            cell.setText(roundTwoDecimal(value))
            if str(value) == "True":
                cell.setBackground(QtGui.QBrush(QtGui.QColor(0,255,0)))
            elif str(value) == "False":
                cell.setBackground(QtGui.QBrush(QtGui.QColor(255, 0, 0)))

    def loadTradeDatafromDB(self):
        dbtrades = database_manager.load_cta_trade_data(self._Strategy, self.start, self.end)
        for trade in dbtrades:
            self.cta_manager.event_engine.put(Event(EVENT_CTA_TRADE, trade))

    def StrategyManagerChoose(self):
        """"""
        if self.cta_manager.currentStrategyName == self._Strategy:
            return
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
class StrategyTradeMonitor(BaseMonitor):
    """
    Monitor for local stop order.
    """

    event_type = EVENT_CTA_DISPLAY_TRADE
    data_key = ""
    sorting = True

    headers  = {
        "strategy": {"display": "策略名", "cell": BaseCell, "update": False},
        "symbol": {"display": "代码", "cell": BaseCell, "update": False},
        "datetime": {"display": "时间", "cell": TimeCell, "update": False},
        "price": {"display": "价格", "cell": BaseCell, "update": False},
        "volume": {"display": "数量", "cell": BaseCell, "update": False},
        "direction": {"display": "方向", "cell": DirectionCell, "update": False},
        "offset": {"display": "开平", "cell": EnumCell, "update": False},
        "date": {"display": "日期", "cell": BaseCell, "update": False},
        # "tradeid": {"display": "成交号 ", "cell": BaseCell, "update": False},
        # "orderid": {"display": "委托号", "cell": BaseCell, "update": False},
        # "exchange": {"display": "交易所", "cell": EnumCell, "update": False},
        # "gateway_name": {"display": "接口", "cell": BaseCell, "update": False},
    }
    def init_ui(self):
        """
        Stretch last column.
        """
        super(StrategyTradeMonitor, self).init_ui()
        self.hideColumn(0)
        self.hideColumn(1)
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)

    def process_event(self, event: Event) -> None:
        """
        Process new data from event and update into table.
        """
        # Disable sorting to prevent unwanted error.
        if self.sorting:
            self.setSortingEnabled(False)

        # Update data into table.
        data = event.data

        if not self.data_key:
            self.insert_new_row(data)
        else:
            key = data.__getattribute__(self.data_key)

            if key in self.cells:
                self.update_old_row(data)
            else:
                self.insert_new_row(data)

        # Enable sorting
        if self.sorting:
            self.setSortingEnabled(True)



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
            parameters = {"strategy_name": "", "vt_symbol": "","vt_local":""}
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