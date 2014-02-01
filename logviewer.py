from PyQt5 import QtGui as gui, QtCore as core, QtWidgets as widgets
import ostools
import codecs
import re
from time import strftime, strptime
from generic import RightClickList, RightClickTree
from parsetools import convertTags
from convo import PesterText
_datadir = ostools.getDataDir()

class PesterLogSearchInput(widgets.QLineEdit):
    def __init__(self, theme, parent=None):
        widgets.QLineEdit.__init__(self, parent)
        self.setStyleSheet(theme["convo/input/style"] + "margin-right:0px;")
    def keyPressEvent(self, event):
        widgets.QLineEdit.keyPressEvent(self, event)
        if hasattr(self.parent(), 'textArea'):
            if event.key() == core.Qt.Key_Return:
                self.parent().logSearch(self.text())
                if self.parent().textArea.find(self.text()):
                    self.parent().textArea.ensureCursorVisible()
        else:
            self.parent().logSearch(self.text())

class PesterLogHighlighter(gui.QSyntaxHighlighter):
    def __init__(self, parent):
        gui.QSyntaxHighlighter.__init__(self, parent)
        self.searchTerm = ""
        self.hilightstyle = gui.QTextCharFormat()
        self.hilightstyle.setBackground(gui.QBrush(core.Qt.green))
        self.hilightstyle.setForeground(gui.QBrush(core.Qt.black))
    def highlightBlock(self, text):
        for i in range(0, len(text)-(len(self.searchTerm)-1)):
            if str(text[i:i+len(self.searchTerm)]).lower() == str(self.searchTerm).lower():
                self.setFormat(i, len(self.searchTerm), self.hilightstyle)

class PesterLogUserSelect(widgets.QDialog):
    def __init__(self, config, theme, parent):
        widgets.QDialog.__init__(self, parent)
        self.setModal(False)
        self.config = config
        self.theme = theme
        self.parent = parent
        self.handle = parent.profile().handle
        self.logpath = _datadir+"logs"

        self.setStyleSheet(self.theme["main/defaultwindow/style"])
        self.setWindowTitle("Pesterlogs")

        instructions = widgets.QLabel("Pick a memo or chumhandle:")

        if ostools.exists(self.logpath, self.handle):
            chumMemoList = ostools.listdir(self.logpath, self.handle)
        else:
            chumMemoList = []
        chumslist = config.chums()
        for c in chumslist:
            if not c in chumMemoList:
                chumMemoList.append(c)
        chumMemoList.sort()

        self.chumsBox = RightClickList(self)
        self.chumsBox.setStyleSheet(self.theme["main/chums/style"])
        self.chumsBox.optionsMenu = widgets.QMenu(self)

        for (i, t) in enumerate(chumMemoList):
            item = widgets.QListWidgetItem(t)
            item.setForeground(gui.QBrush(gui.QColor(self.theme["main/chums/userlistcolor"])))
            self.chumsBox.addItem(item)

        self.search = PesterLogSearchInput(theme, self)
        self.search.setFocus()
        self.cancel = widgets.QPushButton("CANCEL",self)
        self.cancel.clicked.connect(self.reject)
        self.ok = widgets.QPushButton("OK",self)
        self.ok.clicked.connect(self.viewActivatedLog)
        self.directory = widgets.QPushButton("LOG DIRECTORY",self)
        self.directory.clicked.connect(self.openDir)
        self.ok.setDefault(True)
        
        layout_ok = widgets.QHBoxLayout()
        layout_ok.addWidget(self.cancel)
        layout_ok.addWidget(self.ok)

        layout_0 = widgets.QVBoxLayout()
        layout_0.addWidget(instructions)
        layout_0.addWidget(self.chumsBox)
        layout_0.addWidget(self.search)
        layout_0.addLayout(layout_ok)
        layout_0.addWidget(self.directory)

        self.setLayout(layout_0)

    def selectedchum(self):
        return self.chumsBox.currentItem()

    def logSearch(self, search):
        found = self.chumsBox.findItems(search, core.Qt.MatchStartsWith)
        if len(found) > 0 and len(found) < self.chumsBox.count():
            self.chumsBox.setCurrentItem(found[0])

    @core.pyqtSlot()
    def viewActivatedLog(self):
        selectedchum = self.selectedchum().text()
        if not hasattr(self, 'pesterlogviewer'):
            self.pesterlogviewer = None
        if not self.pesterlogviewer:
            self.pesterlogviewer = PesterLogViewer(selectedchum, self.config, self.theme, self.parent)
            self.pesterlogviewer.rejected.connect(self.closeActiveLog)
            self.pesterlogviewer.show()
            self.pesterlogviewer.raise_()
            self.pesterlogviewer.activateWindow()
        self.accept()

    @core.pyqtSlot()
    def closeActiveLog(self):
        self.pesterlogviewer.close()
        self.pesterlogviewer = None

    @core.pyqtSlot()
    def openDir(self):
        ostools.openLocalUrl(_datadir, "logs")

