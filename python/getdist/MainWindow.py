# -*- coding: utf-8 -*-

import os
import sys
import signal
import logging
import GetDistPlots
import matplotlib
import numpy as np
from iniFile import iniFile
from getdist import MCSamples
from sys import platform

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar

try:
    import PySide
    from PySide.QtCore import *
    from PySide.QtGui  import *
    os.environ['QT_API'] = 'pyside'
    matplotlib.rcParams['backend.qt4'] = 'PySide'
    try:
        import Resources_pyside
    except ImportError:
        print "Missing Resources_pyside.py: Run script update_resources.sh"
except ImportError:
    print "Can't import PySide modules, please install PySide first."
    sys.exit()

import batchJob
import makeGrid
# ==============================================================================

class ParamListWidget(QListWidget):
    def __init__(self, widget, owner):
        QListWidget.__init__(self, widget)
        self.setDragDropMode(self.InternalMove)
        self.setMaximumSize(QSize(16777215, 120))
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setDragEnabled(True)
        self.viewport().setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.owner = owner
        list_model = self.model()
        list_model.layoutChanged.connect(owner._updateParameters)


class MainWindow(QMainWindow):

    def __init__(self, app, ini=None, base_dir=None):
        """
        Initialize of GUI components.
        """
        super(MainWindow, self).__init__()

        if base_dir is None: base_dir = batchJob.getCodeRootPath()
        os.chdir(base_dir)
        self.updating = False
        self.app = app
        self.base_dir = base_dir

        # GUI setup
        self.createWidgets()
        self.createActions()
        self.createMenus()
        self.createStatusBar()

        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle("GetDist GUI")

        # Allow to shutdown the GUI with Ctrl+C
        signal.signal(signal.SIGINT, signal.SIG_DFL)

        # Path for .ini file
        self.iniFile = ini or MCSamples.default_getdist_settings

        # Path of root directory
        self.rootdirname = None

        self.plot_module = 'GetDistPlots'

        self._resetGridData()
        self._resetPlotData()

        lastDir = self.getSettings().value('lastSearchDirectory')
        if lastDir:
            self.openDirectory(lastDir)

    def createActions(self):
        """
        Create Qt actions used in GUI.
        """
        self.exportAct = QAction(QIcon(":/images/file_export.png"),
                                 "&Export as PDF/Image", self,
                                 statusTip="Export image as PDF, PNG, JPG",
                                 triggered=self.export)

        self.scriptAct = QAction(QIcon(":/images/file_save.png"),
                                 "Save script", self,
                                 statusTip="Export commands to script",
                                 triggered=self.saveScript)

        self.reLoadAct = QAction("Re-load files", self,
                                 statusTip="Re-scan directory",
                                 triggered=self.reLoad)

        self.exitAct = QAction(QIcon(":/images/application_exit.png"),
                               "E&xit", self,
                               shortcut="Ctrl+Q",
                               statusTip="Exit application",
                               triggered=self.close)

        self.statsAct = QAction(QIcon(":/images/view_text.png"),
                               "Marge Stats", self,
                               shortcut="",
                               statusTip="Show Marge Stats",
                               triggered=self.showMargeStats)

        self.optionsAct = QAction(QIcon(""),
                               "Analysis settings", self,
                               shortcut="",
                               statusTip="Show settings for getdist and plots",
                               triggered=self.showSettings)

        self.aboutAct = QAction(QIcon(":/images/help_about.png"),
                                "&About", self,
                                statusTip="Show About box",
                                triggered=self.about)

    def createMenus(self):
        """
        Create Qt menus.
        """
        self.fileMenu = self.menuBar().addMenu("&File")
        self.fileMenu.addAction(self.exportAct)
        self.fileMenu.addAction(self.scriptAct)
        self.separatorAct = self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.reLoadAct)
        self.fileMenu.addAction(self.exitAct)

        self.menuBar().addSeparator()
        self.dataMenu = self.menuBar().addMenu("&Data")
        self.dataMenu.addAction(self.statsAct)

        self.menuBar().addSeparator()
        self.optionMenu = self.menuBar().addMenu("&Options")
        self.optionMenu.addAction(self.optionsAct)

        self.menuBar().addSeparator()

        self.helpMenu = self.menuBar().addMenu("&Help")
        self.helpMenu.addAction(self.aboutAct)

    def createStatusBar(self):
        """
        Create Qt status bar.
        """
        self.statusBar().showMessage("Ready", 2000)

    def createWidgets(self):
        """
        Create widgets.
        """
        self.centralWidget = QWidget(self)
        self.setCentralWidget(self.centralWidget)

        self.selectWidget = QWidget(self.centralWidget)
        self.lineEditDirectory = QLineEdit(self.selectWidget)
        self.lineEditDirectory.clear()
        self.lineEditDirectory.setReadOnly(True)

        self.pushButtonSelect = QPushButton(QIcon(":/images/file_add.png"),
                                            "", self.selectWidget)
        self.pushButtonSelect.setToolTip("Choose root directory")
        self.connect(self.pushButtonSelect, SIGNAL("clicked()"),
                     self.selectRootDirName)
        shortcut = QShortcut(QKeySequence(self.tr("Ctrl+O")), self)
        self.connect(shortcut, SIGNAL("activated()"), self.selectRootDirName)

        self.listRoots = ParamListWidget(self.selectWidget, self)

        self.connect(self.listRoots,
                     SIGNAL("itemChanged(QListWidgetItem *)"),
                     self.updateListRoots)

        self.pushButtonRemove = QPushButton(QIcon(":/images/file_remove.png"),
                                            "", self.selectWidget)
        self.pushButtonRemove.setToolTip("Remove a root directory")
        self.connect(self.pushButtonRemove, SIGNAL("clicked()"),
                     self.removeRoot)

        self.comboBoxParamTag = QComboBox(self.selectWidget)
        self.comboBoxParamTag.clear()
        self.connect(self.comboBoxParamTag,
                     SIGNAL("activated(const QString&)"), self.setParamTag)

        self.comboBoxDataTag = QComboBox(self.selectWidget)
        self.comboBoxDataTag.clear()
        self.connect(self.comboBoxDataTag,
                     SIGNAL("activated(const QString&)"), self.setDataTag)

        self.comboBoxRootname = QComboBox(self.selectWidget)
        self.comboBoxRootname.clear()
        self.connect(self.comboBoxRootname,
                     SIGNAL("activated(const QString&)"), self.setRootname)

        self.listParametersX = QListWidget(self.selectWidget)
        self.listParametersX.clear()
        self.connect(self.listParametersX,
                     SIGNAL("itemChanged(QListWidgetItem *)"),
                     self.itemParamXChanged)

        self.listParametersY = QListWidget(self.selectWidget)
        self.listParametersY.clear()
        self.connect(self.listParametersY,
                     SIGNAL("itemChanged(QListWidgetItem *)"),
                     self.itemParamYChanged)

        self.selectAllX = QCheckBox("Select All", self.selectWidget)
        self.selectAllX.setCheckState(Qt.Unchecked)
        self.connect(self.selectAllX, SIGNAL("clicked()"),
                     self.statusSelectAllX)

        self.selectAllY = QCheckBox("Select All", self.selectWidget)
        self.selectAllY.setCheckState(Qt.Unchecked)
        self.connect(self.selectAllY, SIGNAL("clicked()"),
                     self.statusSelectAllY)

        self.toggleFilled = QRadioButton("Filled")
        self.toggleLine = QRadioButton("Line")
        self.toggleColor = QRadioButton("Color by:")
        self.comboBoxColor = QComboBox(self)
        self.comboBoxColor.clear()
        self.toggleFilled.setChecked(True)

        self.trianglePlot = QCheckBox("Triangle Plot", self.selectWidget)
        self.trianglePlot.setCheckState(Qt.Unchecked)

        self.pushButtonPlot = QPushButton("Make plot", self.selectWidget)
        self.connect(self.pushButtonPlot, SIGNAL("clicked()"), self.plotData)

        # Graphic Layout
        layoutTop = QGridLayout()
        layoutTop.setSpacing(5)
        layoutTop.addWidget(self.lineEditDirectory, 0, 0, 1, 3)
        layoutTop.addWidget(self.pushButtonSelect, 0, 3, 1, 1)
        layoutTop.addWidget(self.comboBoxRootname, 1, 0, 1, 3)
        layoutTop.addWidget(self.comboBoxParamTag, 1, 0, 1, 4)
        layoutTop.addWidget(self.comboBoxDataTag, 2, 0, 1, 4)
        layoutTop.addWidget(self.listRoots, 3, 0, 2, 3)
        layoutTop.addWidget(self.pushButtonRemove, 3, 3, 1, 1)

        layoutTop.addWidget(self.selectAllX, 5, 0, 1, 2)
        layoutTop.addWidget(self.selectAllY, 5, 2, 1, 2)
        layoutTop.addWidget(self.listParametersX, 6, 0, 5, 2)
        layoutTop.addWidget(self.listParametersY, 6, 2, 1, 2)
        layoutTop.addWidget(self.toggleFilled, 7, 2, 1, 2)
        layoutTop.addWidget(self.toggleLine, 8, 2, 1, 2)
        layoutTop.addWidget(self.toggleColor, 9, 2, 1, 1)
        layoutTop.addWidget(self.comboBoxColor, 9, 3, 1, 1)
        layoutTop.addWidget(self.trianglePlot, 10, 2, 1, 2)
        layoutTop.addWidget(self.pushButtonPlot, 12, 0, 1, 4)
        self.selectWidget.setLayout(layoutTop)

        self.listRoots.hide()
        self.pushButtonRemove.hide()
        self.comboBoxRootname.hide()
        self.comboBoxParamTag.hide()
        self.comboBoxDataTag.hide()

        self.plotWidget = QWidget(self.centralWidget)
        layout = QVBoxLayout(self.plotWidget)
        self.plotWidget.setLayout(layout)

        splitter = QSplitter(self.centralWidget)
        splitter.addWidget(self.selectWidget)
        splitter.addWidget(self.plotWidget)
        w = self.width()
        splitter.setSizes([w / 4., 3 * w / 4.])

        hbox = QHBoxLayout()
        hbox.addWidget(splitter)
        self.centralWidget.setLayout(hbox)
        self.readSettings()

    def closeEvent(self, event):
        self.writeSettings()
        event.accept()

    def getSettings(self):
        return QSettings('cosmomc', 'gui')

    def readSettings(self):
        settings = self.getSettings()
        h = min(QApplication.desktop().screenGeometry().height() * 4 / 5., 700)
        size = QSize(min(QApplication.desktop().screenGeometry().width() * 4 / 5., 900), h)
        pos = settings.value("pos", QPoint(100, 100))
        size = settings.value("size", size)
        self.resize(size)
        self.move(pos)

    def writeSettings(self):
        settings = self.getSettings()
        settings.setValue("pos", self.pos())
        settings.setValue("size", self.size())

    # slots for menu actions

    def export(self):
        """
        Callback for action 'Export as PDF/Image'.
        """
        if self.plotter:
            filename, _ = QFileDialog.getSaveFileName(
                self, "Choose a file name", '.', "PDF (*.pdf);; Image (*.png *.jpg)")
            if not filename: return
            filename = str(filename)
            self.plotter.export(filename)
        else:
            # logging.warning("No plotter data to export")
            QMessageBox.warning(self, "Export", "No plotter data to export")

    def saveScript(self):
        """
        Callback for action 'Save script'.
        """
        if self.script == '':
            QMessageBox.warning(self, "Script", "No script to save")
            # logging.warning("Script is empty!")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Choose a file name", '.', "Python (*.py)")
        if not filename: return
        filename = str(filename)
        logging.debug("Export script to %s" % filename)
        with open(filename, 'w') as f:
            f.write(self.script)

    def reLoad(self):
        adir = self.getSettings().value('lastSearchDirectory')
        batchJob.resetGrid(adir)
        self.openDirectory(adir)

    def showMargeStats(self):
        """
        Callback for action 'Show Marge Stats'.
        """
        rootname = None
        item = self.listRoots.currentItem()
        if not item and self.listRoots.count(): item = self.listRoots.item(0)
        if item is not None:
            rootname = str(item.text())

        if rootname is None:
            QMessageBox.warning(self, "Marge Stats", "Select a root name first. ")
            # logging.warning("No rootname. Can't show marge stats")
            return

        stats = None
