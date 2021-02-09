#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
    tableexplore plotting module
    Created May 2017
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
import sys,os,random
from collections import OrderedDict

import matplotlib as mpl
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.lines import Line2D
try:
    from pandas import plotting
except ImportError:
    from pandas.tools import plotting
import numpy as np
import pandas as pd
from .qt import *
from .dialogs import *
import logging
from . import util

homepath = os.path.expanduser("~")
module_path = os.path.dirname(os.path.abspath(__file__))
iconpath = os.path.join(module_path, 'icons')

colormaps = sorted(m for m in plt.cm.datad if not m.endswith("_r"))
markers = ['','o','.','^','v','>','<','s','+','x','p','d','h','*']
linestyles = ['-','--','-.',':','steps']
valid_kwds = {'line': ['alpha', 'colormap', 'grid', 'legend', 'linestyle','ms',
                  'linewidth', 'marker', 'subplots', 'rot', 'logx', 'logy',
                  'sharex','sharey', 'kind'],
            'scatter': ['alpha', 'grid', 'linewidth', 'marker', 'subplots', 'ms',
                    'legend', 'colormap','sharex','sharey', 'logx', 'logy', 'use_index',
                    'clrcol', 'cscale','colorbar','bw','labelcol','pointsizes'],
            'pie': ['colormap','legend'],
            'hexbin': ['alpha', 'colormap', 'grid', 'linewidth','subplots'],
            'bootstrap': ['grid'],
            'bar': ['alpha', 'colormap', 'grid', 'legend', 'linewidth', 'subplots',
                    'sharex','sharey', 'logy', 'stacked', 'rot', 'kind', 'edgecolor'],
            'barh': ['alpha', 'colormap', 'grid', 'legend', 'linewidth', 'subplots',
                    'sharex','sharey','stacked', 'rot', 'kind', 'logx', 'edgecolor'],
            'histogram': ['alpha', 'linewidth','grid','stacked','subplots','colormap',
                     'sharex','sharey','rot','bins', 'logx', 'logy', 'legend', 'edgecolor'],
            'heatmap': ['colormap','colorbar','rot', 'linewidth','linestyle',
                        'subplots','rot','cscale','bw','alpha','sharex','sharey'],
            'area': ['alpha','colormap','grid','linewidth','legend','stacked',
                     'kind','rot','logx','sharex','sharey','subplots'],
            'density': ['alpha', 'colormap', 'grid', 'legend', 'linestyle',
                         'linewidth', 'marker', 'subplots', 'rot', 'kind'],
            'boxplot': ['rot','grid','logy','colormap','alpha','linewidth','legend',
                        'subplots','edgecolor','sharex','sharey'],
            'violinplot': ['rot','grid','logy','colormap','alpha','linewidth','legend',
                        'subplots','edgecolor','sharex','sharey'],
            'dotplot': ['marker','edgecolor','linewidth','colormap','alpha','legend',
                        'subplots','ms','bw','logy','sharex','sharey'],
            'scatter_matrix':['alpha', 'linewidth', 'marker', 'grid', 's'],
            'contour': ['linewidth','colormap','alpha','subplots'],
            'imshow': ['colormap','alpha'],
            'venn': ['colormap','alpha'],
            'radviz': ['linewidth','marker','edgecolor','s','colormap','alpha']
            }

style = '''
    QLabel {
        font-size: 10px;
    }
    QWidget {
        max-width: 250px;
        min-width: 60px;
        font-size: 14px;
    }
    QPlainTextEdit {
        max-height: 80px;
    }
'''

class PlotWidget(FigureCanvas):
    def __init__(self, parent=None, figure=None, dpi=100, hold=False):

        if figure == None:
            figure = Figure()
        super(PlotWidget, self).__init__(figure)
        self.setParent(parent)
        self.figure = Figure(dpi=dpi)
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)


