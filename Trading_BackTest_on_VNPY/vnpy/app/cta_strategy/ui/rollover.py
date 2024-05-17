from datetime import datetime
from time import sleep
from typing import TYPE_CHECKING
from vnpy.app.algo_trading import AlgoTradingApp
from vnpy.trader.engine import MainEngine
from vnpy.trader.constant import OrderType
from vnpy.trader.object import ContractData, OrderRequest, SubscribeRequest, TickData
from vnpy.trader.object import Direction, Offset
# from vnpy.trader.ui import QtWidgets
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, QCoreApplication
from PyQt5.QtGui import QPixmap, QColor, QFont
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QStyle, QMessageBox, QFrame,
                             QWizard, QWizardPage, QVBoxLayout, QPlainTextEdit, QGridLayout,
                             QLabel, QLineEdit)

from vnpy.trader.converter import OffsetConverter, PositionHolding
from vnpy.trader.constant import Status
from vnpy.trader.utility import round_to
from vnpy.trader.event import (
    EVENT_TRADE
)
from ..engine import CtaEngine, APP_NAME
from ..template import CtaTemplate
from vnpy.event import Event
from threading import Timer
if TYPE_CHECKING:
    from .widget import CtaManager


class WizardPage1(QWizardPage):
    def __init__(self, parent=None):
        super(WizardPage1, self).__init__(parent)

        self.parent = parent
        self.cta_manager: "CtaManager" = parent.cta_manager
        self.cta_engine: CtaEngine = parent.cta_manager.cta_engine
        self.main_engine: MainEngine = parent.cta_manager.main_engine
        self.init_ui()

    def init_ui(self):
        """"""
        self.setTitle("选择移仓合约和策略")

        old_symbols = []

        for vt_symbol, strategies in self.cta_engine.symbol_strategy_map.items():
            if strategies:
                old_symbols.append(vt_symbol)
        self.old_symbol_combo = QtWidgets.QComboBox()
        self.old_symbol_combo.addItems(old_symbols)

        self.new_symbol_line = QtWidgets.QLineEdit()

        self.message_line = QtWidgets.QLabel()

        self.strategy_table = StrategyMonitor()
        self.strategy_table.setMinimumWidth(500)

        button = QtWidgets.QPushButton("待移仓策略")
        button.clicked.connect(self.display_traget_strategies)
        button.setFixedHeight(button.sizeHint().height() * 2)

        form = QtWidgets.QFormLayout()
        form.addRow("移仓合约", self.old_symbol_combo)
        form.addRow("目标合约", self.new_symbol_line)
        form.addRow(self.message_line)
        form.addRow(button)

        hbox = QtWidgets.QHBoxLayout()
        hbox.addLayout(form)
        hbox.addWidget(self.strategy_table)
        self.setLayout(hbox)

    def validatePage(self):
        self.strategy_table.actived_strategyies()
        if self.strategy_table.rollover_strategies_name:
            # (lambda x: x * x, [y for y in range(10)])
            self.parent.rollover_strategies = [self.cta_engine.strategies[x] for x in
                                               self.strategy_table.rollover_strategies_name]
            self.parent.old_symbol = self.old_symbol_combo.currentText()
            if not self.new_symbol_line.text():
                # self.setTitle("移仓目标合约为空")
                QMessageBox.warning(self, '信息', '移仓目标合约为空')
                return False
            elif self.parent.old_symbol == self.new_symbol_line.text():
                # self.setTitle("移仓目标重复")
                QMessageBox.warning(self, '信息', '移仓目标重复')
                return False
            new_symbol = self.new_symbol_line.text()
            # 确认是否有这个合约
            self.parent.subscribe(new_symbol)
            sleep(1)

            new_tick = self.main_engine.get_tick(new_symbol)
            if not new_tick:
                # self.setTitle(f"无法获取目标合约{new_symbol}的盘口数据，请先订阅行情")
                QMessageBox.warning(self, '信息', f"无法获取目标合约{new_symbol}的盘口数据，请先订阅行情")
                return False
            contract = self.main_engine.get_contract(new_symbol)
            self.parent.priceTick = contract.pricetick
            self.parent.new_symbol = new_symbol
            return True
        else:
            # self.setTitle("没有策略被选中")
            QMessageBox.warning(self, '信息', f"没有策略被选中")
            return False

    def display_traget_strategies(self):
        selected_vt_symbol = self.old_symbol_combo.currentText()
        strategies = self.cta_engine.symbol_strategy_map[selected_vt_symbol]
        self.strategy_table.setRowCount(0)
        self.strategy_table.update_data(strategies)