#        if self.batch:
#            jobItem = self.batch.resolveRoot(rootname)
#            fname = jobItem.distRoot + '.margestats'
#            stats = ResultObjs.margeStats(fname)

        if not stats:
            try:
                self.statusBar().showMessage("Calculating margestats....")
                samples = self.plotter.sampleAnalyser.samplesForRoot(rootname)
                stats = samples.getMargeStats()
            finally:
                self.statusBar().showMessage("")

        dlg = DialogMargeStats(self, stats, rootname)
        dlg.show()

    def showSettings(self):
        """
        Callback for action 'Show settings'
        """
        if not self.plotter:
            QMessageBox.warning(self, "settings", "Open chains first ")
            return
        if isinstance(self.iniFile, basestring): self.iniFile = iniFile(self.iniFile)
        dlg = DialogSettings(self, self.iniFile)
        dlg.show()

    def settingsChanged(self):
        if self.plotter:
            self.plotter.sampleAnalyser.reset(self.iniFile)
            self.plotData()


    def about(self):
        """
        Callback for action 'About'.
        """
        QMessageBox.about(
            self, "About GetDist GUI",
            "Qt application for GetDist plots.\n\nMatplotlib: " + matplotlib.__version__ + "\nPySide: " + PySide.__version__)


    def selectRootDirName(self):
        """
        Slot function called when pushButtonSelect is pressed.
        """
        settings = self.getSettings()
        last_dir = settings.value('lastSearchDirectory')
        if not last_dir: last_dir = os.getcwd()

        title = self.tr("Choose an existing chains grid or chains folder")
        dirName = QFileDialog.getExistingDirectory(
            self, title, last_dir,
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks)
        dirName = str(dirName)
        logging.debug("dirName: %s" % dirName)
        if dirName is None or dirName == '':
            return  # No directory selected

        settings.setValue('lastSearchDirectory', dirName)
        self.openDirectory(dirName)

    def openDirectory(self, dirName):

        # Check if it's a grid
        if makeGrid.pathIsGrid(dirName):
            self.rootdirname = dirName
            self.lineEditDirectory.setText(self.rootdirname)
            self._readGridChains(self.rootdirname)
            return
        else:
            if self.is_grid:
                self._resetGridData()

        root_list = MCSamples.GetChainRootFiles(dirName)
        if not len(root_list):
            QMessageBox.critical(self, "Open chains", "No chains or grid found in that directory")
            return
        self.rootdirname = dirName
        self.lineEditDirectory.setText(self.rootdirname)

        self.getPlotter(chain_dir=self.rootdirname)

        self._updateComboBoxRootname(root_list)

    def getPlotter(self, chain_dir=None):
        if self.plotter is None or chain_dir:
            self.plotter = GetDistPlots.GetDistPlotter(mcsamples=True, chain_dir=chain_dir, analysis_settings=self.iniFile)
        return self.plotter

    def _updateParameters(self):

        roots = self.checkedRootNames()
        if not len(roots):
            return
        if self.rootnames.has_key(roots[0]):
            rootname, _ = self.rootnames[roots[0]]
            paramNames = self.plotter.sampleAnalyser.samplesForRoot(rootname).paramNames.list()
        else:
            raise Exception('rootnames out of synch')
