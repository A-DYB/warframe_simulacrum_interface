# This Python file uses the following encoding: utf-8
import os
from pathlib import Path
import sys
import inspect
import re
import pandas as pd
import json

from matplotlib.backends.backend_qtagg import FigureCanvas, NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QTableWidgetItem, QVBoxLayout,QDoubleSpinBox, QFrame, QMessageBox, QComboBox, QCheckBox, QRadioButton, QSpinBox, QSlider, QLineEdit, QHeaderView
from PySide6.QtCore import QFile, Signal, QSize, Qt
from PySide6.QtUiTools import QUiLoader

from custom_widgets import PositionCursorSelectDelegate, ModTableView, ModTableItem, CustomFilterProxyModel, SearchableComboBox, PlotWindow, DragDropTableWidget, TableItemDescriptor, TableItemCategoryLabel
from warframe_simulacrum.weapon import Weapon, FireMode, EventTrigger
from warframe_simulacrum.unit import Unit
from warframe_simulacrum.simulation import Simulacrum, print_tiers, stats_changed, get_first_damage, get_first_status_damage
from string_calc import Calc
import interface_constants as cst

from typing import List, Tuple
import heapq
import seaborn as sns


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = None
        self.load_ui()
        self.adjust_layout()
        self.setup_signals()
        self.plot_window = PlotWindow()

        self.sim = Simulacrum(self.plot_window.canvas.figure, self.plot_window.ax)
        self.display_weapon: Weapon = Weapon("Braton", None, self.sim)
        self.display_enemy: Unit = Unit("Charger Eximus", 200, self.sim)
        self.weapon_data = self.get_weapon_data()
        self.enemy_data = self.get_enemy_data()

        self.setup_mod_table()
        self.init_sim_weapon_combo()
        self.refresh_fire_mode_combo()
        # init effect combo
        self.init_preview_weapon_effect_combo()

        self.init_sim_enemy_combo()
        self.refresh_enemy_mode_combo()

        self.setup_damage_preview_table()
        self.setup_weapon_preview_list()
        self.setup_elem_combo_table()

        self.swap_selected_weapon()
        self.swap_selected_enemy()

    def load_ui(self):
        loader = QUiLoader()
        loader.registerCustomWidget(ModTableView)
        loader.registerCustomWidget(SearchableComboBox)
        loader.registerCustomWidget(DragDropTableWidget)
        path = os.fspath(Path(__file__).resolve().parent / "form.ui")
        ui_file = QFile(path)
        ui_file.open(QFile.ReadOnly)
        self.ui = loader.load(ui_file, self)
        ui_file.close()
        self.resize(QSize(1000, 800)) # set window to a default size
    
    def closeEvent(self, event):
        if self.plot_window:
            self.plot_window.close()

    def adjust_layout(self):
        self.ui.frame_6.layout().setStretchFactor(self.ui.frame_7, 100)
        self.ui.frame_6.layout().setStretchFactor(self.ui.preview_enemy_list, 40)

    def setup_signals(self):
        self.ui.load_mods_button.clicked.connect(self.button_pressed)
        self.ui.sim_weapon_combo.activated.connect(self.swap_selected_weapon)
        self.ui.preview_effect_select_combo.activated.connect(self.setup_weapon_preview_list)

        self.ui.sim_enemy_combo.activated.connect(self.swap_selected_enemy)
        self.ui.sim_bodypart_combo.activated.connect(self.setup_damage_preview_table)
        self.ui.sim_animation_combo.activated.connect(self.setup_damage_preview_table)
        self.ui.sim_level_spinner.valueChanged.connect(self.setup_damage_preview_table)

    def show_plot_window(self):
        if self.plot_window is None:
            self.plot_window = PlotWindow()
        self.plot_window.show()

    def button_pressed(self):
        self.display_weapon = Weapon(self.ui.sim_weapon_combo.currentText(), None, self.sim)
        fire_mode_name = self.ui.sim_firemode_combo.currentText()
        if fire_mode_name not in self.display_weapon.fire_modes:
            return
        
        self.load_mod_table_into_weapon(self.display_weapon)
        self.plot_window.ax.cla()
        fire_mode = self.display_weapon.fire_modes[fire_mode_name]
        self.sim.run_simulation([self.display_enemy], fire_mode)
        self.plot_window.canvas.draw()

        self.plot_window.show()


    def load_mod_table_into_weapon(self, weapon:Weapon):
        filter_proxy_model = self.ui.mod_table_view.model()
        source_model = filter_proxy_model.sourceModel()

        mod_config:dict = {}
        for row in range(source_model.rowCount()):
            source_index = source_model.index(row, 2)
            if source_index.isValid():
                # Retrieve the item at each index
                item = source_model.itemFromIndex(source_index)
                if item is not None:
                    data = item.text()  # Get the text of the item
                    main_type = item.main_type
                    sub_type = item.sub_type
                    try:
                        val = Calc.evaluate(data)
                        if val is None:
                            val = max(0, cst.MOD_MIN_VALUE_MAP.get(main_type, {sub_type:0}).get(sub_type, 0)) 
                    except Exception as e:
                        # invalid entry, use the default mod value
                        val = max(0, cst.MOD_MIN_VALUE_MAP.get(main_type, {sub_type:0}).get(sub_type, 0)) 
                    
                    # print(main_type,sub_type, val)
                    if main_type not in mod_config:
                        mod_config[main_type] = {}
                    mod_config[main_type][sub_type] = val

        # get elemental combo
        model = self.ui.elemental_mod_order_table.model()
        td = [cst.D_INDEX[model.data(model.index(row, col))] for row in range(model.rowCount()) for col in range(model.columnCount()) if model.item(row, col).checkState() == Qt.Checked]
        mod_config["combineElemental_m"] = {"indices":td}

        weapon.load_mod_config(mod_config)

    def get_weapon_data(self):
        with open("./warframe_simulacrum/data/ExportWeapons.json", 'r') as f:
            weapon_data = json.load(f)
        return weapon_data

    def get_enemy_data(self):
        with open("./warframe_simulacrum/data/unit_data.json", 'r') as f:
            enemy_data = json.load(f)
        return enemy_data
    
    def new_mod_table_config(self):
        # mod the weapon
        self.load_mod_table_into_weapon(self.display_weapon)

        # reset the damage preview table
        self.setup_damage_preview_table()

        # setup weapon stat preview
        self.setup_weapon_preview_list()

    def swap_selected_enemy(self):
        self.ui.sim_bodypart_combo.blockSignals(True)
        self.ui.sim_animation_combo.blockSignals(True)
        self.refresh_enemy_mode_combo()
        self.ui.sim_bodypart_combo.blockSignals(False)
        self.ui.sim_animation_combo.blockSignals(False)

        # create new enemy
        enemy_name = self.ui.sim_enemy_combo.currentText()
        enemy_level = self.ui.sim_level_spinner.value()
        if enemy_name not in self.enemy_data:
            #TODO reset combo to valid weapon
            return
        self.display_enemy = Unit(enemy_name, enemy_level, self.sim)

        # reset the damage preview table
        self.setup_damage_preview_table()
    
    def swap_selected_weapon(self):
        # disable signals for the fire mode selction combo while we repopulate it
        self.ui.sim_firemode_combo.blockSignals(True)
        self.refresh_fire_mode_combo()
        self.ui.sim_firemode_combo.blockSignals(False)

        # create new weapon
        weapon_name = self.ui.sim_weapon_combo.currentText()
        if weapon_name not in self.weapon_data:
            #TODO reset combo to valid weapon
            return
        self.display_weapon = Weapon(weapon_name, None, self.sim)

        # mod the weapon
        self.load_mod_table_into_weapon(self.display_weapon)

        # reset the damage preview table
        self.setup_damage_preview_table()

        # reset the weapon preview effect combo 
        self.init_preview_weapon_effect_combo()
        # reset the weapon preview list 
        self.setup_weapon_preview_list()

    def refresh_fire_mode_combo(self):
        weapon_name = self.ui.sim_weapon_combo.currentText()
        if weapon_name not in self.weapon_data:
            return
        self.ui.sim_firemode_combo.clear()
        self.ui.sim_firemode_combo.addItems(sorted(self.weapon_data[weapon_name]['fireModes'].keys()))

    def refresh_enemy_mode_combo(self):
        enemy_name = self.ui.sim_enemy_combo.currentText()
        if enemy_name not in self.enemy_data:
            return

        default_part_mult = {"body":{"multiplier":1, "critical_damage_multiplier":1},
                             "head":{"multiplier":3, "critical_damage_multiplier":2}
                             }
        self.ui.sim_bodypart_combo.clear()
        self.ui.sim_bodypart_combo.addItems(sorted(self.enemy_data[enemy_name].get('bodypart_multipliers', default_part_mult).keys()))

        default_anim_mult = {"normal":{"multiplier":1, "critical_damage_multiplier":1}
                             }
        self.ui.sim_animation_combo.clear()
        self.ui.sim_animation_combo.addItems(sorted(self.enemy_data[enemy_name].get('animation_multipliers', default_anim_mult).keys()))

    def init_sim_weapon_combo(self):
        self.ui.sim_weapon_combo.clear()
        self.ui.sim_weapon_combo.addItems(sorted(self.weapon_data.keys()))

    def init_sim_enemy_combo(self):
        self.ui.sim_enemy_combo.clear()
        self.ui.sim_enemy_combo.addItems(sorted(self.enemy_data.keys()))
    
    def init_preview_weapon_effect_combo(self):
        fire_mode_name = self.ui.sim_firemode_combo.currentText()
        fire_mode = self.display_weapon.fire_modes[fire_mode_name]

        self.ui.preview_effect_select_combo.clear()
        self.ui.preview_effect_select_combo.addItems(["Primary Effect"] + sorted(fire_mode.fire_mode_effects.keys()))

    def setup_weapon_preview_list(self):
        self.ui.preview_weapon_list.clear()
        fire_mode_name = self.ui.sim_firemode_combo.currentText()
        effect_text = self.ui.preview_effect_select_combo.currentText()

        fire_mode = self.display_weapon.fire_modes[fire_mode_name]
        effect = fire_mode.fire_mode_effects.get(effect_text, fire_mode)

        for name, val, tooltip in effect.get_preview_info():
            if name == "Category":
                widget = TableItemCategoryLabel(val)
                self.ui.preview_weapon_list.addItem(widget.list_widget_item)
                self.ui.preview_weapon_list.setItemWidget(widget.list_widget_item, widget)
            else:
                widget = TableItemDescriptor(name, val)  
                self.ui.preview_weapon_list.addItem(widget.list_widget_item)
                self.ui.preview_weapon_list.setItemWidget(widget.list_widget_item, widget)
            if tooltip != "":
                widget.list_widget_item.setToolTip(tooltip)

    def setup_damage_preview_table(self):
        fire_mode_name = self.ui.sim_firemode_combo.currentText()
        if fire_mode_name not in self.display_weapon.fire_modes:
            return
        self.ui.damage_preview_table.clear()
        # fire_mode = self.display_weapon.fire_modes[0] # TODO get selected fire mode 
        fire_mode = self.display_weapon.fire_modes[fire_mode_name]
        damaging_status = [f'{status.upper()}' for status,v in cst.DAMAGING_PROC_NAME_INDEX.items() if fire_mode.damagePerShot.modded[v]>0]
        damaging_status_indices = [index for index in cst.DAMAGING_PROC_NAME_INDEX.values() if fire_mode.damagePerShot.modded[index]>0]
        critical_tiers = [int(fire_mode.criticalChance.modded), int(fire_mode.criticalChance.modded)+1]


        self.ui.damage_preview_table.setRowCount(2)
        self.ui.damage_preview_table.setColumnCount(2 + len(damaging_status))

        self.ui.damage_preview_table.setHorizontalHeaderLabels(["CRIT TIER", "PELLET"] + damaging_status)

        bodypart = self.ui.sim_bodypart_combo.currentText()
        animation = self.ui.sim_animation_combo.currentText()
        afflictions = [(self.display_enemy.health.set_value_multiplier,"hp mul", self.ui.health_multiplier_spinner.value() ), 
                       (self.display_enemy.armor.set_value_multiplier,"ar mul", self.ui.armor_multiplier_spinner.value() ),
                       (self.display_enemy.shield.set_value_multiplier,"sh mul", self.ui.shield_multiplier_spinner.value() )
                       ]
        first_status_damage = get_first_status_damage(self.display_enemy, fire_mode, proc_indices=damaging_status_indices, 
                                                        bodypart=bodypart, animation=animation, enemy_afflictions=afflictions, critical_tiers=critical_tiers)
        first_damage = get_first_damage(self.display_enemy, fire_mode, bodypart=bodypart, animation=animation, enemy_afflictions=afflictions, critical_tiers=critical_tiers)

        for i,ct in enumerate(critical_tiers):
            # row, col, item
            item = QTableWidgetItem(f'{ct}')
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.ui.damage_preview_table.setItem(i, 0, item)

            for elem in first_damage:
                if elem['critical_tier'] != ct:
                    continue
                item = QTableWidgetItem(f'{elem["damage"]}')
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.ui.damage_preview_table.setItem(i, 1, item)

            for elem in first_status_damage:
                if elem['critical_tier'] != ct:
                    continue
                list_index = elem['list_index']
                item = QTableWidgetItem(f'{elem["damage"]}')
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.ui.damage_preview_table.setItem(i, 2 + list_index, item)

        header = self.ui.damage_preview_table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.ui.damage_preview_table.verticalHeader().hide()

    def setup_mod_table(self):
        mods = self.display_weapon.get_mod_dict()

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

            value_item = ModTableItem('', mod_type, sub_type) 
            value_item.setEditable(True)
            model.setItem(row, 2, value_item)
            
            
        filter_proxy_model = CustomFilterProxyModel()
        filter_proxy_model.setSourceModel(model)

        self.ui.mod_filter_line_edit.textChanged.connect(filter_proxy_model.setFilterRegularExpression)

        self.ui.mod_table_view.setModel(filter_proxy_model)
        header = self.ui.mod_table_view.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)

        self.ui.mod_table_view.clicked.connect(self.ui.mod_table_view.cellClicked)
        self.ui.mod_table_view.setItemDelegate(PositionCursorSelectDelegate(self.ui.mod_table_view))

        self.ui.mod_table_view.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.ui.mod_table_view.setFocusPolicy(QtCore.Qt.NoFocus)

        self.ui.mod_table_view.updateSpans()
        self.ui.mod_table_view.verticalHeader().hide()

        model.dataChanged.connect(self.new_mod_table_config)

    def new_elemental_combo_config(self):
        self.load_mod_table_into_weapon(self.display_weapon)

        # reset the damage preview table
        self.setup_damage_preview_table()

        # setup weapon stat preview
        self.setup_weapon_preview_list()


    def setup_elem_combo_table(self):
        # self.ui.elemental_mod_order_table.orderChanged.connect(self.new_elemental_combo_config)
        self.ui.elemental_mod_order_table.set_items(["Viral", "Corrosive", "Radiation","Gas","Magnetic","Blast"])
        self.ui.elemental_mod_order_table.model().itemChanged.connect(self.new_elemental_combo_config)

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