class StrategyMonitor(QtWidgets.QTableWidget):
    """
    Table monitor for parameters and variables.
    """

    def __init__(self):
        """"""
        super(StrategyMonitor, self).__init__()
        self.rollover_strategies_name = []
        self.init_ui()

    def init_ui(self):
        """"""
        labels = list(["选择", "策略名称", "持仓数"])
        self.setColumnCount(len(labels))
        self.setHorizontalHeaderLabels(labels)
        # self.setMaximumWidth(100)

        self.verticalHeader().setVisible(False)
        # self.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)

    def update_data(self, strategies):
        if strategies:
            for iterable, strategy in enumerate(strategies):
                self.insertRow(iterable)
                item_checked = QtWidgets.QTableWidgetItem()
                item_checked.setCheckState(Qt.Checked)
                item_checked.checkState()
                self.setItem(iterable, 0, item_checked)
                self.setItem(iterable, 1, QtWidgets.QTableWidgetItem(strategy.strategy_name))
                self.setItem(iterable, 2, QtWidgets.QTableWidgetItem(str(strategy.pos)))

    def actived_strategyies(self):
        """"""
        rowCount = self.rowCount()
        if rowCount > 0:
            self.rollover_strategies_name = []
            for rowId in range(rowCount):
                if self.item(rowId, 0).checkState():
                    # strategy = self.parent.cta_engine.strategies[self.item(rowId,1)]
                    self.rollover_strategies_name.append(self.item(rowId, 1).text())
        return self.rollover_strategies_name


