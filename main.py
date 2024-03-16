# This Python file uses the following encoding: utf-8
import os
from pathlib import Path
import sys
import re
import json
import unicodedata
import numpy as np

from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtGui import QMouseEvent, QKeySequence, QShortcut, QAction, QIcon
from PySide6.QtWidgets import QApplication, QMainWindow, QTableWidgetItem, QFileDialog, QToolBar, QStyle, QDoubleSpinBox, QListWidgetItem, QHeaderView
from PySide6.QtCore import QFile, QSize, Qt
from PySide6.QtUiTools import QUiLoader

from custom_widgets import ComboBoxDialog, PrimerTableWidget, PositionCursorSelectDelegate, SaveDialog, ModTableView, ModTableItem, CustomFilterProxyModel, SearchableComboBox, PlotWindow, DragDropTableWidget, TableItemDescriptor, TableItemCategoryLabel, ClipSpinBox
from warframe_simulacrum.weapon import Weapon, FireMode, EventTrigger, DamageParameter, Parameter
from warframe_simulacrum.unit import Unit, update
import warframe_simulacrum.constants as sim_cst
from warframe_simulacrum.simulation import Simulacrum, get_first_damage, get_first_status_damage
from string_calc import Calc
import interface_constants as cst
import qrc_resources
import copy

