from PySide6.QtWidgets import QStyledItemDelegate, QLineEdit, QSpinBox, QDoubleSpinBox, QApplication, QStyledItemDelegate, QLineEdit, QTableView, QAbstractItemView, QAbstractItemDelegate, QWidget, QStyle
from PySide6.QtCore import QEvent, Qt, QModelIndex, QSortFilterProxyModel,QItemSelectionModel
from PySide6.QtGui import QCursor, QStandardItem
import interface_constants as cst

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