class WizardPage2(QWizardPage):
    def __init__(self, parent=None):
        super(WizardPage2, self).__init__(parent)

        self.parent = parent

        self.strategy_positive_pos = 0
        self.strategy_negative_pos = 0
        self.strategy_net_pos = 0

        self.account_positive_pos = 0
        self.account_negative_pos = 0
        self.account_net_pos = 0
        self._conclusion_list = {
            0: "持仓待更新",
            1: "策略净持仓和账户合约净持仓相等, 账户单向持仓，净仓模式",
            2: "策略净持仓和账户合约净持仓相等, 账户双向持仓",
            3: "策略净持仓和账户合约净持仓存在差异"

        }
        self.conclusion = 0

        self.init_ui()

    def init_ui(self):
        """"""
        self.setTitle('移仓数量和账户持仓数据')

        AllvLayout = QVBoxLayout()
        # 中间窗口部分显示的内容
        vLayout = QGridLayout()
        self.strategy_info = QLabel()
        self.strategy_positive_info = QLabel()
        self.strategy_negative_info = QLabel()
        self.strategy_net_info = QLabel()
        vLayout.addWidget(self.strategy_info, 0, 0)
        vLayout.addWidget(self.strategy_positive_info, 1, 0)
        vLayout.addWidget(self.strategy_negative_info, 2, 0)
        vLayout.addWidget(self.strategy_net_info, 3, 0)

        frame = QFrame()  #
        frame.setFrameStyle(QFrame.Box)
        self.accnout_info = QLabel()
        self.accnout_positive_info = QLabel()
        self.accnout_negative_info = QLabel()
        self.accnout_net_info = QLabel()
        vLayout.addWidget(self.accnout_info, 0, 1)
        vLayout.addWidget(self.accnout_positive_info, 1, 1)
        vLayout.addWidget(self.accnout_negative_info, 2, 1)
        vLayout.addWidget(self.accnout_net_info, 3, 1)
        frame.setLayout(vLayout)
        self.conclusion_info = QLabel()
        self.conclusion_info.setFont(QFont(self.conclusion_info.font().family(), 14))
        self.conclusion_info.setAlignment(Qt.AlignCenter)

        frame2 = QFrame()
        form = QtWidgets.QFormLayout()
        self.max_order_count_spin = QtWidgets.QSpinBox()
        self.max_order_count_spin.setRange(1,5000)
        self.max_order_count_spin.setValue(100)
        self.wait_time_spin = QtWidgets.QSpinBox()
        self.wait_time_spin.setRange(0, 10000)
        # self.payup_spin.setValue(2)
        self.wait_time_spin.setValue(3)
        form.addRow("交易单笔限额 ", self.max_order_count_spin)
        form.addRow("单笔成交后等待(秒)", self.wait_time_spin)
        # form.addRow(QLabel("市价单发单"))
        frame2.setLayout(form)

        AllvLayout.addWidget(frame)
        AllvLayout.addWidget(self.conclusion_info)
        AllvLayout.addWidget(frame2)


        self.setLayout(AllvLayout)
        self.setButtonText(QWizard.NextButton, '确定移仓')

    def initializePage(self):
        self.strategy_positive_pos = 0
        self.strategy_negative_pos = 0
        for strategy in self.parent.rollover_strategies:
            if strategy.pos > 0:
                self.strategy_positive_pos += strategy.pos
            elif strategy.pos < 0:
                self.strategy_negative_pos += strategy.pos
        self.strategy_net_pos = self.strategy_positive_pos + self.strategy_negative_pos
        self.strategy_info.setText(f"选取 {self.parent.old_symbol} 策略共: {len(self.parent.rollover_strategies)} 个")
        self.strategy_positive_info.setText(f"策略多仓共： {self.strategy_positive_pos}")
        self.strategy_negative_info.setText(f"策略空仓共： {abs(self.strategy_negative_pos)}")
        self.strategy_net_info.setText(f"策略净持仓共： {self.strategy_net_pos}")

        current_holding = self.parent.current_position()
        self.account_positive_pos = current_holding.long_pos
        self.account_negative_pos = -current_holding.short_pos
        self.account_net_pos = self.account_positive_pos + self.account_negative_pos

        self.accnout_info.setText(f"账户当前合约: {self.parent.old_symbol}")
        self.accnout_positive_info.setText(f"账户多仓共： {self.account_positive_pos}")
        self.accnout_negative_info.setText(f"账户空仓共： {abs(self.account_negative_pos)}")
        self.accnout_net_info.setText(f"账户净持仓共： {self.account_net_pos}")

        if self.account_net_pos == self.strategy_net_pos and (
                self.account_negative_pos == 0 or self.account_positive_pos == 0):
            self.conclusion = 1
            self.parent.move_position = self.strategy_net_pos
        elif self.account_net_pos == self.strategy_net_pos and self.account_negative_pos != 0 and self.account_positive_pos != 0:
            self.conclusion = 2
        elif self.account_net_pos != self.strategy_net_pos:
            self.conclusion = 3

        self.conclusion_info.setText(self._conclusion_list[self.conclusion])

    def validatePage(self):

        if self.conclusion == 1:
            self.parent.ROLL_OVER_MAX = self.max_order_count_spin.value()
            self.parent.trade_wait_time = self.wait_time_spin.value()
            return True
        else:
            QMessageBox.warning(self, '信息', self._conclusion_list[self.conclusion])
            return False


