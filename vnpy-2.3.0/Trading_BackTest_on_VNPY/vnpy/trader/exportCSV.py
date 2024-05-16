"""
Export content to CSV
"""

import json
import logging
import sys
from pathlib import Path
from typing import Callable, Dict, Tuple, Union, Optional
from decimal import Decimal
from math import floor, ceil
from datetime import time
import numpy as np
import talib
import csv
from PyQt5 import QtCore, QtGui, QtWidgets
from vnpy.event import Event, EventEngine
from .engine import BaseEngine, MainEngine

from .object import BarData, TickData
from .constant import Exchange, Interval
EngineName = "exportCSVEngine"
class exportCSVEngine(BaseEngine):
    exportPath = ""

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine):
        """"""
        super().__init__(main_engine, event_engine, EngineName)
        """Constructor"""
        self.count: int = 0
        self.widgetsDict: Dict[str, QtWidgets.QWidget] = {}
        self.strategyDict = []
        self.main_engine.addWidgetForCSVExport = self.addWidgetForCSVExport



    def addWidgetForCSVExport(self,widgetName, Widget):
        self.widgetsDict[widgetName] = Widget


    def exportCSV(self,tableWedgit):
        with open(self.exportPath, "w", encoding='utf-8-sig') as f:
            writer = csv.writer(f, lineterminator="\n")

            headers = [d["display"] for d in tableWedgit.headers.values()]
            writer.writerow(headers)

            for row in range(tableWedgit.rowCount()):
                if tableWedgit.isRowHidden(row):
                    continue

                row_data = []
                for column in range(tableWedgit.columnCount()):
                    item = tableWedgit.item(row, column)
                    if item:
                        row_data.append(str(item.text()))
                    else:
                        row_data.append("")
                writer.writerow(row_data)

