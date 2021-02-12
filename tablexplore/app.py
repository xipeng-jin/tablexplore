#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
    TablExplore app
    Created November 2020
    Copyright (C) Damien Farrell

    This program is free software; you can redistribute it and/or
    modify it under the terms of the GNU General Public License
    as published by the Free Software Foundation; either version 2
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
import sys, os, platform, time, traceback
import pickle, gzip
from collections import OrderedDict
from .qt import *
import pandas as pd
from .core import DataFrameModel, DataFrameTable, DataFrameWidget
from .plotting import PlotViewer
from . import util, dataset, core, dialogs

homepath = os.path.expanduser("~")
module_path = os.path.dirname(os.path.abspath(__file__))
stylepath = os.path.join(module_path, 'styles')
iconpath = os.path.join(module_path, 'icons')


class ProgressWidget(QDialog):
    """Progress widget class"""

    def __init__(self, parent=None, label=''):
        super(ProgressWidget, self).__init__(parent)
        layout = QVBoxLayout(self)
        self.setWindowTitle('Saving..')
        self.setMinimumSize(400, 100)
        self.setGeometry(
            QStyle.alignedRect(
                QtCore.Qt.LeftToRight,
                QtCore.Qt.AlignCenter,
                self.size(),
                QGuiApplication.primaryScreen().availableGeometry(),
            ))
        self.setMaximumHeight(100)
        self.label = QLabel(label)
        layout.addWidget(self.label)
        # Create a progress bar
        self.progressbar = QProgressBar(self)
        layout.addWidget(self.progressbar)
        self.progressbar.setGeometry(30, 40, 400, 200)

        return


