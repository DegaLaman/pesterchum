from PyQt5 import QtGui as gui, QtCore as core, QtWidgets as widgets
import ostools, re

from generic import RightClickList, RightClickTree, MultiTextDialog
from dataobjs import pesterQuirk, PesterProfile
from memos import TimeSlider, TimeInput
from version import _pcVersion
_datadir = ostools.getDataDir()

class PesterQuirkItem(widgets.QTreeWidgetItem):
    def __init__(self, quirk):
        parent = None
        widgets.QTreeWidgetItem.__init__(self, parent)
        self.quirk = quirk
        self.setText(0, str(quirk))
    def update(self, quirk):
        self.quirk = quirk
        self.setText(0, str(quirk))
    def __lt__(self, quirkitem):
        """Sets the order of quirks if auto-sorted by Qt. Obsolete now."""
        if self.quirk.type == "prefix":
            return True
        elif (self.quirk.type == "replace" or self.quirk.type == "regexp") and \
                quirkitem.type == "suffix":
            return True
        else:
            return False
class PesterQuirkList(widgets.QTreeWidget):
    def __init__(self, mainwindow, parent):
        widgets.QTreeWidget.__init__(self, parent)
        self.resize(400, 200)
        # make sure we have access to mainwindow info like profiles
        self.mainwindow = mainwindow
        self.setStyleSheet("background:black; color:white;")

        self.itemChanged.connect(self.changeCheckState)

        for q in mainwindow.userprofile.quirks:
            item = PesterQuirkItem(q)
            self.addItem(item, False)
        self.changeCheckState()
        #self.setDragEnabled(True)
        #self.setDragDropMode(gui.QAbstractItemView.InternalMove)
        self.setDropIndicatorShown(True)
        self.setSortingEnabled(False)
        self.setIndentation(15)
        self.header().hide()

    def addItem(self, item, new=True):
        item.setFlags(core.Qt.ItemIsSelectable | core.Qt.ItemIsDragEnabled | core.Qt.ItemIsUserCheckable | core.Qt.ItemIsEnabled)
        if item.quirk.on:
            item.setCheckState(0, 2)
        else:
            item.setCheckState(0, 0)
        if new:
            curgroup = self.currentItem()
            if curgroup:
                if curgroup.parent(): curgroup = curgroup.parent()
                item.quirk.quirk["group"] = item.quirk.group = curgroup.text(0)
        found = self.findItems(item.quirk.group, core.Qt.MatchExactly)
        if len(found) > 0:
            found[0].addChild(item)
        else:
            child_1 = widgets.QTreeWidgetItem([item.quirk.group])
            self.addTopLevelItem(child_1)
            child_1.setFlags(child_1.flags() | core.Qt.ItemIsUserCheckable | core.Qt.ItemIsEnabled)
            child_1.setChildIndicatorPolicy(widgets.QTreeWidgetItem.DontShowIndicatorWhenChildless)
            child_1.setCheckState(0,0)
            child_1.setExpanded(True)
            child_1.addChild(item)
        self.changeCheckState()

    def currentQuirk(self):
        if type(self.currentItem()) is PesterQuirkItem:
            return self.currentItem()
        else: return None

    @core.pyqtSlot()
    def upShiftQuirk(self):
        found = self.findItems(self.currentItem().text(0), core.Qt.MatchExactly)
        if len(found): # group
            i = self.indexOfTopLevelItem(found[0])
            if i > 0:
                expand = found[0].isExpanded()
                shifted_item = self.takeTopLevelItem(i)
                self.insertTopLevelItem(i-1, shifted_item)
                shifted_item.setExpanded(expand)
                self.setCurrentItem(shifted_item)
        else: # quirk
            found = self.findItems(self.currentItem().text(0), core.Qt.MatchExactly | core.Qt.MatchRecursive)
            for f in found:
                if not f.isSelected(): continue
                if not f.parent(): continue
                i = f.parent().indexOfChild(f)
                if i > 0: # keep in same group
                    p = f.parent()
                    shifted_item = f.parent().takeChild(i)
                    p.insertChild(i-1, shifted_item)
                    self.setCurrentItem(shifted_item)
                else: # move to another group
                    j = self.indexOfTopLevelItem(f.parent())
                    if j <= 0: continue
                    shifted_item = f.parent().takeChild(i)
                    self.topLevelItem(j-1).addChild(shifted_item)
                    self.setCurrentItem(shifted_item)
            self.changeCheckState()

    @core.pyqtSlot()
    def downShiftQuirk(self):
        found = self.findItems(self.currentItem().text(0), core.Qt.MatchExactly)
        if len(found): # group
            i = self.indexOfTopLevelItem(found[0])
            if i < self.topLevelItemCount()-1 and i >= 0:
                expand = found[0].isExpanded()
                shifted_item = self.takeTopLevelItem(i)
                self.insertTopLevelItem(i+1, shifted_item)
                shifted_item.setExpanded(expand)
                self.setCurrentItem(shifted_item)
        else: # quirk
            found = self.findItems(self.currentItem().text(0), core.Qt.MatchExactly | core.Qt.MatchRecursive)
            for f in found:
                if not f.isSelected(): continue
                if not f.parent(): continue
                i = f.parent().indexOfChild(f)
                if i < f.parent().childCount()-1 and i >= 0:
                    p = f.parent()
                    shifted_item = f.parent().takeChild(i)
                    p.insertChild(i+1, shifted_item)
                    self.setCurrentItem(shifted_item)
                else:
                    j = self.indexOfTopLevelItem(f.parent())
                    if j >= self.topLevelItemCount()-1 or j < 0: continue
                    shifted_item = f.parent().takeChild(i)
                    self.topLevelItem(j+1).insertChild(0, shifted_item)
                    self.setCurrentItem(shifted_item)
            self.changeCheckState()

    @core.pyqtSlot()
    def removeCurrent(self):
        i = self.currentItem()
        found = self.findItems(i.text(0), core.Qt.MatchExactly | core.Qt.MatchRecursive)
        for f in found:
            if not f.isSelected(): continue
            if not f.parent(): # group
                msgbox = gui.QMessageBox()
                msgbox.setStyleSheet(self.mainwindow.theme["main/defaultwindow/style"])
                msgbox.setWindowTitle("WARNING!")
                msgbox.setInformativeText("Are you sure you want to delete the quirk group: %s" % (f.text(0)))
                msgbox.setStandardButtons(gui.QMessageBox.Ok | gui.QMessageBox.Cancel)
                ret = msgbox.exec_()
                if ret == gui.QMessageBox.Ok:
                    self.takeTopLevelItem(self.indexOfTopLevelItem(f))
            else:
                f.parent().takeChild(f.parent().indexOfChild(f))
        self.changeCheckState()

    @core.pyqtSlot()
    def addQuirkGroup(self):
        if not hasattr(self, 'addgroupdialog'):
            self.addgroupdialog = None
        if not self.addgroupdialog:
            (gname, ok) = widgets.QInputDialogtText(self, "Add Group", "Enter a name for the new quirk group:")
            if ok:
                gname = str(gname)
                if re.search("[^A-Za-z0-9_\s]", gname) is not None:
                    msgbox = gui.QMessageBox()
                    msgbox.setInformativeText("THIS IS NOT A VALID GROUP NAME")
                    msgbox.setStandardButtons(gui.QMessageBox.Ok)
                    ret = msgbox.exec_()
                    self.addgroupdialog = None
                    return
                found = self.findItems(gname, core.Qt.MatchExactly)
                if found:
                    msgbox = gui.QMessageBox()
                    msgbox.setInformativeText("THIS QUIRK GROUP ALREADY EXISTS")
                    msgbox.setStandardButtons(gui.QMessageBox.Ok)
                    ret = msgbox.exec_()
                    return
                child_1 = gui.QTreeWidgetItem([gname])
                self.addTopLevelItem(child_1)
                child_1.setFlags(child_1.flags() | core.Qt.ItemIsUserCheckable | core.Qt.ItemIsEnabled)
                child_1.setChildIndicatorPolicy(gui.QTreeWidgetItem.DontShowIndicatorWhenChildless)
                child_1.setCheckState(0,0)
                child_1.setExpanded(True)

            self.addgroupdialog = None

    @core.pyqtSlot()
    def changeCheckState(self):
        index = self.indexOfTopLevelItem(self.currentItem())
        if index == -1:
            for i in range(self.topLevelItemCount()):
                allChecked = True
                noneChecked = True
                for j in range(self.topLevelItem(i).childCount()):
                    if self.topLevelItem(i).child(j).checkState(0):
                        noneChecked = False
                    else:
                        allChecked = False
                if allChecked:    self.topLevelItem(i).setCheckState(0, 2)
                elif noneChecked: self.topLevelItem(i).setCheckState(0, 0)
                else:             self.topLevelItem(i).setCheckState(0, 1)
        else:
            state = self.topLevelItem(index).checkState(0)
            for j in range(self.topLevelItem(index).childCount()):
                self.topLevelItem(index).child(j).setCheckState(0, state)

