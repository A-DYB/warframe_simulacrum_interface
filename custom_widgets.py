from PySide6.QtWidgets import QTableWidgetItem, QTreeView, QCheckBox, QDoubleSpinBox, QStyledItemDelegate,QHeaderView, QRadioButton, QPushButton, QTableWidget, QDialog, QMessageBox, QFrame, QSpinBox,  QListWidgetItem, QHBoxLayout, QLabel, QLineEdit, QComboBox, QApplication, QStyledItemDelegate, QLineEdit, QTableView, QAbstractItemView, QWidget, QCompleter, QVBoxLayout
from PySide6.QtCore import Qt, QAbstractProxyModel, QSortFilterProxyModel,QItemSelectionModel, Signal, QTimer, QAbstractItemModel, QModelIndex, QObject, Qt, QFileInfo
from PySide6.QtGui import QCursor, QStandardItemModel, QStandardItem, QValidator
import interface_constants as cst

from matplotlib.backends.backend_qtagg import FigureCanvas, NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from typing import List, Dict, Union, Any


# Create a custom QTableView class that inherits from QTableView
class ModTableView(QTableView):
    def __init__(self, parent: QWidget | None = ...) -> None:
        super().__init__(parent)
        self.edit_mode=False

    def cellClicked(self, index):
        model = self.model()
        if model is None:
            return

        # Map the proxy index to the source index
        sourceIndex = self.model().mapToSource(index)

        # Check if the source index is valid
        if sourceIndex.isValid():
            flags = model.sourceModel().flags(sourceIndex)
            if not flags & Qt.ItemIsEditable:
                # print("Cell is not editable.")
                return
        else:
            # print("Invalid index.")
            return
        
        # start editing on single click
        if not (self.state() == QTableView.EditingState):
            self.edit(index)
        else:
            if self.currentIndex() == index:
                self.selectionModel().select(index, QItemSelectionModel.Deselect)

    def rowsInserted(self, parent, start, end):
        super().rowsInserted(parent, start, end)
        self.updateSpans()

    def rowsRemoved(self, parent, start, end):
        super().rowsRemoved(parent, start, end)
        self.updateSpans()

    def updateSpans(self):
        if not self.model():
            return

        column_to_span = 0  # Replace with the index of the column you want to span
        current_span_start = None
        current_span_size = 0

        for row in range(self.model().rowCount()):
            index = self.model().index(row, column_to_span)

            if current_span_start is None:
                current_span_start = row
                current_span_size = 1
            else:
                if self.model().data(index) == self.model().data(self.model().index(current_span_start, column_to_span)):
                    current_span_size += 1
                else:
                    if current_span_size > 1:
                        self.setSpan(current_span_start, column_to_span, current_span_size, 1)
                    current_span_start = row
                    current_span_size = 1

        if current_span_size > 1:
            self.setSpan(current_span_start, column_to_span, current_span_size, 1)

class PositionCursorSelectDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)

        if isinstance(editor, QLineEdit):
            gpos = QCursor.pos()
            lpos = editor.mapFromGlobal(gpos)
            editor.setCursorPosition(editor.cursorPositionAt(lpos))
            
            def position_cursor():
                if QApplication.mouseButtons() == Qt.LeftButton:
                    editor.selectionChanged.disconnect(position_cursor)
                    return

                # Catch the initial selectAll event via the selectionChanged 
                # signal; this ensures the position is calculated after the
                # control is placed on screen, so cursorPositionAt will work
                # correctly.

                # Disconnect so setCursorPosition won't call this func again
                editor.selectionChanged.disconnect(position_cursor)
                # Get cursor position within the editor's coordinate system
                gpos = QCursor.pos()
                lpos = editor.mapFromGlobal(gpos)
                editor.setCursorPosition(editor.cursorPositionAt(lpos))
                editor.selectionChanged.connect(position_cursor)


            editor.selectionChanged.connect(position_cursor)
                
        return editor
    
    def setModelData(self, editor, model, index):
        super().setModelData(editor, model, index)
        # After data has been committed, set the cursor position again
        editor.setCursorPosition(editor.cursorPosition())

        
class ModTableItem(QStandardItem):
    def __init__(self, text:str, main_type:str, sub_type:str):
        super().__init__(text)
        self.main_type = main_type
        self.sub_type = sub_type

class CustomFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.filter_column_1 = 0  # First column
        self.filter_column_2 = 1  # Second column

    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        if model is None:
            return False

        text_filter = self.filterRegularExpression().pattern().casefold()
        if text_filter == '':
            return True

        index_1 = model.index(source_row, self.filter_column_1, source_parent)
        index_2 = model.index(source_row, self.filter_column_2, source_parent)

        if not index_1.isValid() or not index_2.isValid():
            return False

        data_1 = model.data(index_1, Qt.DisplayRole)
        data_2 = model.data(index_2, Qt.DisplayRole)
        # print(data_1, data_2, text_filter in data_1, text_filter in data_2)



        for word in text_filter.split(' '):
            if (word not in data_1.casefold() and word not in data_2.casefold()
                and not any(word in f.casefold() for f in cst.REMAP_MOD_SEARCH.get(data_1, ['']))
                and not any(word in f.casefold() for f in cst.REMAP_MOD_SEARCH.get(data_2, ['']))
                ):
                return False
        return True
        

        # Check if either column matches the filter
        return text_filter in data_1 or text_filter in data_2
    
class SubstringFilterProxyModel(QSortFilterProxyModel):
    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        if model is None:
            return False

        text_filter = self.filterRegularExpression().pattern().casefold()
        if text_filter == '':
            return True

        model_index = model.index(source_row, 0, source_parent)
        if not model_index.isValid():
            return False
        
        model_data = model.data(model_index, Qt.DisplayRole)

        for substring in text_filter.split(' '):
            if (substring not in model_data.casefold()):
                return False
        return True

    def lessThan(self, left, right):
        # get the data from the source model
        left_data = self.sourceModel().data(left)
        right_data = self.sourceModel().data(right)

        if left_data is None:
            return False
        if right_data is None:
            return True

        # find the index of the search string in each data
        text_filter = self.filterRegularExpression().pattern().casefold()

        left_index = left_data.find(text_filter)
        right_index = right_data.find(text_filter)

        # compare the indexes
        return left_index < right_index

class CustomQCompleter(QCompleter):
    def splitPath(self, path):
        self.model().invalidate() # Invalidates the current sorting and filtering.
        self.model().sort(0, Qt.AscendingOrder)
        return ""

    
class SelectAllLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super(SelectAllLineEdit, self).__init__(parent)
        self.readyToEdit = True

    def mousePressEvent(self, e):
        super(SelectAllLineEdit, self).mousePressEvent(e) # deselect on 2nd click
        if self.readyToEdit:
            self.selectAll()
            self.readyToEdit = False

    def focusOutEvent(self, e):
        super(SelectAllLineEdit, self).focusOutEvent(e) # remove cursor on focusOut
        self.deselect()
        self.readyToEdit = True


class SearchableComboBox(QComboBox):
    def __init__(self, parent: QWidget | None = None ) -> None:
        super().__init__(parent)

        self.setEditable(True)
        self.setLineEdit(SelectAllLineEdit())
        self.lineEdit().setEchoMode(QLineEdit.EchoMode.Normal)

        proxy_model = SubstringFilterProxyModel()
        proxy_model.setSourceModel(self.model())

        self.lineEdit().textChanged.connect(proxy_model.setFilterRegularExpression)
        self.lineEdit().editingFinished.connect(self.editing_finished)

        completer = CustomQCompleter()
        completer.setModel(proxy_model)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        completer.popup().setStyleSheet("QListView::item:hover {background-color: rgb(55,134,209);}")

        # Set the completer for the combo box
        self.setCompleter(completer)

        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.completer().popup().pressed.connect(self.popup_pressed)
    
    def popup_pressed(self):
        text = self.completer().currentCompletion()
        index = self.findText(text)
        # self.setCurrentIndex(index)
        # self.activated.emit(index)
        self.completer().popup().clicked.emit(index)
        self.clearFocus()
        self.lineEdit().clearFocus()
        self.lineEdit().setText(text)

    def editing_finished(self):
        text = self.completer().currentCompletion()
        index = self.findText(text)
        self.setCurrentIndex(index)
        self.clearFocus()
        self.activated.emit(index)
        self.completer().popup().clicked.emit(index)


