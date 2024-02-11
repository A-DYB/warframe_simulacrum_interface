# This Python file uses the following encoding: utf-8
import os
from pathlib import Path
import sys
import inspect
import re
import pandas as pd

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QWidget, QDoubleSpinBox, QFrame, QMessageBox, QComboBox, QCheckBox, QRadioButton, QSpinBox, QSlider, QLineEdit, QHeaderView
from PySide6.QtCore import QFile, Signal
from PySide6.QtUiTools import QUiLoader

from custom_widgets import PositionCursorSelectDelegate, ModTableView, ModTableItem, CustomFilterProxyModel
from warframe_simulacrum.weapon import Weapon
from string_calc import Calc
import interface_constants as cst


class MainWindow(QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = None
        self.load_ui()
        app.aboutToQuit.connect(self.close_event)

        self.setup_mod_table()

    def load_ui(self):
        loader = QUiLoader()
        loader.registerCustomWidget(ModTableView)
        path = os.fspath(Path(__file__).resolve().parent / "form.ui")
        ui_file = QFile(path)
        ui_file.open(QFile.ReadOnly)
        self.ui = loader.load(ui_file, self)
        ui_file.close()

    def close_event(self):
        pass

    def setup_signals(self):
        pass

    def setup_mod_table(self):
        weapon = Weapon("Braton", None, None)
        mods = weapon.fire_modes[0].get_mod_dict()

        # sanitize naming to present to user
        # mod_info = {}
        mod_info = []
        for i, mod_type in enumerate(mods.keys()):
            if mod_type[-2:] != '_m':
                continue
            mod_type_san = mod_type[:-2] if mod_type[-2:]=='_m' else mod_type
            mod_type_san = (''.join(map(lambda x: x if x.islower() else " "+x, mod_type_san))).title()

            for sub_type in mods[mod_type].keys():
                if any(f['main_type'] == mod_type and (f['sub_type'] is None or f['sub_type'] == sub_type) for f in cst.NON_USER_MODS):
                    continue 
                sub_type_san = sub_type.replace('_', " ").title()
                # mod_info[f'{mod_type_san} {sub_type_san}'] = {'mod_type_san':mod_type_san, 'sub_type_san':sub_type_san, 'main_type':mod_type, 'sub_type':sub_type}
                mod_info.append((mod_type_san, sub_type_san, mod_type, sub_type))

        model = QtGui.QStandardItemModel(len(mod_info), 3 )
        model.setHorizontalHeaderLabels(['MOD TYPE', "MOD SUBTYPE", 'VALUE'])
        for row, (mod_type_san, sub_type_san, mod_type, sub_type) in enumerate(mod_info):
            item = ModTableItem(mod_type_san, mod_type, sub_type) 
            item.setEditable(False)
            model.setItem(row, 0, item)

            sub_item = ModTableItem(sub_type_san, mod_type, sub_type) 
            sub_item.setEditable(False)
            model.setItem(row, 1, sub_item)
            
        filter_proxy_model = CustomFilterProxyModel()
        filter_proxy_model.setSourceModel(model)
        # filter_proxy_model.setFilterKeyColumn(0) # zeroth column
        # filter_proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseSensitivity(QtCore.Qt.CaseInsensitive)) # does not work with subclassed filterproxymodel

        self.ui.mod_filter_line_edit.textChanged.connect(filter_proxy_model.setFilterRegularExpression)

        self.ui.mod_table_view.setModel(filter_proxy_model)

        self.ui.mod_table_view.clicked.connect(self.ui.mod_table_view.cellClicked)
        self.ui.mod_table_view.setItemDelegate(PositionCursorSelectDelegate(self.ui.mod_table_view))

        self.ui.mod_table_view.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.ui.mod_table_view.setFocusPolicy(QtCore.Qt.NoFocus)

        self.ui.mod_table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.ui.mod_table_view.updateSpans()

    def load_mods_from_table(self):
        pass

def camel_to_title(input_string):
    # Split the camel case string into words
    words = re.findall(r'[A-Z][a-z]*', input_string)

    # Capitalize the first letter of each word
    title_words = [word.capitalize() for word in words]

    # Join the words back together with spaces
    title_string = ' '.join(title_words)

    return title_string



if __name__ == "__main__":
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)
    app = QApplication([])
    app.setStyle('Fusion')
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())
