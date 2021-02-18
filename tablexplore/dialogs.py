#!/usr/bin/env python
"""
    Implements some dialog utilities for tableexplore
    Created Feb 2019
    Copyright (C) Damien Farrell

    This program is free software; you can redistribute it and/or
    modify it under the terms of the GNU General Public License
    as published by the Free Software Foundation; either version 3
    of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

from __future__ import absolute_import, division, print_function
import math, time
import os, types, io
import string, copy
from collections import OrderedDict
import pandas as pd

try:
    import configparser
except:
    import ConfigParser as configparser
from .qt import *
from . import util, core

module_path = os.path.dirname(os.path.abspath(__file__))
iconpath = os.path.join(module_path, 'icons')


def dialog_from_options(parent, opts, sections=None,
                        wrap=2, section_wrap=4,
                        style=None):
    """
    Get Qt widgets dialog from a dictionary of options.
    Args:
        opts: options dictionary
        sections:
        section_wrap: how many sections in one row
        style: stylesheet css if required
    """

    sizepolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    sizepolicy.setHorizontalStretch(0)
    sizepolicy.setVerticalStretch(0)

    if style is None:
        style = '''
        QLabel {
            font-size: 14px;
        }
        QPlainTextEdit {
            max-height: 80px;
        }
        '''

    if sections is None:
        sections = {'options': opts.keys()}

    widgets = {}
    dialog = QWidget(parent)
    dialog.setSizePolicy(sizepolicy)

    l = QGridLayout(dialog)
    l.setSpacing(1)
    l.setAlignment(QtCore.Qt.AlignLeft)
    scol = 1
    srow = 1
    for s in sections:
        row = srow
        col = 1
        f = QWidget()
        f.resize(50, 100)
        f.sizeHint()
        l.addWidget(f, row, scol)
        gl = QGridLayout(f)
        gl.setAlignment(QtCore.Qt.AlignTop)
        gl.setSpacing(5)
        for o in sections[s]:
            label = o
            val = None
            opt = opts[o]
            if 'label' in opt:
                label = opt['label']
            val = opt['default']
            t = opt['type']
            lbl = QLabel(label)
            gl.addWidget(lbl, row, col)
            lbl.setStyleSheet(style)
            if t == 'combobox':
                w = QComboBox()
                w.addItems(opt['items'])
                index = w.findText(val)
                if index != -1:
                    w.setCurrentIndex(index)
                if 'editable' in opt:
                    w.setEditable(True)
                if 'width' in opt:
                    w.setMinimumWidth(opt['width'])
                    w.resize(opt['width'], 20)
            elif t == 'list':
                w = QListWidget()
                w.setSelectionMode(QAbstractItemView.MultiSelection)
                w.addItems(opt['items'])
            elif t == 'entry':
                w = QLineEdit()
                w.setText(str(val))
            elif t == 'textarea':
                w = QPlainTextEdit()
                # w.setSizePolicy(sizepolicy)
                w.insertPlainText(str(val))
            elif t == 'slider':
                w = QSlider(QtCore.Qt.Horizontal)
                s, e = opt['range']
                w.setTickInterval(opt['interval'])
                w.setSingleStep(opt['interval'])
                w.setMinimum(s)
                w.setMaximum(e)
                w.setTickPosition(QSlider.TicksBelow)
                w.setValue(val)
            elif t == 'spinbox':
                if type(val) is float:
                    w = QDoubleSpinBox()
                else:
                    w = QSpinBox()
                w.setValue(val)
                if 'range' in opt:
                    min, max = opt['range']
                    w.setRange(min, max)
                    w.setMinimum(min)
                if 'interval' in opt:
                    w.setSingleStep(opt['interval'])
            elif t == 'checkbox':
                w = QCheckBox()
                w.setChecked(val)
            elif t == 'font':
                w = QFontComboBox()
                index = w.findText(val)
                # w.resize(w.sizeHint())
                w.setCurrentIndex(index)
            col += 1
            gl.addWidget(w, row, col)
            w.setStyleSheet(style)
            widgets[o] = w
            # print (o, row, col)
            if col >= wrap:
                col = 1
                row += 1
            else:
                col += 2

        if scol >= section_wrap:
            scol = 1
            srow += 2
        else:
            scol += 1
    return dialog, widgets


def get_widget_values(widgets):
    """Get values back from a set of widgets"""

    kwds = {}
    for i in widgets:
        val = None
        if i in widgets:
            w = widgets[i]
            if type(w) is QLineEdit:
                val = w.text()
            elif type(w) is QPlainTextEdit:
                val = w.toPlainText()
            elif type(w) is QComboBox or type(w) is QFontComboBox:
                val = w.currentText()
            elif type(w) is QListWidget:
                val = [i.text() for i in w.selectedItems()]
            elif type(w) is QCheckBox:
                val = w.isChecked()
            elif type(w) is QSlider:
                val = w.value()
            elif type(w) in [QSpinBox, QDoubleSpinBox]:
                val = w.value()
            if val != None:
                kwds[i] = val
    kwds = kwds
    return kwds


def setWidgetValues(widgets, values):
    """Set values for a set of widgets from a dict"""

    kwds = {}
    for i in values:
        val = values[i]
        if i in widgets:
            # print (i, val, type(val))
            w = widgets[i]
            if type(w) is QLineEdit:
                w.setText(str(val))
            elif type(w) is QPlainTextEdit:
                w.insertPlainText(str(val))
            elif type(w) is QComboBox or type(w) is QFontComboBox:
                index = w.findText(val)
                w.setCurrentIndex(index)
            elif type(w) is QCheckBox:
                w.setChecked(val)
            elif type(w) is QSlider:
                w.setValue(val)
            elif type(w) in [QSpinBox, QDoubleSpinBox]:
                w.setValue(val)
    return


def addToolBarItems(toolbar, parent, items):
    """Populate toolbar from dict of items"""

    for i in items:
        if 'file' in items[i]:
            iconfile = os.path.join(iconpath, items[i]['file'] + '.png')
            icon = QIcon(iconfile)
        else:
            icon = QIcon.fromTheme(items[i]['icon'])
        btn = QAction(icon, i, parent)
        btn.triggered.connect(items[i]['action'])
        if 'shortcut' in items[i]:
            btn.setShortcut(QKeySequence(items[i]['shortcut']))
        # btn.setCheckable(True)
        toolbar.addAction(btn)
    return toolbar


class PlainTextEditor(QPlainTextEdit):
    def __init__(self, parent=None, **kwargs):
        super(PlainTextEditor, self).__init__(parent, **kwargs)
        font = QFont("Monospace")
        font.setPointSize(10)
        font.setStyleHint(QFont.TypeWriter)
        self.setFont(font)
        return

    def zoom(self, delta):
        if delta < 0:
            self.zoomOut(1)
        elif delta > 0:
            self.zoomIn(1)

    def contextMenuEvent(self, event):

        menu = QMenu(self)
        copyAction = menu.addAction("Copy")
        clearAction = menu.addAction("Clear")
        zoominAction = menu.addAction("Zoom In")
        zoomoutAction = menu.addAction("Zoom Out")
        action = menu.exec_(self.mapToGlobal(event.pos()))
        if action == copyAction:
            self.copy()
        elif action == clearAction:
            self.clear()
        elif action == zoominAction:
            self.zoom(1)
        elif action == zoomoutAction:
            self.zoom(-1)


class TextDialog(QDialog):
    """Text edit dialog"""

    def __init__(self, parent, text='', title='Text', width=400, height=300):
        super(TextDialog, self).__init__(parent)
        self.resize(width, height)
        self.setWindowTitle(title)
        vbox = QVBoxLayout(self)
        b = self.textbox = PlainTextEditor(self)
        b.insertPlainText(text)
        b.move(10, 10)
        b.resize(400, 300)
        vbox.addWidget(self.textbox)
        # self.b.setFontFamily('fixed')
        buttonbox = QDialogButtonBox(self)
        buttonbox.setStandardButtons(QDialogButtonBox.Ok)
        buttonbox.button(QDialogButtonBox.Ok).clicked.connect(self.close)
        vbox.addWidget(buttonbox)
        self.show()
        return


class SearchDialog(QDialog):
    """Search dialog"""

    def __init__(self, parent, sheets):
        super(SearchDialog, self).__init__(parent)
        self.sheets = sheets
        self.resize(1000, 500)
        self.setWindowTitle("Search")
        layout = QVBoxLayout(self)

        # Create text editor widget
        tw = QWidget(parent)
        tw_hbox = QHBoxLayout(tw)
        self.searchbox = PlainTextEditor(self)
        tw_hbox.addWidget(self.searchbox, stretch=1)
        self.resultbox = PlainTextEditor(self)
        tw_hbox.addWidget(self.resultbox, stretch=3)
        layout.addWidget(tw)

        # Create button widget
        bw = QWidget(parent)
        bw_hbox = QHBoxLayout(bw)
        button = QPushButton("Search")
        button.clicked.connect(self.search)
        bw_hbox.addWidget(button)
        button = QPushButton("Close")
        button.clicked.connect(self.close)
        bw_hbox.addWidget(button)
        layout.addWidget(bw)

        self.show()
        return

    def search(self):
        searchbox_val = self.searchbox.toPlainText()
        keywords = searchbox_val.splitlines()
        if type(self.sheets) is not OrderedDict:
            df = self.sheets.dataframe
            result = df[df.stack().str.contains("|".join(keywords)).any(level=0)]
            self.resultbox.setPlainText(result.to_string())
        else:
            self.resultbox.clear()
            names = list(self.sheets.keys())
            for name in names:
                df = self.sheets[name].dataframe
                if df is not None:
                    result = df[df.stack().str.contains("|".join(keywords)).any(level=0)]
                    self.resultbox.insertPlainText(f"# {name}:\n")
                    if result.empty:
                        self.resultbox.insertPlainText("Not found!")
                    else:
                        self.resultbox.insertPlainText(result.to_string())
                    self.resultbox.insertPlainText("\n\n")
        return


class MultipleInputDialog(QDialog):
    """Qdialog with multiple inputs"""

    def __init__(self, parent, options=None, title='Input', width=400, height=200):
        super(MultipleInputDialog, self).__init__(parent)
        self.values = None
        self.accepted = False
        self.setMinimumSize(width, height)
        self.setWindowTitle(title)
        dialog, self.widgets = dialog_from_options(self, options)
        vbox = QVBoxLayout(self)
        vbox.addWidget(dialog)
        buttonbox = QDialogButtonBox(self)
        buttonbox.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        buttonbox.button(QDialogButtonBox.Ok).clicked.connect(self.accept)
        buttonbox.button(QDialogButtonBox.Cancel).clicked.connect(self.close)
        vbox.addWidget(buttonbox)
        self.show()
        return self.values

    def accept(self):
        self.values = get_widget_values(self.widgets)
        self.accepted = True
        self.close()
        return


class ImportDialog(QDialog):
    """Provides a dialog for import settings"""

    def __init__(self, parent=None, filename=None):

        super(ImportDialog, self).__init__(parent)
        self.parent = parent
        self.filename = filename
        self.df = None
        self.cancel = False  # Indicate whether cancel the dialog
        self.setGeometry(QtCore.QRect(250, 250, 900, 600))
        self.setGeometry(
            QStyle.alignedRect(
                QtCore.Qt.LeftToRight,
                QtCore.Qt.AlignCenter,
                self.size(),
                QGuiApplication.primaryScreen().availableGeometry(),
            ))
        self.setWindowTitle('Import File')
        self.create_widgets()
        self.update()
        self.show()
        return

    def create_widgets(self):
        """Create widgets"""

        delimiters = [',', r'\t', ' ', '\s+', ';', '/', '&', '|', '^', '+', '-']
        encodings = ['utf-8', 'ascii', 'latin-1', 'iso8859_15', 'cp037', 'cp1252', 'big5', 'euc_jp']
        timeformats = ['infer', '%d/%m/%Y', '%Y/%m/%d', '%Y/%d/%m',
                       '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M',
                       '%d-%m-%Y %H:%M:%S', '%d-%m-%Y %H:%M']
        grps = {
            'formats': ['sep', 'decimal', 'comment'],
            'data': ['skiprows', 'skipinitialspace',
                     'skip_blank_lines', 'parse_dates', 'encoding', 'time format'],
            'other': ['rowsperfile']
        }
        grps = OrderedDict(sorted(grps.items()))
        opts = self.opts = \
            {'sep': {'type': 'combobox',
                     'default': ',',
                     'editable': True,
                     'items': delimiters,
                     'tooltip': 'seperator'},
             # 'header': {
             #     'type': 'entry',
             #     'default': 0,
             #     'label': 'header',
             #     'tooltip': 'position of column header'},
             'index_col': {'type': 'spinbox',
                           'default': -1,
                           'range': (-1, 1000),
                           'label': 'index column',
                           'tooltip': ''},
             'decimal': {'type': 'combobox',
                         'default': '.',
                         'items': ['.', ','],
                         'tooltip': 'decimal point symbol'},
             'comment': {'type': 'entry',
                         'default': '#',
                         'label': 'comment',
                         'tooltip': 'comment symbol'},
             'skipinitialspace': {'type': 'checkbox',
                                  'default': 0,
                                  'label': 'skip initial space',
                                  'tooltip': 'skip initial space'},
             'skiprows': {'type': 'spinbox',
                          'default': 0,
                          'label': 'skiprows',
                          'tooltip': 'rows to skip'},
             'skip_blank_lines': {'type': 'checkbox',
                                  'default': 0,
                                  'label': 'skip blank lines',
                                  'tooltip': 'do not use blank lines'},
             'parse_dates': {'type': 'checkbox',
                             'default': 1,
                             'label': 'parse dates',
                             'tooltip': 'try to parse date/time columns'},
             'time format': {'type': 'combobox',
                             'default': '',
                             'items': timeformats,
                             'tooltip': 'date/time format'},
             'encoding': {'type': 'combobox',
                          'default': 'utf-8',
                          'items': encodings,
                          'tooltip': 'file encoding'},
             # 'prefix': {'type': 'entry',
             #            'default': None,
             #            'label': 'prefix',
             #            'tooltip':''},
             'rowsperfile': {'type': 'spinbox',
                             'default': 0,
                             'label': 'rows per file',
                             'tooltip': 'rows to read'},
             # 'names': {'type': 'entry',
             #           'default': '',
             #           'label': 'column names',
             #           'tooltip': 'col labels'},
             }

        optsframe, self.widgets = dialog_from_options(self, opts, grps, wrap=1, section_wrap=1)
        layout = QGridLayout()
        layout.setColumnStretch(1, 2)
        layout.addWidget(optsframe, 1, 1)
        optsframe.setMaximumWidth(300)
        bf = self.create_buttons(optsframe)
        layout.addWidget(bf, 2, 1)

        main = QSplitter(self)
        main.setOrientation(QtCore.Qt.Vertical)
        layout.addWidget(main, 1, 2, 2, 1)

        self.textarea = PlainTextEditor(main)
        main.addWidget(self.textarea)
        self.textarea.resize(200, 200)

        t = self.previewtable = core.DataFrameTable(main, font=core.FONT)
        main.addWidget(t)
        self.setLayout(layout)
        return

    def create_buttons(self, parent):

        bw = self.button_widget = QWidget(parent)
        vbox = QVBoxLayout(bw)
        button = QPushButton("Update")
        button.clicked.connect(self.update)
        vbox.addWidget(button)
        button = QPushButton("Import")
        button.clicked.connect(self.do_import)
        vbox.addWidget(button)
        button = QPushButton("Cancel")
        button.clicked.connect(self.quit)
        vbox.addWidget(button)
        return bw

    def show_text(self):
        """Show text contents"""

        with open(self.filename, 'r') as stream:
            try:
                text = stream.read()
            except:
                text = 'failed to preview, check encoding and then update preview\n'
        self.textarea.clear()
        self.textarea.insertPlainText(text)
        self.textarea.verticalScrollBar().setValue(1)
        return

    def update(self):
        """Reload previews"""

        self.show_text()
        self.values = get_widget_values(self.widgets)
        timeformat = self.values['time format']
        if timeformat == 'infer':
            dateparse = None
        else:
            dateparse = lambda x: pd.datetime.strptime(x, timeformat)
        del self.values['time format']
        del self.values['rowsperfile']
        for k in self.values:
            if self.values[k] == '':
                self.values[k] = None
        # if self.values['index_col'] == -1:
        #    self.values['index_col'] = None

        try:
            f = pd.read_csv(self.filename, chunksize=400, error_bad_lines=False,
                            warn_bad_lines=False, date_parser=dateparse, **self.values)
        except Exception as e:
            print('read csv error')
            print(e)
            return
        try:
            df = f.get_chunk()
        except UnicodeDecodeError:
            print('unicode error')
            df = pd.DataFrame()
        except pd.errors.ParserError:
            print('parser error')
            df = pd.DataFrame()

        self.previewtable.model.df = df
        self.previewtable.refresh()
        return

    def do_import(self):
        """Do the import"""

        self.update()
        self.df = pd.read_csv(self.filename, **self.values)
        self.close()
        return

    def quit(self):
        self.cancel = True
        self.close()
        return


class BasicDialog(QDialog):
    """Qdialog for table operations interfaces"""

    def __init__(self, parent, df, title=None):

        super(BasicDialog, self).__init__(parent)
        self.parent = parent
        self.df = df
        self.app = self.parent.app
        self.setWindowTitle(title)
        self.createWidgets()
        self.setGeometry(QtCore.QRect(400, 300, 1000, 600))
        self.show()
        return

    def createWidgets(self):
        """Create widgets - override this"""

        cols = list(self.df.columns)

    def createButtons(self, parent):

        bw = self.button_widget = QWidget(parent)
        vbox = QVBoxLayout(bw)
        vbox.setAlignment(QtCore.Qt.AlignTop)
        button = QPushButton("Apply")
        button.clicked.connect(self.apply)
        vbox.addWidget(button)
        button = QPushButton("Copy to sub-table")
        button.clicked.connect(self.copy_to_subtable)
        vbox.addWidget(button)
        button = QPushButton("Copy to clipboard")
        button.clicked.connect(self.copy_to_clipboard)
        vbox.addWidget(button)
        button = QPushButton("Copy to new sheet")
        button.clicked.connect(self.copy_to_sheet)
        vbox.addWidget(button)
        button = QPushButton("Export result")
        button.clicked.connect(self.export)
        vbox.addWidget(button)
        button = QPushButton("Close")
        button.clicked.connect(self.close)
        vbox.addWidget(button)
        return bw

    def apply(self):
        """Override this"""
        return

    def copy_to_subtable(self):
        """Do the operation"""

        df = self.table.model.df
        self.parent.showSubTable(df)
        return

    def copy_to_sheet(self):
        """Copy result to new sheet in app, if available"""

        if self.app == None:
            return
        name, ok = QInputDialog().getText(self, "Enter Sheet Name",
                                          "Name:", QLineEdit.Normal)
        if ok and name:
            self.app.add_sheet(name=name, df=self.table.model.df)
        return

    def copy_to_clipboard(self):
        """Copy result to clipboard"""

        df = self.table.model.df
        df.to_clipboard()
        return

    def export(self):
        """export result to file"""

        df = self.table.model.df
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getSaveFileName(self, "Export File",
                                                  "", "CSV files (*.csv);;",
                                                  options=options)
        if not filename:
            return
        if not os.path.splitext(filename)[1] == '.csv':
            filename += '.csv'
        df.to_csv(filename)
        return

    def close(self):
        self.destroy()
        return


class AggregateDialog(BasicDialog):
    """Qdialog with multiple inputs"""

    def __init__(self, parent, df, title='Groupby-Aggregate'):

        BasicDialog.__init__(self, parent, df, title)
        return

    def createWidgets(self):
        """Create widgets"""

        cols = list(self.df.columns)
        funcs = ['sum', 'mean', 'size', 'std', 'min', 'max', 'var']
        vbox = QHBoxLayout(self)
        main = QWidget(self)
        main.setMaximumWidth(300)
        vbox.addWidget(main)

        l = QVBoxLayout(main)
        w = self.groupbyw = QListWidget(main)
        w.setSelectionMode(QAbstractItemView.MultiSelection)
        w.addItems(cols)
        l.addWidget(QLabel('Group by'))
        l.addWidget(w)
        w = self.aggw = QListWidget(main)
        w.setSelectionMode(QAbstractItemView.MultiSelection)
        w.addItems(cols)
        l.addWidget(QLabel('Aggregate on'))
        l.addWidget(w)
        w = self.funcw = QListWidget(main)
        w.setSelectionMode(QAbstractItemView.MultiSelection)
        w.addItems(funcs)
        l.addWidget(QLabel('Functions'))
        l.addWidget(w)

        self.table = core.DataFrameTable(self, font=core.FONT)
        vbox.addWidget(self.table)
        bf = self.createButtons(self)
        vbox.addWidget(bf)
        return

    def customButtons():
        vbox.addWidget(QLabel('map cols to functions'))
        mapcolsbtn = QCheckBox()
        vbox.addWidget(mapcolsbtn)

    def apply(self):
        """Do the operation"""

        grpcols = [i.text() for i in self.groupbyw.selectedItems()]
        aggcols = [i.text() for i in self.aggw.selectedItems()]
        funcs = [i.text() for i in self.funcw.selectedItems()]
        aggdict = {}

        if len(funcs) == 1: funcs = funcs[0]
        for a in aggcols:
            aggdict[a] = funcs

        res = self.df.groupby(grpcols).agg(aggdict).reset_index()
        self.table.model.df = res
        self.table.refresh()
        return


class PivotDialog(BasicDialog):
    """Dialog to pivot table"""

    def __init__(self, parent, df, title='Pivot'):
        BasicDialog.__init__(self, parent, df, title)
        return

    def createWidgets(self):
        """Create widgets"""

        cols = list(self.df.columns)
        funcs = ['sum', 'mean', 'size', 'std', 'min', 'max', 'var']
        vbox = QHBoxLayout(self)
        main = QWidget(self)
        main.setMaximumWidth(300)
        vbox.addWidget(main)

        l = QVBoxLayout(main)
        w = self.columnsw = QListWidget(main)
        w.setSelectionMode(QAbstractItemView.MultiSelection)
        w.addItems(cols)
        l.addWidget(QLabel('Columns'))
        l.addWidget(w)
        w = self.idxw = QListWidget(main)
        w.setSelectionMode(QAbstractItemView.MultiSelection)
        w.addItems(cols)
        l.addWidget(QLabel('Index'))
        l.addWidget(w)
        w = self.valuesw = QListWidget(main)
        w.setSelectionMode(QAbstractItemView.MultiSelection)
        w.addItems(cols)
        l.addWidget(QLabel('Values'))
        l.addWidget(w)
        w = self.aggw = QListWidget(main)
        w.addItems(funcs)
        l.addWidget(QLabel('Aggregate function'))
        l.addWidget(w)

        self.table = core.DataFrameTable(self, font=core.FONT)
        vbox.addWidget(self.table)
        bf = self.createButtons(self)
        vbox.addWidget(bf)

    def apply(self):
        """Do the operation"""

        cols = [i.text() for i in self.columnsw.selectedItems()]
        vals = [i.text() for i in self.valuesw.selectedItems()]
        idx = [i.text() for i in self.idxw.selectedItems()]
        aggfuncs = [i.text() for i in self.aggw.selectedItems()]
        res = pd.pivot_table(self.df, index=idx, columns=cols, values=vals, aggfunc=aggfuncs)
        names = res.index.names
        res = res.reset_index(col_level=2)
        # print (res)
        if util.check_multiindex(res.columns) == 1:
            res.columns = res.columns.get_level_values(2)

        self.table.model.df = res
        self.table.refresh()
        return


class MeltDialog(BasicDialog):
    """Dialog to melt table"""

    def __init__(self, parent, df, title='Melt'):
        BasicDialog.__init__(self, parent, df, title)
        return

    def createWidgets(self):
        """Create widgets"""

        cols = list(self.df.columns)
        funcs = ['sum', 'mean', 'size', 'std', 'min', 'max', 'var']
        vbox = QHBoxLayout(self)
        main = QWidget(self)
        main.setMaximumWidth(300)
        vbox.addWidget(main)

        l = QVBoxLayout(main)
        w = self.idvarsw = QListWidget(main)
        w.setSelectionMode(QAbstractItemView.MultiSelection)
        w.addItems(cols)
        l.addWidget(QLabel('ID vars'))
        l.addWidget(w)
        w = self.valuevarsw = QListWidget(main)
        w.setSelectionMode(QAbstractItemView.MultiSelection)
        w.addItems(cols)
        l.addWidget(QLabel('Value vars'))
        l.addWidget(w)
        w = self.varnamew = QLineEdit('var')
        l.addWidget(QLabel('Var name'))
        l.addWidget(w)

        self.table = core.DataFrameTable(self, font=core.FONT)
        vbox.addWidget(self.table)
        bf = self.createButtons(self)
        vbox.addWidget(bf)
        return

    def apply(self):
        """Do the operation"""

        idvars = [i.text() for i in self.idvarsw.selectedItems()]
        value_vars = [i.text() for i in self.valuevarsw.selectedItems()]
        varname = self.varnamew.text()
        res = pd.melt(self.df, idvars, value_vars, varname)

        self.table.model.df = res
        self.table.refresh()
        return


class MergeDialog(BasicDialog):
    """Dialog to melt table"""

    def __init__(self, parent, df, title='Merge Tables'):

        BasicDialog.__init__(self, parent, df, title)
        return

    def createWidgets(self):
        """Create widgets"""

        if hasattr(self.parent, 'subtable') and self.parent.subtable != None:
            self.df2 = self.parent.subtable.table.model.df
            cols2 = self.df2.columns
        else:
            self.df2 = None
            cols2 = []
        cols = list(self.df.columns)
        ops = ['merge', 'concat']
        how = ['inner', 'outer', 'left', 'right']
        hbox = QHBoxLayout(self)
        main = QWidget(self)
        main.setMaximumWidth(300)
        hbox.addWidget(main)

        l = QVBoxLayout(main)
        w = self.ops_w = QComboBox(main)
        w.addItems(ops)
        l.addWidget(QLabel('Operation'))
        l.addWidget(w)
        w = self.lefton_w = QListWidget(main)
        w.setSelectionMode(QAbstractItemView.MultiSelection)
        w.addItems(cols)
        l.addWidget(QLabel('Left on'))
        l.addWidget(w)
        w = self.righton_w = QListWidget(main)
        w.setSelectionMode(QAbstractItemView.MultiSelection)
        w.addItems(cols2)
        l.addWidget(QLabel('Right on'))
        l.addWidget(w)

        w = self.leftindex_w = QCheckBox(main)
        w.setChecked(False)
        l.addWidget(QLabel('Use left index'))
        l.addWidget(w)
        w = self.rightindex_w = QCheckBox(main)
        w.setChecked(False)
        l.addWidget(QLabel('Use right index'))
        l.addWidget(w)

        w = self.how_w = QComboBox(main)
        w.addItems(how)
        l.addWidget(QLabel('How'))
        l.addWidget(w)

        w = self.left_suffw = QLineEdit('_1')
        l.addWidget(QLabel('Left suffix'))
        l.addWidget(w)
        w = self.right_suffw = QLineEdit('_2')
        l.addWidget(QLabel('Right suffix'))
        l.addWidget(w)

        self.table = core.DataFrameTable(self, font=core.FONT)
        hbox.addWidget(self.table)
        bf = self.createButtons(self)
        hbox.addWidget(bf)
        return

    def updateColumns(self):

        # self.df2 =
        cols2 = self.df2.columns
        # w = self.righton_w
        # w.clear()
        # w.addItems(cols2)
        return

    def apply(self):
        """Do the operation"""

        left_index = self.leftindex_w.isChecked()
        right_index = self.rightindex_w.isChecked()
        if left_index == True:
            lefton = None
        else:
            lefton = [i.text() for i in self.lefton_w.selectedItems()]
        if right_index == True:
            righton = None
        else:
            righton = [i.text() for i in self.righton_w.selectedItems()]
        how = self.how_w.currentText()
        op = self.ops_w.currentText()
        if op == 'merge':
            res = pd.merge(self.df, self.df2,
                           left_on=lefton,
                           right_on=righton,
                           left_index=left_index,
                           right_index=right_index,
                           how=how,
                           suffixes=(self.left_suffw.text(), self.right_suffw.text())
                           )
        else:
            res = pd.concat([self.df, self.df2])
        self.table.model.df = res
        self.table.refresh()
        return


class ConvertTypesDialog(BasicDialog):
    """Dialog to melt table"""

    def __init__(self, parent, df, title='Convert types'):
        BasicDialog.__init__(self, parent, df, title)
        return

    def createButtons(self, parent):
        bw = self.button_widget = QWidget(parent)
        vbox = QVBoxLayout(bw)
        vbox.setAlignment(QtCore.Qt.AlignTop)
        button = QPushButton("Apply")
        button.clicked.connect(self.apply)
        vbox.addWidget(button)
        button = QPushButton("Copy to new sheet")
        button.clicked.connect(self.copy_to_sheet)
        vbox.addWidget(button)
        button = QPushButton("Close")
        button.clicked.connect(self.close)
        vbox.addWidget(button)
        return bw

    def createWidgets(self):
        """Create widgets"""

        cols = list(self.df.columns)

        vbox = QHBoxLayout(self)
        main = QWidget(self)
        main.setMaximumWidth(300)
        vbox.addWidget(main)

        res = []
        for col in self.df.columns:
            res.append([col, str(self.df[col].dtype), ''])
        cols = ['name', 'type', 'convert']
        info = pd.DataFrame(res, columns=cols)

        self.table = core.DataFrameTable(self, info, font=core.FONT)
        types = ['int', 'float', 'categorical']

        vbox.addWidget(self.table)
        bf = self.createButtons(self)
        vbox.addWidget(bf)
        return

    def apply(self):
        """Do the operation"""

        idvars = [i.text() for i in self.idvarsw.selectedItems()]
        value_vars = [i.text() for i in self.valuevarsw.selectedItems()]
        varname = self.varnamew.text()
        res = pd.melt(self.df, idvars, value_vars, varname)

        self.table.model.df = res
        self.table.refresh()
        return


class PreferencesDialog(QDialog):
    """Preferences dialog from config parser options"""

    def __init__(self, parent, options={}):
        super(PreferencesDialog, self).__init__(parent)
        self.parent = parent
        self.setWindowTitle('Preferences')
        self.resize(700, 200)
        self.setGeometry(QtCore.QRect(300, 300, 600, 200))
        self.setMaximumWidth(600)
        self.setMaximumHeight(300)
        self.createWidgets(options)
        self.show()
        return

    def createWidgets(self, options):
        """create widgets"""

        import pylab as plt
        colormaps = sorted(m for m in plt.cm.datad if not m.endswith("_r"))
        timeformats = ['%m/%d/%Y', '%d/%m/%Y', '%d/%m/%y',
                       '%Y/%m/%d', '%y/%m/%d', '%Y/%d/%m',
                       '%d-%b-%Y', '%b-%d-%Y',
                       '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M',
                       '%d-%m-%Y %H:%M:%S', '%d-%m-%Y %H:%M']
        self.opts = {'rowheight': {'type': 'spinbox', 'default': 15, 'range': (5, 50), 'label': 'row height'},
                     'columnwidth': {'type': 'spinbox', 'range': (10, 300),
                                     'default': options['columnwidth'], 'label': 'column width'},
                     'alignment': {'type': 'combobox', 'default': 'w', 'items': ['left', 'right', 'center'],
                                   'label': 'text align'},
                     'font': {'type': 'font', 'default': 'Arial', 'default': options['font']},
                     'fontsize': {'type': 'slider', 'default': options['fontsize'], 'range': (5, 40),
                                  'interval': 1, 'label': 'font size'},
                     'timeformat': {'type': 'combobox', 'default': options['timeformat'],
                                    'items': timeformats, 'label': 'Date/Time format'}
                     # 'floatprecision':{'type':'spinbox','default':2, 'label':'precision'},
                     }
        sections = {'table': ['alignment', 'rowheight', 'columnwidth'],
                    'formats': ['font', 'fontsize', 'timeformat']}

        dialog, self.widgets = dialog_from_options(self, self.opts, sections)

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(dialog)
        dialog.setFocus()
        bw = self.createButtons(self)
        self.layout.addWidget(bw)
        return

    def createButtons(self, parent):
        bw = self.button_widget = QWidget(parent)
        vbox = QHBoxLayout(bw)
        button = QPushButton("Apply")
        button.clicked.connect(self.apply)
        vbox.addWidget(button)
        button = QPushButton("Close")
        button.clicked.connect(self.close)
        vbox.addWidget(button)
        return bw

    def apply(self):
        """Apply options to current table"""

        kwds = get_widget_values(self.widgets)
        from . import core
        core.FONT = kwds['font']
        core.FONTSIZE = kwds['fontsize']
        core.COLUMNWIDTH = kwds['columnwidth']
        core.TIMEFORMAT = kwds['timeformat']
        self.parent.refresh()
        return


class FilterDialog(QWidget):
    """Qdialog for table query/filtering"""

    def __init__(self, parent, table, title=None):

        super(FilterDialog, self).__init__(parent)
        self.parent = parent
        # self.app = self.parent.app
        self.table = table
        self.setWindowTitle(title)
        self.resize(400, 200)
        self.createWidgets()
        self.filters = []
        # self.setMinimumHeight(200)
        # self.show()
        return

    def createToolBar(self, parent):

        items = {'Apply': {'action': self.apply, 'file': 'filter'},
                 'Add': {'action': self.addFilter, 'file': 'add'},
                 'Refresh': {'action': self.refresh, 'file': 'table-refresh'},
                 'Subtract': {'action': self.removeFiltered, 'file': 'table-remove'}
                 }
        toolbar = QToolBar("Toolbar")
        toolbar.setOrientation(QtCore.Qt.Horizontal)
        addToolBarItems(toolbar, self, items)
        # vbox.addWidget(toolbar)
        return toolbar

    def createWidgets(self):
        """Create widgets"""

        df = self.table.model.df
        cols = list(df.columns)
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)
        self.query_w = QLineEdit()
        self.layout.addWidget(QLabel('String filter'))
        self.layout.addWidget(self.query_w)
        self.query_w.returnPressed.connect(self.apply)
        w = self.column_w = QListWidget()
        w.setSelectionMode(QAbstractItemView.MultiSelection)
        # w.setFixedHeight(60)
        w.addItems(cols)
        self.layout.addWidget(QLabel('Filter Columns'))
        self.layout.addWidget(self.column_w)
        tb = self.createToolBar(self)
        self.layout.addWidget(tb)
        self.adjustSize()
        return

    def refresh(self):
        """Reset the table"""

        table = self.table
        if table.filtered == True and hasattr(table, 'dataframe'):
            table.model.df = table.dataframe
            table.filtered = False
            table.refresh()
        return

    def update(self):
        """Update the column widgets if table has changed"""

        df = self.table.model.df
        cols = list(df.columns)
        self.column_w.clear()
        self.column_w.addItems(cols)
        return

    def addFilter(self):
        """Add a filter using widgets"""

        df = self.table.model.df
        fb = FilterBar(self, self.table)
        self.layout.insertWidget(4, fb)
        self.filters.append(fb)
        return

    def apply(self):
        """Apply filters"""

        table = self.table
        if table.filtered == True and hasattr(table, 'dataframe'):
            table.model.df = table.dataframe
        df = table.model.df
        mask = None

        s = self.query_w.text()
        cols = [i.text() for i in self.column_w.selectedItems()]
        if len(cols) > 0:
            df = df[cols]
        if s != '':
            try:
                mask = df.eval(s)
            except:
                mask = df.eval(s, engine='python')

        # add widget based filters
        if len(self.filters) > 0:
            mask = self.applyWidgetFilters(df, mask)
        # apply mask
        if mask is not None:
            df = df[mask]
        self.filtdf = df
        table.dataframe = table.model.df.copy()
        table.filtered = True
        table.model.df = df
        table.model.layoutChanged.emit()
        table.refresh()

        return

    def applyWidgetFilters(self, df, mask=None):
        """Apply the widget based filters, returns a boolean mask"""

        if mask is None:
            mask = df.index == df.index

        for f in self.filters:
            col, val, op, b = f.getFilter()
            try:
                val = float(val)
            except:
                pass
            print(col, val, op, b)
            if op == 'contains':
                m = df[col].str.contains(str(val))
            elif op == 'equals':
                m = df[col] == val
            elif op == 'not equals':
                m = df[col] != val
            elif op == '>':
                m = df[col] > val
            elif op == '<':
                m = df[col] < val
            elif op == 'is empty':
                m = df[col].isnull()
            elif op == 'not empty':
                m = ~df[col].isnull()
            elif op == 'excludes':
                m = -df[col].str.contains(val)
            elif op == 'starts with':
                m = df[col].str.startswith(val)
            elif op == 'has length':
                m = df[col].str.len() > val
            elif op == 'is number':
                m = df[col].astype('object').str.isnumeric()
            elif op == 'is lowercase':
                m = df[col].astype('object').str.islower()
            elif op == 'is uppercase':
                m = df[col].astype('object').str.isupper()
            else:
                continue
            if b == 'AND':
                mask = mask & m
            elif b == 'OR':
                mask = mask | m
            elif b == 'NOT':
                mask = mask ^ m
        return mask

    def removeFiltered(self):
        """Subtract current filtered result from original table"""

        reply = QMessageBox.question(self, 'Perform Action?',
                                     'This will overwrite the current table. Are you sure?',
                                     QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.No:
            return
        table = self.table
        if table.filtered == False:
            return
        idx = list(self.filtdf.index)
        df = table.dataframe
        table.dataframe = None
        table.filtered = False
        table.model.df = df.loc[~df.index.isin(idx)]
        table.model.layoutChanged.emit()
        table.refresh()
        return

    def onClose(self):

        self.table.showAll()
        self.close()


class FilterBar(QWidget):
    """Single Widget based filter"""

    def __init__(self, parent, table):
        super(FilterBar, self).__init__(parent)
        self.parent = parent
        # self.app = self.parent.app
        self.table = table
        self.createWidgets()

    def createWidgets(self):
        """Create widgets"""

        operators = ['contains', 'excludes', 'equals', 'not equals', '>', '<', 'is empty', 'not empty',
                     'starts with', 'ends with', 'has length', 'is number', 'is lowercase', 'is uppercase']
        booleanops = ['AND', 'OR', 'NOT']
        df = self.table.model.df
        cols = list(df.columns)
        l = self.layout = QHBoxLayout(self)
        self.setLayout(self.layout)
        w = self.boolean_w = QComboBox()
        w.addItems(booleanops)
        l.addWidget(self.boolean_w)
        w = self.column_w = QComboBox()
        w.addItems(cols)
        # l.addWidget(QLabel('Column:'))
        l.addWidget(self.column_w)
        w = self.operator_w = QComboBox()
        w.addItems(operators)
        l.addWidget(self.operator_w)

        self.term_w = QLineEdit()
        l.addWidget(self.term_w)
        icon = QIcon(os.path.join(iconpath, 'remove.png'))
        btn = QPushButton()
        btn.setIcon(icon)
        btn.setMaximumWidth(30)
        btn.clicked.connect(self.onClose)
        l.addWidget(btn)
        return

    def getFilter(self):
        """Get filter values for this instance"""

        col = self.column_w.currentText()
        val = self.term_w.text()
        op = self.operator_w.currentText()
        booleanop = self.boolean_w.currentText()
        return col, val, op, booleanop

    def onClose(self, ce):
        self.parent.filters.remove(self)
        self.close()