from copy import copy
from convo import PesterInput, PesterText
from parsetools import convertTags, lexMessage, splitMessage, mecmd, colorBegin, colorEnd, img2smiley, smiledict
from dataobjs import pesterQuirks, PesterHistory
class QuirkTesterWindow(widgets.QDialog):
    def __init__(self, parent):
        widgets.QDialog.__init__(self, parent)
        self.prnt = parent
        self.mainwindow = parent.mainwindow
        self.setStyleSheet(self.mainwindow.theme["main/defaultwindow/style"])
        self.setWindowTitle("Quirk Tester")
        self.resize(350,300)

        self.textArea = PesterText(self.mainwindow.theme, self)
        self.textInput = PesterInput(self.mainwindow.theme, self)
        self.textInput.setFocus()

        self.textInput.returnPressed.connect(self.sentMessage)

        self.chumopen = True
        self.chum = self.mainwindow.profile()
        self.history = PesterHistory()

        layout_0 = widgets.QVBoxLayout()
        layout_0.addWidget(self.textArea)
        layout_0.addWidget(self.textInput)
        self.setLayout(layout_0)

    def parent(self):
        return self.prnt

    def clearNewMessage(self):
        pass
    @core.pyqtSlot()
    def sentMessage(self):
        text = str(self.textInput.text())
        if text == "" or text[0:11] == "PESTERCHUM:":
            return
        self.history.add(text)
        quirks = pesterQuirks(self.parent().testquirks())
        lexmsg = lexMessage(text)
        if type(lexmsg[0]) is not mecmd:
            try:
                lexmsg = quirks.apply(lexmsg)
            except Exception as e:
                msgbox = gui.QMessageBox()
                msgbox.setText("Whoa there! There seems to be a problem.")
                msgbox.setInformativeText("A quirk seems to be having a problem. (Possibly you're trying to capture a non-existant group?)\n\
                %s" % e)
                msgbox.exec_()
                return
        lexmsgs = splitMessage(lexmsg)

        for lm in lexmsgs:
            serverMsg = copy(lm)
            self.addMessage(lm, True)
            text = convertTags(serverMsg, "ctag")
        self.textInput.setText("")
    def addMessage(self, msg, me=True):
        if type(msg) in [str, str]:
            lexmsg = lexMessage(msg)
        else:
            lexmsg = msg
        if me:
            chum = self.mainwindow.profile()
        else:
            chum = self.chum
        self.textArea.addMessage(lexmsg, chum)

    def closeEvent(self, event):
        self.parent().quirktester = None

class PesterQuirkTypes(widgets.QDialog):
    def __init__(self, parent, quirk=None):
        widgets.QDialog.__init__(self, parent)
        self.mainwindow = parent.mainwindow
        self.setStyleSheet(self.mainwindow.theme["main/defaultwindow/style"])
        self.setWindowTitle("Quirk Wizard")
        self.resize(500,310)

        self.quirk = quirk
        self.pages = widgets.QStackedWidget(self)

        self.next = widgets.QPushButton("Next", self)
        self.next.setDefault(True)
        self.__next__.clicked.connect(self.nextPage)
        self.back = widgets.QPushButton("Back", self)
        self.back.setEnabled(False)
        self.back.clicked.connect(self.backPage)
        self.cancel = widgets.QPushButton("Cancel", self)
        self.cancel.clicked.connect(self.reject)
        layout_2 = widgets.QHBoxLayout()
        layout_2.setAlignment(core.Qt.AlignRight)
        layout_2.addWidget(self.back)
        layout_2.addWidget(self.__next__)
        layout_2.addSpacing(5)
        layout_2.addWidget(self.cancel)

        vr = widgets.QFrame()
        vr.setFrameShape(widgets.QFrame.VLine)
        vr.setFrameShadow(widgets.QFramen.Sunken)
        vr2 = widgets.QFrame()
        vr2.setFrameShape(widgets.QFrame.VLine)
        vr2.setFrameShadow(widgets.QFrame.Sunken)

        self.funclist = widgets.QListWidget(self)
        self.funclist.setStyleSheet("color: #000000; background-color: #FFFFFF;")
        self.funclist2 = widgets.QListWidget(self)
        self.funclist2.setStyleSheet("color: #000000; background-color: #FFFFFF;")

        funcs = [q+"()" for q in list(quirkloader.quirks.keys())]
        funcs.sort()
        self.funclist.addItems(funcs)
        self.funclist2.addItems(funcs)

        self.reloadQuirkFuncButton = widgets.QPushButton("RELOAD FUNCTIONS", self)
        self.reloadQuirkFuncButton.clicked.connect(self.reloadQuirkFuncSlot)
        self.reloadQuirkFuncButton2 = widgets.QPushButton("RELOAD FUNCTIONS", self)
        self.reloadQuirkFuncButton2.clicked.connect(self.reloadQuirkFuncSlot)

        self.funclist.setMaximumWidth(160)
        self.funclist.resize(160,50)
        self.funclist2.setMaximumWidth(160)
        self.funclist2.resize(160,50)
        layout_f = widgets.QVBoxLayout()
        layout_f.addWidget(widgets.QLabel("Available Regexp\nFunctions"))
        layout_f.addWidget(self.funclist)
        layout_f.addWidget(self.reloadQuirkFuncButton)
        layout_g = widgets.QVBoxLayout()
        layout_g.addWidget(widgets.QLabel("Available Regexp\nFunctions"))
        layout_g.addWidget(self.funclist2)
        layout_g.addWidget(self.reloadQuirkFuncButton2)

        # Pages
        # Type select
        widget = widgets.QWidget()
        self.pages.addWidget(widget)
        layout_select = widgets.QVBoxLayout(widget)
        layout_select.setAlignment(core.Qt.AlignTop)
        self.radios = []
        self.radios.append(gui.QRadioButton("Prefix", self))
        self.radios.append(gui.QRadioButton("Suffix", self))
        self.radios.append(gui.QRadioButton("Simple Replace", self))
        self.radios.append(gui.QRadioButton("Regexp Replace", self))
        self.radios.append(gui.QRadioButton("Random Replace", self))
        self.radios.append(gui.QRadioButton("Mispeller", self))

        layout_select.addWidget(widgets.QLabel("Select Quirk Type:"))
        for r in self.radios:
            layout_select.addWidget(r)

        # Prefix
        widget = widgets.QWidget()
        self.pages.addWidget(widget)
        layout_prefix = widgets.QVBoxLayout(widget)
        layout_prefix.setAlignment(core.Qt.AlignTop)
        layout_prefix.addWidget(widgets.QLabel("Prefix"))
        layout_3 = widgets.QHBoxLayout()
        layout_3.addWidget(widgets.QLabel("Value:"))
        layout_3.addWidget(widgets.QLineEdit())
        layout_prefix.addLayout(layout_3)

        # Suffix
        widget = widgets.QWidget()
        self.pages.addWidget(widget)
        layout_suffix = widgets.QVBoxLayout(widget)
        layout_suffix.setAlignment(core.Qt.AlignTop)
        layout_suffix.addWidget(widgets.QLabel("Suffix"))
        layout_3 = widgets.QHBoxLayout()
        layout_3.addWidget(widgets.QLabel("Value:"))
        layout_3.addWidget(widgets.QLineEdit())
        layout_suffix.addLayout(layout_3)

        # Simple Replace
        widget = widgets.QWidget()
        self.pages.addWidget(widget)
        layout_replace = widgets.QVBoxLayout(widget)
        layout_replace.setAlignment(core.Qt.AlignTop)
        layout_replace.addWidget(widgets.QLabel("Simple Replace"))
        layout_3 = widgets.QHBoxLayout()
        layout_3.addWidget(widgets.QLabel("Replace:"))
        layout_3.addWidget(widgets.QLineEdit())
        layout_replace.addLayout(layout_3)
        layout_3 = widgets.QHBoxLayout()
        layout_3.addWidget(widgets.QLabel("With:"))
        layout_3.addWidget(widgets.QLineEdit())
        layout_replace.addLayout(layout_3)

        # Regexp Replace
        widget = widgets.QWidget()
        self.pages.addWidget(widget)
        layout_all = widgets.QHBoxLayout(widget)
        layout_regexp = widgets.QVBoxLayout()
        layout_regexp.setAlignment(core.Qt.AlignTop)
        layout_regexp.addWidget(widgets.QLabel("Regexp Replace"))
        layout_3 = widgets.QHBoxLayout()
        layout_3.addWidget(widgets.QLabel("Regexp:"))
        layout_3.addWidget(widgets.QLineEdit())
        layout_regexp.addLayout(layout_3)
        layout_3 = widgets.QHBoxLayout()
        layout_3.addWidget(widgets.QLabel("Replace With:"))
        layout_3.addWidget(widgets.QLineEdit())
        layout_regexp.addLayout(layout_3)
        layout_all.addLayout(layout_f)
        layout_all.addWidget(vr)
        layout_all.addLayout(layout_regexp)

        # Random Replace
        widget = widgets.QWidget()
        self.pages.addWidget(widget)
        layout_all = widgets.QHBoxLayout(widget)
        layout_random = widgets.QVBoxLayout()
        layout_random.setAlignment(core.Qt.AlignTop)
        layout_random.addWidget(widgets.QLabel("Random Replace"))
        layout_5 = widgets.QHBoxLayout()
        regexpl = widgets.QLabel("Regexp:", self)
        self.regexp = widgets.QLineEdit("", self)
        layout_5.addWidget(regexpl)
        layout_5.addWidget(self.regexp)
        replacewithl = widgets.QLabel("Replace With:", self)
        layout_all.addLayout(layout_g)
        layout_all.addWidget(vr2)
        layout_all.addLayout(layout_random)

        layout_6 = widgets.QVBoxLayout()
        layout_7 = widgets.QHBoxLayout()
        self.replacelist = widgets.QListWidget(self)
        self.replaceinput = widgets.QLineEdit(self)
        addbutton = widgets.QPushButton("ADD", self)
        addbutton.clicked.connect(self.addRandomString)
        removebutton = widgets.QPushButton("REMOVE", self)
        removebutton.clicked.connect(self.removeRandomString)
        layout_7.addWidget(addbutton)
        layout_7.addWidget(removebutton)
        layout_6.addLayout(layout_5)
        layout_6.addWidget(replacewithl)
        layout_6.addWidget(self.replacelist)
        layout_6.addWidget(self.replaceinput)
        layout_6.addLayout(layout_7)
        layout_random.addLayout(layout_6)

        # Misspeller
        widget = widgets.QWidget()
        self.pages.addWidget(widget)
        layout_mispeller = widgets.QVBoxLayout(widget)
        layout_mispeller.setAlignment(core.Qt.AlignTop)
        layout_mispeller.addWidget(widgets.QLabel("Mispeller"))
        layout_1 = widgets.QHBoxLayout()
        zero = widgets.QLabel("1%", self)
        hund = widgets.QLabel("100%", self)
        self.current = widgets.QLabel("50%", self)
        self.current.setAlignment(core.Qt.AlignHCenter)
        self.slider = widgets.QSlider(core.Qt.Horizontal, self)
        self.slider.setMinimum(1)
        self.slider.setMaximum(100)
        self.slider.setValue(50)
        self.slider.valueChanged.connect(self.printValue)
        layout_1.addWidget(zero)
        layout_1.addWidget(self.slider)
        layout_1.addWidget(hund)
        layout_mispeller.addLayout(layout_1)
        layout_mispeller.addWidget(self.current)

        layout_0 = widgets.QVBoxLayout()
        layout_0.addWidget(self.pages)
        layout_0.addLayout(layout_2)

        if quirk:
            types = ["prefix","suffix","replace","regexp","random","spelling"]
            for (i,r) in enumerate(self.radios):
                if i == types.index(quirk.quirk.type):
                    r.setChecked(True)
            self.changePage(types.index(quirk.quirk.type)+1)
            page = self.pages.currentWidget().layout()
            q = quirk.quirk.quirk
            if q["type"] in ("prefix","suffix"):
                page.itemAt(1).layout().itemAt(1).widget().setText(q["value"])
            elif q["type"] == "replace":
                page.itemAt(1).layout().itemAt(1).widget().setText(q["from"])
                page.itemAt(2).layout().itemAt(1).widget().setText(q["to"])
            elif q["type"] == "regexp":
                page.itemAt(2).layout().itemAt(1).layout().itemAt(1).widget().setText(q["from"])
                page.itemAt(2).layout().itemAt(2).layout().itemAt(1).widget().setText(q["to"])
            elif q["type"] == "random":
                self.regexp.setText(q["from"])
                for v in q["randomlist"]:
                    item = widgets.QListWidgetItem(v, self.replacelist)
            elif q["type"] == "spelling":
                self.slider.setValue(q["percentage"])

        self.setLayout(layout_0)

    def closeEvent(self, event):
        self.parent().quirkadd = None

    def changePage(self, page):
        c = self.pages.count()
        if page >= c or page < 0: return
        self.back.setEnabled(page > 0)
        if page >= 1 and page <= 6:
            self.next.setText("Finish")
        else:
            self.next.setText("Next")
        self.pages.setCurrentIndex(page)
    @core.pyqtSlot()
    def nextPage(self):
        if self.next.text() == "Finish":
            self.accept()
            return
        cur = self.pages.currentIndex()
        if cur == 0:
            for (i,r) in enumerate(self.radios):
                if r.isChecked():
                    self.changePage(i+1)
        else:
            self.changePage(cur+1)
    @core.pyqtSlot()
    def backPage(self):
        cur = self.pages.currentIndex()
        if cur >= 1 and cur <= 6:
            self.changePage(0)

    @core.pyqtSlot(int)
    def printValue(self, value):
        self.current.setText(str(value)+"%")
    @core.pyqtSlot()
    def addRandomString(self):
        text = str(self.replaceinput.text())
        item = widgets.QListWidgetItem(text, self.replacelist)
        self.replaceinput.setText("")
        self.replaceinput.setFocus()
    @core.pyqtSlot()
    def removeRandomString(self):
        if not self.replacelist.currentItem():
            return
        else:
            self.replacelist.takeItem(self.replacelist.currentRow())
        self.replaceinput.setFocus()

    @core.pyqtSlot()
    def reloadQuirkFuncSlot(self):
        reloadQuirkFunctions()
        funcs = [q+"()" for q in list(quirkloader.quirks.keys())]
        funcs.sort()
        self.funclist.clear()
        self.funclist.addItems(funcs)
        self.funclist2.clear()
        self.funclist2.addItems(funcs)