#         all_params = []
#
#         for root in  self.checkedRootNames():
#             if self.rootnames.has_key(root):
#                 rootname, _ = self.roonames[root]
#                 params = self.plotter.sampleAnalyser.samplesForRoot(rootname).paramNames.list()
#                 logging.debug("%i parameters" % len(params))
#                 all_params.append(params)
#         if all_params:
#             if len(all_params) == 1:
#                 paramNames = all_params[0]
#                 logging.debug("%i parameters used" % len(paramNames))
#             else:
#                 # Find shared parameters
#                 shared_params = []
#                 for param in all_params[0]:
#                     shared = True
#                     for other_params in all_params[1:]:
#                         if not param in other_params: shared = False
#                     if shared: shared_params.append(param)
#                 paramNames = shared_params
#                 logging.debug("%i (shared) parameters used" % len(paramNames))

        self._updateListParametersX(paramNames)
        self._updateListParametersY(paramNames)
        self._updateComboBoxColor(paramNames)

    def _resetPlotData(self):
        # Plot parameters
        self.items_x = []
        self.items_y = []
        self.plotter = None

        # Script
        self.script = ""

    def _resetGridData(self):
        # Grid chains parameters
        self.is_grid = False
        self.batch = None
        self.grid_paramtag_jobItems = {}
        self.paramTag = ""
        self.dataTag = ""
        self.data2chains = {}
        self.listRoots.clear()
        self.rootnames = {}
        self.plotter = None

    def _readGridChains(self, batchPath):
        """
        Setup of a grid chain.
        """
        # Reset data
        self._resetPlotData()
        self._resetGridData()
        self.is_grid = True
        logging.debug("Read grid chain in %s" % batchPath)
        try:
            batch = batchJob.readobject(batchPath)
        except:
            batchJob.resetGrid(batchPath)
            batch = batchJob.readobject(batchPath)

        self.batch = batch
        items = dict()
        for jobItem in batch.items(True, True):
            if jobItem.chainExists():
                if not jobItem.paramtag in items: items[jobItem.paramtag] = []
                items[jobItem.paramtag].append(jobItem)
        logging.debug("Found %i names for grid" % len(items.keys()))
        self.grid_paramtag_jobItems = items

        self.getPlotter(chain_dir=self.rootdirname)

        self.comboBoxRootname.hide()
        self.listRoots.show()
        self.pushButtonRemove.show()
        self.comboBoxParamTag.clear()
        self.comboBoxParamTag.addItems(sorted(self.grid_paramtag_jobItems.keys()))
        self.setParamTag(self.comboBoxParamTag.itemText(0))
        self.comboBoxParamTag.show()
        self.comboBoxDataTag.show()


    def _updateComboBoxRootname(self, listOfRoots):
        self.comboBoxParamTag.hide()
        self.comboBoxDataTag.hide()
        self.comboBoxRootname.show()
        self.comboBoxRootname.clear()
        self.listRoots.show()
        self.pushButtonRemove.show()
        baseRoots = [ os.path.basename(root) for root in listOfRoots ]
        self.comboBoxRootname.addItems(baseRoots)
        if len(baseRoots) > 1:
            self.comboBoxRootname.setCurrentIndex(-1)
        elif len(baseRoots):
            self.comboBoxRootname.setCurrentIndex(0)
            self.setRootname(self.comboBoxRootname.itemText(0))


    def newRootItem(self, root, fileroot=None):
        if self.rootnames.has_key(root):
            logging.warning("Root allready in list")
            return

        self.updating = True
        item = QListWidgetItem(self.listRoots)
        item.setText('Loading... ' + root)
        self.listRoots.addItem(item)
        self.listRoots.repaint()
        QCoreApplication.processEvents()
        try:
            if self.batch:
                self.plotter.sampleAnalyser.addRootGrid(root)
            else:
                self.plotter.sampleAnalyser.addRoot(fileroot)
            self.rootnames[root] = [fileroot or root, True]
            item.setCheckState(Qt.Checked)
            item.setText(root)
            self._updateParameters()
        except:
            self.listRoots.takeItem(self.listRoots.count() - 1)
            raise
        finally:
            self.updating = False

    def setRootname(self, strParamName):
        """
        Slot function called on change of comboBoxRootname.
        """
        root = str(strParamName)
        fileroot = os.path.join(self.rootdirname, root)

        if self.plotter is None:
            QMessageBox.warning(self, "Set root", "No plotter defined")
            return
        self.newRootItem(root, fileroot)

    def updateListRoots(self, item):
        if self.updating: return
        logging.debug("updateListRoots")
        nitems = self.listRoots.count()
        for i in range(nitems):
            item = self.listRoots.item(i)
            root = item.text()
            state = item.checkState() == Qt.Checked
            if self.rootnames.has_key(root):
                self.rootnames[root][1] = state
            else:
                logging.warning('No root found for %s' % root)
        self._updateParameters()

    def removeRoot(self):
        logging.debug("Remove root")
        self.updating = True
        try:
            for i in range(self.listRoots.count()):
                item = self.listRoots.item(i)
                if item and item.isSelected():
                    root = str(item.text())
                    logging.debug("Remove root %s" % root)
                    self.plotter.sampleAnalyser.removeRoot(root)
                    if self.rootnames.has_key(root):
                        del self.rootnames[root]
                    self.listRoots.takeItem(i)
        finally:
            self._updateParameters()
            self.updating = False

    def getRoots(self):
        logging.debug("Get status for roots")
        for i in range(self.listRoots.count()):
            item = self.listRoots.item(i)
            root = str(item.text())
            state = (item.checkState() == Qt.Checked)
            if self.rootnames.has_key(root):
                self.rootnames[root][1] = state
                logging.debug("status for '%s': %s" % (root, state))
            else:
                logging.warning("No key for root '%s'" % root)

    def setParamTag(self, strParamTag):
        """
        Slot function called on change of comboBoxParamTag.
        """
        self.paramTag = str(strParamTag)
        logging.debug("Param: %s" % self.paramTag)

        self.comboBoxDataTag.clear()
        self.comboBoxDataTag.addItems([ jobItem.datatag for jobItem in self.grid_paramtag_jobItems[self.paramTag]])
        self.comboBoxDataTag.setCurrentIndex(-1)
        self.comboBoxDataTag.show()

    def setDataTag(self, strDataTag):
        """
        Slot function called on change of comboBoxDataTag.
        """
        self.dataTag = str(strDataTag)
        logging.debug("Data: %s" % strDataTag)
        self.newRootItem(self.paramTag + '_' + self.dataTag)

    def _updateListParametersX(self, items):
        """
        """
        logging.debug("Fill ListParametersX with %i items" % (len(items)))
        items_x_old = self.items_x
        self.items_x = []
        self.listParametersX.clear()
        for item in items:
            listItem = QListWidgetItem()
            listItem.setText(item)
            listItem.setFlags(listItem.flags() | Qt.ItemIsUserCheckable)
            listItem.setCheckState(Qt.Unchecked)
            self.listParametersX.addItem(listItem)

        if items_x_old:
            for item_x in items_x_old:
                match_items = self.listParametersX.findItems(item_x, Qt.MatchExactly)
                if match_items:
                    logging.debug("Re check param %s" % item_x)
                    match_items[0].setCheckState(Qt.Checked)

    def itemParamXChanged(self, item):
        """
        Slot function called when item in listParametersX changes.
        """
        item_x = str(item.text())
        if item.checkState() == Qt.Checked:
            if item_x not in self.items_x:
                logging.debug("Add item %s" % item_x)
                self.items_x.append(item_x)
        else:
            if item_x in self.items_x:
                logging.debug("Del item %s" % item_x)
                self.items_x.remove(item_x)

    def _updateListParametersY(self, items):
        """
        """
        logging.debug("Fill ListParametersY with %i items" % (len(items)))
        items_y_old = self.items_y
        self.items_y = []
        self.listParametersY.clear()
        for item in items:
            listItem = QListWidgetItem()
            listItem.setText(item)
            listItem.setFlags(listItem.flags() | Qt.ItemIsUserCheckable)
            listItem.setCheckState(Qt.Unchecked)
            self.listParametersY.addItem(listItem)

        if items_y_old:
            for item_y in items_y_old:
                match_items = self.listParametersY.findItems(item_y, Qt.MatchExactly)
                if match_items:
                    logging.debug("Re check param %s" % item_y)
                    match_items[0].setCheckState(Qt.Checked)

    def itemParamYChanged(self, item):
        """
        Slot function called when item in listParametersY changes.
        """
        item_y = str(item.text())
        if item.checkState() == Qt.Checked:
            if item_y not in self.items_x:
                logging.debug("Add item %s" % item_y)
                self.items_y.append(item_y)
        else:
            if item_y in self.items_y:
                logging.debug("Del item %s" % item_y)
                self.items_y.remove(item_y)

    def statusSelectAllX(self):
        """
        Slot function called when selectAllX is modified.
        """
        self.items_x = []
        if self.selectAllX.isChecked():
            state = Qt.Checked
        else:
            state = Qt.Unchecked
        for i in range(self.listParametersX.count()):
            self.listParametersX.item(i).setCheckState(state)

    def statusSelectAllY(self):
        """
        Slot function called when selectAllY is modified.
        """
        self.items_y = []
        if self.selectAllY.isChecked():
            state = Qt.Checked
        else:
            state = Qt.Unchecked
        for i in range(self.listParametersY.count()):
            self.listParametersY.item(i).setCheckState(state)

    def _updateComboBoxColor(self, listOfParams):
        if self.rootdirname and os.path.isdir(self.rootdirname):
            param_old = str(self.comboBoxColor.currentText())
            self.comboBoxColor.clear()
            self.comboBoxColor.addItems(listOfParams)
            idx = self.comboBoxColor.findText(param_old, Qt.MatchExactly)
            if idx <> -1:
                self.comboBoxColor.setCurrentIndex(idx)
                logging.debug("Re set param %s at index %i" % (param_old, idx))
            else:
                logging.debug("Param %s not found in new list" % (param_old))

    def checkedRootNames(self):
        items = []
        for i in range(self.listRoots.count()):
            item = self.listRoots.item(i)
            if item.checkState() == Qt.Checked:
                items.append(str(item.text()))
        return items


    def plotData(self):
        """
        Slot function called when pushButtonPlot is pressed.
        """
        self.statusBar().showMessage("Generating plot....")
        try:
            # Ensure at least 1 root name specified
            self.getRoots()
            os.chdir(self.base_dir)

            nroots = 0
            for basename, values in self.rootnames.items():
                rootname, state = values
                if state: nroots += 1

            if nroots == 0:
                logging.warning("No rootname selected")
                QMessageBox.warning(self, "Plot data", "No root selected")
                return

            if self.plotter is None:
                QMessageBox.warning(self, "Plot data", "No GetDistPlotter instance")
                return

            if self.plotter.fig is not None:
                self.plotter.fig.clf()

            plt.close('all')

            # X and Y items
            items_x = self.items_x
            items_y = self.items_y
            self.plotter.settings.setWithSubplotSize(3.5)
            self.plotter.settings.legend_position_config = 2
            self.plotter.settings.legend_frac_subplot_margin = 0.05

            script = "import %s as s\nimport os\n\n" % self.plot_module
            if len(items_x) > 1 or len(items_y) > 1:
                plot_func = 'getSubplotPlotter'
            else:
                plot_func = 'getSinglePlotter'
            if self.is_grid:
                script += "g=s.%s(chain_dir=r'%s')\n" % (plot_func, self.rootdirname)
            else:
                if isinstance(self.iniFile, basestring):
                    script += "g=s.%s(mcsamples=True, ini_file=r'%s')\n" % (plot_func, self.iniFile)
                else:
                    script += "g=s.%s(mcsamples=True)\n" % (plot_func)

            # Root names
            roots = []
            for basename in self.checkedRootNames():
                if self.rootnames.has_key(basename):
                    rootname, state = self.rootnames[basename]
                    roots.append(os.path.basename(rootname))
                    if not self.is_grid:
                        script += "g.sampleAnalyser.addRoot(r'%s')\n" % (rootname)

            script += "roots = []\n"
            for root in roots:
                script += "roots.append('%s')\n" % (root)

            logging.debug("Plotting with roots = %s" % str(roots))

            height = self.plotWidget.height() * 0.75
            width = self.plotWidget.width() * 0.75

            def setSizeQT(sz):
                self.plotter.settings.setWithSubplotSize(max(2.0, sz / 80.))

            def setSizeForN(n):
                setSizeQT(min(height, width) / max(n, 2))

            # Plot parameters
            filled = self.toggleFilled.isChecked()
            line = self.toggleLine.isChecked()
            color = self.toggleColor.isChecked()
            color_param = str(self.comboBoxColor.currentText())

            # Check type of plot
            if self.trianglePlot.isChecked():
                # Triangle plot
                if len(items_x) > 1:
                    params = items_x
                    logging.debug("Triangle plot with params = %s" % str(params))
                    script += "params = %s\n" % str(params)
                    if color:
                        param_3d = color_param
                        script += "param_3d = '%s'\n" % str(color_param)
                    else:
                        param_3d = None
                        script += "param_3d = None\n"
                    script += "filled = %s\n" % filled
                    setSizeForN(len(params))
                    try:
                        self.plotter.triangle_plot(roots, params, plot_3d_with_param=param_3d, filled_compare=filled)
                    except:
                        QMessageBox.critical(
                            self, "Triangle plot",
                            "Error for command:\n\ntriangle_plot(roots, params, plot_3d_with_param=param_3d, filled_compare=filled)\n\nwith roots=%s\nparams=%s\nparam_3d=%s\nfilled=%s\n" % (str(roots), str(params), str(param_3d), str(filled)))
                        raise
                    self.updatePlot()
                    script += "g.triangle_plot(roots, params, plot_3d_with_param=param_3d, filled_compare=filled)\n"
                else:
                    QMessageBox.warning(self, "Triangle plot", "Select more than 1 x parameter")

            elif len(items_x) > 0 and len(items_y) == 0:
                # 1D plot
                params = items_x
                logging.debug("1D plot with params = %s" % str(params))
                script += "params=%s\n" % str(params)
                setSizeForN(round(np.sqrt(len(params) / 1.4)))
                try:
                    if len(roots) > 3:
                        ncol = 2
                    else:
                        ncol = None
                    self.plotter.plots_1d(roots, params=params, legend_ncol=ncol)
                except:
                    QMessageBox.critical(
                            self, "Plot 1D",
                            "Error for command:\n\nplots_1d(roots, params=params)\n\nwith roots=%s\nparams=%s\n" % (str(roots), str(params)))
                    raise
                self.updatePlot()
                script += "g.plots_1d(roots, params=params)\n"

            elif len(items_x) > 0 and len(items_y) > 0:
                    if len(items_x) > 1 and len(items_y) > 1:
                        # Rectangle plot
                        script += "xparams = %s\n" % str(items_x)
                        script += "yparams = %s\n" % str(items_y)
                        script += "filled=%s\n" % filled
                        logging.debug("Rectangle plot with xparams=%s and yparams=%s" % (str(items_x), str(items_y)))

                        setSizeQT(min(height / len(items_y), width / len(items_x)))
                        try:
                            self.plotter.rectangle_plot(items_x, items_y, roots=roots, filled=filled)
                        except:
                            QMessageBox.critical(
                                self, "Plot 2D",
                                "Error for command:\n\nrectangle_plot(xparams, yparams, roots=roots)\n\nwith xparams=%s\nyparams=%s\nroots=%s\n" % (str(items_x), str(items_y), str(roots)))
                            raise
                        self.updatePlot()
                        script += "g.rectangle_plot(xparams, yparams, roots=roots,filled=filled)\n"

                    else:
                        # 2D plot
                        if len(items_x) == 1 and len(items_y) == 1:
                            pairs = [ [items_x[0], items_y[0]] ]
                            setSizeQT(min(height, width))
                        elif len(items_x) == 1 and len(items_y) > 1:
                            item_x = items_x[0]
                            pairs = zip([item_x] * len(items_y), items_y)
                            setSizeForN(round(np.sqrt(len(pairs) / 1.4)))
                        elif len(items_x) > 1 and len(items_y) == 1:
                            item_y = items_y[0]
                            pairs = zip(items_x, [item_y] * len(items_x))
                            setSizeForN(round(np.sqrt(len(pairs) / 1.4)))
                        else:
                            pairs = []
                        if filled or line:
                            script += "pairs = %s\n" % pairs
                            logging.debug("2D plot with pairs = %s" % str(pairs))
                            script += "filled=%s\n" % filled

                            try:
                                self.plotter.plots_2d(roots, param_pairs=pairs, filled=filled)
                            except:
                                QMessageBox.critical(
                                    self, "Plot 2D",
                                    "Error for command:\n\nplots_2d(roots, param_pairs=pairs, filled=filled)\n\nwith roots=%s\npairs=%s\nfilled=%s\n"
                                    % (str(roots), str(pairs), str(filled)))
                                raise
                            self.updatePlot()
                            script += "g.plots_2d(roots, param_pairs=pairs, filled=filled)\n"
                        elif color:
                            # 3D plot
                            sets = [list(pair) + [color_param] for pair in pairs]
                            logging.debug("3D plot with sets = %s" % str(sets))
                            try:
                                triplets = ["['%s', '%s', '%s']" % tuple(trip) for trip in sets]
                                if len(sets) == 1:
                                    script += "g.plot_3d(roots, %s)\n" % triplets[0]
                                    self.plotter.settings.scatter_size = 6
                                    self.plotter.make_figure(1, ystretch=0.75)
                                    self.plotter.plot_3d(roots, sets[0])
                                else:
                                    script += "sets = [" + ",".join(triplets) + "]\n"
                                    script += "g.plots_3d(roots, sets)\n"
                                    self.plotter.plots_3d(roots, sets)
                            except:
                                QMessageBox.critical(
                                    self, "Plot 3D",
                                    "Error for command:\n\nplots_3d(roots, sets)\n\nwith roots=%s\nsets=%s\n" % (str(roots), str(sets)))
                                raise
                            self.updatePlot()


            else:
                text = ""
                text += "Wrong parameters selection. Specify parameters such as:\n"
                text += "\n"
                text += "Triangle plot: Click on 'Triangle plot' and select more than 1 x parameters\n"
                text += "\n"
                text += "1D plot: Select x parameter(s)\n"
                text += "\n"
                text += "2D plot: Select x parameter(s), y parameter(s) and select 'Filled' or 'Line'\n"
                text += "\n"
                text += "3D plot: Select x parameter, y parameter and 'Color by' parameter\n"
                text += "\n"

                QMessageBox.warning(self, "Plot usage", text)
                return

            script += "g.export()\n"
            self.script = script

        finally:
            self.statusBar().showMessage("")


    def updatePlot(self):
        if self.plotter.fig is None:
            # logging.debug("Define an empty central widget")
            # self.figure = None
            self.canvas = None
        else:
            # logging.debug("Define new canvas in central widget")
            # Remove everything from layout
            i = 0
            while 1:
                item = self.plotWidget.layout().takeAt(i)
                if item is None: break
            if hasattr(self, "canvas"): del self.canvas
            if hasattr(self, "toolbar"): del self.toolbar
            self.canvas = FigureCanvas(self.plotter.fig)
            if platform <> "darwin":
                # for some reason the toolbar crashes out on a Mac; just don't show it
                self.toolbar = NavigationToolbar(self.canvas, self)
                self.plotWidget.layout().addWidget(self.toolbar)
            self.plotWidget.layout().addWidget(self.canvas)
            self.canvas.draw()
            # self.plotWidget.update()
            self.plotWidget.show()



