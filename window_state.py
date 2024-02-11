import inspect
from PySide6.QtWidgets import QApplication, QWidget, QDoubleSpinBox, QFrame, QMessageBox, QComboBox, QCheckBox, QRadioButton, QSpinBox, QSlider, QLineEdit, QHeaderView
from PySide6.QtCore import QSettings, QPoint, Qt

from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from main import MainWindow

def guisave(window:MainWindow, settings:QSettings):
        # Save geometry
        settings.setValue('size', window.size())
        settings.setValue('pos', window.pos())

        for name, obj in inspect.getmembers(window.ui):
            if name == 'window_name_combo' and isinstance(obj, QComboBox):
                name = obj.objectName()  # get combobox name
                index = obj.currentIndex()  # get current index from combobox
                text = obj.itemText(index)  # get the text for current index
                result = " ".join(text.split()[1:])
                settings.setValue(name, result)  # save combobox selection to registry

            elif isinstance(obj, QComboBox):
                name = obj.objectName()  # get combobox name
                index = obj.currentIndex()  # get current index from combobox
                text = obj.itemText(index)  # get the text for current index
                settings.setValue(name, text)  # save combobox selection to registry

            if isinstance(obj, QCheckBox):
                name = obj.objectName()
                state = obj.isChecked()
                settings.setValue(name, state)

            if isinstance(obj, QRadioButton):
                name = obj.objectName()
                value = obj.isChecked()
                settings.setValue(name, value)
                
            if isinstance(obj, QSpinBox):
                name  = obj.objectName()
                value = obj.value()           
                settings.setValue(name, value)

            if isinstance(obj, QDoubleSpinBox):
                name  = obj.objectName()
                value = obj.value()           
                settings.setValue(name, value)

            if isinstance(obj, QSlider):
                name  = obj.objectName()
                value = obj.value()           
                settings.setValue(name, value)

            if isinstance(obj, QLineEdit):
                name = obj.objectName()
                value = obj.text()
                settings.setValue(name, value)

def guirestore(window, settings:QSettings):
    window.move(settings.value('pos', QPoint(60, 60)))
    for name, obj in inspect.getmembers(window.ui):
        if isinstance(obj, QComboBox):
            index = obj.currentIndex()
            name = obj.objectName()

            value = (settings.value(name))

            if value == "":
                continue

            index = obj.findText(value, Qt.MatchContains)

            if index != -1:
                obj.setCurrentIndex(index) 

        if isinstance(obj, QLineEdit):
            name = obj.objectName()
            value = settings.value(name)
            if value is not None:
                obj.clear()
                obj.insert(str(value))

        if isinstance(obj, QCheckBox):
            name = obj.objectName()
            value = settings.value(name)
            if value != None:
                obj.setChecked(str_to_bool(value))

        if isinstance(obj, QRadioButton):
            name = obj.objectName()
            value = settings.value(name)
            if value != None:
                obj.setChecked(str_to_bool(value))
        
        if isinstance(obj, QSlider):
            name = obj.objectName()
            value = settings.value(name)  
            if value != None:           
                obj. setValue(int(value))

        if isinstance(obj, QSpinBox):
            name = obj.objectName()
            value = settings.value(name)  
            if value != None:
                obj. setValue(int(value))

        if isinstance(obj, QDoubleSpinBox):
            name = obj.objectName()
            value = settings.value(name)  
            if value != None:
                obj. setValue(float(value))

def str_to_bool(v):
  return v.lower() in ("yes", "true", "t", "1")