class PesterChooseQuirks(widgets.QDialog):
    def __init__(self, config, theme, parent):
        widgets.QDialog.__init__(self, parent)
        self.setModal(False)
        self.config = config
        self.theme = theme
        self.mainwindow = parent
        self.setStyleSheet(self.theme["main/defaultwindow/style"])
        self.setWindowTitle("Set Quirks")

        self.quirkList = PesterQuirkList(self.mainwindow, self)

        self.addQuirkButton = widgets.QPushButton("ADD QUIRK", self)
        self.addQuirkButton.clicked.connect(self.addQuirkDialog)

        self.upShiftButton = widgets.QPushButton("^", self)
        self.downShiftButton = widgets.QPushButton("v", self)
        self.upShiftButton.setToolTip("Move quirk up one")
        self.downShiftButton.setToolTip("Move quirk down one")
        self.upShiftButton.clicked.connect(self.quirkList.upShiftQuirk)
        self.downShiftButton.clicked.connect(self.quirkList.downShiftQuirk)

        self.newGroupButton = widgets.QPushButton("*", self)
        self.newGroupButton.setToolTip("New Quirk Group")
        self.newGroupButton.clicked.connect(self.quirkList.addQuirkGroup)

        layout_quirklist = widgets.QHBoxLayout() #the nude layout quirklist
        layout_shiftbuttons = widgets.QVBoxLayout() #the shift button layout
        layout_shiftbuttons.addWidget(self.upShiftButton)
        layout_shiftbuttons.addWidget(self.newGroupButton)
        layout_shiftbuttons.addWidget(self.downShiftButton)
        layout_quirklist.addWidget(self.quirkList)
        layout_quirklist.addLayout(layout_shiftbuttons)

        layout_1 = widgets.QHBoxLayout()
        layout_1.addWidget(self.addQuirkButton)

        self.editSelectedButton = widgets.QPushButton("EDIT", self)
        self.editSelectedButton.clicked.connect(self.editSelected)
        self.removeSelectedButton = widgets.QPushButton("REMOVE", self)
        self.removeSelectedButton.clicked.connect(self.quirkList.removeCurrent)
        layout_3 = widgets.QHBoxLayout()
        layout_3.addWidget(self.editSelectedButton)
        layout_3.addWidget(self.removeSelectedButton)

        self.ok = widgets.QPushButton("OK", self)
        self.ok.setDefault(True)
        self.ok.clicked.connect(self.accept)
        self.test = widgets.QPushButton("TEST QUIRKS", self)
        self.test.clicked.connect(self.testQuirks)
        self.cancel = widgets.QPushButton("CANCEL", self)
        self.cancel.clicked.connect(self.reject)
        layout_ok = widgets.QHBoxLayout()
        layout_ok.addWidget(self.cancel)
        layout_ok.addWidget(self.test)
        layout_ok.addWidget(self.ok)

        layout_0 = widgets.QVBoxLayout()
        layout_0.addLayout(layout_quirklist)
        layout_0.addLayout(layout_1)
        #layout_0.addLayout(layout_2)
        layout_0.addLayout(layout_3)
        layout_0.addLayout(layout_ok)

        self.setLayout(layout_0)

    def quirks(self):
        u = []
        for i in range(self.quirkList.topLevelItemCount()):
            for j in range(self.quirkList.topLevelItem(i).childCount()):
                u.append(self.quirkList.topLevelItem(i).child(j).quirk)
        return u
        #return [self.quirkList.item(i).quirk for i in range(self.quirkList.count())]
    def testquirks(self):
        u = []
        for i in range(self.quirkList.topLevelItemCount()):
            for j in range(self.quirkList.topLevelItem(i).childCount()):
                item = self.quirkList.topLevelItem(i).child(j)
                if (item.checkState(0) == core.Qt.Checked):
                    u.append(item.quirk)
        return u

    @core.pyqtSlot()
    def testQuirks(self):
        if not hasattr(self, 'quirktester'):
            self.quirktester = None
        if self.quirktester:
            return
        self.quirktester = QuirkTesterWindow(self)
        self.quirktester.show()

    @core.pyqtSlot()
    def editSelected(self):
        q = self.quirkList.currentQuirk()
        if not q: return
        quirk = q.quirk
        self.addQuirkDialog(q)

    @core.pyqtSlot()
    def addQuirkDialog(self, quirk=None):
        if not hasattr(self, 'quirkadd'):
            self.quirkadd = None
        if self.quirkadd:
            return
        self.quirkadd = PesterQuirkTypes(self, quirk)
        self.quirkadd.accepted.connect(self.addQuirk)
        self.quirkadd.rejected.connect(self.closeQuirk)
        self.quirkadd.show()
    @core.pyqtSlot()
    def addQuirk(self):
        types = ["prefix","suffix","replace","regexp","random","spelling"]
        vdict = {}
        vdict["type"] = types[self.quirkadd.pages.currentIndex()-1]
        page = self.quirkadd.pages.currentWidget().layout()
        if vdict["type"] in ("prefix","suffix"):
            vdict["value"] = str(page.itemAt(1).layout().itemAt(1).widget().text())
        elif vdict["type"] == "replace":
            vdict["from"] = str(page.itemAt(1).layout().itemAt(1).widget().text())
            vdict["to"] = str(page.itemAt(2).layout().itemAt(1).widget().text())
        elif vdict["type"] == "regexp":
            vdict["from"] = str(page.itemAt(2).layout().itemAt(1).layout().itemAt(1).widget().text())
            vdict["to"] = str(page.itemAt(2).layout().itemAt(2).layout().itemAt(1).widget().text())
        elif vdict["type"] == "random":
            vdict["from"] = str(self.quirkadd.regexp.text())
            randomlist = [str(self.quirkadd.replacelist.item(i).text())
                          for i in range(0,self.quirkadd.replacelist.count())]
            vdict["randomlist"] = randomlist
        elif vdict["type"] == "spelling":
            vdict["percentage"] = self.quirkadd.slider.value()

        if vdict["type"] in ("regexp", "random"):
            try:
                re.compile(vdict["from"])
            except re.error as e:
                quirkWarning = gui.QMessageBox(self)
                quirkWarning.setText("Not a valid regular expression!")
                quirkWarning.setInformativeText("H3R3S WHY DUMP4SS: %s" % (e))
                quirkWarning.exec_()
                self.quirkadd = None
                return

        quirk = pesterQuirk(vdict)
        if self.quirkadd.quirk is None:
            item = PesterQuirkItem(quirk)
            self.quirkList.addItem(item)
        else:
            self.quirkadd.quirk.update(quirk)
        self.quirkadd = None
    @core.pyqtSlot()
    def closeQuirk(self):
        self.quirkadd = None