class PlotViewer(QWidget):
    """Plot viewer class"""
    def __init__(self, table, parent=None):
        super(PlotViewer, self).__init__(parent)
        self.parent = parent
        self.table = table
        self.createWidgets()
        self.currentdir = os.path.expanduser('~')
        sizepolicy = QSizePolicy()
        self.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))
        self.style = None
        return

    def addPlotWidget(self):
        """Create mpl plot canvas and toolbar"""

        layout = self.left
        vbox = self.vbox
        self.canvas = PlotWidget(layout)
        self.fig = self.canvas.figure
        self.ax = self.canvas.ax
        self.toolbar = NavigationToolbar(self.canvas, layout)
        vbox.addWidget(self.toolbar)
        vbox.addWidget(self.canvas)
        return

    def createWidgets(self):
        """Create widgets. Plot on left and dock for tools on right."""

        #self.main = QSplitter(Qt.Horizontal, self)
        self.main = QWidget(self)
        hbox = QHBoxLayout(self)
        self.left = left = QWidget(self.main)
        hbox.addWidget(left)

        #bw = self.createButtons(left)
        #vbox.addWidget(bw)
        self.vbox = vbox = QVBoxLayout(left)
        self.addPlotWidget()

        dock = QDockWidget('options',self)
        dock.setMaximumWidth(280)
        dock.setMinimumWidth(220)
        scrollarea = QScrollArea(dock)
        scrollarea.setWidgetResizable(True)
        dock.setWidget(scrollarea)
        toolsarea = QWidget()
        toolsarea.setMinimumSize(180,900)
        scrollarea.setWidget(toolsarea)
        hbox.addWidget(dock)
        ow = self.createDialogs(toolsarea)
        #dock.setWidget(ow)
        return

    def setFigure(self, figure):
        """Recreate canvas with given figure"""

        self.canvas.figure = figure
        self.fig = self.canvas.figure
        self.ax = self.canvas.ax
        self.canvas.draw()
        return

    def createDialogs(self, parent):
        """Create widgets"""

        style = '''
            QLabel {
                font-size: 12px;
                max-width: 90px;
            }
            QWidget {
                max-width: 250px;
                min-width: 35px;
                font-size: 12px;
            }
            QComboBox {
                max-width: 90px;
                font-size: 12px;
            }
            QSlider {
                max-width: 90px;
            }
            QSpinBox {
                max-width: 90px;
            }
            '''

        tab = QTabWidget(parent)
        w = QWidget(tab)
        idx = tab.addTab(w, 'general')
        self.generalopts = MPLBaseOptions(parent=self)
        dialog = self.generalopts.showDialog(w, wrap=2, section_wrap=1, style=style)
        dialog.resize(200,200)
        #self.generaldialog = dialog
        l=QVBoxLayout(w)
        l.addWidget(dialog)

        w = QWidget(tab)
        w.setStyleSheet(style)
        idx = tab.addTab(w, 'labels')
        self.labelopts = AnnotationOptions(parent=self)
        dialog = self.labelopts.showDialog(w, wrap=2, section_wrap=1, style=style)
        dialog.resize(200,200)
        l=QVBoxLayout(w)
        l.addWidget(dialog)

        w = QWidget(tab)
        idx = tab.addTab(w, 'axes')
        self.axesopts = AxesOptions(parent=self)
        dialog = self.axesopts.showDialog(w, wrap=2, section_wrap=1, style=style)
        dialog.resize(200,200)
        l=QVBoxLayout(w)
        l.addWidget(dialog)
        return tab

    def createButtons(self, parent):
        """Create button widgets"""

        buttons = {'Plot': {'action':self.plot,'icon':'plot'},
                   'Clear': {'action':self.clear,'icon':'view-restore'},
                   'Zoom Out': {'action': lambda: self.zoom(zoomin=False),
                                'icon':'zoom-out','label':''},
                   'Zoom In': {'action':lambda: self.zoom(zoomin=True),
                                'icon':'zoom-in','label':''},
                   'Save': {'action':self.savePlot,'icon':'document-save'}
            }
        w=80; h=35
        bw = self.button_widget = QWidget(parent)
        bw.setMaximumHeight(100)
        box = QHBoxLayout(bw)
        box.setContentsMargins(0,0,0,0)
        for b in buttons:
            btn = QPushButton(b)
            btn.clicked.connect(buttons[b]['action'])
            btn.setMinimumSize(w,h)
            if 'icon' in buttons[b]:
                icon = buttons[b]['icon']
                iconfile = os.path.join(iconpath,icon+'.png')
                if os.path.exists(iconfile):
                    btn.setIcon(QIcon(iconfile))
                else:
                    iconw = QIcon.fromTheme(icon)
                    btn.setIcon(QIcon(iconw))
            if 'label' in buttons[b]:
                btn.setText(buttons[b]['label'])
            box.addWidget(btn)

        self.globalopts = GlobalOptions(parent=self)
        dialog = self.globalopts.showDialog(bw, wrap=3)
        dialog.resize(200,200)
        box.addWidget(dialog)
        bw.setMaximumHeight(60)
        return bw

    def simple_plot(self, df):
        """test plot"""

        kwds = self.generalopts.kwds
        self.ax = self.fig.add_subplot(111)
        cols = df.columns
        x=df[cols[0]]
        y=df[cols[1]]
        cmap = plt.cm.get_cmap(kwds['colormap'])
        self.ax.scatter(x, y, s=kwds['ms']*10, marker=kwds['marker'] )
        self.canvas.draw()
        return

    def zoom(self, zoomin=True):
        """Zoom in/out to plot by changing size of elements"""

        if zoomin == False:
            val=-1.0
        else:
            val=1.0
        self.generalopts.increment('linewidth',val)
        self.generalopts.increment('ms',val)
        self.labelopts.increment('fontsize',val)
        self.replot()
        return

    def clear(self):

        self.canvas.axes.clear()
        self.canvas.draw()
        return

    def plot(self):
        self.replot()

    def replot(self, data=None):
        """Replot with given dataframe"""

        self.clear()
        if data is None:
            self.data = self.table.getSelectedDataFrame()
        else:
            self.data = data

        self.setStyle()
        self.applyPlotoptions()
        self.plotCurrent()
        return

    def plotCurrent(self, redraw=True):
        """Plot the current data"""

        plot3d = self.generalopts.kwds['3D plot']
        self._initFigure()
        if plot3d == 1:
            self.plot3D(redraw=redraw)
        else:
            self.plot2D(redraw=redraw)
        return

    def applyPlotoptions(self):
        """Apply the current plotter/options"""

        self.generalopts.applyOptions()
        #self.globalopts.applyOptions()
        #self.mplopts3d.applyOptions()
        self.labelopts.applyOptions()
        self.axesopts.applyOptions()
        self.style = self.generalopts.kwds['style']
        mpl.rcParams['savefig.dpi'] = self.generalopts.kwds['dpi']
        return

    def updateData(self):
        """Update data widgets"""

        if self.table is None:
            return
        df = self.table.model.df
        self.generalopts.update(df)
        return

    def clear(self):
        """Clear plot"""

        self.fig.clear()
        self.ax = None
        self.canvas.draw()
        self.table.plotted=None
        self.gridaxes = {}
        return

    def savePlot(self, filename=None):
        """Save the current plot"""

        ftypes = [('png','*.png'),('jpg','*.jpg'),('tif','*.tif'),('pdf','*.pdf'),
                    ('eps','*.eps'),('svg','*.svg')]
        if filename == None:
            filename, _ = QFileDialog.getSaveFileName(self,"Save Project",
                                              "","png files (*.png);;jpg files (*.jpg)")
        if filename:
            self.currentdir = os.path.dirname(os.path.abspath(filename))
            dpi = self.globalopts['dpi']
            self.fig.savefig(filename, dpi=dpi)
        return

    def showWarning(self, text='plot error', ax=None):
        """Show warning message in the plot window"""

        if ax==None:
            ax = self.fig.add_subplot(111)
        ax.clear()
        ax.text(.5, .5, text, transform=self.ax.transAxes,
                       horizontalalignment='center', color='blue', fontsize=16)
        self.canvas.draw()
        return

    def _initFigure(self):
        """Clear figure or add a new axis to existing layout"""

        from matplotlib.gridspec import GridSpec
        plot3d = self.generalopts.kwds['3D plot']
        if plot3d == 1:
            #self.canvas.close()
            #self.toolbar.close()
            #self.addPlotWidget()
            self.ax = self.fig.add_subplot(1, 1, 1, projection='3d',label='3d')
            self.ax.mouse_init()
            print (self.ax)
        else:
            #default layout is just a single axis
            self.fig.clear()
            self.gridaxes = {}
            self.ax = self.fig.add_subplot(111)

        return

    def plot2D(self, redraw=True):
        """Plot method for current data. Relies on pandas plot functionality
           if possible. There is some temporary code here to make sure only the valid
           plot options are passed for each plot kind."""

        if not hasattr(self, 'data'):
            return

        data = self.data
        #print (data)
        data.columns = self.checkColumnNames(data.columns)

        #get all options from the mpl options object
        kwds = self.generalopts.kwds
        axes_layout = kwds['axes_layout']
        lkwds = self.labelopts.kwds.copy()
        axkwds = self.axesopts.kwds

        kind = kwds['kind']
        by = kwds['by']
        by2 = kwds['by2']
        errorbars = kwds['errorbars']
        useindex = kwds['use_index']
        bw = kwds['bw']
        style = kwds['style']

        nrows = axkwds['rows']
        ncols = axkwds['cols']

        if self._checkNumeric(data) == False and kind != 'venn':
            self.showWarning('no numeric data to plot')
            return

        kwds['edgecolor'] = 'black'
        #valid kwd args for this plot type
        kwargs = dict((k, kwds[k]) for k in valid_kwds[kind] if k in kwds)

        ax = self.ax

        if by != '':
            #groupby needs to be handled per group so we can create the axes
            #for our figure and add them outside the pandas logic
            if by not in data.columns:
                self.showWarning('the grouping column must be in selected data')
                return
            if by2 != '' and by2 in data.columns:
                by = [by,by2]
            g = data.groupby(by)

            if axes_layout == 'multiple':
                i=1
                if len(g) > 30:
                    self.showWarning('%s is too many subplots' %len(g))
                    return
                size = len(g)
                if nrows == 0:
                    nrows = round(np.sqrt(size),0)
                    ncols = np.ceil(size/nrows)

                self.ax.set_visible(False)
                kwargs['subplots'] = None
                for n,df in g:
                    if ncols==1 and nrows==1:
                        ax = self.fig.add_subplot(111)
                        self.ax.set_visible(True)
                    else:
                        ax = self.fig.add_subplot(nrows,ncols,i)
                    kwargs['legend'] = False #remove axis legends
                    d = df.drop(by,1) #remove grouping columns
                    axs = self._doplot(d, ax, kind, 'single',  errorbars, useindex,
                                  bw=bw, yerr=None, nrows=0, ncols=0, kwargs=kwargs)
                    ax.set_title(n)
                    handles, labels = ax.get_legend_handles_labels()
                    i+=1

                if 'sharey' in kwargs and kwargs['sharey'] == True:
                    self.autoscale()
                if  'sharex' in kwargs and kwargs['sharex'] == True:
                    self.autoscale('x')
                self.fig.legend(handles, labels, loc='center right', #bbox_to_anchor=(0.9, 0),
                                 bbox_transform=self.fig.transFigure )
                axs = self.fig.get_axes()

            else:
                kwargs['subplots'] = 0
                #single plot grouped only apply to some plot kinds
                #the remainder are not supported
                axs = self.ax
                labels = []; handles=[]
                cmap = plt.cm.get_cmap(kwargs['colormap'])
                #handle as pivoted data for some line, bar
                data = data.apply( lambda x: pd.to_numeric(x,errors='ignore',downcast='float') )
                if kind in ['line','bar','barh']:
                    df = pd.pivot_table(data,index=by)
                    errs = data.groupby(by).std()
                    self._doplot(df, axs, kind, axes_layout, errorbars, useindex=None, yerr=errs,
                                      bw=bw, nrows=0, ncols=0, kwargs=kwargs)
                elif kind == 'scatter':
                    #we plot multiple groups and series in different colors
                    #this logic could be placed in the scatter method?
                    d = data.drop(by,1)
                    d = d._get_numeric_data()
                    xcol = d.columns[0]
                    ycols = d.columns[1:]
                    c=0
                    legnames = []
                    handles = []
                    slen = len(g)*len(ycols)
                    clrs = [cmap(float(i)/slen) for i in range(slen)]
                    for n, df in g:
                        for y in ycols:
                            kwargs['color'] = clrs[c]
                            currax, sc = self.scatter(df[[xcol,y]], ax=axs, **kwargs)
                            if type(n) is tuple:
                                n = ','.join(n)
                            legnames.append(','.join([n,y]))
                            handles.append(sc[0])
                            c+=1
                    if kwargs['legend'] == True:
                        if slen>6:
                            lc = int(np.round(slen/10))
                        else:
                            lc = 1
                        axs.legend([])
                        axs.legend(handles, legnames, ncol=lc)
                else:
                    self.showWarning('single grouped plots not supported for %s\n'
                                     'try using multiple subplots' %kind)
        else:
            #special case of twin axes
            if axes_layout == 'twin axes':
                ax = self.fig.add_subplot(111)
                if kind != 'line':
                    self.showWarning('twin axes only supported for line plots')
                lw = kwds['linewidth']
                bw = kwds['bw']
                marker = kwds['marker']
                ms = kwds['ms']
                ls = kwds['linestyle']
                if useindex == False:
                    data = data.set_index(data.columns[0])
                cols = list(data.columns)
                twinaxes = [ax]
                for i in range(len(cols)-1):
                    twinaxes.append(ax.twinx())

                styles = []
                cmap = plt.cm.get_cmap(kwds['colormap'])
                #cmap = util.adjustColorMap(cmap, 0.15,1.0)
                i=0
                handles=[]
                for col in cols:
                    d = data[col]
                    cax = twinaxes[i]
                    clr = cmap(float(i+1)/(len(cols)))
                    d.plot(ax=cax, kind='line', c=clr, style=styles, linewidth=lw,
                            linestyle=ls, marker=marker, ms=ms, legend=False)
                    if i>1:
                        cax.spines["right"].set_position(("axes", 1+i/20))
                    cax.set_ylabel(col)
                    handles.append(cax.get_lines()[0])
                    i+=1

                ax.legend(handles, cols, loc='best')
                self._setAxisTickFormat(ax)
                self.ax=axs=ax
            else:
                #default plot - mostly uses pandas so we directly call _doplot
                try:
                    axs = self._doplot(data, ax, kind, axes_layout, errorbars,
                                       useindex, bw=bw, yerr=None, nrows=nrows, ncols=ncols,
                                       kwargs=kwargs)
                except Exception as e:
                    self.showWarning(e)
                    logging.error("Exception occurred", exc_info=True)
                    return

        #set options general for all plot types
        #annotation optons are separate
        lkwds.update(kwds)
        self.setFigureOptions(axs, lkwds)
        scf = 12/lkwds['fontsize']
        try:
            self.fig.tight_layout()
            self.fig.subplots_adjust(top=0.9)
            if by != '':
                self.fig.subplots_adjust(right=0.9)
        except:
            self.fig.subplots_adjust(left=0.1, right=0.9, top=0.89,
                                     bottom=0.1, hspace=.4/scf, wspace=.2/scf)
            print ('tight_layout failed')

        #set axes formats
        self._setAxisRanges()
        if axes_layout == 'multiple':
            for ax in self.fig.axes:
                self._setAxisTickFormat(ax)
        else:
            self._setAxisTickFormat(self.ax)

        if style == 'dark_background':
            self.fig.set_facecolor('black')
        else:
            self.fig.set_facecolor('white')
        if redraw == True:
            self.canvas.draw()
        return

    def setFigureOptions(self, axs, kwds):
        """Set axis wide options such as ylabels, title"""

        if type(axs) is np.ndarray:
            self.ax = axs.flat[0]
        elif type(axs) is list:
            self.ax = axs[0]
        self.fig.suptitle(kwds['title'], fontsize=kwds['fontsize']*1.2)

        axes_layout = kwds['axes_layout']
        if axes_layout == 'multiple':
            for ax in self.fig.axes:
                self.setAxisLabels(ax, kwds)
        else:
            self.setAxisLabels(self.ax, kwds)
        return

    def setAxisLabels(self, ax, kwds):
        """Set a plots axis labels"""

        if kwds['xlabel'] != '':
            ax.set_xlabel(kwds['xlabel'])
        if kwds['ylabel'] != '':
            ax.set_ylabel(kwds['ylabel'])
        ax.xaxis.set_visible(kwds['showxlabels'])
        ax.yaxis.set_visible(kwds['showylabels'])
        #try:
        #    ax.tick_params(labelrotation=kwds['rot'])
        #except:
        #    logging.error("Exception occurred", exc_info=True)
        return

    def autoscale(self, axis='y'):
        """Set all subplots to limits of largest range"""

        l=None
        u=None
        for ax in self.fig.axes:
            if axis=='y':
                a, b  = ax.get_ylim()
            else:
                a, b  = ax.get_xlim()
            if l == None or a<l:
                l=a
            if u == None or b>u:
                u=b
        lims = (l, u)
        #print (lims)
        for a in self.fig.axes:
            if axis=='y':
                a.set_ylim(lims)
            else:
                a.set_xlim(lims)
        return

    def _clearArgs(self, kwargs):
        """Clear kwargs of formatting options so that a style can be used"""

        keys = ['colormap','grid']
        for k in keys:
            if k in kwargs:
                kwargs[k] = None
        return kwargs

    def _doplot(self, data, ax, kind, axes_layout, errorbars, useindex, bw, yerr,
                nrows, ncols, kwargs):
        """Core plotting method where the individual plot functions are called"""

        kwargs = kwargs.copy()
        kwargs['alpha'] = kwargs['alpha']/10

        cols = data.columns
        if kind == 'line':
            data = data.sort_index()

        #calculate required rows
        rows = int(round(np.sqrt(len(data.columns)),0))
        if len(data.columns) == 1 and kind not in ['pie']:
            kwargs['subplots'] = 0
        #print (kwargs)
        if 'colormap' in kwargs:
            cmap = plt.cm.get_cmap(kwargs['colormap'])
        else:
            cmap = None
        #change some things if we are plotting in b&w
        styles = []
        if bw == True and kind not in ['pie','heatmap']:
            cmap = None
            kwargs['color'] = 'k'
            kwargs['colormap'] = None
            styles = ["-","--","-.",":"]
            if 'linestyle' in kwargs:
                del kwargs['linestyle']

        if axes_layout == 'single':
            layout = None
        elif nrows != 0:
            #override automatic rows/cols with widget options
            layout = (nrows,ncols)
            kwargs['subplots'] = 1
        else:
            layout = (rows,-1)
            kwargs['subplots'] = 1

        if errorbars == True and yerr == None:
            yerr = data[data.columns[1::2]]
            data = data[data.columns[0::2]]
            yerr.columns = data.columns
            plt.rcParams['errorbar.capsize']=4

        if kind == 'bar' or kind == 'barh':
            if len(data) > 50:
                ax.get_xaxis().set_visible(False)
            if len(data) > 300:
                self.showWarning('too many bars to plot')
                return
        if kind == 'scatter':
            axs, sc = self.scatter(data, ax, axes_layout, **kwargs)
            if kwargs['sharey'] == 1:
                lims = self.fig.axes[0].get_ylim()
                for a in self.fig.axes:
                    a.set_ylim(lims)
        elif kind == 'boxplot':
            axs = data.boxplot(ax=ax, grid=kwargs['grid'],
                               patch_artist=True, return_type='dict')
            lw = kwargs['linewidth']
            plt.setp(axs['boxes'], color='black', lw=lw)
            plt.setp(axs['whiskers'], color='black', lw=lw)
            plt.setp(axs['fliers'], color='black', marker='+', lw=lw)
            clr = cmap(0.5)
            for patch in axs['boxes']:
                patch.set_facecolor(clr)
            if kwargs['logy'] == 1:
                ax.set_yscale('log')
        elif kind == 'violinplot':
            axs = self.violinplot(data, ax, kwargs)
        elif kind == 'dotplot':
            axs = self.dotplot(data, ax, kwargs)

        elif kind == 'histogram':
            #bins = int(kwargs['bins'])
            axs = data.plot(kind='hist',layout=layout, ax=ax, **kwargs)
        elif kind == 'heatmap':
            if len(data) > 1000:
                self.showWarning('too many rows to plot')
                return
            axs = self.heatmap(data, ax, kwargs)
        elif kind == 'bootstrap':
            axs = plotting.bootstrap_plot(data)
        elif kind == 'scatter_matrix':
            axs = plotting.scatter_matrix(data, ax=ax, **kwargs)
        elif kind == 'hexbin':
            x = cols[0]
            y = cols[1]
            axs = data.plot(x,y,ax=ax,kind='hexbin',gridsize=20,**kwargs)
        elif kind == 'contour':
            xi,yi,zi = self.contourData(data)
            cs = ax.contour(xi,yi,zi,15,linewidths=.5,colors='k')
            #plt.clabel(cs,fontsize=9)
            cs = ax.contourf(xi,yi,zi,15,cmap=cmap)
            self.fig.colorbar(cs,ax=ax)
            axs = ax
        elif kind == 'imshow':
            xi,yi,zi = self.contourData(data)
            im = ax.imshow(zi, interpolation="nearest",
                           cmap=cmap, alpha=kwargs['alpha'])
            self.fig.colorbar(im,ax=ax)
            axs = ax
        elif kind == 'pie':
            if useindex == False:
                x=data.columns[0]
                data.set_index(x,inplace=True)
            if kwargs['legend'] == True:
                lbls=None
            else:
                lbls = list(data.index)

            axs = data.plot(ax=ax,kind='pie', labels=lbls, layout=layout,
                            autopct='%1.1f%%', subplots=True, **kwargs)
            if lbls == None:
                axs[0].legend(labels=data.index, loc='best')
        elif kind == 'venn':
            axs = self.venn(data, ax, **kwargs)
        elif kind == 'radviz':
            if kwargs['marker'] == '':
                kwargs['marker'] = 'o'
            col = data.columns[-1]
            axs = pd.plotting.radviz(data, col, ax=ax, **kwargs)
        else:
            #line, bar and area plots
            if useindex == False:
                x=data.columns[0]
                data.set_index(x,inplace=True)
            if len(data.columns) == 0:
                msg = "Not enough data.\nIf 'use index' is off select at least 2 columns"
                self.showWarning(msg)
                return
            #adjust colormap to avoid white lines
            if cmap != None:
                cmap = util.adjustColorMap(cmap, 0.15,1.0)
                del kwargs['colormap']
            if kind == 'barh':
                kwargs['xerr']=yerr
                yerr=None

            axs = data.plot(ax=ax, layout=layout, yerr=yerr, style=styles, cmap=cmap,
                             **kwargs)
        return axs

    def setStyle(self):

        if self.style == None:
            mpl.rcParams.update(mpl.rcParamsDefault)
        else:
            plt.style.use(self.style)
        return

    def _setAxisRanges(self):

        kwds = self.axesopts.kwds
        ax = self.ax
        try:
            xmin=float(kwds['xmin'])
            xmax=float(kwds['xmax'])
            ax.set_xlim((xmin,xmax))
        except:
            pass
        try:
            ymin=float(kwds['ymin'])
            ymax=float(kwds['ymax'])
            ax.set_ylim((ymin,ymax))
        except:
            pass
        return

    def _setAxisTickFormat(self, ax):
        """Set axis tick format"""

        import matplotlib.ticker as mticker
        import matplotlib.dates as mdates
        kwds = self.axesopts.kwds
        #ax = self.ax
        data = self.data
        cols = list(data.columns)
        x = data[cols[0]]
        xt = kwds['major x-ticks']
        yt = kwds['major y-ticks']
        xmt = kwds['minor x-ticks']
        ymt = kwds['minor y-ticks']
        symbol = kwds['symbol']
        places = kwds['precision']
        dateformat = kwds['date format']

        if xt != 0:
            ax.xaxis.set_major_locator(mticker.MaxNLocator(nbins=xt))
        if yt != 0:
            ax.yaxis.set_major_locator(mticker.MaxNLocator(nbins=yt))
        if xmt != 0:
            ax.xaxis.set_minor_locator(mticker.AutoMinorLocator(n=xmt))
            ax.grid(b=True, which='minor', linestyle='--', linewidth=.5)
        if ymt != 0:
            ax.yaxis.set_minor_locator(mticker.AutoMinorLocator(n=ymt))
            ax.grid(b=True, which='minor', linestyle='--', linewidth=.5)
        formatter = kwds['formatter']
        if formatter == 'percent':
            ax.xaxis.set_major_formatter(mticker.PercentFormatter())
        elif formatter == 'eng':
            ax.xaxis.set_major_formatter(mticker.EngFormatter(unit=symbol,places=places))
        elif formatter == 'sci notation':
            ax.xaxis.set_major_formatter(mticker.LogFormatterSciNotation())
        elif formatter == 'date':
            locator = mdates.AutoDateLocator(minticks=4, maxticks=10)
            formatter = mdates.ConciseDateFormatter(locator)
            ax.xaxis.set_major_locator(locator)
            ax.xaxis.set_major_formatter(formatter)
        if dateformat != '':
            ax.xaxis.set_major_formatter(mdates.DateFormatter(dateformat))
        return

    def scatter(self, df, ax, axes_layout='single', alpha=0.8, marker='o', color=None, **kwds):
        """A custom scatter plot rather than the pandas one. By default this
        plots the first column selected versus the others"""

        if len(df.columns)<2:
            return
        data = df
        df = df.copy()._get_numeric_data()
        cols = list(df.columns)
        x = df[cols[0]]
        s=1
        cmap = plt.cm.get_cmap(kwds['colormap'])
        lw = kwds['linewidth']
        clrcol = kwds['clrcol']  #color by values in a column
        cscale = kwds['cscale']
        grid = kwds['grid']
        bw = kwds['bw']

        if cscale == 'log':
            norm = mpl.colors.LogNorm()
        else:
            norm = None
        if color != None:
            c = color
        elif clrcol != '':
            if clrcol in df.columns:
                if len(cols)>2:
                    cols.remove(clrcol)
            c = data[clrcol]
            if c.dtype.kind not in 'bifc':
                c = pd.factorize(c)[0]
        else:
            c = None
        plots = len(cols)
        if marker == '':
            marker = 'o'
        if axes_layout == 'multiple':
            size = plots-1
            nrows = round(np.sqrt(size),0)
            ncols = np.ceil(size/nrows)
            self.fig.clear()
        if c is not None:
            colormap = kwds['colormap']
        else:
            colormap = None
            c=None

        #print (kwds)
        labelcol = kwds['labelcol']
        pointsizes = kwds['pointsizes']
        handles = []
        for i in range(s,plots):
            y = df[cols[i]]
            ec = 'black'
            if bw == True:
                clr = 'white'
                colormap = None
            else:
                clr = cmap(float(i)/(plots))
            if colormap != None:
                clr=None
            if marker in ['x','+'] and bw == False:
                ec = clr

            if kwds['logx'] == 1:
                ax.set_xscale('log')
            if kwds['logy'] == 1:
                ax.set_yscale('log')

            if axes_layout == 'multiple':
                ax = self.fig.add_subplot(nrows,ncols,i)
            if pointsizes != '' and pointsizes in df.columns:
                ms = df[pointsizes]
                s=kwds['ms']
                getsizes = lambda x : (((x-x.min())/float(x.max()-x.min())+1)*s)**2.3
                ms = getsizes(ms)
                #print (ms)
            else:
                ms = kwds['ms'] * 12
            sc = ax.scatter(x, y, marker=marker, alpha=alpha, linewidth=lw, c=c,
                       s=ms, edgecolors=ec, facecolor=clr, cmap=colormap,
                       norm=norm, label=cols[i], picker=True)

            #create proxy artist for markers so we can return these handles if needed
            mkr = Line2D([0], [0], marker=marker, alpha=alpha, ms=10, markerfacecolor=c,
                        markeredgewidth=lw, markeredgecolor=ec, linewidth=0)
            handles.append(mkr)
            ax.set_xlabel(cols[0])
            if grid == 1:
                ax.grid(True)
            if axes_layout == 'multiple':
                ax.set_title(cols[i])
            if colormap is not None and kwds['colorbar'] == True:
                self.fig.colorbar(scplt, ax=ax)

            if labelcol != '':
                if not labelcol in data.columns:
                    self.showWarning('label column %s not in selected data' %labelcol)
                elif len(data)<1500:
                    for i, r in data.iterrows():
                        txt = r[labelcol]
                        if pd.isnull(txt) is True:
                            continue
                        ax.annotate(txt, (x[i],y[i]), xycoords='data',
                                    xytext=(5, 5), textcoords='offset points',)

        if kwds['legend'] == 1 and axes_layout == 'single':
            ax.legend(cols[1:])

        return ax, handles

    def violinplot(self, df, ax, kwds):
        """violin plot"""

        data=[]
        clrs=[]
        df = df._get_numeric_data()
        cols = len(df.columns)
        cmap = plt.cm.get_cmap(kwds['colormap'])
        for i,d in enumerate(df):
            clrs.append(cmap(float(i)/cols))
            data.append(df[d].values)
        lw = kwds['linewidth']
        alpha = kwds['alpha']
        parts = ax.violinplot(data, showextrema=False, showmeans=True)
        i=0
        for pc in parts['bodies']:
            pc.set_facecolor(clrs[i])
            pc.set_edgecolor('black')
            pc.set_alpha(alpha)
            pc.set_linewidth(lw)
            i+=1
        labels = df.columns
        ax.set_xticks(np.arange(1, len(labels) + 1))
        ax.set_xticklabels(labels)
        return

    def dotplot(self, df, ax, kwds):
        """Dot plot"""

        marker = kwds['marker']
        if marker == '':
            marker = 'o'
        cmap = plt.cm.get_cmap(kwds['colormap'])
        ms = kwds['ms']
        lw = kwds['linewidth']
        alpha = kwds['alpha']
        cols = len(df.columns)
        axs = df.boxplot(ax=ax, grid=False, return_type='dict')
        plt.setp(axs['boxes'], color='white')
        plt.setp(axs['whiskers'], color='white')
        plt.setp(axs['caps'], color='black', lw=lw)
        plt.setp(axs['medians'], color='black', lw=lw)
        np.random.seed(42)
        for i,d in enumerate(df):
            clr = cmap(float(i)/cols)
            y = df[d]
            x = np.random.normal(i+1, 0.04, len(y))
            ax.plot(x, y, c=clr, mec='k', ms=ms, marker=marker, alpha=alpha,
                    mew=lw, linestyle="None")
        if kwds['logy'] == 1:
            ax.set_yscale('log')
        return ax

    def heatmap(self, df, ax, kwds):
        """Plot heatmap"""

        X = df._get_numeric_data()
        clr='black'
        lw = kwds['linewidth']
        if lw==0:
            clr=None
            lw=None
        if kwds['cscale']=='log':
            norm=mpl.colors.LogNorm()
        else:
            norm=None
        hm = ax.pcolor(X, cmap=kwds['colormap'], edgecolor=clr,
                       linewidth=lw,alpha=kwds['alpha'],norm=norm)
        if kwds['colorbar'] == True:
            self.fig.colorbar(hm, ax=ax)
        ax.set_xticks(np.arange(0.5, len(X.columns)))
        ax.set_yticks(np.arange(0.5, len(X.index)))
        ax.set_xticklabels(X.columns, minor=False)
        ax.set_yticklabels(X.index, minor=False)
        ax.set_ylim(0, len(X.index))
        ##if kwds['rot'] != 0:
        #    for tick in ax.get_xticklabels():
        #        tick.set_rotation(kwds['rot'])
        #from mpl_toolkits.axes_grid1 import make_axes_locatable
        #divider = make_axes_locatable(ax)
        return

    def venn(self, data, ax, colormap=None, alpha=0.8):
        """Plot venn diagram, requires matplotlb-venn"""

        try:
            from matplotlib_venn import venn2,venn3
        except:
            self.showWarning('requires matplotlib_venn')
            return
        l = len(data.columns)
        if l<2: return
        x = data.values[:,0]
        y = data.values[:,1]
        if l==2:
            labels = list(data.columns[:2])
            v = venn2([set(x), set(y)], set_labels=labels, ax=ax)
        else:
            labels = list(data.columns[:3])
            z = data.values[:,2]
            v = venn3([set(x), set(y), set(z)], set_labels=labels, ax=ax)
        ax.axis('off')
        ax.set_axis_off()
        return ax

    def contourData(self, data):
        """Get data for contour plot"""

        x = data.values[:,0]
        y = data.values[:,1]
        z = data.values[:,2]
        xi = np.linspace(x.min(), x.max())
        yi = np.linspace(y.min(), y.max())
        zi = griddata(x, y, z, xi, yi, interp='linear')
        return xi,yi,zi

    def meshData(self, x,y,z):
        """Prepare 1D data for plotting in the form (x,y)->Z"""

        xi = np.linspace(x.min(), x.max())
        yi = np.linspace(y.min(), y.max())
        zi = griddata(x, y, z, xi, yi, interp='linear')
        X, Y = np.meshgrid(xi, yi)
        return X,Y,zi

    def getcmap(self, name):
        try:
            return plt.cm.get_cmap(name)
        except:
            return plt.cm.get_cmap('Spectral')

    def getView(self):
        ax = self.ax
        if hasattr(ax,'azim'):
            azm=ax.azim
            ele=ax.elev
            dst=ax.dist
        else:
            return None,None,None
        return azm,ele,dst

    def plot3D(self, redraw=True):
        """3D plot"""

        if not hasattr(self, 'data') or len(self.data.columns)<3:
            return
        kwds = self.generalopts.kwds.copy()
        #use base options by joining the dicts
        #kwds.update(self.mplopts3d.kwds)
        kwds.update(self.labelopts.kwds)
        #print (kwds)
        data = self.data
        x = data.values[:,0]
        y = data.values[:,1]
        z = data.values[:,2]
        azm,ele,dst = self.getView()

        #self.fig.clear()
        ax = self.ax# = Axes3D(self.fig)
        kind = kwds['kind']
        #mode = kwds['mode']
        #rstride = kwds['rstride']
        #cstride = kwds['cstride']
        lw = kwds['linewidth']
        alpha = kwds['alpha']
        cmap = kwds['colormap']

        if kind == 'scatter':
            self.scatter3D(data, ax, kwds)
        elif kind == 'bar':
            self.bar3D(data, ax, kwds)
        elif kind == 'contour':
            from scipy.interpolate import griddata
            xi = np.linspace(x.min(), x.max())
            yi = np.linspace(y.min(), y.max())
            zi = griddata((x, y), z, (xi[None,:], yi[:,None]), method='cubic')
            surf = ax.contour(xi, yi, zi, rstride=rstride, cstride=cstride,
                              cmap=kwds['colormap'], alpha=alpha,
                              linewidth=lw, antialiased=True)
        elif kind == 'wireframe':
            if mode == '(x,y)->z':
                X,Y,zi = self.meshData(x,y,z)
            else:
                X,Y,zi = x,y,z
            w = ax.plot_wireframe(X, Y, zi, rstride=rstride, cstride=cstride,
                                  linewidth=lw)
        elif kind == 'surface':
            X,Y,zi = self.meshData(x,y,z)
            surf = ax.plot_surface(X, Y, zi, rstride=rstride, cstride=cstride,
                                   cmap=cmap, alpha=alpha,
                                   linewidth=lw)
            cb = self.fig.colorbar(surf, shrink=0.5, aspect=5)
            surf.set_clim(vmin=zi.min(), vmax=zi.max())
        #if kwds['points'] == True:
        #    self.scatter3D(data, ax, kwds)

        self.setFigureOptions(ax, kwds)
        if azm!=None:
            self.ax.azim = azm
            self.ax.elev = ele
            self.ax.dist = dst
        #handles, labels = self.ax.get_legend_handles_labels()
        #self.fig.legend(handles, labels)
        self.canvas.draw()
        return

    def bar3D(self, data, ax, kwds):
        """3D bar plot"""

        i=0
        plots=len(data.columns)
        cmap = plt.cm.get_cmap(kwds['colormap'])
        for c in data.columns:
            h = data[c]
            c = cmap(float(i)/(plots))
            ax.bar(data.index, h, zs=i, zdir='y', color=c)
            i+=1

    def scatter3D(self, data, ax, kwds):
        """3D scatter plot"""

        def doscatter(data, ax, color=None, pointlabels=None):
            data = data._get_numeric_data()
            l = len(data.columns)
            if l<3: return

            X = data.values
            x = X[:,0]
            y = X[:,1]
            handles=[]
            labels=data.columns[2:]
            for i in range(2,l):
                z = X[:,i]
                if color == None:
                    c = cmap(float(i)/(l))
                else:
                    c = color
                c='blue'
                h=ax.scatter(x, y, z, edgecolor='black', linewidth=lw, facecolor=c,
                           alpha=alpha, marker=marker, s=ms)
                handles.append(h)
            if pointlabels is not None:
                trans_offset = mtrans.offset_copy(ax.transData, fig=self.fig,
                                  x=0.05, y=0.10, units='inches')
                for i in zip(x,y,z,pointlabels):
                    txt=i[3]
                    ax.text(i[0],i[1],i[2], txt, None,
                    transform=trans_offset)

            return handles,labels

        lw = kwds['linewidth']
        alpha = kwds['alpha']/10
        ms = kwds['ms']*6
        marker = kwds['marker']
        if marker=='':
            marker='o'
        by = kwds['by']
        legend = kwds['legend']
        cmap = self.getcmap(kwds['colormap'])
        labelcol = kwds['labelcol']
        handles=[]
        pl=None
        if by != '':
            if by not in data.columns:
                self.showWarning('grouping column not in selection')
                return
            g = data.groupby(by)
            i=0
            pl=None
            for n,df in g:
                c = cmap(float(i)/(len(g)))
                if labelcol != '':
                    pl = df[labelcol]
                h,l = doscatter(df, ax, color=c, pointlabels=pl)
                handles.append(h[0])
                i+=1
            self.fig.legend(handles, g.groups)

        else:
            if labelcol != '':
                pl = data[labelcol]
            handles,lbls=doscatter(data, ax, pointlabels=pl)
            self.fig.legend(handles, lbls)
        return

    def checkColumnNames(self, cols):
        """Check length of column names"""

        from textwrap import fill
        try:
            cols = [fill(l, 25) for l in cols]
        except:
            logging.error("Exception occurred", exc_info=True)
        return cols

    def _checkNumeric(self, df):
        """Get only numeric data that can be plotted"""

        x = df.apply( lambda x: pd.to_numeric(x,errors='ignore',downcast='float') )
        if x.empty == True:
            return False


