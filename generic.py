from PyQt5 import QtGui as gui, QtCore as core, QtWidgets as widgets
from datetime import timedelta

def contextMenuEvent(self, event):
    if event.reason() == gui.QContextMenuEvent.Mouse:
        listing = self.itemAt(event.pos())
        self.setCurrentItem(listing)
        optionsMenu = self.getOptionsMenu()
        if optionsMenu:
            optionsMenu.popup(event.globalPos())

def getOptionsMenu(self): return self.optionsMenu

class CaseInsensitiveDict(dict):
    def __setitem__(self, key, value):
        super(CaseInsensitiveDict, self).__setitem__(key.lower(), value)
    def __getitem__(self, key):
        return super(CaseInsensitiveDict, self).__getitem__(key.lower())
    def __contains__(self, key):
        return super(CaseInsensitiveDict, self).__contains__(key.lower())
    def has_key(self, key):
        return key.lower() in super(CaseInsensitiveDict, self)
    def __delitem__(self, key):
        super(CaseInsensitiveDict, self).__delitem__(key.lower())
        
class RightClickList(widgets.QListWidget):
    contextMenuEvent = contextMenuEvent
    getOptionsMenu = getOptionsMenu

class RightClickTree(widgets.QTreeWidget):
    contextMenuEvent = contextMenuEvent
    getOptionsMenu = getOptionsMenu
    

class MultiTextDialog(widgets.QDialog):
    def __init__(self, title, parent, *queries):
        widgets.QDialog.__init__(self, parent)
        self.setWindowTitle(title)
        if len(queries) == 0:
            return
        self.inputs = {}
        layout_1 = widgets.QHBoxLayout()
        for d in queries:
            label = d["label"]
            inputname = d["inputname"]
            value = d.get("value", "")
            l = widgets.QLabel(label, self)
            layout_1.addWidget(l)
            self.inputs[inputname] = widgets.QLineEdit(value, self)
            layout_1.addWidget(self.inputs[inputname])
        self.ok = widgets.QPushButton("OK",self)
        self.ok.clicked.connect(self.accept)
        self.cancel = widgets.QPushButton("CANCEL",self)
        self.cancel.clicked.connect(self.reject)
        
        self.ok.setDefault(True)
        layout_ok = widgets.QHBoxLayout()
        layout_ok.addWidget(self.cancel)
        layout_ok.addWidget(self.ok)

        layout_0 = widgets.QVBoxLayout()
        layout_0.addLayout(layout_1)
        layout_0.addLayout(layout_ok)

        self.setLayout(layout_0)
    def getText(self):
        r = self.exec_()
        if r == widgets.QDialog.Accepted:
            retval = {}
            for (name, widget) in list(self.inputs.items()):
                retval[name] = str(widget.text())
            return retval
        else:
            return None

class MovingWindow(widgets.QFrame):
    def __init__(self, *x, **y):
        widgets.QFrame.__init__(self, *x, **y)
        self.moving = None
        self.moveupdate = 0
    def mouseMoveEvent(self, event):
        if self.moving:
            move = event.globalPos() - self.moving
            self.move(move)
            self.moveupdate += 1
            if self.moveupdate > 5:
                self.moveupdate = 0
                self.update()
    def mousePressEvent(self, event):
        if event.button() == 1:
            self.moving = event.globalPos() - self.pos()
    def mouseReleaseEvent(self, event):
        if event.button() == 1:
            self.update()
            self.moving = None

class mysteryTime(timedelta):
    def __sub__(self, other):
        return self
    def __eq__(self, other):
        return isinstance(other,mysteryTime)
    def __neq__(self, other):
        return not isinstance(other,mysteryTime)

class NoneSound(object):
    def play(self): pass
    def set_volume(self, v): pass

class PesterList(list):
    def __init__(self, l):
        self.extend(l)

class PesterIcon(gui.QIcon):
    def __init__(self, *x):
        gui.QIcon.__init__(self, x[0])
        if isinstance(x[0], str):
            self.icon_pixmap = gui.QPixmap(x[0])
        else:
            self.icon_pixmap = None
    def realsize(self):
        if self.icon_pixmap:
            return self.icon_pixmap.size()
        else:
            try:
                return self.availableSizes()[0]
            except IndexError:
                return None

class WMButton(widgets.QPushButton):
    def __init__(self, icon, parent=None):
        widgets.QPushButton.__init__(self, icon, "", parent)
        self.setIconSize(icon.realsize())
        self.resize(icon.realsize())
        self.setFlat(True)
        self.setStyleSheet("QPushButton { padding: 0px; }")
        self.setAutoDefault(False)