# ==============================================================================

class DialogMargeStats(QDialog):

    def __init__(self, parent=None, stats="", root=''):
        QDialog.__init__(self, parent)

        self.label = QLabel(self)
        self.table = QTableWidget(self)
#       self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
#       self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
#       self.table.horizontalHeader().hide()
        self.table.verticalHeader().hide()

        layout = QGridLayout()
        layout.addWidget(self.table, 0, 0)
        self.setLayout(layout)

        self.setWindowTitle(self.tr('Marginalized constraints: ' + root + ".margestats"))

        if (stats):

            headers = stats.headerLine(inc_limits=True)[0].split() + [ 'label' ]
            self.table.setColumnCount(len(headers))
            self.table.setHorizontalHeaderLabels([h.replace('_', ' ') for h in headers])
            self.table.verticalHeader().setVisible(False)
#            self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.table.setSelectionBehavior(QAbstractItemView.SelectItems)
            self.table.setSelectionMode(QAbstractItemView.SingleSelection)
            self.table.setRowCount(stats.numParams())
            for irow, par in enumerate(stats.names):
                vals = [par.name, "%5g" % par.mean, "%5g" % par.err]
                for lim in par.limits:
                    vals += ["%5g" % lim.lower, "%5g" % lim.upper, lim.limitTag()]
                vals += [par.label]
                for icol, value in enumerate(vals):
                    item = QTableWidgetItem(str(value))
                    item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                    if icol == 0 and not par.isDerived:
                        font = QFont()
                        font.setBold(True)
                        item.setFont(font)
                    self.table.setItem(irow, icol, item)