class PesterChooseTheme(widgets.QDialog):
    def __init__(self, config, theme, parent):
        widgets.QDialog.__init__(self, parent)
        self.config = config
        self.theme = theme
        self.parent = parent
        self.setStyleSheet(self.theme["main/defaultwindow/style"])
        self.setWindowTitle("Pick a theme")

        instructions = widgets.QLabel("Pick a theme:")

        avail_themes = config.availableThemes()
        self.themeBox = widgets.QComboBox(self)
        for (i, t) in enumerate(avail_themes):
            self.themeBox.addItem(t)
            if t == theme.name:
                self.themeBox.setCurrentIndex(i)

        self.ok = widgets.QPushButton("OK", self)
        self.ok.setDefault(True)
        self.ok.clicked.connect(self.accept)
        self.cancel = widgets.QPushButton("CANCEL", self)
        self.cancel.clicked.connect(self.reject)
        layout_ok = widgets.QHBoxLayout()
        layout_ok.addWidget(self.cancel)
        layout_ok.addWidget(self.ok)

        layout_0 = widgets.QVBoxLayout()
        layout_0.addWidget(instructions)
        layout_0.addWidget(self.themeBox)
        layout_0.addLayout(layout_ok)

        self.setLayout(layout_0)

        self.accepted.connect(parent.themeSelected)
        selfself.rejected.connect(parent.closeTheme)

class PesterChooseProfile(widgets.QDialog):
    def __init__(self, userprofile, config, theme, parent, collision=None):
        widgets.QDialog.__init__(self, parent)
        self.userprofile = userprofile
        self.theme = theme
        self.config = config
        self.parent = parent
        self.setStyleSheet(self.theme["main/defaultwindow/style"])

        self.currentHandle = widgets.QLabel("CHANGING FROM %s" % userprofile.chat.handle)
        self.chumHandle = widgets.QLineEdit(self)
        self.chumHandle.setMinimumWidth(200)
        self.chumHandleLabel = widgets.QLabel(self.theme["main/mychumhandle/label/text"], self)
        self.chumColorButton = widgets.QPushButton(self)
        self.chumColorButton.resize(50, 20)
        self.chumColorButton.setStyleSheet("background: %s" % (userprofile.chat.colorhtml()))
        self.chumcolor = userprofile.chat.color
        self.chumColorButton.clicked.connect(self.openColorDialog)
        layout_1 = widgets.QHBoxLayout()
        layout_1.addWidget(self.chumHandleLabel)
        layout_1.addWidget(self.chumHandle)
        layout_1.addWidget(self.chumColorButton)

        # available profiles?
        avail_profiles = self.config.availableProfiles()
        if avail_profiles:
            self.profileBox = widgets.QComboBox(self)
            self.profileBox.addItem("Choose a profile...")
            for p in avail_profiles:
                self.profileBox.addItem(p.chat.handle)
        else:
            self.profileBox = None

        self.defaultcheck = widgets.QCheckBox(self)
        self.defaultlabel = widgets.QLabel("Set This Profile As Default", self)
        layout_2 = widgets.QHBoxLayout()
        layout_2.addWidget(self.defaultlabel)
        layout_2.addWidget(self.defaultcheck)

        self.ok = widgets.QPushButton("OK", self)
        self.ok.setDefault(True)
        self.ok.clicked.connect(self.validateProfile)
        self.cancel = widgets.QPushButton("CANCEL", self)
        self.cancel.clicked.connect(self.reject)
        if not collision and avail_profiles:
            self.delete = widgets.QPushButton("DELETE", self)
            self.delete.clicked.connect(self.deleteProfile)
        layout_ok = widgets.QHBoxLayout()
        layout_ok.addWidget(self.cancel)
        layout_ok.addWidget(self.ok)

        layout_0 = widgets.QVBoxLayout()
        if collision:
            collision_warning = widgets.QLabel("%s is taken already! Pick a new profile." % (collision))
            layout_0.addWidget(collision_warning)
        else:
            layout_0.addWidget(self.currentHandle, alignment=core.Qt.AlignHCenter)
        layout_0.addLayout(layout_1)
        if avail_profiles:
            profileLabel = widgets.QLabel("Or choose an existing profile:", self)
            layout_0.addWidget(profileLabel)
            layout_0.addWidget(self.profileBox)
        layout_0.addLayout(layout_ok)
        if not collision and avail_profiles:
            layout_0.addWidget(self.delete)
        layout_0.addLayout(layout_2)
        self.errorMsg = widgets.QLabel(self)
        self.errorMsg.setStyleSheet("color:red;")
        layout_0.addWidget(self.errorMsg)
        self.setLayout(layout_0)

        self.accepted.connect(parent.profileSelected)
        self.rejected.connect(parent.closeProfile)

    @core.pyqtSlot()
    def openColorDialog(self):
        self.colorDialog = widgets.QColorDialog(self)
        color = self.colorDialog.getColor(initial=self.userprofile.chat.color)
        self.chumColorButton.setStyleSheet("background: %s" % color.name())
        self.chumcolor = color
        self.colorDialog = None

    @core.pyqtSlot()
    def validateProfile(self):
        if not self.profileBox or self.profileBox.currentIndex() == 0:
            handle = str(self.chumHandle.text())
            if not PesterProfile.checkLength(handle):
                self.errorMsg.setText("PROFILE HANDLE IS TOO LONG")
                return
            if not PesterProfile.checkValid(handle)[0]:
                self.errorMsg.setText("NOT A VALID CHUMTAG. REASON:\n%s" % (PesterProfile.checkValid(handle)[1]))
                return
        self.accept()

    @core.pyqtSlot()
    def deleteProfile(self):
        if self.profileBox and self.profileBox.currentIndex() > 0:
            handle = str(self.profileBox.currentText())
            if handle == self.parent.profile().handle:
                problem = gui.QMessageBox()
                problem.setStyleSheet(self.theme["main/defaultwindow/style"])
                problem.setWindowTitle("Problem!")
                problem.setInformativeText("You can't delete the profile you're currently using!")
                problem.setStandardButtons(gui.QMessageBox.Ok)
                problem.exec_()
                return
            msgbox = gui.QMessageBox()
            msgbox.setStyleSheet(self.theme["main/defaultwindow/style"])
            msgbox.setWindowTitle("WARNING!")
            msgbox.setInformativeText("Are you sure you want to delete the profile: %s" % (handle))
            msgbox.setStandardButtons(gui.QMessageBox.Ok | gui.QMessageBox.Cancel)
            ret = msgbox.exec_()
            if ret == gui.QMessageBox.Ok:
                try:
                    ostools.remove(_datadir,"profiles/",handle,".js")
                except OSError:
                    problem = gui.QMessageBox()
                    problem.setStyleSheet(self.theme["main/defaultwindow/style"])
                    problem.setWindowTitle("Problem!")
                    problem.setInformativeText("There was a problem deleting the profile: %s" % (handle))
                    problem.setStandardButtons(gui.QMessageBox.Ok)
                    problem.exec_()

class PesterMentions(widgets.QDialog):
    def __init__(self, window, theme, parent):
        widgets.QDialog.__init__(self, parent)
        self.setWindowTitle("Mentions")
        self.setModal(True)
        self.mainwindow = window
        self.theme = theme
        self.setStyleSheet(self.theme["main/defaultwindow/style"])

        self.mentionlist = widgets.QListWidget(self)
        self.mentionlist.addItems(self.mainwindow.userprofile.getMentions())

        self.addBtn = widgets.QPushButton("ADD MENTION", self)
        self.addBtn.clicked.connect(self.addMention)

        self.editBtn = widgets.QPushButton("EDIT", self)
        self.editBtn.clicked.connect(self.editSelected)
        self.rmBtn = widgets.QPushButton("REMOVE", self)
        self.rmBtn.clicked.connect(self.removeCurrent)
        layout_1 = widgets.QHBoxLayout()
        layout_1.addWidget(self.editBtn)
        layout_1.addWidget(self.rmBtn)

        self.ok = widgets.QPushButton("OK", self)
        self.ok.setDefault(True)
        self.ok.clicked.connect(self.accept)
        self.cancel = widgets.QPushButton("CANCEL", self)
        self.cancel.clicked.connect(self.reject)
        layout_2 = widgets.QHBoxLayout()
        layout_2.addWidget(self.cancel)
        layout_2.addWidget(self.ok)

        layout_0 = widgets.QVBoxLayout()
        layout_0.addWidget(self.mentionlist)
        layout_0.addWidget(self.addBtn)
        layout_0.addLayout(layout_1)
        layout_0.addLayout(layout_2)

        self.setLayout(layout_0)

    @core.pyqtSlot()
    def editSelected(self):
        m = self.mentionlist.currentItem()
        if not m:
            return
        self.addMention(m)

    @core.pyqtSlot()
    def addMention(self, mitem=None):
        d = {"label": "Mention:", "inputname": "value" }
        if mitem is not None:
            d["value"] = str(mitem.text())
        pdict = MultiTextDialog("ENTER MENTION", self, d).getText()
        if pdict is None:
            return
        try:
            re.compile(pdict["value"])
        except re.error as e:
            quirkWarning = gui.QMessageBox(self)
            quirkWarning.setText("Not a valid regular expression!")
            quirkWarning.setInformativeText("H3R3S WHY DUMP4SS: %s" % (e))
            quirkWarning.exec_()
        else:
            if mitem is None:
                self.mentionlist.addItem(pdict["value"])
            else:
                mitem.setText(pdict["value"])

    @core.pyqtSlot()
    def removeCurrent(self):
        i = self.mentionlist.currentRow()
        if i >= 0:
            self.mentionlist.takeItem(i)