class PlotWindow(QWidget):
    """
    This "window" is a QWidget. If it has no parent, it
    will appear as a free-floating window as we want.
    """
    def __init__(self):
        super().__init__()
        self.plot_text = None

        self.setLayout(QVBoxLayout())
        # self.label = QLabel("Another Window")
        # self.layout().addWidget(self.label)

        self.canvas = FigureCanvas(Figure())
        self.ax = self.canvas.figure.add_subplot(1, 1, 1)
        self.toolbar = NavigationToolbar(self.canvas, self)

        self.layout().addWidget(self.toolbar)
        self.layout().addWidget(self.canvas)



class DragDropTableWidget(QTableView):
    orderChanged = Signal()
    def __init__(self, parent=None):
        super(DragDropTableWidget, self).__init__(parent)

        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropOverwriteMode(False)
        self.setDropIndicatorShown(True)

        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.setDragDropMode(QAbstractItemView.InternalMove)

        hheader = self.horizontalHeader()
        hheader.setSectionResizeMode(QHeaderView.Stretch)

        vheader = self.verticalHeader()
        vheader.setSectionResizeMode(QHeaderView.Stretch)


    # def dropMimeData(self, data, action, row, col, parent):
    #     """
    #     Always move the entire row, and don't allow column "shifting"
    #     """
    #     response = super().dropMimeData(data, Qt.CopyAction, row, 0, parent)
    #     return response
    
    def dropEvent(self, event):
        super().dropEvent(event)
        QTimer.singleShot(0,self,self.afterDrop)
    
    def afterDrop(self):
        self.orderChanged.emit()
    
    def set_items(self, string_list):
        self.blockSignals(True)
        table_model = QStandardItemModel()
        for i, elem in enumerate(string_list):
            item = QStandardItem()
            item.setText(str(elem))
            item.setCheckable(True)
            item.setDropEnabled(False)
            item.setEditable(False)

            table_model.setItem(i, 0, item)

        table_model.setHorizontalHeaderLabels(["Elemental\nCombo & Order".upper()])
        self.setModel(table_model)
        self.blockSignals(False)

    def update_items(self, string_list):
        if len(string_list) != self.model().rowCount():
            raise Exception('String list given to DragDropTableWidget not of correct length!')
        
        self.blockSignals(True)
        for row in range(self.model().rowCount()):
            self.model().item(row, 0).setText(string_list[row])
        self.blockSignals(False)

class TableItemDescriptor(QWidget):
    def __init__(self, descriptor:str, value:str):
        super().__init__()
        self.label = QLabel(f"{descriptor}")
        self.label_val = QLabel(f"{value}")
        # self.line_edit = QLineEdit()
        # self.line_edit.setReadOnly(True)

        # self.label_val.setFrameShape(QFrame.Panel)
        # self.label_val.setFrameShadow(QFrame.Sunken)
        # self.label_val.setLineWidth(1)

        self.label_val.setFrameShape(QFrame.StyledPanel)

        
        self.layoutv = QHBoxLayout()
        self.layoutv.addWidget(self.label)
        # self.layoutv.addWidget(self.line_edit)
        self.layoutv.addWidget(self.label_val)
        self.layoutv.setContentsMargins(4, 0, 0, 0)
        self.setLayout(self.layoutv)

        self.list_widget_item = QListWidgetItem()
        self.list_widget_item.setSizeHint(self.sizeHint())
        self.list_widget_item.setFlags(self.list_widget_item.flags() & ~Qt.ItemIsSelectable)

class TableItemCategoryLabel(QWidget):
    def __init__(self, value:str):
        super().__init__()
        self.label = QLabel(f"{value}")
        self.label.setStyleSheet("font-weight: bold")

        self.layoutv = QHBoxLayout()
        self.layoutv.addWidget(self.label)
        self.layoutv.setContentsMargins(4, 0, 0, 0)
        self.setLayout(self.layoutv)

        self.list_widget_item = QListWidgetItem()
        self.list_widget_item.setSizeHint(self.sizeHint())
        self.list_widget_item.setFlags(self.list_widget_item.flags() & ~Qt.ItemIsSelectable)