def addFigure(parent, figure=None, resize_callback=None):
    """Create a tk figure and canvas in the parent frame"""

    if figure == None:
        figure = Figure(figsize=(8,4), dpi=100, facecolor='white')

    canvas = FigureCanvas(figure=figure)
    canvas.setSizePolicy( QSizePolicy.Expanding,
                          QSizePolicy.Expanding)
    canvas.updateGeometry()
    return figure, canvas


class BaseOptions(object):
    """Class to generate widget dialog for dict of options"""
    def __init__(self, parent=None):
        """Setup variables"""

        self.parent = parent
        #df = self.parent.table.model.df
        return

    def applyOptions(self):
        """Set the plot kwd arguments from the widgets"""

        self.kwds = get_widget_values(self.widgets)
        return

    def apply(self):
        self.applyOptions()
        if self.callback != None:
            self.callback()
        return

    def showDialog(self, parent, wrap=2, section_wrap=2, style=None):
        """Auto create widgets for corresponding options and
           and return the dialog.
          Args:
            parent: parent frame
            wrap: wrap for internal widgets
        """

        dialog, self.widgets = dialog_from_options(parent, self.opts, self.groups, wrap=wrap, section_wrap=section_wrap,
                                                   style=style)
        return dialog

    def setWidgetValue(self, key, value):

        setWidgetValues(self.widgets, {key: value})
        self.applyOptions()
        return

    def updateWidgets(self, kwds):

        for k in kwds:
            setWidgetValues(self.widgets, {k: kwds[k]})
        return

    def increment(self, key, inc):
        """Increase the value of a widget"""

        new = self.kwds[key]+inc
        self.setWidgetValue(key, new)
        return