class PesterOptions(widgets.QDialog):
    def __init__(self, config, theme, parent):
        widgets.QDialog.__init__(self, parent)
        self.setWindowTitle("Options")
        self.setModal(False)
        self.config = config
        self.theme = theme
        self.setStyleSheet(self.theme["main/defaultwindow/style"])

        layout_4 = widgets.QVBoxLayout()

        hr = widgets.QFrame()
        hr.setFrameShape(widgets.QFrame.VLine)
        hr.setFrameShadow(widgets.QFrame.Sunken)
        vr = widgets.QFrame()
        vr.setFrameShape(widgets.QFrame.VLine)
        vr.setFrameShadow(widgets.QFrame.Sunken)

        self.tabs = widgets.QButtonGroup(self)
        self.tabs.buttonClicked.connect(self.changePage)
        tabNames = ["Chum List", "Conversations", "Interface", "Sound", "Notifications", "Logging", "Idle/Updates", "Theme", "Connection"]
        if parent.advanced: tabNames.append("Advanced")
        for t in tabNames:
            button = widgets.QPushButton(t)
            self.tabs.addButton(button)
            layout_4.addWidget(button)
            button.setCheckable(True)
        self.tabs.button(-2).setChecked(True)
        self.pages = widgets.QStackedWidget(self)

        self.bandwidthcheck = widgets.QCheckBox("Low Bandwidth", self)
        if self.config.lowBandwidth():
            self.bandwidthcheck.setChecked(True)
        bandwidthLabel = widgets.QLabel("(Stops you for receiving the flood of MOODS,\n"
                                      " though stops chumlist from working properly)")
        font = bandwidthLabel.font()
        font.setPointSize(8)
        bandwidthLabel.setFont(font)

        self.autonickserv = widgets.QCheckBox("Auto-Identify with NickServ", self)
        self.autonickserv.setChecked(parent.userprofile.getAutoIdentify())
        self.autonickserv.stateChanged.connect(self.autoNickServChange)
        self.nickservpass = widgets.QLineEdit(self)
        self.nickservpass.setPlaceholderText("NickServ Password")
        self.nickservpass.setEchoMode(widgets.QLineEdit.PasswordEchoOnEdit)
        self.nickservpass.setText(parent.userprofile.getNickServPass())

        self.autojoinlist = widgets.QListWidget(self)
        self.autojoinlist.addItems(parent.userprofile.getAutoJoins())
        self.addAutoJoinBtn = widgets.QPushButton("Add",self)
        self.addAutoJoinBtn.clicked.connect(self.addAutoJoin)
        self.delAutoJoinBtn = widgets.QPushButton("Remove",self)
        self.delAutoJoinBtn.clicked.connect(self.delAutoJoin)
        
        self.tabcheck = widgets.QCheckBox("Tabbed Conversations", self)
        if self.config.tabs():
            self.tabcheck.setChecked(True)
        self.tabmemocheck = widgets.QCheckBox("Tabbed Memos", self)
        if self.config.tabMemos():
            self.tabmemocheck.setChecked(True)
        self.hideOffline = widgets.QCheckBox("Hide Offline Chums", self)
        if self.config.hideOfflineChums():
            self.hideOffline.setChecked(True)

        self.soundcheck = widgets.QCheckBox("Sounds On", self)
        self.soundcheck.stateChanged.connect(self.soundChange)
        self.chatsoundcheck = widgets.QCheckBox("Pester Sounds", self)
        self.chatsoundcheck.setChecked(self.config.chatSound())
        self.memosoundcheck = widgets.QCheckBox("Memo Sounds", self)
        self.memosoundcheck.setChecked(self.config.memoSound())
        self.memosoundcheck.stateChanged.connect(self.memoSoundChange)
        self.memopingcheck = widgets.QCheckBox("Memo Ping", self)
        self.memopingcheck.setChecked(self.config.memoPing())
        self.namesoundcheck = widgets.QCheckBox("Memo Mention (initials)", self)
        self.namesoundcheck.setChecked(self.config.nameSound())
        if self.config.soundOn():
            self.soundcheck.setChecked(True)
            if not self.memosoundcheck.isChecked():
                self.memoSoundChange(0)
        else:
            self.chatsoundcheck.setEnabled(False)
            self.memosoundcheck.setEnabled(False)
            self.memoSoundChange(0)

        self.editMentions = widgets.QPushButton("Edit Mentions", self)
        self.editMentions.clicked.connect(self.openMentions)

        self.volume = widgets.QSlider(core.Qt.Horizontal, self)
        self.volume.setMinimum(0)
        self.volume.setMaximum(100)
        self.volume.setValue(self.config.volume())
        self.volume.valueChanged.connect(self.printValue)
        self.currentVol = widgets.QLabel(str(self.config.volume())+"%", self)
        self.currentVol.setAlignment(core.Qt.AlignHCenter)


        self.timestampcheck = widgets.QCheckBox("Time Stamps", self)
        if self.config.showTimeStamps():
            self.timestampcheck.setChecked(True)

        self.timestampBox = widgets.QComboBox(self)
        self.timestampBox.addItem("12 hour")
        self.timestampBox.addItem("24 hour")
        if self.config.time12Format():
            self.timestampBox.setCurrentIndex(0)
        else:
            self.timestampBox.setCurrentIndex(1)
        self.secondscheck = widgets.QCheckBox("Show Seconds", self)
        if self.config.showSeconds():
            self.secondscheck.setChecked(True)

        self.memomessagecheck = widgets.QCheckBox("Show OP and Voice Messages in Memos", self)
        if self.config.opvoiceMessages():
            self.memomessagecheck.setChecked(True)

        if not ostools.isOSXBundle():
            self.animationscheck = widgets.QCheckBox("Use animated smilies", self)
            if self.config.animations():
                self.animationscheck.setChecked(True)
            animateLabel = widgets.QLabel("(Disable if you leave chats open for LOOOONG periods of time)")
            font = animateLabel.font()
            font.setPointSize(8)
            animateLabel.setFont(font)

        self.userlinkscheck = widgets.QCheckBox("Disable #Memo and @User Links", self)
        self.userlinkscheck.setChecked(self.config.disableUserLinks())
        self.userlinkscheck.setVisible(False)


        # Will add ability to turn off groups later
        #self.groupscheck = widgets.QCheckBox("Use Groups", self)
        #self.groupscheck.setChecked(self.config.useGroups())
        self.showemptycheck = widgets.QCheckBox("Show Empty Groups", self)
        self.showemptycheck.setChecked(self.config.showEmptyGroups())
        self.showonlinenumbers = widgets.QCheckBox("Show Number of Online Chums", self)
        self.showonlinenumbers.setChecked(self.config.showOnlineNumbers())

        sortLabel = widgets.QLabel("Sort Chums")
        self.sortBox = widgets.QComboBox(self)
        self.sortBox.addItem("Alphabetically")
        self.sortBox.addItem("By Mood")
        self.sortBox.addItem("Manually")
        method = self.config.sortMethod()
        if method >= 0 and method < self.sortBox.count():
            self.sortBox.setCurrentIndex(method)
        layout_3 = widgets.QHBoxLayout()
        layout_3.addWidget(sortLabel)
        layout_3.addWidget(self.sortBox, 10)

        self.logpesterscheck = widgets.QCheckBox("Log all Pesters", self)
        if self.config.logPesters() & self.config.LOG:
            self.logpesterscheck.setChecked(True)
        self.logmemoscheck = widgets.QCheckBox("Log all Memos", self)
        if self.config.logMemos() & self.config.LOG:
            self.logmemoscheck.setChecked(True)
        self.stamppestercheck = widgets.QCheckBox("Log Time Stamps for Pesters", self)
        if self.config.logPesters() & self.config.STAMP:
            self.stamppestercheck.setChecked(True)
        self.stampmemocheck = widgets.QCheckBox("Log Time Stamps for Memos", self)
        if self.config.logMemos() & self.config.STAMP:
            self.stampmemocheck.setChecked(True)

        self.idleBox = widgets.QSpinBox(self)
        self.idleBox.setStyleSheet("background:#FFFFFF")
        self.idleBox.setRange(1, 1440)
        self.idleBox.setValue(self.config.idleTime())
        layout_5 = widgets.QHBoxLayout()
        layout_5.addWidget(widgets.QLabel("Minutes before Idle:"))
        layout_5.addWidget(self.idleBox)

        self.updateBox = widgets.QComboBox(self)
        self.updateBox.addItem("Once a Day")
        self.updateBox.addItem("Once a Week")
        self.updateBox.addItem("Only on Start")
        self.updateBox.addItem("Never")
        check = self.config.checkForUpdates()
        if check >= 0 and check < self.updateBox.count():
            self.updateBox.setCurrentIndex(check)
        layout_6 = widgets.QHBoxLayout()
        layout_6.addWidget(widgets.QLabel("Check for\nPesterchum Updates:"))
        layout_6.addWidget(self.updateBox)

        if not ostools.isOSXLeopard():
            self.mspaCheck = widgets.QCheckBox("Check for MSPA Updates", self)
            self.mspaCheck.setChecked(self.config.checkMSPA())

        self.randomscheck = widgets.QCheckBox("Receive Random Encounters")
        self.randomscheck.setChecked(parent.userprofile.randoms)
        if not parent.randhandler.running:
            self.randomscheck.setEnabled(False)

        avail_themes = self.config.availableThemes()
        self.themeBox = widgets.QComboBox(self)
        notheme = (theme.name not in avail_themes)
        for (i, t) in enumerate(avail_themes):
            self.themeBox.addItem(t)
            if (not notheme and t == theme.name) or (notheme and t == "pesterchum"):
                self.themeBox.setCurrentIndex(i)
        self.refreshtheme = widgets.QPushButton("Refresh current theme", self)
        self.refreshtheme.clicked.connect(parent.themeSelectOverride)
        self.ghostchum = widgets.QCheckBox("Pesterdunk Ghostchum!!", self)
        self.ghostchum.setChecked(self.config.ghostchum())

        self.buttonOptions = ["Minimize to Taskbar", "Minimize to Tray", "Quit"]
        self.miniBox = widgets.QComboBox(self)
        self.miniBox.addItems(self.buttonOptions)
        self.miniBox.setCurrentIndex(self.config.minimizeAction())
        self.closeBox = widgets.QComboBox(self)
        self.closeBox.addItems(self.buttonOptions)
        self.closeBox.setCurrentIndex(self.config.closeAction())
        layout_mini = widgets.QHBoxLayout()
        layout_mini.addWidget(widgets.QLabel("Minimize"))
        layout_mini.addWidget(self.miniBox)
        layout_close = widgets.QHBoxLayout()
        layout_close.addWidget(widgets.QLabel("Close"))
        layout_close.addWidget(self.closeBox)

        self.pesterBlink = widgets.QCheckBox("Blink Taskbar on Pesters", self)
        if self.config.blink() & self.config.PBLINK:
            self.pesterBlink.setChecked(True)
        self.memoBlink = widgets.QCheckBox("Blink Taskbar on Memos", self)
        if self.config.blink() & self.config.MBLINK:
            self.memoBlink.setChecked(True)

        self.notifycheck = widgets.QCheckBox("Toast Notifications", self)
        if self.config.notify():
            self.notifycheck.setChecked(True)
        self.notifycheck.stateChanged.connect(self.notifyChange)
        self.notifyOptions = widgets.QComboBox(self)
        types = self.parent().tm.availableTypes()
        cur = self.parent().tm.currentType()
        self.notifyOptions.addItems(types)
        for (i,t) in enumerate(types):
            if t == cur:
                self.notifyOptions.setCurrentIndex(i)
                break
        self.notifyTypeLabel = widgets.QLabel("Type", self)
        layout_type = widgets.QHBoxLayout()
        layout_type.addWidget(self.notifyTypeLabel)
        layout_type.addWidget(self.notifyOptions)
        self.notifySigninCheck   = widgets.QCheckBox("Chum signs in", self)
        if self.config.notifyOptions() & self.config.SIGNIN:
            self.notifySigninCheck.setChecked(True)
        self.notifySignoutCheck  = widgets.QCheckBox("Chum signs out", self)
        if self.config.notifyOptions() & self.config.SIGNOUT:
            self.notifySignoutCheck.setChecked(True)
        self.notifyNewMsgCheck   = widgets.QCheckBox("New messages", self)
        if self.config.notifyOptions() & self.config.NEWMSG:
            self.notifyNewMsgCheck.setChecked(True)
        self.notifyNewConvoCheck = widgets.QCheckBox("Only new conversations", self)
        if self.config.notifyOptions() & self.config.NEWCONVO:
            self.notifyNewConvoCheck.setChecked(True)
        self.notifyMentionsCheck = widgets.QCheckBox("Memo Mentions (initials)", self)
        if self.config.notifyOptions() & self.config.INITIALS:
            self.notifyMentionsCheck.setChecked(True)
        self.notifyChange(self.notifycheck.checkState())

        if parent.advanced:
            self.modechange = widgets.QLineEdit(self)
            layout_change = widgets.QHBoxLayout()
            layout_change.addWidget(widgets.QLabel("Change:"))
            layout_change.addWidget(self.modechange)

        self.ok = widgets.QPushButton("OK", self)
        self.ok.setDefault(True)
        self.ok.clicked.connect(self.accept)
        self.cancel = widgets.QPushButton("CANCEL", self)
        self.cancel.clicked.connect(self.reject)
        layout_2 = widgets.QHBoxLayout()
        layout_2.addWidget(self.cancel)
        layout_2.addWidget(self.ok)

        # Tab layouts
        # Chum List
        widget = widgets.QWidget()
        layout_chumlist = widgets.QVBoxLayout(widget)
        layout_chumlist.setAlignment(core.Qt.AlignTop)
        layout_chumlist.addWidget(self.hideOffline)
        #layout_chumlist.addWidget(self.groupscheck)
        layout_chumlist.addWidget(self.showemptycheck)
        layout_chumlist.addWidget(self.showonlinenumbers)
        layout_chumlist.addLayout(layout_3)
        self.pages.addWidget(widget)

        # Conversations
        widget = widgets.QWidget()
        layout_chat = widgets.QVBoxLayout(widget)
        layout_chat.setAlignment(core.Qt.AlignTop)
        layout_chat.addWidget(self.timestampcheck)
        layout_chat.addWidget(self.timestampBox)
        layout_chat.addWidget(self.secondscheck)
        layout_chat.addWidget(self.memomessagecheck)
        if not ostools.isOSXBundle():
            layout_chat.addWidget(self.animationscheck)
            layout_chat.addWidget(animateLabel)
        layout_chat.addWidget(self.randomscheck)
        # Re-enable these when it's possible to disable User and Memo links
        #layout_chat.addWidget(hr)
        #layout_chat.addWidget(widgets.QLabel("User and Memo Links"))
        #layout_chat.addWidget(self.userlinkscheck)
        self.pages.addWidget(widget)

        # Interface
        widget = widgets.QWidget()
        layout_interface = widgets.QVBoxLayout(widget)
        layout_interface.setAlignment(core.Qt.AlignTop)
        layout_interface.addWidget(self.tabcheck)
        layout_interface.addWidget(self.tabmemocheck)
        layout_interface.addLayout(layout_mini)
        layout_interface.addLayout(layout_close)
        layout_interface.addWidget(self.pesterBlink)
        layout_interface.addWidget(self.memoBlink)
        self.pages.addWidget(widget)

        # Sound
        widget = widgets.QWidget()
        layout_sound = widgets.QVBoxLayout(widget)
        layout_sound.setAlignment(core.Qt.AlignTop)
        layout_sound.addWidget(self.soundcheck)
        layout_indent = widgets.QVBoxLayout()
        layout_indent.addWidget(self.chatsoundcheck)
        layout_indent.addWidget(self.memosoundcheck)
        layout_doubleindent = widgets.QVBoxLayout()
        layout_doubleindent.addWidget(self.memopingcheck)
        layout_doubleindent.addWidget(self.namesoundcheck)
        layout_doubleindent.addWidget(self.editMentions)
        layout_doubleindent.setContentsMargins(22,0,0,0)
        layout_indent.addLayout(layout_doubleindent)
        layout_indent.setContentsMargins(22,0,0,0)
        layout_sound.addLayout(layout_indent)
        layout_sound.addSpacing(15)
        layout_sound.addWidget(widgets.QLabel("Master Volume:", self))
        layout_sound.addWidget(self.volume)
        layout_sound.addWidget(self.currentVol)
        self.pages.addWidget(widget)

        # Notifications
        widget = widgets.QWidget()
        layout_notify = widgets.QVBoxLayout(widget)
        layout_notify.setAlignment(core.Qt.AlignTop)
        layout_notify.addWidget(self.notifycheck)
        layout_indent = widgets.QVBoxLayout()
        layout_indent.addLayout(layout_type)
        layout_indent.setContentsMargins(22,0,0,0)
        layout_indent.addWidget(self.notifySigninCheck)
        layout_indent.addWidget(self.notifySignoutCheck)
        layout_indent.addWidget(self.notifyNewMsgCheck)
        layout_doubleindent = widgets.QVBoxLayout()
        layout_doubleindent.addWidget(self.notifyNewConvoCheck)
        layout_doubleindent.setContentsMargins(22,0,0,0)
        layout_indent.addLayout(layout_doubleindent)
        layout_indent.addWidget(self.notifyMentionsCheck)
        #layout_indent.addWidget(self.e)
        layout_notify.addLayout(layout_indent)
        self.pages.addWidget(widget)

        # Logging
        widget = widgets.QWidget()
        layout_logs = widgets.QVBoxLayout(widget)
        layout_logs.setAlignment(core.Qt.AlignTop)
        layout_logs.addWidget(self.logpesterscheck)
        layout_logs.addWidget(self.logmemoscheck)
        layout_logs.addWidget(self.stamppestercheck)
        layout_logs.addWidget(self.stampmemocheck)
        self.pages.addWidget(widget)

        # Idle/Updates
        widget = widgets.QWidget()
        layout_idle = widgets.QVBoxLayout(widget)
        layout_idle.setAlignment(core.Qt.AlignTop)
        layout_idle.addLayout(layout_5)
        layout_idle.addLayout(layout_6)
        if not ostools.isOSXLeopard():
            layout_idle.addWidget(self.mspaCheck)
        self.pages.addWidget(widget)

        # Theme
        widget = widgets.QWidget()
        layout_theme = widgets.QVBoxLayout(widget)
        layout_theme.setAlignment(core.Qt.AlignTop)
        layout_theme.addWidget(widgets.QLabel("Pick a Theme:"))
        layout_theme.addWidget(self.themeBox)
        layout_theme.addWidget(self.refreshtheme)
        layout_theme.addWidget(self.ghostchum)
        self.pages.addWidget(widget)

        # Connection
        widget = widgets.QWidget()
        layout_connect = widgets.QVBoxLayout(widget)
        layout_connect.setAlignment(core.Qt.AlignTop)
        layout_connect.addWidget(self.bandwidthcheck)
        layout_connect.addWidget(bandwidthLabel)
        layout_connect.addWidget(self.autonickserv)
        layout_indent = widgets.QVBoxLayout()
        layout_indent.addWidget(self.nickservpass)
        layout_indent.setContentsMargins(22,0,0,0)
        layout_connect.addLayout(layout_indent)
        layout_connect.addWidget(widgets.QLabel("Auto-Join Memos:"))
        layout_connect.addWidget(self.autojoinlist)
        layout_8 = widgets.QHBoxLayout()
        layout_8.addWidget(self.addAutoJoinBtn)
        layout_8.addWidget(self.delAutoJoinBtn)
        layout_connect.addLayout(layout_8)
        self.pages.addWidget(widget)

        # Advanced
        if parent.advanced:
            widget = widgets.QWidget()
            layout_advanced = widgets.QVBoxLayout(widget)
            layout_advanced.setAlignment(core.Qt.AlignTop)
            layout_advanced.addWidget(widgets.QLabel("Current User Mode: %s" % parent.modes))
            layout_advanced.addLayout(layout_change)
            self.pages.addWidget(widget)

        layout_0 = widgets.QVBoxLayout()
        layout_1 = widgets.QHBoxLayout()
        layout_1.addLayout(layout_4)
        layout_1.addWidget(vr)
        layout_1.addWidget(self.pages)
        layout_0.addLayout(layout_1)
        layout_0.addSpacing(30)
        layout_0.addLayout(layout_2)

        self.setLayout(layout_0)

    @core.pyqtSlot(widgets.QPushButton)
    def changePage(self, page):
        if isinstance(page, int):
            self.tabs.button(page).setChecked(True)
        else:
            page = self.tabs.id(page)
            self.tabs.button(page).setChecked(True)
        # What is this, I don't even. qt, fuck
        page = -page - 2
        self.pages.setCurrentIndex(page)

    @core.pyqtSlot(int)
    def notifyChange(self, state):
        if state == 0:
            self.notifyTypeLabel.setEnabled(False)
            self.notifyOptions.setEnabled(False)
            self.notifySigninCheck.setEnabled(False)
            self.notifySignoutCheck.setEnabled(False)
            self.notifyNewMsgCheck.setEnabled(False)
            self.notifyNewConvoCheck.setEnabled(False)
            self.notifyMentionsCheck.setEnabled(False)
        else:
            self.notifyTypeLabel.setEnabled(True)
            self.notifyOptions.setEnabled(True)
            self.notifySigninCheck.setEnabled(True)
            self.notifySignoutCheck.setEnabled(True)
            self.notifyNewMsgCheck.setEnabled(True)
            self.notifyNewConvoCheck.setEnabled(True)
            self.notifyMentionsCheck.setEnabled(True)

    @core.pyqtSlot(int)
    def autoNickServChange(self, state):
        self.nickservpass.setEnabled(state != 0)

    @core.pyqtSlot()
    def addAutoJoin(self, mitem=None):
        d = {"label": "Memo:", "inputname": "value" }
        if mitem is not None:
            d["value"] = str(mitem.text())
        pdict = MultiTextDialog("ENTER MEMO", self, d).getText()
        if pdict is None:
            return
        pdict["value"] = "#" + pdict["value"]
        if mitem is None:
            items = self.autojoinlist.findItems(pdict["value"], core.Qt.MatchFixedString)
            if len(items) == 0:
                self.autojoinlist.addItem(pdict["value"])
        else:
            mitem.setText(pdict["value"])
            
    @core.pyqtSlot()
    def delAutoJoin(self):
        i = self.autojoinlist.currentRow()
        if i >= 0:
            self.autojoinlist.takeItem(i)

    @core.pyqtSlot(int)
    def soundChange(self, state):
        if state == 0:
            self.chatsoundcheck.setEnabled(False)
            self.memosoundcheck.setEnabled(False)
            self.memoSoundChange(0)
        else:
            self.chatsoundcheck.setEnabled(True)
            self.memosoundcheck.setEnabled(True)
            if self.memosoundcheck.isChecked():
                self.memoSoundChange(1)
    @core.pyqtSlot(int)
    def memoSoundChange(self, state):
        if state == 0:
            self.memopingcheck.setEnabled(False)
            self.namesoundcheck.setEnabled(False)
        else:
            self.memopingcheck.setEnabled(True)
            self.namesoundcheck.setEnabled(True)
    @core.pyqtSlot(int)
    def printValue(self, v):
        self.currentVol.setText(str(v)+"%")

    @core.pyqtSlot()
    def openMentions(self):
        if not hasattr(self, 'mentionmenu'):
            self.mentionmenu = None
        if not self.mentionmenu:
            self.mentionmenu = PesterMentions(self.parent(), self.theme, self)
            self.mentionmenu.accepted.connect(self.updateMentions)
            self.mentionmenu.rejected.connect(self.closeMentions)
            self.mentionmenu.show()
            self.mentionmenu.raise_()
            self.mentionmenu.activateWindow()
    @core.pyqtSlot()
    def closeMentions(self):
        self.mentionmenu.close()
        self.mentionmenu = None
    @core.pyqtSlot()
    def updateMentions(self):
        m = []
        for i in range(self.mentionmenu.mentionlist.count()):
            m.append(str(self.mentionmenu.mentionlist.item(i).text()))
        self.parent().userprofile.setMentions(m)
        self.mentionmenu = None

