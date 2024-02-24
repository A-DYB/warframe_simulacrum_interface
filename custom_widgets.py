from PySide6.QtWidgets import QStyledItemDelegate,QHeaderView, QCheckBox, QTableWidgetItem, QTableWidget, QFrame, QListWidgetItem, QHBoxLayout, QLabel, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QApplication, QStyledItemDelegate, QLineEdit, QTableView, QAbstractItemView, QAbstractItemDelegate, QWidget, QStyle, QCompleter, QVBoxLayout
from PySide6.QtCore import QEvent, Qt, QModelIndex, QSortFilterProxyModel,QItemSelectionModel, Signal, QTimer
from PySide6.QtGui import QCursor, QStandardItemModel, QStandardItem, QDropEvent
import interface_constants as cst

from matplotlib.backends.backend_qtagg import FigureCanvas, NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import pandas as pd
import numpy as np

from matplotlib.offsetbox import (AnchoredOffsetbox, DrawingArea, HPacker,
                                  TextArea)

# Create a custom QTableView class that inherits from QTableView
class ModTableView(QTableView):
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
        self.local_completion_prefix = path
        # self.model().invalidateFilter()  # invalidate the current filtering - model should be set to a QSortFilterProxyModel. Need to call this otherwise it won't use the custom QSortFilterProxyModel
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

        completer = CustomQCompleter()
        proxy_model = SubstringFilterProxyModel()
        proxy_model.setSourceModel(self.model())
        completer.setModel(proxy_model)

        self.lineEdit().textChanged.connect(proxy_model.setFilterRegularExpression)
        self.lineEdit().editingFinished.connect(self.editing_finished)

        # Set the completer to use popup completion mode and a custom delay
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)

        # Set the completer for the combo box
        self.setCompleter(completer)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
    
    def editing_finished(self):
        text = self.completer().currentCompletion()
        index = self.findText(text)
        self.setCurrentIndex(index)
        self.clearFocus()
        self.activated.emit(index)

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
        self.layoutv.setContentsMargins(0, 0, 0, 0)
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
        self.layoutv.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layoutv)

        self.list_widget_item = QListWidgetItem()
        self.list_widget_item.setSizeHint(self.sizeHint())
        self.list_widget_item.setFlags(self.list_widget_item.flags() & ~Qt.ItemIsSelectable)