class GlobalOptions(BaseOptions):
    """Class to provide a dialog for global plot options"""

    def __init__(self, parent=None):
        """Setup variables"""

        self.parent = parent
        self.groups = {'global': ['dpi','3D plot']}
        self.opts = OrderedDict({ 'dpi': {'type':'spinbox','default':100,'width':4},
                                 #'grid layout': {'type':'checkbox','default':0,'label':'grid layout'},
                                 '3D plot': {'type':'checkbox','default':0,'label':'3D plot'}  })
        self.kwds = {}
        return

class MPLBaseOptions(BaseOptions):
    """Class to provide a dialog for matplotlib options and returning
        the selected prefs"""

    kinds = ['line', 'scatter', 'bar', 'barh', 'pie', 'histogram', 'boxplot', 'violinplot', 'dotplot',
             'heatmap', 'area', 'hexbin', 'contour', 'imshow', 'scatter_matrix', 'density', 'radviz', 'venn']
    legendlocs = ['best','upper right','upper left','lower left','lower right','right','center left',
                'center right','lower center','upper center','center']

    def __init__(self, parent=None):
        """Setup variables"""

        self.parent = parent
        if self.parent is not None:
            df = self.parent.table.model.df
            datacols = list(df.columns)
            datacols.insert(0,'')
        else:
            datacols=[]

        layouts = ['single','multiple','twin axes']
        scales = ['linear','log']
        style_list = ['default', 'classic'] + sorted(
                    style for style in plt.style.available if style != 'classic')
        grps = {'data':['by','by2','labelcol','pointsizes'],
                'formats':['marker','ms','linestyle','linewidth','alpha'],
                'global':['dpi','3D plot'],
                'general':['kind','axes_layout','bins','stacked','use_index','errorbars'],
                'axes':['grid','legend','showxlabels','showylabels','sharex','sharey','logx','logy'],
                'colors':['style','colormap','bw','clrcol','cscale','colorbar']}
        order = ['general','data','axes','formats','colors','global']
        self.groups = OrderedDict((key, grps[key]) for key in order)
        opts = self.opts = {
                'style':{'type':'combobox','default':'default','items': style_list},
                'marker':{'type':'combobox','default':'','items': markers},
                'linestyle':{'type':'combobox','default':'-','items': linestyles},
                'ms':{'type':'slider','default':5,'range':(1,80),'interval':1,'label':'marker size'},
                'grid':{'type':'checkbox','default':0,'label':'show grid'},
                'logx':{'type':'checkbox','default':0,'label':'log x'},
                'logy':{'type':'checkbox','default':0,'label':'log y'},
                'use_index':{'type':'checkbox','default':1,'label':'use index'},
                'errorbars':{'type':'checkbox','default':0,'label':'errorbar column'},
                'clrcol':{'type':'combobox','items':datacols,'label':'color by value','default':''},
                'cscale':{'type':'combobox','items':scales,'label':'color scale','default':'linear'},
                'colorbar':{'type':'checkbox','default':0,'label':'show colorbar'},
                'bw':{'type':'checkbox','default':0,'label':'black & white'},
                'showxlabels':{'type':'checkbox','default':1,'label':'x tick labels'},
                'showylabels':{'type':'checkbox','default':1,'label':'y tick labels'},
                'sharex':{'type':'checkbox','default':0,'label':'share x'},
                'sharey':{'type':'checkbox','default':0,'label':'share y'},
                'legend':{'type':'checkbox','default':1,'label':'legend'},
                #'loc':{'type':'combobox','default':'best','items':self.legendlocs,'label':'legend loc'},
                'kind':{'type':'combobox','default':'line','items':self.kinds,'label':'plot type'},
                'stacked':{'type':'checkbox','default':0,'label':'stacked'},
                'linewidth':{'type':'slider','default':2,'range':(0,10),'interval':1,'label':'line width'},
                'alpha':{'type':'spinbox','default':9,'range':(1,10),'interval':1,'label':'alpha'},
                #'subplots':{'type':'checkbox','default':0,'label':'multiple subplots'},
                'axes_layout':{'type':'combobox','default':'single','items':layouts,'label':'axes layout'},
                'colormap':{'type':'combobox','default':'Spectral','items':colormaps},
                'bins':{'type':'spinbox','default':20,'width':5},
                'by':{'type':'combobox','items':datacols,'label':'group by','default':''},
                'by2':{'type':'combobox','items':datacols,'label':'group by 2','default':''},
                'labelcol':{'type':'combobox','items':datacols,'label':'point labels','default':''},
                'pointsizes':{'type':'combobox','items':datacols,'label':'point sizes','default':''},
                 'dpi': {'type':'spinbox','default':100,'width':4,'range':(10,300)},
                 '3D plot': {'type':'checkbox','default':0,'label':'3D plot'}
                }
        self.kwds = {}
        return

    def update(self, df):
        """Update data widget(s) when dataframe changes"""

        if util.check_multiindex(df.columns) == 1:
            cols = list(df.columns.get_level_values(0))
        else:
            cols = list(df.columns)
        #add empty value
        cols = ['']+cols
        for name in ['by','by2','labelcol','clrcol']:
            self.widgets[name].clear()
            self.widgets[name].addItems(cols)
        return