class WizardPage3(QWizardPage):
    def __init__(self, parent=None):
        super(WizardPage3, self).__init__(parent)
        self.parent = parent

        self.init_ui()

    def init_ui(self):

        self.setTitle("移仓交易")
        self.setMinimumHeight(600)
        vboxLayout = QtWidgets.QVBoxLayout()
        self.old_symbol_info = QLabel()
        self.new_symbol_info = QLabel()
        self.move_pistion = QLabel()
        self.move_strategy = QLabel()
        self.roll_over_info = QLabel()

        form = QtWidgets.QFormLayout()
        form.addRow("移仓合约 ", self.old_symbol_info)
        form.addRow("目标合约 ", self.new_symbol_info)
        form.addRow("委托移仓数量 ", self.move_pistion)
        form.addRow("更新策略 ", self.move_strategy)
        form.addRow("交易说明 ", self.roll_over_info)

        button = QtWidgets.QPushButton("移仓启动")
        button.clicked.connect(self.parent.roll_all)
        button.setFixedHeight(button.sizeHint().height() * 2)

        self.log_edit = QtWidgets.QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMinimumWidth(500)
        self.log_edit.setMinimumHeight(200)

        vboxLayout.addLayout(form)
        vboxLayout.addWidget(button)
        vboxLayout.addWidget(self.log_edit)
        self.setLayout(vboxLayout)

    def initializePage(self):
        self.old_symbol_info.setText(self.parent.old_symbol)
        self.new_symbol_info.setText(self.parent.new_symbol)
        self.move_pistion.setText(str(self.parent.move_position))
        textline = ""
        for strategy in self.parent.rollover_strategies:
            textline += f"策略： {strategy.strategy_name} 仓位： {strategy.pos}" + "\n"
        self.move_strategy.setText(textline)

        roundCount = abs(self.parent.move_position) // self.parent.ROLL_OVER_MAX
        self.parent.request_split_list = [self.parent.ROLL_OVER_MAX for x in range(roundCount)]
        lastAmount = abs(self.parent.move_position) - self.parent.ROLL_OVER_MAX * roundCount
        if lastAmount != 0:
            self.parent.request_split_list.append(abs(self.parent.move_position) - self.parent.ROLL_OVER_MAX * roundCount)
        self.parent.send_count = len(self.parent.request_split_list)


        if self.parent.send_count > 0:

            self.roll_over_info.setText(f"移仓手数： {self.parent.move_position}； 发单限额： {self.parent.ROLL_OVER_MAX} \n" +
                                        f"交易将会分: {self.parent.send_count} 次发出; 每次笔数为 {self.parent.request_split_list} \n"
                                        f"按照市价发单, 每个交易完成后等待{self.parent.trade_wait_time}秒\n")
        elif self.parent.move_position !=0:
            self.roll_over_info.setText(f"交易将会单次发出; 按当前"
                                        f"市价发单")
        elif self.parent.move_position ==0:
            self.roll_over_info.setText(f"无需交易，仅作策略合约切换")