class PesterLogViewer(widgets.QDialog):
    def __init__(self, chum, config, theme, parent):
        widgets.QDialog.__init__(self, parent)
        self.setModal(False)
        self.config = config
        self.theme = theme
        self.parent = parent
        self.mainwindow = parent
        global _datadir
        self.handle = parent.profile().handle
        self.chum = chum
        self.convos = {}
        self.logpath = _datadir+"logs"

        self.setStyleSheet(self.theme["main/defaultwindow/style"])
        self.setWindowTitle("Pesterlogs with " + self.chum)

        self.format = "bbcode"
        if ostools.exists(self.logpath, self.handle, chum, self.format):
            self.logList = ostools.listdir(self.logpath, self.handle, self.chum, self.format)
        else:
            self.logList = []

        if not ostools.exists(self.logpath, self.handle, chum, self.format) or len(self.logList) == 0:
            instructions = widgets.QLabel("No Pesterlogs were found")

            self.ok = widgets.QPushButton("CLOSE",self)
            self.ok.clicked.connect(self.reject)
            self.ok.setDefault(True)
            layout_ok = widgets.QHBoxLayout()
            layout_ok.addWidget(self.ok)

            layout_0 = widgets.QVBoxLayout()
            layout_0.addWidget(instructions)
            layout_0.addLayout(layout_ok)

            self.setLayout(layout_0)
        else:
            self.instructions = widgets.QLabel("Pesterlog with " +self.chum+ " on")

            self.textArea = PesterLogText(theme, self.parent)
            self.textArea.setReadOnly(True)
            self.textArea.setFixedWidth(600)
            if "convo/scrollbar" in theme:
                self.textArea.setStyleSheet("QTextEdit { width:500px; %s } QScrollBar:vertical { %s } QScrollBar::handle:vertical { %s } QScrollBar::add-line:vertical { %s } QScrollBar::sub-line:vertical { %s } QScrollBar:up-arrow:vertical { %s } QScrollBar:down-arrow:vertical { %s }" % (theme["convo/textarea/style"], theme["convo/scrollbar/style"], theme["convo/scrollbar/handle"], theme["convo/scrollbar/downarrow"], theme["convo/scrollbar/uparrow"], theme["convo/scrollbar/uarrowstyle"], theme["convo/scrollbar/darrowstyle"] ))
            else:
                self.textArea.setStyleSheet("QTextEdit { width:500px; %s }" % (theme["convo/textarea/style"]))

            self.logList.sort()
            self.logList.reverse()

            self.tree = RightClickTree()
            self.tree.optionsMenu = widgets.QMenu(self)
            self.tree.setFixedSize(260, 300)
            self.tree.header().hide()
            if "convo/scrollbar" in theme:
                self.tree.setStyleSheet("QTreeWidget { %s } QScrollBar:vertical { %s } QScrollBar::handle:vertical { %s } QScrollBar::add-line:vertical { %s } QScrollBar::sub-line:vertical { %s } QScrollBar:up-arrow:vertical { %s } QScrollBar:down-arrow:vertical { %s }" % (theme["convo/textarea/style"], theme["convo/scrollbar/style"], theme["convo/scrollbar/handle"], theme["convo/scrollbar/downarrow"], theme["convo/scrollbar/uparrow"], theme["convo/scrollbar/uarrowstyle"], theme["convo/scrollbar/darrowstyle"] ))
            else:
                self.tree.setStyleSheet("%s" % (theme["convo/textarea/style"]))
            self.tree.itemSelectionChanged.connect(self.loadSelectedLog)
            self.tree.setSortingEnabled(False)

            child_1 = None
            last = ["",""]
            for (i,l) in enumerate(self.logList):
                my = self.fileToMonthYear(l)
                if my[0] != last[0]:
                    child_1 = widgets.QTreeWidgetItem(["%s %s" % (my[0], my[1])])
                    self.tree.addTopLevelItem(child_1)
                    if i == 0:
                        child_1.setExpanded(True)
                child_1.addChild(widgets.QTreeWidgetItem([self.fileToTime(l)]))
                last = self.fileToMonthYear(l)

            self.hilight = PesterLogHighlighter(self.textArea)
            if len(self.logList) > 0: self.loadLog(self.logList[0])

            self.search = PesterLogSearchInput(theme, self)
            self.search.setFocus()
            self.find = widgets.QPushButton("Find", self)
            font = self.find.font()
            font.setPointSize(8)
            self.find.setFont(font)
            self.find.setDefault(True)
            self.find.setFixedSize(40, 20)
            layout_search = widgets.QHBoxLayout()
            layout_search.addWidget(self.search)
            layout_search.addWidget(self.find)

            self.qdb = widgets.QPushButton("Pesterchum QDB")
            self.qdb.clicked.connect(self.openQDB)
            self.ok = widgets.QPushButton("CLOSE")
            self.ok.clicked.connect(self.reject)
            self.qdb.setFixedWidth(260)
            self.ok.setFixedWidth(80)
            
            layout_ok = widgets.QHBoxLayout()
            layout_ok.addWidget(self.qdb)
            layout_ok.addWidget(self.ok)
            layout_ok.setAlignment(self.ok, core.Qt.AlignRight)

            layout_logs = widgets.QHBoxLayout()
            layout_logs.addWidget(self.tree)
            layout_right = widgets.QVBoxLayout()
            layout_right.addWidget(self.textArea)
            layout_right.addLayout(layout_search)
            layout_logs.addLayout(layout_right)

            layout_0 = widgets.QVBoxLayout()
            layout_0.addWidget(self.instructions)
            layout_0.addLayout(layout_logs)
            layout_0.addLayout(layout_ok)

            self.setLayout(layout_0)

    @core.pyqtSlot()
    def loadSelectedLog(self):
        if len(self.tree.currentItem().text(0)) > len("September 2011"):
            self.loadLog(self.timeToFile(self.tree.currentItem().text(0)))

    @core.pyqtSlot()
    def openQDB(self):
        gui.QDesktopServices.openUrl(core.QUrl("http://qdb.pesterchum.net/index.php?p=browse", core.QUrl.TolerantMode))

    def loadLog(self, fname):
        fp = codecs.open("%s/%s/%s/%s/%s" % (self.logpath, self.handle, self.chum, self.format, fname), encoding='utf-8', mode='r')
        self.textArea.clear()
        for line in fp:
            cline = line.replace("\r\n", "").replace("[/color]","</c>").replace("[url]","").replace("[/url]","")
            cline = re.sub("\[color=(#.{6})]", r"<c=\1>", cline)
            self.textArea.append(convertTags(cline))
        textCur = self.textArea.textCursor()
        textCur.movePosition(1)
        self.textArea.setTextCursor(textCur)
        self.instructions.setText("Pesterlog with " +self.chum+ " on " + self.fileToTime(str(fname)))

    def logSearch(self, search):
        self.hilight.searchTerm = search
        self.hilight.rehighlight()

    def fileToMonthYear(self, fname):
        time = strptime(fname[(fname.index(".")+1):fname.index(".txt")], "%Y-%m-%d.%H.%M")
        return [strftime("%B", time), strftime("%Y", time)]
    def fileToTime(self, fname):
        timestr = fname[(fname.index(".")+1):fname.index(".txt")]
        return strftime("%a %d %b %Y %H %M", strptime(timestr, "%Y-%m-%d.%H.%M"))
    def timeToFile(self, time):
        return self.chum + strftime(".%Y-%m-%d.%H.%M.txt", strptime(str(time), "%a %d %b %Y %H %M"))