class AnnotationOptions(BaseOptions):
    """This class also provides custom tools for adding items to the plot"""
    def __init__(self, parent=None):
        """Setup variables"""

        from matplotlib import colors
        import six
        colors = list(six.iteritems(colors.cnames))
        colors = sorted([c[0] for c in colors])
        fillpatterns = ['-', '+', 'x', '\\', '*', 'o', 'O', '.']
        bstyles = ['square','round','round4','circle','rarrow','larrow','sawtooth']
        fonts = util.getFonts()
        defaultfont = 'Arial'
        fontweights = ['normal','bold','heavy','light','ultrabold','ultralight']
        alignments = ['left','center','right']

        self.parent = parent
        self.groups = grps = {'global labels':['title','xlabel','ylabel','rot'],
                             'format': ['font','fontsize','fontweight','align'],
                             # 'textbox': ['boxstyle','facecolor','linecolor','rotate'],
                             # 'text to add': ['text']
                             }
        self.groups = OrderedDict(sorted(grps.items()))
        opts = self.opts = {
                'title':{'type':'textarea','default':'','width':30},
                'xlabel':{'type':'entry','default':'','width':20},
                'ylabel':{'type':'entry','default':'','width':20},
                'facecolor':{'type':'combobox','default':'white','items': colors},
                'linecolor':{'type':'combobox','default':'black','items': colors},
                'fill':{'type':'combobox','default':'-','items': fillpatterns},
                'rotate':{'type':'scale','default':0,'range':(-180,180),'interval':1,'label':'rotate'},
                'boxstyle':{'type':'combobox','default':'square','items': bstyles},
                'text':{'type':'scrolledtext','default':'','width':20},
                'align':{'type':'combobox','default':'center','items': alignments},
                'font':{'type':'combobox','default':defaultfont,'items':fonts},
                'fontsize':{'type':'spinbox','default':12,'range':(4,50),'label':'font size'},
                'fontweight':{'type':'combobox','default':'normal','items': fontweights},
                'rot':{'type':'entry','default':0, 'label':'ticklabel angle'}
                }
        self.kwds = {}
        #used to store annotations
        self.textboxes = {}
        return

    def applyOptions(self):
        """Set the plot kwd arguments from the tk variables"""

        BaseOptions.applyOptions(self)
        from matplotlib.font_manager import FontProperties
        size = self.kwds['fontsize']
        #font = FontProperties()
        #font.set_family(self.kwds['font'])

        plt.rc("font", family=self.kwds['font'], size=size)#, weight=self.kwds['fontweight'])
        plt.rc('legend', fontsize=size-1)
        return