class Application(QMainWindow):
    def __init__(self, project_file=None, csv_file=None):

        QMainWindow.__init__(self, parent=None)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle("DataExplore")
        self.setWindowIcon(QIcon(os.path.join(module_path, 'logo.png')))
        # Initialize menu bar
        self.file_menu = QMenu(title='&File', parent=self)
        self.recent_files_menu = QMenu(title="Recent Projects", parent=self.file_menu)
        self.import_files_menu = QMenu(title="Import Files", parent=self.file_menu)
        self.edit_menu = QMenu(title='&Edit', parent=self)
        self.view_menu = QMenu(title='&View', parent=self)
        self.style_menu = QMenu(title="Styles", parent=self.view_menu)
        self.sheet_menu = QMenu(title='&Sheet', parent=self)
        self.tools_menu = QMenu(title='&Tools', parent=self)
        self.dataset_menu = QMenu(title='&Datasets', parent=self)
        self.plots_menu = QMenu(title='&Plots', parent=self)
        self.plugin_menu = QMenu(title='&Plugins', parent=self)
        self.help_menu = QMenu(title='&Help', parent=self)
        self.create_menu()

        self.main = QTabWidget(self)
        self.main.setTabsClosable(True)
        self.main.tabCloseRequested.connect(lambda index: self.remove_sheet(index))
        screen_resolution = QGuiApplication.primaryScreen().availableGeometry()
        width, height = screen_resolution.width() * 0.7, screen_resolution.height() * 0.7
        self.setGeometry(QtCore.QRect(200, 200, width, height))
        self.setMinimumSize(800, 600)

        self.main.setFocus()
        self.setCentralWidget(self.main)
        self.statusbar = QStatusBar(parent=None)
        self.setStatusBar(self.statusbar)
        self.create_tool_bar()

        s = self.settings = QtCore.QSettings('tablexplore', 'default')
        self.proj_label = QLabel(text="", parent=None)
        self.statusbar.addWidget(self.proj_label, 1)
        self.proj_label.setStyleSheet('color: blue')
        self.style = 'default'
        self.font = 'monospace'
        self.recent_files = ['']
        self.recent_urls = []
        self.plots = {}
        self.openplugins = {}
        self.filename = None

        self.load_settings()
        self.show_recent_files()
        if project_file is not None:
            self.open_project(project_file)
        elif csv_file is not None:
            self.new_project()
            self.import_csv_txt(csv_file)
        else:
            self.new_project()
        self.threadpool = QtCore.QThreadPool()
        self.running = False
        self.discover_plugins()
        return

    def load_settings(self):
        """Load GUI settings"""

        try:
            self.resize(self.s.value('window_size'))
            self.move(self.s.value('window_position'))
            self.set_style(self.s.value('style'))
            core.FONT = self.s.value("font")
            core.FONTSIZE = int(self.s.value("fontsize"))
            core.COLUMNWIDTH = int(self.s.value("columnwidth"))
            core.TIMEFORMAT = self.s.value("timeformat")
            r = self.s.value("recent_files")
            if r != '':
                self.recent_files = r.split(',')
            r = self.s.value("recent_urls")
            if r != '':
                self.recent_urls = r.split('^^')
        except:
            pass
        return

    def save_settings(self):
        """Save GUI settings"""

        self.settings.setValue('window_size', self.size())
        self.settings.setValue('window_position', self.pos())
        self.settings.setValue('style', self.style)
        self.settings.setValue('columnwidth', core.COLUMNWIDTH)
        self.settings.setValue('font', core.FONT)
        self.settings.setValue('fontsize', core.FONTSIZE)
        self.settings.setValue('timeformat', core.TIMEFORMAT)
        self.settings.setValue('recent_files', ','.join(self.recent_files))
        self.settings.setValue('recent_urls', '^^'.join(self.recent_urls))
        if hasattr(self, 'plotgallery'):
            self.settings.setValue('plotgallery_size', self.plotgallery.size())
        self.settings.sync()
        return

    def set_style(self, style='default'):
        """Change interface style."""

        if style == 'default':
            self.setStyleSheet("")
        else:
            f = open(os.path.join(stylepath, '%s.qss' % style), 'r')
            self.style_data = f.read()
            f.close()
            self.setStyleSheet(self.style_data)
        self.style = style
        return

    def create_tool_bar(self):
        """Create tool bar"""

        items = {'new': {'action': lambda: self.new_project(ask=True), 'file': 'document-new'},
                 'open': {'action': self.open_project, 'file': 'document-open'},
                 'save': {'action': lambda: self.save_project(None), 'file': 'save'},
                 'zoom out': {'action': self.zoomOut, 'file': 'zoom-out'},
                 'zoom in': {'action': self.zoomIn, 'file': 'zoom-in'},
                 'decrease columns': {'action': lambda: self.changeColumnWidths(.9), 'file': 'decrease-width'},
                 'increase columns': {'action': lambda: self.changeColumnWidths(1.1), 'file': 'increase-width'},
                 'add sheet': {'action': lambda: self.add_sheet(name=None), 'file': 'add'},
                 # 'lock': {'action':self.lockTable,'file':'lock'},
                 'clean data': {'action': lambda: self._call('cleanData'), 'file': 'clean'},
                 'table to text': {'action': lambda: self._call('showAsText'), 'file': 'tabletotext'},
                 'table info': {'action': lambda: self._call('info'), 'file': 'tableinfo'},
                 'plot gallery': {'action': self.show_plot_gallery, 'file': 'plot-gallery'},
                 'preferences': {'action': self.preferences, 'file': 'preferences-system'},
                 'quit': {'action': self.file_quit, 'file': 'application-exit'}
                 }

        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        for i in items:
            if 'file' in items[i]:
                iconfile = os.path.join(iconpath, items[i]['file'] + '.png')
                icon = QIcon(iconfile)
            else:
                icon = QIcon.fromTheme(items[i]['icon'])
            btn = QAction(icon, i, self)
            btn.triggered.connect(items[i]['action'])
            # btn.setCheckable(True)
            toolbar.addAction(btn)
        return

    def create_menu(self):
        """Main menu"""

        # File menu
        icon = QIcon(os.path.join(iconpath, 'document-new.png'))
        self.file_menu.addAction(icon, '&New', lambda: self.new_project(ask=True),
                                 QtCore.Qt.CTRL + QtCore.Qt.Key_N)
        icon = QIcon(os.path.join(iconpath, 'open.png'))
        self.file_menu.addAction(icon, '&Open', self.open_project,
                                 QtCore.Qt.CTRL + QtCore.Qt.Key_O)
        self.file_menu.addAction(self.recent_files_menu.menuAction())
        icon = QIcon(os.path.join(iconpath, 'save.png'))
        self.file_menu.addAction(icon, '&Save', self.save_project,
                                 QtCore.Qt.CTRL + QtCore.Qt.Key_S)
        self.file_menu.addAction('&Save As', self.save_as_project)
        self.file_menu.addAction(self.import_files_menu.menuAction())
        self.import_files_menu.addAction('&CSV...', self.import_csv_txt)
        self.import_files_menu.addAction('&Excel...', self.import_excel)
        self.import_files_menu.addAction('&HDF5...', self.importHDF)
        self.import_files_menu.addAction('&URL...', self.importURL)
        self.file_menu.addAction('&Export As', self.export_as)
        icon = QIcon(os.path.join(iconpath, 'application-exit.png'))
        self.file_menu.addAction(icon, '&Quit', self.file_quit,
                                 QtCore.Qt.CTRL + QtCore.Qt.Key_Q)
        self.menuBar().addMenu(self.file_menu)

        # Edit menu
        self.menuBar().addMenu(self.edit_menu)
        self.undo_item = self.edit_menu.addAction('&Undo', self.undo,
                                                  QtCore.Qt.CTRL + QtCore.Qt.Key_Z)
        # self.undo_item.setDisabled(True)
        # self.edit_menu.addAction('&Run Last Action', self.runLastAction)
        icon = QIcon(os.path.join(iconpath, 'preferences-system.png'))
        self.edit_menu.addAction(icon, '&Preferences', self.preferences)

        # View menu
        self.menuBar().addMenu(self.view_menu)
        icon = QIcon(os.path.join(iconpath, 'zoom-in.png'))
        self.view_menu.addAction(icon, '&Zoom In', self.zoomIn,
                                 QtCore.Qt.CTRL + QtCore.Qt.Key_Equal)
        icon = QIcon(os.path.join(iconpath, 'zoom-out.png'))
        self.view_menu.addAction(icon, '&Zoom Out', self.zoomOut,
                                 QtCore.Qt.CTRL + QtCore.Qt.Key_Minus)
        icon = QIcon(os.path.join(iconpath, 'decrease-width.png'))
        self.view_menu.addAction(icon, '&Decrease Column Width', lambda: self.changeColumnWidths(.9))
        icon = QIcon(os.path.join(iconpath, 'increase-width.png'))
        self.view_menu.addAction(icon, '&Increase Column Width', self.changeColumnWidths)
        # Style menu
        self.style_menu.addAction('&Default', self.set_style)
        self.style_menu.addAction('&Light', lambda: self.set_style('light'))
        self.style_menu.addAction('&Dark', lambda: self.set_style('dark'))
        self.view_menu.addAction(self.style_menu.menuAction())

        # Sheet menu
        self.menuBar().addMenu(self.sheet_menu)
        icon = QIcon(os.path.join(iconpath, 'add.png'))
        self.sheet_menu.addAction(icon, '&Add', self.add_sheet)
        self.sheet_menu.addAction('&Rename', self.rename_sheet)
        icon = QIcon(os.path.join(iconpath, 'copy.png'))
        self.sheet_menu.addAction(icon, '&Copy', self.copy_sheet)

        # Tools menu
        icon = QIcon(os.path.join(iconpath, 'tableinfo.png'))
        self.tools_menu.addAction(icon, '&Table Info', lambda: self._call('info'),
                                  QtCore.Qt.CTRL + QtCore.Qt.Key_I)
        icon = QIcon(os.path.join(iconpath, 'clean.png'))
        self.tools_menu.addAction(icon, '&Clean Data', lambda: self._call('cleanData'))
        icon = QIcon(os.path.join(iconpath, 'table-duplicates.png'))
        self.tools_menu.addAction(icon, '&Find Duplicates', lambda: self._call('findDuplicates'))
        self.tools_menu.addAction('&Convert Numeric', lambda: self._call('convertNumeric'))
        self.tools_menu.addAction('&Convert Column Names', lambda: self._call('convertColumnNames'))
        self.tools_menu.addAction('&Time Series Resample', lambda: self._call('resample'))
        icon = QIcon(os.path.join(iconpath, 'tabletotext.png'))
        self.tools_menu.addAction(icon, '&Table to Text', lambda: self._call('showAsText'),
                                  QtCore.Qt.CTRL + QtCore.Qt.Key_T)
        icon = QIcon(os.path.join(iconpath, 'interpreter.png'))
        self.tools_menu.addAction(icon, '&Python Interpreter', self.interpreter)
        self.menuBar().addMenu(self.tools_menu)

        # Datasets menu
        self.menuBar().addMenu(self.dataset_menu)
        self.dataset_menu.addAction('&Sample', lambda: self.get_sample_data('sample'))
        self.dataset_menu.addAction('&Iris', lambda: self.get_sample_data('iris'))
        self.dataset_menu.addAction('&Titanic', lambda: self.get_sample_data('titanic'))
        self.dataset_menu.addAction('&Pima Diabetes', lambda: self.get_sample_data('pima'))

        # Plots menu
        self.menuBar().addMenu(self.plots_menu)
        self.plots_menu.addAction('&Store Plot', lambda: self.store_plot())
        self.plots_menu.addAction('&Show Plots', lambda: self.show_plot_gallery())

        # Plugin menu
        self.menuBar().addMenu(self.plugin_menu)
        # self.plugin_menu.addAction('&Store Plot', lambda: self.storePlot())

        # Help menu
        self.menuBar().addSeparator()
        self.menuBar().addMenu(self.help_menu)
        icon = QIcon(os.path.join(iconpath, 'logo.png'))
        self.help_menu.addAction(icon, '&About', self.about)

        # plot shortcut
        self.plotshc = QShortcut(QKeySequence('Ctrl+P'), self)
        self.plotshc.activated.connect(self.replot)
        return

    def _call(self, func, **args):
        """Call a table function from it's string name"""

        table = self.get_current_table()
        getattr(table, func)(**args)
        return

    def _check_snap(self):

        if os.environ.has_key('SNAP_USER_COMMON'):
            print('running inside snap')
            return True
        return False

    def _check_tables(self):
        """Check tables before saving that so we are not saving
        filtered copies"""

        for s in self.sheets:
            t = self.sheets[s]
            if t.filtered:
                t.showAll()
        return

    @Slot(str)
    def state_changed(self, boolean):
        print(boolean)

    def show_recent_files(self):
        """Populate recent files menu"""

        from functools import partial
        if self.recent_files is None:
            return
        for fname in self.recent_files:
            self.recent_files_menu.addAction(fname, partial(self.open_project, fname))
        self.recent_files_menu.setEnabled(len(self.recent_files))
        return

    def add_recent_file(self, fname):
        """Add file to recent if not present"""

        fname = os.path.abspath(fname)
        if fname and fname not in self.recent_files:
            self.recent_files.insert(0, fname)
            if len(self.recent_files) > 5:
                self.recent_files.pop()
        self.recent_files_menu.setEnabled(len(self.recent_files))
        return

    def new_project(self, data=None, ask=False):
        """New project"""

        if ask:
            reply = QMessageBox.question(self, 'Are you sure?',
                                         'Save current project?',
                                         QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if reply == QMessageBox.Yes:
                self.save_project()
        if not type(data) is dict:
            data = None
        self.main.clear()
        self.sheets = OrderedDict()
        self.filename = None
        self.projopen = True
        self.plots = {}
        if data is not None:
            for s in data.keys():
                if s in ['meta', 'plots']:
                    continue
                df = data[s]['table']
                if 'meta' in data[s]:
                    meta = data[s]['meta']
                else:
                    meta = None
                self.add_sheet(s, df, meta)
            if 'plots' in data:
                self.plots = data['plots']
        else:
            self.add_sheet('dataset1')
        return

    @staticmethod
    def close_project(self):
        """Close"""

        return None

    def open_project(self, filename=None, asksave=False):
        """Open project file"""

        w = True
        if asksave:
            w = self.close_project()
        if w is None:
            return

        if filename is None:
            options = QFileDialog.Options()
            filename, _ = QFileDialog.getOpenFileName(self, "Open Project",
                                                      homepath, "tablexplore Files (*.txpl);;All files (*.*)",
                                                      options=options)

        if not filename:
            return
        if not os.path.exists(filename):
            print('no such file')
            self.removeRecent(filename)
            return
        ext = os.path.splitext(filename)[1]
        if ext != '.txpl':
            print('does not appear to be a project file')
            return
        if os.path.isfile(filename):
            data = pickle.load(gzip.GzipFile(filename, 'r'))
        else:
            print('no such file')
            self.quit()
            return
        self.new_project(data)
        self.filename = filename

        self.proj_label.setText(self.filename)
        self.projopen = True
        self.defaultsavedir = os.path.dirname(os.path.abspath(filename))
        self.add_recent_file(filename)
        return

    def save_as_project(self):
        """Save as a new project filename"""

        options = QFileDialog.Options()
        filename, _ = QFileDialog.getSaveFileName(self, "Save Project",
                                                  homepath, "tablexplore Files (*.txpl);;All files (*.*)",
                                                  options=options)
        if not filename:
            return

        self.filename = filename
        if not os.path.splitext(filename)[1] == '.txpl':
            self.filename += '.txpl'
        self.do_save_project(filename)
        self.add_recent_file(filename)
        self.proj_label.setText(self.filename)
        return

    def save_project(self, filename=None):
        """Save project"""

        if self.filename is not None:
            filename = self.filename
        if filename is None:
            self.save_as_project()
        if not filename:
            return
        self.running = True
        self.filename = filename
        if not os.path.splitext(filename)[1] == '.txpl':
            self.filename += '.txpl'
        self.defaultsavedir = os.path.dirname(os.path.abspath(filename))
        # self.do_saveProject(self.filename)
        self.save_with_progress(self.filename)
        return

    def save_with_progress(self, filename):
        """Save with progress bar"""

        self.savedlg = dlg = ProgressWidget(label='Saving to %s' % filename)
        dlg.show()

        def func(progress_callback):
            self.do_save_project(self.filename)

        self.run_threaded_process(func, self.processing_completed)
        return

    def run_threaded_process(self, process, on_complete):
        """Execute a function in the background with a worker"""

        # if self.running == True:
        #    return
        worker = Worker(fn=process)
        self.threadpool.start(worker)
        worker.signals.finished.connect(on_complete)
        # worker.signals.progress.connect(self.progress_fn)
        self.savedlg.progressbar.setRange(0, 0)
        # self.worker = worker
        return

    def progress_fn(self, msg):
        return

    def processing_completed(self):
        """Generic process completed"""

        self.savedlg.progressbar.setRange(0, 1)
        self.savedlg.close()
        self.running = False
        return

    def do_save_project(self, filename, progress_callback=None):
        """Does the actual saving. Save sheets inculding table dataframes
           and meta data as dict to compressed pickle.
        """

        data = {}
        for i in self.sheets:
            tablewidget = self.sheets[i]
            table = tablewidget.table
            data[i] = {}
            # save dataframe with current column order
            if table.filtered:
                df = table.dataframe
            else:
                df = table.model.df
            cols = table.getColumnOrder()
            data[i]['table'] = df[cols]
            data[i]['meta'] = self.save_meta(tablewidget)
        data['plots'] = self.plots
        file = gzip.GzipFile(filename, 'w')
        pickle.dump(data, file)
        return

    def save_meta(self, tablewidget):
        """Save meta data such as current plot options and certain table attributes.
         These are re-loaded when the sheet is opened."""

        meta = {}
        pf = tablewidget.pf
        pf.applyPlotoptions()
        table = tablewidget.table
        # save plot options
        meta['generalopts'] = pf.generalopts.kwds
        # meta['mplopts3d'] = pf.mplopts3d.kwds
        meta['labelopts'] = pf.labelopts.kwds
        meta['axesopts'] = pf.axesopts.kwds

        # save table selections
        meta['table'] = util.getAttributes(table)
        meta['table']['column_widths'] = table.getColumnWidths()
        meta['plotviewer'] = util.getAttributes(pf)
        # print (meta['plotviewer'])
        # save child table if present
        if tablewidget.subtable is not None:
            meta['subtable'] = tablewidget.subtable.table.model.df
        #    meta['childselected'] = util.getAttributes(table.child)

        return meta

    def load_meta(self, table, meta):
        """Load meta data for a sheet/table, this includes plot options and
        table selections"""

        tablesettings = meta['table']
        if 'subtable' in meta:
            subtable = meta['subtable']
            # childsettings = meta['childselected']
        else:
            subtable = None
        # load plot options
        opts = {'generalopts': table.pf.generalopts,
                # 'mplopts3d': table.pf.mplopts3d,
                'labelopts': table.pf.labelopts,
                'axesopts': table.pf.axesopts,
                }
        for m in opts:
            if m in meta and meta[m] is not None:
                # util.setAttributes(opts[m], meta[m])
                # print (m,meta[m])
                opts[m].updateWidgets(meta[m])
                # check options loaded for missing values
                # avoids breaking file saves when options changed
                # defaults = plotting.get_defaults(m)
                # for key in defaults:
                #    if key not in opts[m].opts:
                #        opts[m].opts[key] = defaults[key]

        # load table settings
        util.setAttributes(table.table, tablesettings)
        if 'column_widths' in tablesettings:
            table.table.setColumnWidths(tablesettings['column_widths'])
        table.refresh()
        # load plotviewer
        if 'plotviewer' in meta:
            # print (meta['plotviewer'])
            fig = meta['plotviewer']['fig']
            table.pf.setFigure(fig)
            table.pf.canvas.draw()
            # util.setAttributes(table.pf, meta['plotviewer'])
            # table.pf.updateWidgets()

        if subtable is not None:
            table.showSubTable(df=subtable)
            # util.setAttributes(table.child, childsettings)

        # redraw col selections
        # if type(table.multiplecollist) is tuple:
        #    table.multiplecollist = list(table.multiplecollist)
        # table.drawMultipleCols()
        return

    def import_csv_txt(self, filepath=None, dialog=True):

        if dialog is True and filepath is None:
            options = QFileDialog.Options()
            filepath, _ = QFileDialog.getOpenFileName(
                self, "Import File",
                "", "CSV files (*.csv);;Text Files (*.txt);;All Files (*)",
                options=options
            )
            if filepath:
                dlg = dialogs.ImportDialog(self, filepath)
                dlg.exec_()
                if dlg.accepted:
                    filename = os.path.basename(filepath)
                    filename = os.path.splitext(filename)[0]
                    self.add_sheet(name=filename, df=dlg.df)
                else:
                    return
            else:
                return
        elif filepath is not None:
            df = pd.read_csv(filepath)
            self.add_sheet(df=df)
        return

    def import_excel(self, filepath=None):
        """Import Excel file"""

        def convert_column_letters(n):
            string = ""
            while n > 0:
                n, remainder = divmod(n-1, 26)
                string = chr(65 + remainder) + string
            return string

        def read_excel_sheets(path):
            df_dict = pd.read_excel(path, sheet_name=None, header=None)
            sheet_names = list(df_dict.keys())
            sheet_dfs = list(df_dict.values())
            return sheet_names, sheet_dfs

        if filepath is None:
            options = QFileDialog.Options()
            filepath, _ = QFileDialog.getOpenFileName(
                self, "Import Excel",
                "", "xlsx files (*.xlsx);;xls Files (*.xls);;All Files (*)",
                options=options
            )
            if filepath:
                names, dfs = read_excel_sheets(filepath)
                for name, df in zip(names, dfs):
                    column_letters = []
                    for idx in list(df.columns):
                        letter = convert_column_letters(idx+1)
                        column_letters.append(letter)
                    df.columns = column_letters
                    self.add_sheet(name, df)
            else:
                return
        elif filepath is not None:
            names, dfs = read_excel_sheets(filepath)
            for name, df in zip(names, dfs):
                self.add_sheet(name, df)
        return

    def importHDF(self):

        self.add_sheet()
        w = self.get_current_table()
        w.importHDF()
        return

    def importURL(self):
        """Import from URL"""

        self.add_sheet()
        w = self.get_current_table()
        recent = self.recent_urls
        url = w.importURL()
        if url is not False and url not in self.recent_urls:
            self.recent_urls.append(url)
        return

    def export_as(self):
        """Export as"""

        options = QFileDialog.Options()
        w = self.get_current_table()
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export",
            "",
            "csv files (*.csv);;xlsx files (*.xlsx);;xls Files (*.xls);;hdf files (*.hdf5);;All Files (*)",
            options=options
        )
        df = w.table.model.df
        ext = os.path.splitext(filename)[1]
        if ext == '.csv':
            df.to_csv(filename)
        elif ext == '.hdf5':
            df.to_hdf(filename)
        elif ext == '.xls':
            df.to_excel(filename)
        return

    def add_sheet(self, name=None, df=None, meta=None):
        """Add a new sheet"""

        names = list(self.sheets.keys())
        i = len(self.sheets) + 1
        if name is None or name in names:
            name = 'dataset' + str(i)
        if name in names:
            import random
            name = 'dataset' + str(random.randint(i, 100))

        sheet = QSplitter(self.main)
        idx = self.main.addTab(sheet, name)
        # provide reference to self to dataframewidget
        dfw = DataFrameWidget(sheet, dataframe=df, app=self,
                              font=core.FONT, fontsize=core.FONTSIZE,
                              columnwidth=core.COLUMNWIDTH, timeformat=core.TIMEFORMAT)
        sheet.addWidget(dfw)

        self.sheets[name] = dfw
        self.currenttable = dfw
        pf = dfw.createPlotViewer(sheet)
        sheet.addWidget(pf)
        sheet.setSizes((500, 1000))
        # reload attributes of table and plotter if present
        if meta is not None:
            self.load_meta(dfw, meta)
        self.main.setCurrentIndex(idx)
        return

    def remove_sheet(self, index, ask=True):
        """Remove sheet"""

        if ask:
            reply = QMessageBox.question(self, 'Delete this sheet?',
                                         'Are you sure?', QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.No:
                return False
        name = self.main.tabText(index)
        del self.sheets[name]
        self.main.removeTab(index)
        return

    def rename_sheet(self):
        """Rename the current sheet"""

        index = self.main.currentIndex()
        name = self.main.tabText(index)
        new, ok = QInputDialog.getText(self, 'New name', 'Name:',
                                       QLineEdit.Normal, name)
        if ok:
            if new in self.sheets:
                QMessageBox.information(self, "Cannot rename",
                                        "Sheet name already present")
                return
            self.sheets[new] = self.sheets[name]
            del self.sheets[name]
            self.main.setTabText(index, new)
        return

    def copy_sheet(self):
        """Copy sheet"""

        index = self.main.currentIndex()
        name = self.main.tabText(index)
        df = self.sheets[name].table.model.df
        new, ok = QInputDialog.getText(self, 'New name', 'Name:',
                                       QLineEdit.Normal, name + '_copy')
        if ok:
            self.add_sheet(new, df)
        return

    def load_dataframe(self, df, name=None, select=False):
        """Load a DataFrame into a new sheet
           Args:
            df: dataframe
            name: name of new sheet
            select: set new sheet as selected
        """

        if hasattr(self, 'sheets'):
            self.add_sheet(df=df)
        else:
            data = {name: {'table': df}}
            self.new_project(data)
        return

    def load_pickle(self, filename):
        """Load a pickle file"""

        df = pd.read_pickle(filename)
        name = os.path.splitext(os.path.basename(filename))[0]
        self.load_dataframe(df, name)
        return

    def file_quit(self):
        self.close()

    def closeEvent(self, event):
        """Close event"""

        reply = QMessageBox.question(self, 'Close',
                                     'Save current project?',
                                     QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        if reply == QMessageBox.Cancel:
            event.ignore()
            return
        if reply == QMessageBox.Yes:
            self.save_project()

        for s in self.sheets:
            self.sheets[s].close()
        self.save_settings()
        if hasattr(self, 'plotgallery'):
            self.plotgallery.close()
        self.threadpool.waitForDone()
        self.file_quit()
        return

    def get_sample_data(self, name, rows=None):
        """Sample table"""

        ok = True
        sheetname = name
        if name in self.sheets:
            i = len(self.sheets)
            sheetname = name + '-' + str(i)
        if name == 'sample':
            if rows is None:
                opts = {'rows': {'type': 'spinbox', 'default': 10, 'range': (1, 1e7)},
                        'cols': {'type': 'spinbox', 'default': 5, 'range': (1, 26)}}
                dlg = dialogs.MultipleInputDialog(self, opts, title='Sample data',
                                                  width=250, height=150)
                dlg.exec_()
                if not dlg.accepted:
                    return
                kwds = dlg.values
                rows = kwds['rows']
                cols = kwds['cols']
            if ok:
                df = dataset.getSampleData(rows, cols)
            else:
                return
        else:
            df = dataset.getPresetData(name)
        self.add_sheet(sheetname, df)
        return

    def get_current_table(self):
        """Return the currently used table"""

        idx = self.main.currentIndex()
        name = self.main.tabText(idx)
        table = self.sheets[name]
        return table

    def replot(self):
        """Plot current"""

        w = self.get_current_table()
        pf = w.pf
        pf.replot()

    def zoomIn(self):

        w = self.get_current_table()
        w.table.zoomIn()
        return

    def zoomOut(self):

        w = self.get_current_table()
        w.table.zoomOut()
        return

    def changeColumnWidths(self, factor=1.1):
        w = self.get_current_table()
        w.table.changeColumnWidths(factor)

    def undo(self):

        w = self.get_current_table()
        w.table.undo()
        w.refresh()
        return

    '''def runLastAction(self):
        w = self.getCurrentTable()
        w.runLastAction()
        return'''

    def refresh(self):
        """Refresh all tables"""

        for s in self.sheets:
            w = self.sheets[s].table
            w.font = core.FONT
            w.fontsize = core.FONTSIZE
            w.refresh()
        return

    def store_plot(self):
        """Cache the current plot so it can be viewed later"""

        w = self.get_current_table()
        index = self.main.currentIndex()
        name = self.main.tabText(index)
        # get the current figure and make a copy of it by using pickle
        fig = w.pf.fig
        p = pickle.dumps(fig)
        fig = pickle.loads(p)
        t = time.strftime("%H:%M:%S")
        label = name + '-' + t
        self.plots[label] = fig
        if hasattr(self, 'plotgallery'):
            self.plotgallery.update(self.plots)
        return

    def show_plot_gallery(self):
        """Show stored plot figures"""

        from . import plotting
        if not hasattr(self, 'plotgallery'):
            self.plotgallery = plotting.PlotGallery()
            try:
                self.plotgallery.resize(self.settings.value('plotgallery_size'))
            except:
                pass
        self.plotgallery.update(self.plots)
        self.plotgallery.show()
        self.plotgallery.activateWindow()
        return

    def interpreter(self):
        """Launch python interpreter"""

        table = self.get_current_table()
        table.showInterpreter()
        return

    def discover_plugins(self):
        """Discover available plugins"""

        from . import plugin
        default = os.path.join(module_path, 'plugins')
        paths = [default]
        # paths = [apppath,self.configpath]

        failed = plugin.init_plugin_system(paths)
        self.update_plugin_menu()
        return

    def load_plugin(self, plugin):
        """Instantiate the plugin and call it's main method"""

        index = self.main.currentIndex()
        name = self.main.tabText(index)
        tablew = self.sheets[name]

        p = plugin()
        # plugin should be added to the splitter as a dock widget
        # should also be able to add standalone windows
        try:
            p.main(parent=self, table=tablew)
        except Exception as e:
            QMessageBox.information(self, "Plugin error", str(e))

        tablew.splitter.addWidget(p.mainwin)
        index = tablew.splitter.indexOf(p.mainwin)
        tablew.splitter.setCollapsible(index, False)

        # track which plugin is running so the last one is removed?
        self.openplugins[name] = p
        return

    def update_plugin_menu(self):
        """Update plugins"""

        from . import plugin
        # self.plugin_menu['var'].delete(3, self.plugin_menu['var'].index(END))
        plgmenu = self.plugin_menu
        for plg in plugin.get_plugins_classes('gui'):
            def func(p, **kwargs):
                def new():
                    self.load_plugin(p)

                return new

            # plgmenu.add_command(label=plg.menuentry,
            #                   command=func(plg))
            plgmenu.addAction(plg.menuentry, func(plg))
        return

    def preferences(self):
        """Preferences dialog"""

        from . import dialogs
        opts = {'font': core.FONT, 'fontsize': core.FONTSIZE,
                'columnwidth': core.COLUMNWIDTH, 'timeformat': core.TIMEFORMAT}
        dlg = dialogs.PreferencesDialog(self, opts)
        dlg.exec_()
        return

    def online_documentation(self, event=None):
        """Open the online documentation"""

        import webbrowser
        link = 'https://github.com/dmnfarrell/tablexplore'
        webbrowser.open(link, autoraise=1)
        return

    def about(self):
        from . import __version__
        import matplotlib

        pandasver = pd.__version__
        pythonver = platform.python_version()
        mplver = matplotlib.__version__
        if 'PySide2' in sys.modules:
            import PySide2
            qtver = 'PySide2=' + PySide2.QtCore.__version__
        else:
            import PyQt5
            qtver = 'PyQt5=' + PyQt5.QtCore.QT_VERSION_STR

        text = 'Tablexplore Application\n' \
               + 'Version ' + __version__ + '\n' \
               + 'Copyright (C) Damien Farrell 2018-\n' \
               + 'This program is free software; you can redistribute it and/or\n' \
               + 'modify it under the terms of the GNU General Public License ' \
               + 'as published by the Free Software Foundation; either version 3 ' \
               + 'of the License, or (at your option) any later version.\n' \
               + 'Using Python v%s, %s\n' % (pythonver, qtver) \
               + 'pandas v%s, matplotlib v%s' % (pandasver, mplver)

        msg = QMessageBox.about(self, "About", text)
        return


# https://www.learnpyqt.com/courses/concurrent-execution/multithreading-pyqt-applications-qthreadpool/
class Worker(QtCore.QRunnable):
    """Worker thread for running background tasks."""

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.kwargs['progress_callback'] = self.signals.progress

    @QtCore.Slot()
    def run(self):
        try:
            result = self.fn(
                *self.args, **self.kwargs,
            )
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()


class WorkerSignals(QtCore.QObject):
    """
    Defines the signals available from a running worker thread.
    Supported signals are:
    finished
        No data
    error
        `tuple` (exctype, value, traceback.format_exc() )
    result
        `object` data returned from processing, anything
    """
    finished = QtCore.Signal()
    error = QtCore.Signal(tuple)
    result = QtCore.Signal(object)
    progress = QtCore.Signal(str)


def main():
    import sys, os

    from argparse import ArgumentParser
    parser = ArgumentParser()
    # parser.add_argument("-f", "--file", dest="msgpack",
    #                    help="Open a dataframe as msgpack", metavar="FILE")
    parser.add_argument("-p", "--project", dest="project_file",
                        help="Open a dataexplore project file", metavar="FILE")
    parser.add_argument("-i", "--csv", dest="csv_file",
                        help="Import a csv file", metavar="FILE")
    # parser.add_argument("-x", "--excel", dest="excel",
    #                    help="Import an excel file", metavar="FILE")
    # parser.add_argument("-t", "--test", dest="test",  action="store_true",
    #                    default=False, help="Run a basic test app")
    args = vars(parser.parse_args())

    app = QApplication(sys.argv)
    aw = Application(**args)
    aw.show()
    app.exec_()


if __name__ == '__main__':
    main()