class ClipSpinBox(QSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)

    def fixup(self, text):
        # Convert the text to an integer
        value = int(text)

        # If the value is larger than the maximum, set it to the maximum
        if value > self.maximum():
            value = self.maximum()
        # If the value is smaller than the minimum, set it to the minimum
        elif value < self.minimum():
            value = self.minimum()

        # Set the corrected value to the spin box
        self.setValue(value)
    
    def validate(self, input: str, pos: int) -> object:
        try:
            val = int(input, self.displayIntegerBase())
        except:
            return super().validate(input, pos)
        
        if val > self.minimum() and val < self.maximum():
            return QValidator.State.Acceptable
        if val < self.minimum():
            self.setValue(self.minimum())
        elif val > self.maximum():
            self.setValue(self.maximum())
        return QValidator.State.Acceptable
        
class SaveDialog(QDialog):
    def __init__(self, accept_method):
        super().__init__()
        self.setModal(True) # user has to select option before continuing
        self.setWindowTitle("Save as")
        self.radio1 = QRadioButton("Save weapon config")
        self.radio1.setChecked(True)
        self.radio2 = QRadioButton("Save enemy config")
        self.save_button = QPushButton("Save")
        self.cancel_button = QPushButton("Cancel")
        self.save_button.clicked.connect(self.ok_clicked)
        self.cancel_button.clicked.connect(self.cancel_clicked)
        self.radio_layout = QVBoxLayout()
        self.radio_layout.addWidget(self.radio1)
        self.radio_layout.addWidget(self.radio2)
        self.button_layout = QHBoxLayout()
        self.button_layout.addWidget(self.save_button)
        self.button_layout.addWidget(self.cancel_button)
        self.main_layout = QVBoxLayout()
        self.main_layout.addLayout(self.radio_layout)
        self.main_layout.addLayout(self.button_layout)
        self.setLayout(self.main_layout)
        self.accepted.connect(accept_method)

    def ok_clicked(self):
        # close the dialog
        self.accept()

    def cancel_clicked(self):
        # close the dialog
        self.reject()

class PrimerTableWidget(QTableWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setRowCount(16)
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(['Status', 'Count'])

        for row in range(self.rowCount()):
            key = list(cst.PROCINDEX_INFO.keys())[row]
            item = QTableWidgetItem()
            self.setItem(row, 1, item )
            cell_widget = CheckableSpinnerTableItem(cst.PROCINDEX_INFO[key])
            self.setCellWidget(row, 1, cell_widget)
            if key=='Heat':
                cell_widget.spinner.valueChanged.connect(self.heat_spinner_changed)

            item = QTableWidgetItem()
            item.setText(key)
            self.setItem(row, 0, item )
    
    def heat_spinner_changed(self, value):
        child_widget = self.parent().findChild(QWidget, "heat_settings_widget")
        if child_widget is None:
            print(f'Could not find child widget heat_settings_widget')
            return
        if value == 0:
            child_widget.hide()
        else:
            child_widget.show()


class CheckableSpinnerTableItem(QWidget):
    def __init__(self, proc_info):
        super().__init__()
        self.proc_info = proc_info
        self.spinner = QSpinBox()
        self.checkbox = QCheckBox()
        self.checkbox.setText('↑')
        self.spinner.setMaximum(proc_info["max_stacks"])

        self.layoutv = QHBoxLayout()
        self.layoutv.addWidget(self.spinner)
        self.layoutv.addWidget(self.checkbox)
        self.layoutv.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layoutv)

        # self.list_widget_item = QListWidgetItem()
        # self.list_widget_item.setSizeHint(self.sizeHint())
        # self.list_widget_item.setFlags(self.list_widget_item.flags() & ~Qt.ItemIsSelectable)

        self.checkbox.stateChanged.connect(self.check_state_change)

    def check_state_change(self, state):
        if state == Qt.CheckState.Unchecked.value:
            self.spinner.setValue(self.spinner.minimum())
        elif state == Qt.CheckState.Checked.value:
            self.spinner.setValue(self.spinner.maximum())


class ComboBoxDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Combo Box Dialog')
        self.setModal(True)
        
        # Create a QVBoxLayout instance for the dialog
        layout = QVBoxLayout(self)
        
        # Create a QComboBox and add some items
        self.comboBox = QComboBox(self)
        self.comboBox.addItems(['Option 1', 'Option 2', 'Option 3'])
        
        # Create a QPushButton to accept the selection
        select_button = QPushButton('Select', self)
        select_button.clicked.connect(self.accept_selection)
        
        # Add the combo box and button to the layout
        layout.addWidget(self.comboBox)
        layout.addWidget(select_button)
    
    def accept_selection(self):
        self.accept()