class AxesOptions(BaseOptions):
    """Class for additional formatting options like styles"""
    def __init__(self, parent=None):
        """Setup variables"""

        self.parent = parent
        self.styles = sorted(plt.style.available)
        formats = ['auto','date','percent','eng','sci notation']
        datefmts = ['','%d','%b %d,''%Y-%m-%d','%d-%m-%Y',"%d-%m-%Y %H:%M"]
        self.groups = grps = OrderedDict({'layout':['rows','cols'],
                              'axis ranges':['xmin','xmax','ymin','ymax'],
                              'axis tick positions':['major x-ticks','major y-ticks',
                                                   'minor x-ticks','minor y-ticks'],
                              'tick label format':['formatter','date format','symbol','precision'],
                             })
        opts = self.opts = {'rows':{'type':'spinbox','default':0},
                            'cols':{'type':'spinbox','default':0},
                            'xmin':{'type':'entry','default':'','label':'x min'},
                            'xmax':{'type':'entry','default':'','label':'x max'},
                            'ymin':{'type':'entry','default':'','label':'y min'},
                            'ymax':{'type':'entry','default':'','label':'y max'},
                            'major x-ticks':{'type':'spinbox','default':0},
                            'major y-ticks':{'type':'spinbox','default':0},
                            'minor x-ticks':{'type':'spinbox','default':0},
                            'minor y-ticks':{'type':'spinbox','default':0},
                            'formatter':{'type':'combobox','items':formats,'default':'auto'},
                            'symbol':{'type':'entry','default':''},
                            'precision':{'type':'entry','default':0},
                            'date format':{'type':'combobox','items':datefmts,'default':''}
                            }
        self.kwds = {}
        return