#             lines = text.split("\n")
#             line0 = lines.pop(0)
#             self.label.setText(line0)
#             line = lines.pop(0)  # empty
#             line = lines.pop(0)  # headers
#             headers = line.split(' ')
#             headers = [ h for h in headers if h <> '' ] + [ 'Label' ]
#             self.table.setColumnCount(len(headers))
#             self.table.setHorizontalHeaderLabels(headers)
#             self.table.verticalHeader().setVisible(False)
#             self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
#             self.table.setSelectionMode(QAbstractItemView.SingleSelection)
#             self.table.setRowCount(len(lines))
#             irow = 0
#             for line in lines:
#                 values = line.split(' ')
#                 values = [ v for v in values if v <> '' ]
#                 icol = 0
#                 for value in values:
#                     item = QTableWidgetItem(value)
#                     item.setFlags(item.flags() ^ Qt.ItemIsEditable)
#                     self.table.setItem(irow, icol, item)
#                     icol += 1
#                 irow += 1

            self.table.resizeRowsToContents()
            self.table.resizeColumnsToContents()

            w = self.table.horizontalHeader().length() + 40
            h = self.table.verticalHeader().length() + 40
            h = min(QApplication.desktop().screenGeometry().height() * 4 / 5, h)
            self.resize(w, h)