from qt_json_view import model as view_model
from qt_json_view.model import JsonModel
from qt_json_view.view import JsonView

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = None
        self.enemy_ui = None
        self.weapon_ui = None
        self.load_ui()
        self.setAcceptDrops(True)
        self._create_actions()
        self._create_menu_bar()
        self._create_toolbar()
        self._connect_actions()

        self.adjust_layout()
        self.adjust_style()
        self.adjust_startup_settings()
        # self.setup_signals()
        self.plot_window = PlotWindow()

        self.sim = Simulacrum(self.plot_window.canvas.figure, self.plot_window.ax)
        self.display_weapon: Weapon = Weapon("Braton", None, self.sim)
        self.primer_weapon: Weapon = Weapon("Braton", None, self.sim)
        self.display_enemy: Unit = Unit("Charger Eximus", 200, self.sim)
        self.weapon_data = self.get_weapon_data()
        self.enemy_data = self.get_enemy_data()
        self.save_dialog = SaveDialog(self.save_config_to_file)
        self.select_fire_mode_dialog = ComboBoxDialog()

        self.setup_mod_table()
        self.setup_primer_weapon()
        self.setup_edit_enemy_table()
        self.setup_edit_weapon_table()
        self.init_sim_weapon_combo()
        self.refresh_fire_mode_combo()
        # init effect combo
        self.init_preview_weapon_effect_combo()

        self.init_sim_enemy_combo()
        self.refresh_enemy_mode_combo()

        self.setup_damage_preview_table()
        self.setup_weapon_preview_list()
        self.setup_elem_combo_table()

        self.setup_enmey_ui()
        self.setup_weapon_ui()

        self.setup_signals()

        self.swap_selected_weapon()
        self.swap_selected_enemy()

    def adjust_startup_settings(self):
        self.ui.health_multiplier_spinner.setValue(1)
        self.ui.shield_multiplier_spinner.setValue(1)
        self.ui.armor_multiplier_spinner.setValue(1)

    def setup_enmey_ui(self):
        self.enemy_ui.setModal(True)
        self.enemy_ui.setWindowTitle("Add/Edit Enemy")
        self.enemy_ui.edit_enemy_enemyname_lineedit.setText(self.ui.sim_enemy_combo.currentText())

    def setup_edit_enemy_table(self, config=sim_cst.DEFAULT_ENEMY_CONFIG):
        self.edit_enemy_view = JsonView()
        self.update_edit_enemy_jsonview(config)
        # self.enemy_ui.layout().addWidget(self.edit_enemy_view)
        self.enemy_ui.layout().insertWidget(2, self.edit_enemy_view)
    
    def update_edit_enemy_jsonview(self, config=sim_cst.DEFAULT_ENEMY_CONFIG):
        proxy = view_model.JsonSortFilterProxyModel()
        self.jmodel = JsonModel(data=config, editable_keys=True, editable_values=True)
        proxy.setSourceModel(self.jmodel)
        self.edit_enemy_view.setModel(proxy)

    def enemy_edit_mode(self, state):
        if state == Qt.CheckState.Unchecked.value:
            self.enemy_ui.edit_enemy_enemyname_lineedit.setEnabled(False)
            self.enemy_ui.edit_enemy_enemyname_lineedit.setText(self.ui.sim_enemy_combo.currentText())
            self.enemy_ui.delete_enemy_button.setEnabled(True)

        elif state == Qt.CheckState.Checked.value:
            self.enemy_ui.edit_enemy_enemyname_lineedit.setEnabled(True)
            self.enemy_ui.edit_enemy_enemyname_lineedit.setText('')
            self.enemy_ui.delete_enemy_button.setEnabled(False)

    def close_enemy_editor(self):
        self.enemy_ui.close()
    
    def save_enemy_editor(self):
        enemy_name = self.enemy_ui.edit_enemy_enemyname_lineedit.text()
        if self.enemy_ui.edit_enemy_create_new_checkbox.isChecked():
            if (enemy_name == '' or enemy_name in self.enemy_data):
                return
        data = self.jmodel.serialize()
        json_data = self.convert_enemy_jsonview_json(data)
        self.enemy_data[enemy_name] = json_data

        with open("./warframe_simulacrum/data/unit_data.json", 'w') as f:
            json.dump(self.enemy_data, f, indent=4)
        
        self.weapon_ui.edit_enemy_create_new_checkbox.setChecked(False)
        self.enemy_ui.close()
        self.refresh_sim_enemy_combo()
        self.enemy_config_changed()

    def setup_weapon_ui(self):
        self.weapon_ui.setModal(True)
        self.weapon_ui.setWindowTitle("Add/Edit Weapon")
        self.weapon_ui.weapon_lineedit.setText(self.ui.sim_weapon_combo.currentText())

    def setup_edit_weapon_table(self, config=sim_cst.DEFAULT_WEAPON_CONFIG):
        self.edit_weapon_view = JsonView()
        self.update_edit_weapon_jsonview(config)
        self.weapon_ui.layout().insertWidget(2, self.edit_weapon_view)
    
    def update_edit_weapon_jsonview(self, config=sim_cst.DEFAULT_WEAPON_CONFIG):
        proxy = view_model.JsonSortFilterProxyModel()
        self.jmodel = JsonModel(data=config, editable_keys=True, editable_values=True)
        proxy.setSourceModel(self.jmodel)
        self.edit_weapon_view.setModel(proxy)

    def weapon_edit_mode(self, state):
        if state == Qt.CheckState.Unchecked.value:
            self.weapon_ui.weapon_lineedit.setEnabled(False)
            self.weapon_ui.weapon_lineedit.setText(self.ui.sim_weapon_combo.currentText())
            self.weapon_ui.delete_weapon_button.setEnabled(True)

        elif state == Qt.CheckState.Checked.value:
            self.weapon_ui.weapon_lineedit.setEnabled(True)
            self.weapon_ui.weapon_lineedit.setText('')
            self.weapon_ui.delete_weapon_button.setEnabled(False)

    def close_weapon_editor(self):
        self.weapon_ui.close()
    
    def save_weapon_editor(self):
        weapon_name = self.weapon_ui.weapon_lineedit.text()
        if self.weapon_ui.add_new_weapon_checkbox.isChecked():
            if (weapon_name == '' or weapon_name in self.weapon_data):
                return
        data = self.jmodel.serialize()
        json_data = self.convert_weapon_jsonview_json(data)
        self.weapon_data[weapon_name] = json_data

        with open("./warframe_simulacrum/data/ExportWeapons.json", 'w') as f:
            json.dump(self.weapon_data, f, indent=4)
            
        self.weapon_ui.add_new_weapon_checkbox.setChecked(False)
        self.weapon_ui.close()
        self.refresh_sim_weapon_combo()
        self.swap_selected_weapon()
        

    def primer_activate_all(self, state):

        check_state = False
        if state == Qt.CheckState.Unchecked.value:
            check_state = False
        elif state == Qt.CheckState.Checked.value:
            check_state = True
        
        for row in range(self.ui.primer_mod_table.rowCount()):
            item = self.ui.primer_mod_table.cellWidget(row, 1)
            item.checkbox.setChecked(check_state)

        
    def setup_primer_weapon(self):
        primer_fire_mode = next(iter(self.primer_weapon.fire_modes.values()))
        primer_fire_mode.damagePerShot = DamageParameter(np.array([0]*20))
        primer_fire_mode.totalDamage = Parameter(0)

        self.primer_weapon.heat_m['base'] = self.ui.primer_heat_spinner.value()
        self.primer_weapon.statusDuration_m['base'] = self.ui.primer_status_duration_spinner.value()
        self.primer_weapon.factionDamage_m['base'] = self.ui.primer_faction_spinner.value()
        forced_procs = []
        for row in range(self.ui.primer_mod_table.rowCount()):
            item = self.ui.primer_mod_table.cellWidget(row, 1)
            forced_procs += [item.proc_info["proc_index"]]*item.spinner.value()
        for elem in self.primer_weapon.fire_modes:
            self.primer_weapon.fire_modes[elem].forcedProc = forced_procs
            break
        self.swap_primer_config()

    def load_ui(self):
        loader = QUiLoader()
        loader.registerCustomWidget(ModTableView)
        loader.registerCustomWidget(SearchableComboBox)
        loader.registerCustomWidget(DragDropTableWidget)
        loader.registerCustomWidget(ClipSpinBox)
        loader.registerCustomWidget(PrimerTableWidget)

        path = os.fspath(Path(__file__).resolve().parent / "form.ui")
        ui_file = QFile(path)
        ui_file.open(QFile.ReadOnly)
        self.ui = loader.load(ui_file, self)
        ui_file.close()
        self.resize(QSize(1000, 800)) # set window to a default size

        path = os.fspath(Path(__file__).resolve().parent / "enemy_edit_dialog.ui")
        ui_file = QFile(path)
        ui_file.open(QFile.ReadOnly)
        self.enemy_ui = loader.load(ui_file, self)
        ui_file.close()

        path = os.fspath(Path(__file__).resolve().parent / "weapon.ui")
        ui_file = QFile(path)
        ui_file.open(QFile.ReadOnly)
        self.weapon_ui = loader.load(ui_file, self)
        ui_file.close()
    
    def closeEvent(self, event):
        if self.plot_window:
            self.plot_window.close()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
    def dropEvent(self, event):
        fp = event.mimeData().urls()[0].toLocalFile()
        self.load_config_from_file(fp)
        event.accept()

    def adjust_layout(self):
        self.ui.frame_6.layout().setStretchFactor(self.ui.frame_7, 100)
        self.ui.frame_6.layout().setStretchFactor(self.ui.preview_enemy_list, 55)

        self.ui.frame_4.layout().setStretchFactor(self.ui.tabWidget, 100)
        self.ui.frame_4.layout().setStretchFactor(self.ui.groupBox_2, 10)

    def adjust_style(self):
        self.ui.tabWidget.setDocumentMode(True)
        self.ui.heat_settings_widget.hide()

        header = self.ui.primer_mod_table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch)
    
    def setup_signals(self):
        self.ui.load_mods_button.clicked.connect(self.button_pressed)
        self.ui.sim_weapon_combo.activated.connect(self.swap_selected_weapon)
        self.ui.preview_effect_select_combo.activated.connect(self.setup_weapon_preview_list)

        self.ui.sim_enemy_combo.activated.connect(self.swap_selected_enemy)
        self.ui.sim_bodypart_combo.activated.connect(self.setup_damage_preview_table)
        self.ui.sim_animation_combo.activated.connect(self.setup_damage_preview_table)
        self.ui.sim_level_spinner.valueChanged.connect(self.enemy_config_changed)
        self.ui.health_multiplier_spinner.valueChanged.connect(self.enemy_config_changed)
        self.ui.shield_multiplier_spinner.valueChanged.connect(self.enemy_config_changed)
        self.ui.armor_multiplier_spinner.valueChanged.connect(self.enemy_config_changed)
        self.ui.old_level_scale_checkbox.stateChanged.connect(self.enemy_config_changed)

        self.ui.clear_mod_tables_button.clicked.connect(lambda: self.load_mod_config({}))
        self.ui.apply_steel_path_conditions_button.clicked.connect(self.apply_sp_conditions)

        shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        shortcut.activated.connect(lambda: self.save_dialog.show())

        for row in range(self.ui.primer_mod_table.rowCount()):
            item = self.ui.primer_mod_table.cellWidget(row, 1)
            item.spinner.valueChanged.connect(self.setup_primer_weapon)

        self.ui.primer_activate_all_checkbox.stateChanged.connect(self.primer_activate_all)

        self.ui.primer_status_duration_spinner.valueChanged.connect(self.setup_primer_weapon)
        self.ui.primer_faction_spinner.valueChanged.connect(self.setup_primer_weapon)
        self.ui.primer_heat_spinner.valueChanged.connect(self.setup_primer_weapon)

        self.ui.clear_enemy_scaling_button.clicked.connect(self.reset_enemy_scaling_settings)
        self.ui.primer_clear_settings_button.clicked.connect(self.reset_primer_settings)

        self.enemy_ui.edit_enemy_create_new_checkbox.stateChanged.connect(self.enemy_edit_mode)
        self.enemy_ui.edit_enemy_save_button.clicked.connect(self.save_enemy_editor)
        self.enemy_ui.edit_enemy_cancel_button.clicked.connect(self.close_enemy_editor)

        self.enemy_ui.add_bodypart_button.clicked.connect(self.add_enemy_bodypart)
        self.enemy_ui.add_animation_button.clicked.connect(self.add_enemy_animation)
        self.enemy_ui.delete_enemy_button.clicked.connect(self.delete_enemy)

        self.weapon_ui.add_new_weapon_checkbox.stateChanged.connect(self.weapon_edit_mode)
        self.weapon_ui.save_weapon_button.clicked.connect(self.save_weapon_editor)
        self.weapon_ui.cancel_weapon_button.clicked.connect(self.close_weapon_editor)

        self.weapon_ui.add_fire_mode_button.clicked.connect(self.add_fire_mode)
        self.weapon_ui.add_fire_mode_effect_button.clicked.connect(self.add_fire_mode_effect)
        self.weapon_ui.delete_weapon_button.clicked.connect(self.delete_weapon)
    
    def add_enemy_bodypart(self):
        data = self.jmodel.serialize()
        data["bodypart_multipliers"]['new_bodypart'] = {"multiplier": 1., "critical_damage_multiplier": 1.}
        self.update_edit_enemy_jsonview(config=data)

    def add_enemy_animation(self):
        data = self.jmodel.serialize()
        data["animation_multipliers"]['new_animation'] = {"multiplier": 1., "critical_damage_multiplier": 1.}
        self.update_edit_enemy_jsonview(config=data)

    def delete_enemy(self):
        if self.enemy_ui.edit_enemy_create_new_checkbox.isChecked():
            return
        
        enemy_name = self.enemy_ui.edit_enemy_enemyname_lineedit.text()
        self.enemy_data.pop(enemy_name, None)
        self.save_enemy_data()
        # refresh combos
        self.enemy_ui.close()
        self.refresh_sim_enemy_combo()
        self.enemy_config_changed()

    def save_enemy_data(self):
        with open("./warframe_simulacrum/data/unit_data.json", 'w') as f:
            json.dump(self.enemy_data, f, indent=4)

    def add_fire_mode(self):
        data = self.jmodel.serialize()
        converted = self.convert_weapon_json_jsonview(copy.deepcopy(sim_cst.DEFAULT_WEAPON_CONFIG))
        data["fireModes"]['new_fire_mode'] = converted['fireModes']['default']
        self.update_edit_weapon_jsonview(config=data)

    def add_fire_mode_effect(self): #TODO open dialog to select which fire mode to add the fire mode effect
        data = self.jmodel.serialize()
        if len(data["fireModes"]) ==0:
            return
        self.select_fire_mode_dialog.comboBox.clear()
        self.select_fire_mode_dialog.comboBox.addItems(list(data["fireModes"]))
        self.select_fire_mode_dialog.exec()
        fire_mode_name = self.select_fire_mode_dialog.comboBox.currentText()
        fire_mode_effect = data["fireModes"][fire_mode_name]['secondaryEffects']

        dfm = copy.deepcopy(sim_cst.DEFAULT_WEAPON_CONFIG)
        deff = copy.deepcopy(sim_cst.DEFAULT_FIRE_MODE_EFFECT)
        dfm["fireModes"]["default"]['secondaryEffects']['new_fire_mode_effect'] = deff
        cvrt = self.convert_weapon_json_jsonview(dfm)

        fire_mode_effect['new_fire_mode_effect'] = cvrt["fireModes"]["default"]['secondaryEffects']['new_fire_mode_effect']
        self.update_edit_weapon_jsonview(config=data)

    def delete_weapon(self):
        if self.weapon_ui.add_new_weapon_checkbox.isChecked():
            return
        
        weapon_name = self.weapon_ui.weapon_lineedit.text()
        self.weapon_data.pop(weapon_name, None)
        self.save_weapon_data()
        # refresh combos
        self.weapon_ui.close()
        self.refresh_sim_weapon_combo()
        self.swap_selected_weapon()
    
    def save_weapon_data(self):
        with open("./warframe_simulacrum/data/ExportWeapons.json", 'w') as f:
            json.dump(self.weapon_data, f, indent=4)

    def _create_menu_bar(self):
        menuBar = self.menuBar()
        # file menu
        file_menu = menuBar.addMenu("&File")
        # save menu
        save_menu = file_menu.addMenu("&Save")
        save_menu.addAction(self.save_weapon_config_action)
        save_menu.addAction(self.save_enemy_config_action)
        # open menu
        open_menu = file_menu.addMenu("&Open")
        open_menu.addAction(self.open_enemy_config_action)
        open_menu.addAction(self.open_weapon_config_action)

        edit_menu = menuBar.addMenu("&Edit")
        edit_menu.addAction(self.edit_enemy_config_action)
        edit_menu.addAction(self.edit_weapon_config_action)


    def _create_toolbar(self):
        file_toolbar = QToolBar("File")
        file_toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(file_toolbar)
        file_toolbar.addAction(self.save_weapon_config_action)
        file_toolbar.addAction(self.save_enemy_config_action)
        file_toolbar.addAction(self.open_weapon_config_action)
        file_toolbar.addAction(self.open_enemy_config_action)

        edit_toolbar = QToolBar("Edit")
        edit_toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(edit_toolbar)
        edit_toolbar.addAction(self.edit_enemy_config_action)
        edit_toolbar.addAction(self.edit_weapon_config_action)

    
    def _create_actions(self):
        self.save_weapon_config_action = QAction(QIcon(":save_weapon.png"), "Save &Build", self)
        self.save_enemy_config_action= QAction(QIcon(":save_enemy.png"),"Save E&nemy Config", self)
        self.open_enemy_config_action= QAction(QIcon(":load_enemy.png"),"Open E&nemy Config", self)
        self.open_weapon_config_action= QAction(QIcon(":load_weapon.png"),"Open &Build", self)

        self.edit_enemy_config_action= QAction(QIcon(":edit_enemy.png"),"Edit &Enemy", self)
        self.edit_weapon_config_action= QAction(QIcon(":edit_weapon.png"),"Edit &Enemy", self)


    def _connect_actions(self):
        self.save_weapon_config_action.triggered.connect(self.save_weapon_config)
        self.save_enemy_config_action.triggered.connect(self.save_enemy_config)
        self.open_weapon_config_action.triggered.connect(self.open_weapon_config)
        self.open_enemy_config_action.triggered.connect(self.open_enemy_config)

        self.edit_enemy_config_action.triggered.connect(self.edit_enemy_config)
        self.edit_weapon_config_action.triggered.connect(self.edit_weapon_config)

    def edit_weapon_config(self):
        weapon_name = self.ui.sim_weapon_combo.currentText()
        if weapon_name not in self.weapon_data:
            return
        if not self.weapon_ui.add_new_weapon_checkbox.isChecked():
            self.weapon_ui.weapon_lineedit.setText(weapon_name)
        else:
            self.weapon_ui.weapon_lineedit.setText('')
        default = copy.deepcopy(sim_cst.DEFAULT_WEAPON_CONFIG)
        weapon_data = update(default, self.weapon_data.get(weapon_name, default))

        weapon_jsonview_data = self.convert_weapon_json_jsonview(weapon_data)
        self.update_edit_weapon_jsonview(config=weapon_jsonview_data)

        self.edit_weapon_view.header().resizeSection(0, 200)
        self.weapon_ui.show()

    def convert_weapon_json_jsonview(self, data):
        damage_types = [f.capitalize() for f in list(sim_cst.EXPORT_DAMAGE_TYPES)]

        new_data = copy.deepcopy(data)
        new_data['productCategory'] = {"value": new_data.get('productCategory', "Pistols"), "choices": sim_cst.productCategory_types}
        new_data['rivenType'] = {"value": new_data.get('rivenType', "Pistol Riven Mod"), "choices": sim_cst.rivenType_types}

        for fm in new_data['fireModes'].values():
            fm["noise"] = {"value": new_data.get('noise', "ALARMING"), "choices": sim_cst.noise_types}
            fm["trigger"] = {"value": new_data.get('trigger', "SEMI"), "choices": sim_cst.trigger_types}
            # replace damage list with dict
            vals = [float(f) for f in fm.get('damagePerShot',[0]*20)]
            fm['damagePerShot'] = dict(zip(damage_types, vals))
            # replace force proc list with dict

            count_list = [fm.get('forcedProc',[]).count(i) for i in range(20)]
            fm['forcedProc'] = dict(zip(damage_types, count_list))

            for se in fm.get("secondaryEffects", {}).values():
                vals = [float(f) for f in se.get('damagePerShot',[0]*20)]
                se["damagePerShot"] = dict(zip(damage_types, vals))

                count_list = [se.get('forcedProc',[]).count(i) for i in range(20)]
                se['forcedProc'] = dict(zip(damage_types, count_list))

        return new_data
    
    def convert_se_json_jsonview(self, data):
        damage_types = [f.capitalize() for f in list(sim_cst.EXPORT_DAMAGE_TYPES)]

        new_data = copy.deepcopy(data)

        vals = [float(f) for f in new_data.get('damagePerShot',[0]*20)]
        new_data["damagePerShot"] = dict(zip(damage_types, vals))

        count_list = [new_data.get('forcedProc',[]).count(i) for i in range(20)]
        new_data['forcedProc'] = dict(zip(damage_types, count_list))

        return new_data
    
    def convert_weapon_jsonview_json(self, data):
        new_data = copy.deepcopy(data)

        new_data['productCategory'] = new_data.get('productCategory',{}).get("value", "Pistols")
        new_data['rivenType'] = new_data.get('rivenType',{}).get("value", "Pistol Riven Mod")

        if 'fireModes' not in new_data:
            new_data['fireModes'] = self.convert_weapon_json_jsonview(copy.deepcopy(sim_cst.DEFAULT_WEAPON_CONFIG))['fireModes']
        
        if len(new_data['fireModes']) == 0:
            fm_def = self.convert_weapon_json_jsonview(copy.deepcopy(sim_cst.DEFAULT_WEAPON_CONFIG))['fireModes']
            new_data['fireModes'][next(iter(fm_def))] = next(iter(fm_def.values()))
        
        for fm in new_data['fireModes'].values():

            fm["noise"] = new_data.get('noise',{}).get("value", "ALARMING")
            fm["trigger"] = new_data.get('trigger',{}).get("value", "SEMI")
            
            fm["damagePerShot"] = list(fm.get('damagePerShot', dict(zip(list(sim_cst.EXPORT_DAMAGE_TYPES), [0]*20))).values())
            fm['totalDamage'] = sum(fm.get('damagePerShot',[0]*20))

            original_indices = []
            count_list = fm.get('forcedProc', dict(zip(list(sim_cst.EXPORT_DAMAGE_TYPES), [0]*20)) ).values()
            for index, count in enumerate(count_list):
                original_indices.extend([index] * count)
            fm['forcedProc'] = original_indices

            if 'secondaryEffects' not in fm:
                new_data['secondaryEffects'] = {'default':self.convert_se_json_jsonview(copy.deepcopy(sim_cst.DEFAULT_FIRE_MODE_EFFECT))}

            for se in fm["secondaryEffects"].values():
                se["damagePerShot"] = list(se.get('damagePerShot', dict(zip(list(sim_cst.EXPORT_DAMAGE_TYPES), [0]*20))).values())
                se['totalDamage'] = sum(se.get('damagePerShot',[0]*20))

                original_indices = []
                count_list = se.get('forcedProc', dict(zip(list(sim_cst.EXPORT_DAMAGE_TYPES), [0]*20)) ).values()
                for index, count in enumerate(count_list):
                    original_indices.extend([index] * count)
                se['forcedProc'] = original_indices

        return new_data

    def edit_enemy_config(self):
        enemy_name = self.ui.sim_enemy_combo.currentText()
        if enemy_name not in self.enemy_data:
            return
        if not self.enemy_ui.edit_enemy_create_new_checkbox.isChecked():
            self.enemy_ui.edit_enemy_enemyname_lineedit.setText(self.ui.sim_enemy_combo.currentText())
        else:
            self.enemy_ui.edit_enemy_enemyname_lineedit.setText('')
        default = copy.deepcopy(sim_cst.DEFAULT_ENEMY_CONFIG)
        enemy_data = update(default, self.enemy_data.get(enemy_name, default))

        enemy_jsonview_data = self.convert_enemy_json_jsonview(enemy_data)
        self.update_edit_enemy_jsonview(config=enemy_jsonview_data)

        # self.edit_enemy_view.resizeColumnToContents(0)
        self.edit_enemy_view.header().resizeSection(0, 200)
        self.enemy_ui.show()
    
    def convert_enemy_json_jsonview(self, data):
        new_data = copy.deepcopy(data)
        new_data['shield_type'] = {"value": new_data.get('shield_type', "None"), "choices": sim_cst.shield_types}
        new_data['health_type'] = {"value": new_data.get('health_type', "Flesh"), "choices": sim_cst.health_types}
        new_data['armor_type'] = {"value": new_data.get('armor_type', "None"), "choices": sim_cst.armor_types}
        
        new_data['damage_controller_type'] = {"value": new_data.get('damage_controller_type', "DC_NORMAL"), "choices": sim_cst.damage_controller_types}
        new_data['critical_controller_type'] = {"value": new_data.get('critical_controller_type', "CC_NORMAL"), "choices": sim_cst.critical_controller_types}

        return new_data
    
    def convert_enemy_jsonview_json(self, data):
        new_data = copy.deepcopy(data)
        new_data['shield_type'] = new_data.get('shield_type',{}).get("value", "None")
        new_data['health_type'] = new_data.get('health_type',{}).get("value", "Flesh")
        new_data['armor_type'] = new_data.get('armor_type',{}).get("value", "None")
        
        new_data['damage_controller_type'] = new_data.get('damage_controller_type',{}).get("value", "DC_NORMAL")
        new_data['critical_controller_type'] = new_data.get('critical_controller_type',{}).get("value", "CC_NORMAL")

        return new_data

    def open_weapon_config(self):
        file_name = QFileDialog.getOpenFileName(self, 'Open weapon configuration', f'./configs/weapon', "JSON (*.json)", selectedFilter='')
        if not file_name or file_name[0]=='':
            return
        
        self.load_config_from_file(file_name[0])

    def open_enemy_config(self):
        file_name = QFileDialog.getOpenFileName(self, 'Open enemy configuration', f'./configs/enemy', "JSON (*.json)", selectedFilter='')
        if not file_name or file_name[0]=='':
            return
        
        self.load_config_from_file(file_name[0])


    def reset_primer_settings(self):
        self.ui.primer_status_duration_spinner.setValue(0)
        self.ui.primer_faction_spinner.setValue(0)
        self.ui.primer_heat_spinner.setValue(0)
        
        for row in range(self.ui.primer_mod_table.rowCount()):
            item = self.ui.primer_mod_table.cellWidget(row, 1)
            item.spinner.setValue(0)
            item.checkbox.setChecked(False)

    def reset_enemy_scaling_settings(self):
        self.ui.health_multiplier_spinner.setValue(1)
        self.ui.shield_multiplier_spinner.setValue(1)
        self.ui.armor_multiplier_spinner.setValue(1)

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
        self.setup_primer_weapon()
        self.plot_window.ax.cla()
        fire_mode = self.display_weapon.fire_modes[fire_mode_name]
        fire_mode.target_bodypart = self.ui.sim_bodypart_combo.currentText()
        self.sim.run_simulation([self.display_enemy], fire_mode, next(iter(self.primer_weapon.fire_modes.values())))
        self.plot_window.canvas.draw()

        self.plot_window.show()

    def enemy_config_changed(self):
        # create new enemy
        enemy_name = self.ui.sim_enemy_combo.currentText()
        enemy_level = self.ui.sim_level_spinner.value()
        if enemy_name not in self.enemy_data:
            #TODO reset combo to valid weapon
            return
        scaling = sim_cst.OLD_PROTECTION_SCALING if self.ui.old_level_scale_checkbox.isChecked() else sim_cst.NEW_PROTECTION_SCALING
        self.display_enemy = Unit(enemy_name, enemy_level, self.sim, scaling)

        self.setup_enemy_preview_list()
        self.setup_damage_preview_table()

    def load_config_from_file(self, filepath):
        if not filepath.lower().endswith(('.json')):
            return
        with open(filepath) as f:
            try:
                d = json.load(f)
            except Exception as e:
                print(e)
                return
        if 'weapon_config' in d:
            self.load_mod_config(d['weapon_config'])
        if 'primer_config' in d:
            self.load_primer_config(d['primer_config'])
        if 'enemy_config' in d:
            self.load_enemy_config(d['enemy_config'])

    def load_enemy_config(self, config:dict):
        enemy_name = config['enemy_name']
        bodypart = config['bodypart']
        animation = config['animation']
        enemy_level = int(config['level'])

        health_multiplier = float(config['health_multiplier'])
        armor_multiplier = float(config['armor_multiplier'])
        shield_multiplier = float(config['shield_multiplier'])

        index = self.ui.sim_enemy_combo.findText(enemy_name)
        if index != -1:
            self.ui.sim_enemy_combo.setCurrentIndex(index)

        index = self.ui.sim_bodypart_combo.findText(bodypart)
        if index != -1:
            self.ui.sim_bodypart_combo.setCurrentIndex(index)

        index = self.ui.sim_animation_combo.findText(animation)
        if index != -1:
            self.ui.sim_animation_combo.setCurrentIndex(index)

        self.ui.health_multiplier_spinner.setValue(health_multiplier)
        self.ui.armor_multiplier_spinner.setValue(armor_multiplier)
        self.ui.shield_multiplier_spinner.setValue(shield_multiplier)
        self.ui.sim_level_spinner.setValue(enemy_level)

    def load_primer_config(self, primer_config:dict):
        self.ui.primer_status_duration_spinner.setValue(primer_config.get("statusDuration_m", {}).get("base", 0))
        self.ui.primer_faction_spinner.setValue(primer_config.get("factionDamage_m", {}).get("base", 0))
        self.ui.primer_heat_spinner.setValue(primer_config.get("heat_m", {}).get("base", 0))
        
        for row in range(self.ui.primer_mod_table.rowCount()):
            item = self.ui.primer_mod_table.cellWidget(row, 1)
            proc_name = item.proc_info["name"]
            item.spinner.setValue(primer_config.get("forcedProcs", {}).get(proc_name, {}).get("count", 0))
            item.checkbox.setChecked(primer_config.get("forcedProcs", {}).get(proc_name, {}).get("checked", False))
    
    def load_mod_config(self, config:dict):
        # disable signals
        self.ui.mod_table_view.edit_mode = True
            
        # populate table
        filter_proxy_model = self.ui.mod_table_view.model()
        source_model = filter_proxy_model.sourceModel()

        for row in range(source_model.rowCount()):
            source_index = source_model.index(row, 2)
            if source_index.isValid():
                # Retrieve the item at each index
                item = source_model.itemFromIndex(source_index)
                if item is not None:
                    main_type = item.main_type
                    sub_type = item.sub_type
                    ldata = config.get(main_type, {}).get(sub_type, "")
                    item.setText(str(ldata))

        selected_items = [cst.INDEX_COMBINABLEDAMAGE[i] for i in config.get("combineElemental_m", {}).get("indices", [])]
        unselected_items = [key for key in cst.COMBINABLEDAMAGE_INDEX if key not in selected_items]
        self.ui.elemental_mod_order_table.set_items(selected_items+unselected_items)
        model = self.ui.elemental_mod_order_table.model()
        for row in range(len(selected_items)):
            model.item(row, 0).setCheckState(Qt.Checked)

        # setup weapon combo
        weapon_name = config.get("weapon_name", "")
        index = self.ui.sim_weapon_combo.findText(weapon_name)
        if index != -1:
            self.ui.sim_weapon_combo.setCurrentIndex(index)

        fire_mode_name = config.get("fire_mode_name", "")
        index = self.ui.sim_firemode_combo.findText(fire_mode_name)
        if index != -1:
            self.ui.sim_firemode_combo.setCurrentIndex(index)

        self.ui.mod_table_view.edit_mode=False
        self.new_mod_table_config()

        

    # called by ok_clicked method of save_dialog
    def save_config_to_file(self):
        # self.save_dialog.show()
        state1 = self.save_dialog.radio1.isChecked()
        state2 = self.save_dialog.radio2.isChecked()

        if state1:
            self.save_weapon_config()
        elif state2:
            self.save_enemy_config()
    
    def save_weapon_config(self):
        filter_proxy_model = self.ui.mod_table_view.model()
        source_model = filter_proxy_model.sourceModel()
        
        config = {"weapon_config":{}, "primer_config":{}}
        mod_config:dict = config["weapon_config"]
        for row in range(source_model.rowCount()):
            source_index = source_model.index(row, 2)
            if source_index.isValid():
                # Retrieve the item at each index
                item = source_model.itemFromIndex(source_index)
                if item is not None:
                    data = item.text()  # Get the text of the item
                    main_type = item.main_type
                    sub_type = item.sub_type

                    if main_type not in mod_config:
                        mod_config[main_type] = {}
                    mod_config[main_type][sub_type] = data

        model = self.ui.elemental_mod_order_table.model()
        td = [cst.D_INDEX[model.data(model.index(row, col))] for row in range(model.rowCount()) for col in range(model.columnCount()) if model.item(row, col).checkState() == Qt.Checked]
        mod_config["combineElemental_m"] = {"indices":td}

        weapon_name = self.ui.sim_weapon_combo.currentText()
        fire_mode_name = self.ui.sim_firemode_combo.currentText()
        def_filename = slugify(f'{weapon_name}_{fire_mode_name}')
        file_name = QFileDialog.getSaveFileName(self, 'Save configuration as', f'./configs/weapon/{def_filename}.json', "JSON (*.json)", selectedFilter='')
        if not file_name or file_name[0]=='':
            return
        mod_config["weapon_name"] = weapon_name
        mod_config["fire_mode_name"] = fire_mode_name

        # primer
        primer_config = config["primer_config"]
        primer_config["statusDuration_m"] = {"base":self.ui.primer_status_duration_spinner.value()}
        primer_config["factionDamage_m"] = {"base":self.ui.primer_faction_spinner.value()}
        primer_config["heat_m"] = {"base":self.ui.primer_heat_spinner.value()}
        primer_config["forcedProcs"] = {}
        
        for row in range(self.ui.primer_mod_table.rowCount()):
            item = self.ui.primer_mod_table.cellWidget(row, 1)
            primer_config["forcedProcs"][item.proc_info["name"]] = {"count": item.spinner.value() , "checked": item.checkbox.isChecked()}

        
        with open(file_name[0], 'w') as f:
            json.dump(config, f, indent=4)

    def apply_sp_conditions(self):
        self.ui.health_multiplier_spinner.setValue(2.5)
        self.ui.armor_multiplier_spinner.setValue(2.5)
        if self.display_enemy.is_eximus:
            self.ui.shield_multiplier_spinner.setValue(2.5**3)
        else:
            self.ui.shield_multiplier_spinner.setValue(2.5**2)


    def save_enemy_config(self):
        enemy_name = self.ui.sim_enemy_combo.currentText()
        bodypart = self.ui.sim_bodypart_combo.currentText()
        animation = self.ui.sim_animation_combo.currentText()
        enemy_level = self.ui.sim_level_spinner.value()

        health_multiplier = self.ui.health_multiplier_spinner.value()
        armor_multiplier = self.ui.armor_multiplier_spinner.value()
        shield_multiplier = self.ui.shield_multiplier_spinner.value()

        config = {"enemy_config":{}}
        enemy_config = config["enemy_config"]

        enemy_config.update({'enemy_name':enemy_name, 'bodypart':bodypart, 'animation':animation, 
                     'level':enemy_level, 'health_multiplier':health_multiplier, 'armor_multiplier':armor_multiplier, 'shield_multiplier':shield_multiplier})
        
        def_filename = slugify(f'{enemy_name}_level_{enemy_level}')
        file_name = QFileDialog.getSaveFileName(self, 'Save configuration as', f'./configs/enemy/{def_filename}.json', "JSON (*.json)", selectedFilter='')
        if not file_name or file_name[0]=='':
            return
        
        with open(file_name[0], 'w') as f:
            json.dump(config, f, indent=4)
    
    def get_build_summary_string(self):
        weapon_name = self.ui.sim_weapon_combo.currentText()
        fire_mode_name = self.ui.sim_firemode_combo.currentText()



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
        if self.ui.mod_table_view.edit_mode:
            return
        
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
        scaling = sim_cst.OLD_PROTECTION_SCALING if self.ui.old_level_scale_checkbox.isChecked() else sim_cst.NEW_PROTECTION_SCALING
        self.display_enemy = Unit(enemy_name, enemy_level, self.sim, scaling)

        # reset the damage preview table
        self.setup_damage_preview_table()
        self.setup_enemy_preview_list()
    
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

    def swap_primer_config(self):
        # reset the damage preview table
        self.setup_damage_preview_table()


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
    
    def refresh_sim_enemy_combo(self):
        enemy_name = self.ui.sim_enemy_combo.currentText()
        name1 = self.ui.sim_bodypart_combo.currentText()
        name2 = self.ui.sim_animation_combo.currentText()

        self.init_sim_enemy_combo()

        self.ui.sim_enemy_combo.setCurrentIndex(max(0,self.ui.sim_enemy_combo.findText(enemy_name)))
        self.swap_selected_enemy()

        self.ui.sim_bodypart_combo.setCurrentIndex(max(0,self.ui.sim_bodypart_combo.findText(name1)))
        self.ui.sim_animation_combo.setCurrentIndex(max(0, self.ui.sim_animation_combo.findText(name2)))

    def refresh_sim_weapon_combo(self):
        name = self.ui.sim_weapon_combo.currentText()
        name1 = self.ui.sim_firemode_combo.currentText()
        
        self.init_sim_weapon_combo()

        self.ui.sim_weapon_combo.setCurrentIndex(max(0,self.ui.sim_weapon_combo.findText(name)))
        self.ui.sim_firemode_combo.setCurrentIndex(max(0,self.ui.sim_firemode_combo.findText(name1)))
    
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

    def setup_enemy_preview_list(self):
        self.ui.preview_enemy_list.clear()
        self.display_enemy.reset()

        self.display_enemy.health.set_value_multiplier('hp_bonus', self.ui.health_multiplier_spinner.value())
        self.display_enemy.shield.set_value_multiplier('sh_bonus', self.ui.shield_multiplier_spinner.value())
        self.display_enemy.armor.set_value_multiplier('ar_bonus', self.ui.armor_multiplier_spinner.value())

        preview_info = self.display_enemy.get_preview_info()
        for name, val, tooltip in preview_info:
            if name == "Category":
                widget = TableItemCategoryLabel(val)
                self.ui.preview_enemy_list.addItem(widget.list_widget_item)
                self.ui.preview_enemy_list.setItemWidget(widget.list_widget_item, widget)
            else:
                widget = TableItemDescriptor(name, val)  
                self.ui.preview_enemy_list.addItem(widget.list_widget_item)
                self.ui.preview_enemy_list.setItemWidget(widget.list_widget_item, widget)
            if tooltip != "":
                widget.list_widget_item.setToolTip(tooltip)

    def setup_damage_preview_table(self):
        fire_mode_name = self.ui.sim_firemode_combo.currentText()
        if fire_mode_name not in self.display_weapon.fire_modes:
            return
        self.ui.damage_preview_table.clear()
        # fire_mode = self.display_weapon.fire_modes[0] # TODO get selected fire mode 
        fire_mode = self.display_weapon.fire_modes[fire_mode_name]
        damaging_status = [f'{status.upper()}' for status,v in cst.DAMAGING_PROC_NAME_INDEX.items() if (fire_mode.damagePerShot.modded[v]>0 or v in fire_mode.forcedProc)]
        damaging_status_indices = [index for index in cst.DAMAGING_PROC_NAME_INDEX.values() if (fire_mode.damagePerShot.modded[index]>0 or index in fire_mode.forcedProc)]
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
                                                        bodypart=bodypart, animation=animation, enemy_afflictions=afflictions, critical_tiers=critical_tiers, primer=next(iter(self.primer_weapon.fire_modes.values())) )
        first_damage = get_first_damage(self.display_enemy, fire_mode, bodypart=bodypart, animation=animation, enemy_afflictions=afflictions, critical_tiers=critical_tiers, primer=next(iter(self.primer_weapon.fire_modes.values())) )

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

def slugify(value, allow_unicode=False):
    """
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        value = (
            unicodedata.normalize("NFKD", value)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-_")


if __name__ == "__main__":
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)
    app = QApplication([])
    app.setStyle('Fusion')
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())