class RolloverTool(QWizard):
    """"""
    log_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(str)
    # trade_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(Event)
    def __init__(self, cta_manager: "CtaManager") -> None:
        """"""
        super().__init__()

        self.cta_manager: "CtaManager" = cta_manager
        self.event_engine = cta_manager.event_engine
        self.cta_engine: CtaEngine = cta_manager.cta_engine
        self.main_engine: MainEngine = cta_manager.main_engine



        self.rollover_strategies = []
        self.new_strategies = []
        self.old_symbol = ""
        self.new_symbol = ""
        self.move_position = 0
        self.ROLL_OVER_MAX = 100
        self.send_count = 0
        self.request_split_list = []
        self.request_count = 0
        self.payup = 2
        self.trade_wait_time = 3
        self.deal_volume = 0
        self.priceTick = 0
        self.old_completed_traders = 0
        self.new_completed_traders = 0




        self.new_vt_orderids = []
        self.old_vt_orderids = []

        self.new_vt_traders = []
        self.old_vt_traders = []

        self.total_new_vt_traders = []
        self.total_old_vt_traders = []


        self.page1 = WizardPage1(self)
        self.page2 = WizardPage2(self)
        self.page3 = WizardPage3(self)

        self.register_event()
        self.log_signal.connect(self.log_txt_append)
        self.init_ui()

    def register_event(self):
        """"""
        # self.trade_signal.connect(self.process_trade_event)
        self.event_engine.register(EVENT_TRADE, self.process_trade_event)


    # def process_order_event(self, event):
    #   """"""
    #   order = event.data
    #   if order.vt_orderid in self.old_vt_orderids and order.status == Status.ALLTRADED:
    #       self.old_vt_orderids_complete += 1
    #
    #   if order.vt_orderid in self.new_vt_orderids and order.status == Status.ALLTRADED:
    #       self.new_vt_orderids_complete += 1

    def process_trade_event(self, event):
        trade = event.data
        if trade.vt_orderid in self.old_vt_orderids:
            self.old_vt_traders.append((trade.volume,trade.price))
            self.old_completed_traders +=trade.volume
        elif trade.vt_orderid in self.new_vt_orderids:
            self.new_vt_traders.append((trade.volume,trade.price))
            self.new_completed_traders +=trade.volume
        else:
            return

        if self.new_completed_traders == 0 or self.old_completed_traders == 0:
            return


        if self.send_count == 0 and self.old_completed_traders == self.deal_volume and self.new_completed_traders == self.deal_volume:
            self.update_strategies(self.old_vt_traders,self.new_vt_traders)

        elif self.send_count != 0 and self.old_completed_traders == self.deal_volume and self.new_completed_traders == self.deal_volume:
            self.total_old_vt_traders.extend(self.old_vt_traders)
            self.total_new_vt_traders.extend(self.new_vt_traders)
            self.write_log(f"第({self.request_count+1})笔移仓交易完成，移仓数量：{self.deal_volume}")
            if self.request_count == self.send_count:
                self.update_strategies(self.total_old_vt_traders,self.total_new_vt_traders)
                return
            # sleep(self.trade_wait_time)
            wait_Timer = Timer(self.trade_wait_time,self.next_trade_request)
            self.write_log(f"等待{self.trade_wait_time}秒后启动下一个笔交易")
            wait_Timer.start()

    def next_trade_request(self):
        self.old_vt_traders = []
        self.new_vt_traders = []
        self.old_completed_traders = 0
        self.new_completed_traders = 0
        self.deal_volume = self.request_split_list[self.request_count]
        self.roll_position(self.old_symbol, self.new_symbol, self.payup)
        self.request_count += 1


    def init_ui(self):
        self.setPage(0, self.page1)
        self.setPage(1, self.page2)
        self.setPage(2, self.page3)

        # 去掉帮助按钮
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        # 窗口最小化
        self.setWindowFlags(Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)
        # 设置导航样式
        self.setWizardStyle(QWizard.ModernStyle)
        # 设置导航窗口标题
        self.setWindowTitle("移仓助手")

        # self.setWindowModality(Qt.ApplicationModal)

        # 去掉页面的一些按钮
        self.setOption(QWizard.NoBackButtonOnStartPage)  # 首页没有回退按钮
        # self.setOption(QWizard.NoBackButtonOnLastPage)  # 最后一页没有回退按钮
        self.setOption(QWizard.NoCancelButton)  # 没有取消按钮

        # # 设置导航栏背景标题
        # pix = QPixmap(640, 64)
        # pix.fill(QColor(52, 104, 192))
        # self.setPixmap(QWizard.BannerPixmap, pix)

        # # 设置标题栏图标
        # pix = QPixmap(os.path.dirname(__file__) + "/python.png")
        # self.setPixmap(QWizard.LogoPixmap, pix.scaled(48, 48))

        # 设置页面主标题显示格式
        self.setTitleFormat(Qt.RichText)
        # # 设置子标题显示格式
        # self.setSubTitleFormat(Qt.RichText)

        # 设置按钮的显示名称
        self.setButtonText(QWizard.NextButton, '下一步')
        self.setButtonText(QWizard.BackButton, '上一步')
        self.setButtonText(QWizard.FinishButton, '完成')

    def write_log(self, text: str) -> None:
        """"""
        now = datetime.now()
        text = now.strftime("%H:%M:%S\t") + text
        self.log_signal.emit(text)
        self.main_engine.write_log(text)

    def log_txt_append(self,text):
        self.page3.log_edit.append(text)
        self.page3.log_edit.moveCursor(QtGui.QTextCursor.End)

    def subscribe(self, vt_symbol: str) -> None:
        """"""
        contract = self.main_engine.get_contract(vt_symbol)
        if not contract:
            return

        req = SubscribeRequest(contract.symbol, contract.exchange)
        self.main_engine.subscribe(req, contract.gateway_name)

    def roll_all(self) -> None:
        """"""
        # Check all strategies inited (pos data loaded from disk json file)
        for strategy in self.rollover_strategies:
            if not strategy.inited:
                self.write_log(f"策略{strategy.strategy_name}尚未初始化，无法执行移仓")
                return
            if strategy.trading:
                self.write_log(f"策略{strategy.strategy_name}是交易状态，将停止交易")
                self.cta_engine.stop_strategy(strategy.strategy_name)
                self.write_log(f"策略{strategy.strategy_name}已经停止交易")

        # self.setOption(QWizard.NoBackButtonOnLastPage)
        # self.setEnabled(False)
        # Roll position first
        if self.send_count == 0:
            self.deal_volume = abs(self.move_position)
            self.roll_position(self.old_symbol, self.new_symbol, self.payup)
        else:
            self.deal_volume = self.request_split_list[self.request_count]
            self.roll_position(self.old_symbol, self.new_symbol, self.payup)
            self.request_count +=1

    # Disable self




    def rollover_price_diff(self,old_tuplelist, new_tuplelist):
        old_average_price = self.calculte_average(old_tuplelist)
        self.write_log(f"旧合约平仓均价：{round_to(old_average_price,self.priceTick)}")
        new_average_price = self.calculte_average(new_tuplelist)
        self.write_log(f"目标合约开仓均价：{round_to(new_average_price,self.priceTick)}")
        price_diff = new_average_price - old_average_price
        self.write_log(f"新旧移仓差价：{price_diff}")
        return price_diff

    def calculte_average(self, tuplelist):
        total_volume= 0
        total_price = 0
        for tupleOne in tuplelist:
            total_volume += tupleOne[0]
            total_price += tupleOne[0]*tupleOne[1]
        return total_price/total_volume

    def current_position(self) -> PositionHolding:
        """"""
        converter = self.cta_engine.offset_converter
        holding: PositionHolding = converter.get_position_holding(self.old_symbol)

        return holding

    def roll_position(self, old_symbol: str, new_symbol: str, payup: int) -> None:
        """"""
        converter = self.cta_engine.offset_converter
        holding: PositionHolding = converter.get_position_holding(old_symbol)

        if self.deal_volume == 0:
            self.write_log(f"无需交易，移仓数量：{self.deal_volume}")
            self.update_strategies(self.old_vt_traders,self.new_vt_traders)
            return

        if holding.long_pos:
            # if holding.long_pos != self.move_position:
            #   QMessageBox.warning(self, '信息', f"账户持仓数量改变，请退回")
            #   return

            self.old_vt_orderids = self.send_order(
                old_symbol,
                Direction.SHORT,
                Offset.CLOSE,
                payup,
                self.deal_volume
            )

            self.new_vt_orderids = self.send_order(
                new_symbol,
                Direction.LONG,
                Offset.OPEN,
                payup,
                self.deal_volume
            )

        # Roll short postiion
        if holding.short_pos:
            # if holding.short_pos != self.move_position:
            #   QMessageBox.warning(self, '信息', f"账户持仓数量改变，请退回")
            #   return

            self.old_vt_orderids = self.send_order(
                old_symbol,
                Direction.LONG,
                Offset.CLOSE,
                payup,
                self.deal_volume
            )

            self.new_vt_orderids = self.send_order(
                new_symbol,
                Direction.SHORT,
                Offset.OPEN,
                payup,
                self.deal_volume
            )
        self.write_log(f"第({self.request_count+1})笔移仓交易请求发出，移仓数量：{self.deal_volume}")

    def update_strategies(self,old_vt_traders,new_vt_traders):
        """when deal complete, update_strategies"""
        self.write_log(f"===========持仓更新完成，开始更新策略, 请完成后再关闭窗口============")
        if old_vt_traders and new_vt_traders:
            price_diff = self.rollover_price_diff(old_vt_traders,new_vt_traders)
        else:
            old_tick: TickData = self.main_engine.get_tick(self.old_symbol)
            new_tick: TickData = self.main_engine.get_tick(self.new_symbol)
            price_diff = new_tick.last_price - old_tick.last_price
        # Then roll strategy
        for strategy in self.rollover_strategies:
            self.roll_strategy(strategy, self.new_symbol, price_diff)

        check_Timer = Timer(5, self.check_update_strategies)
        check_Timer.start()
    # self.setEnabled(False)
    # for new_strategy in self.new_strategies:
    #   while not new_strategy.inited:
    #       sleep(2)
    #   self.cta_engine.start_strategy(new_strategy.strategy_name)
    #   self.write_log(f"更新策略 [{new_strategy.strategy_name}] 初始化完成，启动完成")
    # self.write_log(f"==========={self.old_symbol} -> {self.new_symbol} 移仓完成 ============")
    #
    # self.setEnabled(True)

    def check_update_strategies(self):
        if self.new_strategies:
            for new_strategy in self.new_strategies:
                if new_strategy.inited:
                    self.cta_engine.start_strategy(new_strategy.strategy_name)
                    self.write_log(f"更新策略 [{new_strategy.strategy_name}] 初始化完成，启动完成")
                    self.new_strategies.remove(new_strategy)
            check_Timer = Timer(5,self.check_update_strategies)
            check_Timer.start()
        else:
            self.write_log(f"==========={self.old_symbol} -> {self.new_symbol} 移仓完成 请关闭窗口 ============")
            self.setEnabled(True)



    def roll_strategy(self, strategy: CtaTemplate, vt_symbol: str, price_diff) -> None:
        """"""
        if not strategy.inited:
            self.cta_engine._init_strategy(strategy.strategy_name)

        # Save data of old strategy
        pos = strategy.pos
        name = strategy.strategy_name
        vt_local = strategy.vt_local
        parameters = strategy.get_parameters()
        if pos !=0:
            new_price = round_to(strategy.PosPrice + price_diff, self.priceTick)
        else:
            new_price = 0


        # Remove old strategy
        result = self.cta_engine.remove_strategy(name)
        if result:
            self.cta_manager.remove_strategy(name)

        self.write_log(f"移除老策略 [{name}] [{strategy.vt_symbol}],仓位:{strategy.pos}, 原价格:{strategy.PosPrice}")

        # Add new strategy
        if ("init_pos" in parameters) and ("init_entry_price" in parameters):
            parameters["init_pos"] = pos
            parameters["init_entry_price"] = new_price

        # Add new strategy
        self.cta_engine.add_strategy(
            strategy.__class__.__name__,
            name,
            vt_symbol,
            vt_local,
            parameters
        )
        # self.write_log(f"创建策略 [{name}] [{vt_symbol}]")

        # Init new strategy
        self.cta_engine.init_strategy(name)
        # self.write_log(f"初始化策略 [{name}] [{vt_symbol}]")

        # Update pos to new strategy
        new_strategy: CtaTemplate = self.cta_engine.strategies[name]
        new_strategy.pos = pos
        new_strategy.PosPrice = new_price
        self.cta_engine.sync_strategy_data(new_strategy)
        self.cta_engine.put_strategy_event(new_strategy)
        self.new_strategies.append(new_strategy)
        self.write_log(f"更新策略 [{name}] [{vt_symbol}]完成,仓位:{new_strategy.pos}, 价格:{new_price}")


    def send_order(
            self,
            vt_symbol: str,
            direction: Direction,
            offset: Offset,
            payup: int,
            volume: float,
    ):
        """
        Send a new order to server.
        """
        contract: ContractData = self.main_engine.get_contract(vt_symbol)
        tick: TickData = self.main_engine.get_tick(vt_symbol)
        offset_converter: OffsetConverter = self.cta_engine.offset_converter

        if direction == Direction.LONG:
            if tick.limit_up:
                price = tick.limit_up
            else:
                price = tick.ask_price_5
        else:
            if tick.limit_down:
                price = tick.limit_down
            else:
                price = tick.bid_price_5

        original_req: OrderRequest = OrderRequest(
            symbol=contract.symbol,
            exchange=contract.exchange,
            direction=direction,
            offset=offset,
            type=OrderType.LIMIT,
            price=price,
            volume=volume,
            reference=f"{APP_NAME}_Rollover"
        )

        req_list = offset_converter.convert_order_request(original_req, False, False)

        vt_orderids = []
        for req in req_list:
            vt_orderid = self.main_engine.send_order(req, contract.gateway_name)
            if not vt_orderid:
                continue

            vt_orderids.append(vt_orderid)
            offset_converter.update_order_request(req, vt_orderid)

        msg = f"发出委托{vt_symbol}，{direction.value} {offset.value}，{volume}@{price}"
        self.write_log(msg)
        return vt_orderids