# ==============================================================================


class DialogSettings(QDialog):

    def __init__(self, parent, ini):
        QDialog.__init__(self, parent)

        self.table = QTableWidget(self)
        self.table.verticalHeader().hide()

        layout = QGridLayout()
        layout.addWidget(self.table, 0, 0)
        button = QPushButton("Update")
        self.connect(button, SIGNAL("clicked()"),
                     self.doUpdate)

        layout.addWidget(button, 1, 0)
        self.setLayout(layout)

        self.setWindowTitle(self.tr('Settings'))

        headers = ['parameter', 'value']
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)

        names = iniFile(os.path.join(os.path.dirname(__file__), 'analysis_defaults.ini'))
        items = []
        self.ini = ini
        for key in ini.readOrder:
            if key in names.params:
                items.append(key)

        for key in ini.params:
            if not key in items and key in names.params:
                items.append(key)

        nblank = 3
        self.rows = len(items) + nblank
        self.table.setRowCount(self.rows)
        for irow, key in enumerate(items):
                item = QTableWidgetItem(str(key))
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self.table.setItem(irow, 0, item)
                item = QTableWidgetItem(ini.string(key))
                self.table.setItem(irow, 1, item)
        for i in range(nblank):
            item = QTableWidgetItem(str(""))
            irow = len(items) + i
            self.table.setItem(irow, 0, item)
            item = QTableWidgetItem(str(""))
            self.table.setItem(irow, 1, item)
        self.table.resizeRowsToContents()
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True);
        self.table.setEditTriggers(QAbstractItemView.AllEditTriggers)

        h = self.table.verticalHeader().length() + 40
        h = min(QApplication.desktop().screenGeometry().height() * 4 / 5, h)
        self.resize(300, h)
        self.setAttribute(Qt.WA_DeleteOnClose)

    def doUpdate(self):
        for row in range(self.rows):
            key = self.table.item(row, 0).text().strip()
            if key:
                self.ini.params[key] = self.table.item(row, 1).text().strip()
        self.parent().settingsChanged()


if __name__ == "__main__":

    app = QApplication(sys.argv)
    mainWin = MainWindow(app)
    mainWin.show()
    sys.exit(app.exec_())

# ==============================================================================