class PesterUserlist(widgets.QDialog):
    def __init__(self, config, theme, parent):
        widgets.QDialog.__init__(self, parent)
        self.setModal(False)
        self.config = config
        self.theme = theme
        self.mainwindow = parent
        self.setStyleSheet(self.theme["main/defaultwindow/style"])
        self.resize(200, 600)

        self.searchbox = widgets.QLineEdit(self)
        #self.searchbox.setStyleSheet(theme["convo/input/style"]) # which style is better?
        self.searchbox.setPlaceholderText("Search")
        self.searchbox.textChanged.connect(self.updateUsers)

        self.label = widgets.QLabel("USERLIST")
        self.userarea = RightClickList(self)
        self.userarea.setStyleSheet(self.theme["main/chums/style"])
        self.userarea.optionsMenu = widgets.QMenu(self)

        self.addChumAction = widgets.QAction(self.mainwindow.theme["main/menus/rclickchumlist/addchum"], self)
        self.addChumAction.triggered.connect(self.addChumSlot)
        self.pesterChumAction = widgets.QAction(self.mainwindow.theme["main/menus/rclickchumlist/pester"], self)
        self.pesterChumAction.triggered.connect(self.pesterChumSlot)
        self.userarea.optionsMenu.addAction(self.addChumAction)
        self.userarea.optionsMenu.addAction(self.pesterChumAction)

        self.ok = widgets.QPushButton("OK", self)
        self.ok.setDefault(True)
        self.ok.clicked.connect(self.accept)

        layout_0 = widgets.QVBoxLayout()
        layout_0.addWidget(self.label)
        layout_0.addWidget(self.userarea)
        layout_0.addWidget(self.searchbox)
        layout_0.addWidget(self.ok)

        self.setLayout(layout_0)

        self.mainwindow.namesUpdated.connect(self.updateUsers)

        self.mainwindow.userPresentSignal.connect(self.updateUserPresent)
        self.updateUsers()

        self.searchbox.setFocus()
    @core.pyqtSlot()
    def updateUsers(self):
        names = self.mainwindow.namesdb["#pesterchum"]
        self.userarea.clear()
        for n in names:
            if str(self.searchbox.text()) == "" or n.lower().find(str(self.searchbox.text()).lower()) != -1:
                item = widgets.QListWidgetItem(n)
                item.setForeground(gui.QBrush(gui.QColor(self.theme["main/chums/userlistcolor"])))
                self.userarea.addItem(item)
        self.userarea.sortItems()
    @core.pyqtSlot('QString', 'QString', 'QString')
    def updateUserPresent(self, handle, channel, update):
        h = str(handle)
        c = str(channel)
        if update == "quit":
            self.delUser(h)
        elif update == "left" and c == "#pesterchum":
            self.delUser(h)
        elif update == "join" and c == "#pesterchum":
            if str(self.searchbox.text()) == "" or h.lower().find(str(self.searchbox.text()).lower()) != -1:
                self.addUser(h)
    def addUser(self, name):
        item = widgets.QListWidgetItem(name)
        item.setForeground(gui.QBrush(gui.QColor(self.theme["main/chums/userlistcolor"])))
        self.userarea.addItem(item)
        self.userarea.sortItems()
    def delUser(self, name):
        matches = self.userarea.findItems(name, core.Qt.MatchFlags(0))
        for m in matches:
            self.userarea.takeItem(self.userarea.row(m))

    def changeTheme(self, theme):
        self.theme = theme
        self.setStyleSheet(theme["main/defaultwindow/style"])
        self.userarea.setStyleSheet(theme["main/chums/style"])
        self.addChumAction.setText(theme["main/menus/rclickchumlist/addchum"])
        for item in [self.userarea.item(i) for i in range(0, self.userarea.count())]:
            item.setForeground(gui.QColor(theme["main/chums/userlistcolor"]))

    @core.pyqtSlot()
    def addChumSlot(self):
        cur = self.userarea.currentItem()
        if not cur:
            return
        self.addChum.emit(cur.text())
    @core.pyqtSlot()
    def pesterChumSlot(self):
        cur = self.userarea.currentItem()
        if not cur:
            return
        self.pesterChum.emit(cur.text())

    addChum = core.pyqtSignal('QString')
    pesterChum = core.pyqtSignal('QString')


