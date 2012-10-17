# Generate ui_update.pu with
# $ pyuic4 ui_updater.ui > ui_updater.py

import os, sys
import json
import sqlite3 as lite
from PyQt4 import QtCore, QtGui
from ui_updater import Ui_Dialog

class StartQT4(QtGui.QDialog):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        self.update = {}

        self.connect(self.ui.toolButton, QtCore.SIGNAL('pressed()'),
                     self, QtCore.SLOT('file_select()'))
        self.connect(self, QtCore.SIGNAL('accepted()'),
                     self, QtCore.SLOT('update()'))

    @QtCore.pyqtSlot()
    def file_select(self):
        filestr = QtGui.QFileDialog.getOpenFileName(self, self.tr("Select updater file"), "", self.tr("JSON (*.js)"))
        if filestr == "":
            return

        self.ui.lineEdit.setText(filestr);

        with open(filestr) as f:
            try:
                j = json.load(f)
                self.ui.plainTextEdit.setPlainText(json.dumps(j, indent=4))
            except:
                self.ui.plainTextEdit.setPlainText("")
                self.ui.label_status.setText("Error while loading")
                self.update = {}
            else:
                self.ui.label_status.setText("Loaded")
                self.update = j

    @QtCore.pyqtSlot()
    def update(self):
        if self.update == {}:
            return

        if "update" in self.update and not os.path.exists('test.db'):
            warning = QtGui.QMessageBox(QtGui.QMessageBox.Warning, "No database exists!", "Warning: No Pesterchum database exists to update!", QtGui.QMessageBox.Ok, self)
            warning.show()
            if "add" not in self.update:
                return

        with lite.connect('test.db') as con:
            con.row_factory = lite.Row
            cur = con.cursor()
            if "update" in self.update:
                cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [x[0].lower() for x in cur.fetchall()]
                print tables
                for table,rows in self.update['update'].iteritems():
                    table = table.lower()
                    if table not in tables:
                        continue
                    cur.execute("PRAGMA TABLE_INFO(%s)" % (table))
                    columns = cur.fetchall()
                    column_names = []
                    for v in columns:
                        column_names.append(v['name'].lower())
                    columns = column_names
                    for col, data in rows.iteritems():
                        if col.lower() not in columns:
                            continue
                        cur.execute("UPDATE %s SET %s=?" % (table, col), (data,))


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    myapp = StartQT4()
    myapp.show()
    sys.exit(app.exec_())