class PlotGallery(QWidget):
    """Plot gallery class"""
    def __init__(self, parent=None):
        super(PlotGallery, self).__init__(parent)
        self.parent = parent
        self.setMinimumSize(400,300)
        self.setGeometry(QtCore.QRect(300, 200, 800, 600))
        self.setWindowTitle("Saved Figures")
        self.createWidgets()
        sizepolicy = QSizePolicy()
        self.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))
        self.plots = {}
        return

    def createWidgets(self):
        """Create widgets. Plot on left and dock for tools on right."""

        self.main = QTabWidget(self)
        self.main.setTabsClosable(True)
        self.main.tabCloseRequested.connect(lambda index: self.remove(index))
        layout = QVBoxLayout(self)
        toolbar = QToolBar("toolbar")
        layout.addWidget(toolbar)
        items = { 'save': {'action':self.save,'file':'save'},
                  'save all': {'action':self.saveAll,'file':'save-all'},
                  'clear': {'action':self.clear,'file':'clear'}
                    }
        for i in items:
            if 'file' in items[i]:
                iconfile = os.path.join(iconpath,items[i]['file']+'.png')
                icon = QIcon(iconfile)
            else:
                icon = QIcon.fromTheme(items[i]['icon'])
            btn = QAction(icon, i, self)
            btn.triggered.connect(items[i]['action'])
            toolbar.addAction(btn)
        layout.addWidget(self.main)
        return

    def update(self, plots):
        """Display a dict of stored mpl figures"""

        self.main.clear()
        for name in plots:
            fig = plots[name]
            #fig.savefig(name+'.png')
            pw = PlotWidget(self.main)
            self.main.addTab(pw, name)
            pw.figure = fig
            pw.draw()
            plt.tight_layout()
        self.plots = plots
        return

    def remove(self, idx):
        """Remove selected tab and figure"""

        index = self.main.currentIndex()
        name = self.main.tabText(index)
        del self.plots[name]
        self.main.removeTab(index)
        return

    def save(self):
        """Save selected figure"""

        index = self.main.currentIndex()
        name = self.main.tabText(index)
        suff = "PNG files (*.png);;JPG files (*.jpg);;PDF files (*.pdf);;All files (*.*)"
        filename, _ = QFileDialog.getSaveFileName(self, "Save Figure", name, suff)
        if not filename:
            return

        fig = self.plots[name]
        fig.savefig(filename+'.png', dpi=100)
        return

    def saveAll(self):
        """Save all figures in a folder"""

        dir =  QFileDialog.getExistingDirectory(self, "Save Folder",
                                             homepath, QFileDialog.ShowDirsOnly)
        if not dir:
            return
        for name in self.plots:
            fig = self.plots[name]
            fig.savefig(os.path.join(dir,name+'.png'), dpi=100)
        return

    def clear(self):
        """Clear plots"""

        self.plots.clear()
        self.main.clear()
        return