class MemoListItem(widgets.QTreeWidgetItem):
    def __init__(self, channel, usercount):
        widgets.QTreeWidgetItem.__init__(self, [channel, str(usercount)])
        self.target = channel
    def __lt__(self, other):
        column = self.treeWidget().sortColumn()
        if str(self.text(column)).isdigit() and str(other.text(column)).isdigit():
            return int(self.text(column)) < int(other.text(column))
        return self.text(column) < other.text(column)

class PesterMemoList(widgets.QDialog):
    def __init__(self, parent, channel=""):
        widgets.QDialog.__init__(self, parent)
        self.setModal(False)
        self.theme = parent.theme
        self.mainwindow = parent
        self.setStyleSheet(self.theme["main/defaultwindow/style"])
        self.resize(460, 300)

        self.label = widgets.QLabel("MEMOS")
        self.channelarea = RightClickTree(self)
        self.channelarea.setSelectionMode(widgets.QAbstractItemView.ExtendedSelection)
        self.channelarea.setStyleSheet(self.theme["main/chums/style"])
        self.channelarea.optionsMenu = widgets.QMenu(self)
        self.channelarea.setColumnCount(2)
        self.channelarea.setHeaderLabels(["Memo", "Users"])
        self.channelarea.setIndentation(0)
        self.channelarea.setColumnWidth(0,200)
        self.channelarea.setColumnWidth(1,10)
        self.channelarea.setSortingEnabled(True)
        self.channelarea.sortByColumn(0, core.Qt.AscendingOrder)
        self.channelarea.itemDoubleClicked.connect(self.AcceptSelection)

        self.orjoinlabel = widgets.QLabel("OR MAKE A NEW MEMO:")
        self.newmemo = widgets.QLineEdit(channel, self)
        self.secretChannel = widgets.QCheckBox("HIDDEN CHANNEL?", self)
        self.inviteChannel = widgets.QCheckBox("INVITATION ONLY?", self)

        self.timelabel = widgets.QLabel("TIMEFRAME:")
        self.timeslider = TimeSlider(core.Qt.Horizontal, self)
        self.timeinput = TimeInput(self.timeslider, self)

        self.cancel = widgets.QPushButton("CANCEL", self)
        self.cancel.clicked.connect(self.reject)
        self.join = widgets.QPushButton("JOIN", self)
        self.join.setDefault(True)
        self.join.clicked.connect(self.AcceptIfSelectionMade)
        layout_ok = widgets.QHBoxLayout()
        layout_ok.addWidget(self.cancel)
        layout_ok.addWidget(self.join)

        layout_left  = widgets.QVBoxLayout()
        layout_right = widgets.QVBoxLayout()
        layout_right.setAlignment(core.Qt.AlignTop)
        layout_0 = widgets.QVBoxLayout()
        layout_1 = widgets.QHBoxLayout()
        layout_left.addWidget(self.label)
        layout_left.addWidget(self.channelarea)
        layout_right.addWidget(self.orjoinlabel)
        layout_right.addWidget(self.newmemo)
        layout_right.addWidget(self.secretChannel)
        layout_right.addWidget(self.inviteChannel)
        layout_right.addWidget(self.timelabel)
        layout_right.addWidget(self.timeslider)
        layout_right.addWidget(self.timeinput)
        layout_1.addLayout(layout_left)
        layout_1.addLayout(layout_right)
        layout_0.addLayout(layout_1)
        layout_0.addLayout(layout_ok)

        self.setLayout(layout_0)

    def newmemoname(self):
        return self.newmemo.text()

    def SelectedMemos(self):
        return self.channelarea.selectedItems()

    def HasSelection(self):
        return len(self.SelectedMemos()) > 0 or self.newmemoname()

    def updateChannels(self, channels):
        for c in channels:
            item = MemoListItem(c[0][1:],c[1])
            item.setForeground(0, gui.QBrush(gui.QColor(self.theme["main/chums/userlistcolor"])))
            item.setForeground(1, gui.QBrush(gui.QColor(self.theme["main/chums/userlistcolor"])))
            item.setIcon(0, gui.QIcon(self.theme["memos/memoicon"]))
            self.channelarea.addTopLevelItem(item)

    def updateTheme(self, theme):
        self.theme = theme
        self.setStyleSheet(theme["main/defaultwindow/style"])
        for item in [self.userarea.item(i) for i in range(0, self.channelarea.count())]:
            item.setForeground(gui.QBrush(gui.QColor(self.theme["main/chums/userlistcolor"])))
            item.setIcon(gui.QIcon(theme["memos/memoicon"]))

    @core.pyqtSlot()
    def AcceptIfSelectionMade(self):
        if self.HasSelection():
            self.AcceptSelection()
            
    @core.pyqtSlot()
    def AcceptSelection(self):
        self.accept()