class PesterLogText(PesterText):
    def __init__(self, theme, parent=None):
        PesterText.__init__(self, theme, parent)

    def focusInEvent(self, event):
        widgets.QTextEdit.focusInEvent(self, event)
    def mousePressEvent(self, event):
        url = self.anchorAt(event.pos())
        if url != "":
            if url[0] == "#" and url != "#pesterchum":
                self.parent().parent.showMemos(url[1:])
            elif url[0] == "@":
                handle = str(url[1:])
                self.parent().parent.newConversation(handle)
            else:
                gui.QDesktopServices.openUrl(core.QUrl(url, core.QUrl.TolerantMode))
        widgets.QTextEdit.mousePressEvent(self, event)
    def mouseMoveEvent(self, event):
        widgets.QTextEdit.mouseMoveEvent(self, event)
        if self.anchorAt(event.pos()):
            if self.viewport().cursor().shape != core.Qt.PointingHandCursor:
                self.viewport().setCursor(gui.QCursor(core.Qt.PointingHandCursor))
        else:
            self.viewport().setCursor(gui.QCursor(core.Qt.IBeamCursor))

    def contextMenuEvent(self, event):
        textMenu = self.createStandardContextMenu()
        if self.textSelected:
            self.submitLogAction = widgets.QAction("Submit to Pesterchum QDB", self)
            self.submitLogAction.triggered.connect(self.submitLog)
            textMenu.addAction(self.submitLogAction)
        a = textMenu.actions()
        a[0].setText("Copy Plain Text")
        a[0].setShortcut(self.tr("Ctrl+C"))
        textMenu.exec_(event.globalPos())