class LoadingScreen(widgets.QDialog):
    def __init__(self, parent=None):
        widgets.QDialog.__init__(self, parent, (core.Qt.CustomizeWindowHint |
                                              core.Qt.FramelessWindowHint))
        self.mainwindow = parent
        self.setStyleSheet(self.mainwindow.theme["main/defaultwindow/style"])

        self.loadinglabel = widgets.QLabel("CONN3CT1NG", self)
        self.cancel = widgets.QPushButton("QU1T >:?", self)
        self.ok = widgets.QPushButton("R3CONN3CT >:]", self)
        self.cancel.clicked.connect(self.reject)
        self.ok.clicked.connect(self.tryAgain)

        self.layout = widgets.QVBoxLayout()
        self.layout.addWidget(self.loadinglabel)
        layout_1 = widgets.QHBoxLayout()
        layout_1.addWidget(self.cancel)
        layout_1.addWidget(self.ok)
        self.layout.addLayout(layout_1)
        self.setLayout(self.layout)

    def hideReconnect(self):
        self.ok.hide()
    def showReconnect(self):
        self.ok.show()

    tryAgain = core.pyqtSignal()

class AboutPesterchum(widgets.QDialog):
    def __init__(self, parent=None):
        widgets.QDialog.__init__(self, parent)
        self.mainwindow = parent
        self.setStyleSheet(self.mainwindow.theme["main/defaultwindow/style"])

        self.title = widgets.QLabel("P3ST3RCHUM V. %s" % (_pcVersion))
        self.credits = widgets.QLabel("Programming by:\n\
  illuminatedwax (ghostDunk)\n\
  Kiooeht (evacipatedBox)\n\
  Lexi (lexicalNuance)\n\
  oakwhiz\n\
  alGore\n\
  Cerxi (binaryCabalist)\n\
\n\
Art by:\n\
  Grimlive (aquaMarinist)\n\
  Cerxi (binaryCabalist)\n\
\n\
Special Thanks:\n\
  ABT\n\
  gamblingGenocider\n\
  Eco-Mono")

        self.ok = widgets.QPushButton("OK", self)
        self.ok.clicked.connect(self.reject)

        layout_0 = widgets.QVBoxLayout()
        layout_0.addWidget(self.title)
        layout_0.addWidget(self.credits)
        layout_0.addWidget(self.ok)

        self.setLayout(layout_0)

class UpdatePesterchum(widgets.QDialog):
    def __init__(self, ver, url, parent=None):
        widgets.QDialog.__init__(self, parent)
        self.url = url
        self.mainwindow = parent
        self.setStyleSheet(self.mainwindow.theme["main/defaultwindow/style"])
        self.setWindowTitle("Pesterchum v%s Update" % (ver))
        self.setModal(False)

        self.title = widgets.QLabel("An update to Pesterchum is available!")

        layout_0 = widgets.QVBoxLayout()
        layout_0.addWidget(self.title)

        self.ok = widgets.QPushButton("D0WNL04D 4ND 1NST4LL N0W", self)
        self.ok.setDefault(True)
        self.ok.clicked.connect(self.accept)
        self.cancel = widgets.QPushButton("CANCEL", self)
        self.cancel.clicked.connect(self.reject)
        layout_2 = widgets.QHBoxLayout()
        layout_2.addWidget(self.cancel)
        layout_2.addWidget(self.ok)

        layout_0.addLayout(layout_2)

        self.setLayout(layout_0)

class AddChumDialog(widgets.QDialog):
    def __init__(self, avail_groups, parent=None):
        widgets.QDialog.__init__(self, parent)

        self.mainwindow = parent
        self.setStyleSheet(self.mainwindow.theme["main/defaultwindow/style"])
        self.setWindowTitle("Enter Chum Handle")
        self.setModal(True)

        self.title = widgets.QLabel("Enter Chum Handle")
        self.chumBox = widgets.QLineEdit(self)
        self.groupBox = widgets.QComboBox(self)
        avail_groups.sort()
        avail_groups.pop(avail_groups.index("Chums"))
        avail_groups.insert(0, "Chums")
        for g in avail_groups:
            self.groupBox.addItem(g)
        self.newgrouplabel = widgets.QLabel("Or make a new group:")
        self.newgroup = widgets.QLineEdit(self)

        layout_0 = widgets.QVBoxLayout()
        layout_0.addWidget(self.title)
        layout_0.addWidget(self.chumBox)
        layout_0.addWidget(self.groupBox)
        layout_0.addWidget(self.newgrouplabel)
        layout_0.addWidget(self.newgroup)

        self.ok = widgets.QPushButton("OK", self)
        self.ok.setDefault(True)
        self.ok.clicked.connect(self.accept)
        self.cancel = widgets.QPushButton("CANCEL", self)
        self.cancel.clicked.connect(self.reject)
        layout_2 = widgets.QHBoxLayout()
        layout_2.addWidget(self.cancel)
        layout_2.addWidget(self.ok)
