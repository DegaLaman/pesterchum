import logging
import os
from string import Template
import json
import re
import codecs
import platform
from datetime import *
from time import strftime, time
from PyQt4 import QtGui, QtCore

import ostools
from generics import CaseInsensitiveDict
from mood import Mood
from dataobjs import PesterProfile, pesterQuirk, pesterQuirks
from parsetools import convertTags, addTimeInitial, themeChecker, ThemeException

_datadir = ostools.getDataDir()

class PesterLog(object):
    def __init__(self, handle, parent=None):
        global _datadir
        self.parent = parent
        self.handle = handle
        self.convos = {}
        self.logpath = _datadir+"logs"

    def log(self, handle, msg):
        if self.parent.config.time12Format():
            time = strftime("[%I:%M")
        else:
            time = strftime("[%H:%M")
        if self.parent.config.showSeconds():
            time += strftime(":%S] ")
        else:
            time += "] "
        if handle[0] == '#':
            if not self.parent.config.logMemos() & self.parent.config.LOG: return
            if not self.parent.config.logMemos() & self.parent.config.STAMP:
                time = ""
        else:
            if not self.parent.config.logPesters() & self.parent.config.LOG: return
            if not self.parent.config.logPesters() & self.parent.config.STAMP:
                time = ""
        if unicode(handle).upper() == "NICKSERV": return
        #watch out for illegal characters
        handle = re.sub(r'[<>:"/\\|?*]', "_", handle)
        bbcodemsg = time + convertTags(msg, "bbcode")
        html = time + convertTags(msg, "html")+"<br />"
        msg = time +convertTags(msg, "text")
        modes = {"bbcode": bbcodemsg, "html": html, "text": msg}
        if not self.convos.has_key(handle):
            time = datetime.now().strftime("%Y-%m-%d.%H.%M")
            self.convos[handle] = {}
            for (format, t) in modes.iteritems():
                if not os.path.exists("%s/%s/%s/%s" % (self.logpath, self.handle, handle, format)):
                    os.makedirs("%s/%s/%s/%s" % (self.logpath, self.handle, handle, format))
                try:
                    fp = codecs.open("%s/%s/%s/%s/%s.%s.txt" % (self.logpath, self.handle, handle, format, handle, time), encoding='utf-8', mode='a')
                except IOError:
                    errmsg = QtGui.QMessageBox(self)
                    errmsg.setText("Warning: Pesterchum could not open the log file for %s!" % (handle))
                    errmsg.setInformativeText("Your log for %s will not be saved because something went wrong. We suggest restarting Pesterchum. Sorry :(" % (handle))
                    errmsg.show()
                    continue
                self.convos[handle][format] = fp
        for (format, t) in modes.iteritems():
            f = self.convos[handle][format]
            if platform.system() == "Windows":
                f.write(t+"\r\n")
            else:
                f.write(t+"\r\n")
            f.flush()
    def finish(self, handle):
        if not self.convos.has_key(handle):
            return
        for f in self.convos[handle].values():
            f.close()
        del self.convos[handle]
    def close(self):
        for h in self.convos.keys():
            for f in self.convos[h].values():
                f.close()

class SQLConfig(object):
    def __init__(self, cur, conn):
        self.cur = cur
        self.conn = conn

    def __getitem__(self, name):
        name = name.lower()
        if name == 'defaultprofile':
            return self.defaultprofile()
        try:
            self.cur.execute("SELECT %s FROM Config" % (name))
        except lite.OperationalError:
            raise AttributeError
        value = self.cur.fetchone()[name]
        self.cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='Config'")
        row = self.cur.fetchone()
        sql = row['sql']
        sql = [x.lower() for x if re.split(' |,', sql)]
        if sql[sql.index(name)+1] == 'bool':
            return bool(value)
        else:
            return value

    def defaultprofile(self):
        self.cur.execute("SELECT Name FROM Profiles, Config ON Config.DefaultProfile=Profiles.Id")
        row = self.cur.fetchone()
        if row == None:
            return None
        return row['name']

    def __setitem__(self, name, value):
        name = name.lower()
        if name == 'defaultprofile':
            self.cur.execute("UPDATE Config SET DefaultProfile=(SELECT Id FROM People WHERE Name=?)", (value,))
        else:
            try:
                self.cur.execute("UPDATE Config SET [%s]=?" % (name), (value,))
            except lite.OperationalError:
                raise AttributeError
        self.conn.commit()

class userConfig(object):
    def __init__(self, parent):
        self.parent = parent
        # Use for bit flag log setting
        self.LOG = 1
        self.STAMP = 2
        # Use for bit flag blink
        self.PBLINK = 1
        self.MBLINK = 2
        # Use for bit flag notfications
        self.SIGNIN   = 1
        self.SIGNOUT  = 2
        self.NEWMSG   = 4
        self.NEWCONVO = 8
        self.INITIALS  = 16
        self.filename = _datadir+"pesterchum.db"
        self.conn = lite.connect(self.filename)
        self.conn.row_factory = lite.Row
        self.cur = self.con.cursor()
        self.config = SQLConfig(cur, conn)
        if self.config['defaultprofile']:
            self.userprofile = userProfile(self.config['defaultprofile'])
        else:
            self.userprofile = None

        self.logpath = _datadir+"logs"

        if not os.path.exists(self.logpath):
            os.makedirs(self.logpath)

    def chums(self):
        self.cur.execute("SELECT People.Name AS Handle FROM People, Chums ON Chums.Person = People.Id")
        return [x['handle'] for x in cur.fetchall()]
    def setChums(self, newchums):
        """newchums = list of strings of handles"""
        """This function serves to completely change the chums
           Before setting chums IT WILL COMPLETELY DROP ALL CURRENT CHUMS"""
        self.cur.execute("DELETE FROM Chums")
        for c in newchums:
            self.cur.execute("INSERT OR IGNORE INTO People (Name) VALUES(?)", (c,))
            self.cur.execute("INSERT OR IGNORE INTO Chums (Person) SELECT Id FROM People WHERE Name=?", (c,))
            self.conn.commit()
    def hideOfflineChums(self):
        return self.config['hideOfflineChums']
    def defaultprofile(self):
        return self.config['defaultprofile']
    def tabs(self):
        return self.config['tabs']
    def tabMemos(self):
        return self.config['tabmemos']
    def showTimeStamps(self):
        return config.showTimeStamps()
    def time12Format(self):
        return self.config['time12Format']
    def showSeconds(self):
        return self.config['showSeconds']
    def sortMethod(self):
        return self.config['sortMethod']
    def useGroups(self):
        return self.config['useGroups']
    def openDefaultGroup(self):
        self.cur.execute("SELECT (Open) FROM Groups WHERE Name='Chums'")
        return self.cur.fetchone()['open']
    def showEmptyGroups(self):
        return self.config['emptyGroups']
    def showOnlineNumbers(self):
        return self.config['onlineNumbers']
    def logPesters(self):
        return self.config['logPesters']
    def logMemos(self):
        return self.config['logMemos']
    def disableUserLinks(self):
        return not self.config['userLinks']
    def idleTime(self):
        return self.config['idleTime']
    def minimizeAction(self):
        return self.config['miniAction']
    def closeAction(self):
        return self.config['closeAction']
    def opvoiceMessages(self):
        return self.config['opvMessages']
    def animations(self):
        return self.config['animations']
    def checkForUpdates(self):
        return self.config['checkUpdates']
        """depricated so I can remember old bool conversion
        u = self.config.get('checkUpdates', 0)
        if type(u) == type(bool()):
            if u: u = 2
            else: u = 3
        return u"""
        # Once a day
        # Once a week
        # Only on start
        # Never
    def lastUCheck(self):
        return self.config['lastUCheck']
    def checkMSPA(self):
        return self.config['mspa']
    def blink(self):
        return self.config['blink']
    def notify(self):
        return self.config['notify']
    def notifyType(self):
        return self.config['notifyType']
    def notifyOptions(self):
        return self.config['notifyOptions']
        #return self.config.get('notifyOptions', self.SIGNIN | self.NEWMSG | self.NEWCONVO | self.INITIALS)
    def lowBandwidth(self):
        return self.config['lowBandwidth']
    def ghostchum(self):
        return self.config['ghostchum']
    def addChum(self, chum):
        if type(chum) is PesterProfile:
            self.cur.execute("INSERT OR REPLACE INTO People (Name, Color, Mood) VALUES(?,?,?)", (chum.handle, chum.color, chum.mood.value()))
            self.cur.execute("INSERT OR REPLACE INTO Chums (Person, [Group]) SELECT People.Id, Groups.Id FROM People, Groups WHERE People.Name=? AND Groups.Name=?", (chum.handle, chum.group))
        elif type(chum) in [str,unicode]:
            self.cur.execute("INSERT OR IGNORE INTO People (Name) VALUES(?)", (chum,))
            self.cur.execute("INSERT OR REPLACE INTO Chums (Person) SELECT People.Id FROM People WHERE People.Name=?", (chum,))
        self.conn.commit()
    def removeChum(self, chum):
        if type(chum) is PesterProfile:
            handle = chum.handle
        else:
            handle = chum
        self.cur.execute("DELETE FROM Chums WHERE Person = (SELECT Id FROM People WHERE Name=?)", (handle,))
        self.conn.commit()
    def getBlocklist(self):
        self.cur.execute("SELECT Name FROM Blocked, People ON People.Id=Blocked.Person")
        return [x[0] for x in self.cur.fetchall()]
    def addBlocklist(self, handle):
        self.cur.execute("INSERT OR IGNORE INTO Blocked (Person) SELECT People.Id FROM People WHERE People.Name=?", (handle,))
        self.conn.commit()
    def delBlocklist(self, handle):
        self.cur.execute("DELETE FROM Blocked WHERE Person = (SELECT Id FROM People WHERE Name?)", (handle,))
        self.cur.commit()
    def getGroups(self):
        self.cur.execute("SELECT Name, Open FROM Groups ORDER BY Ordering ASC")
        return [[name, bool(b)] for name,b in self.cur.fetchall()]
    def addGroup(self, group, open=True):
        self.cur.execute("INSERT OR REPLACE INTO Groups (Name, Open) VALUES(?,?)", (group, open))
        self.cur.execute("UPDATE Groups SET Ordering=(SELECT MAX(Ordering)+1 FROM Groups) WHERE Name=?", (group,))
        self.conn.commit()
    def delGroup(self, group):
        self.cur.execute("DELETE FROM Groups WHERE Name=?", (group,))
        self.conn.commit()
    def expandGroup(self, group, open=True):
        self.cur.execute("UPDATE Groups SET Open=? WHERE Name=?", (open, group))
        self.conn.commit()

    def server(self):
        if hasattr(self.parent, 'serverOverride'):
            return self.parent.serverOverride
        return self.config['server']
    def port(self):
        if hasattr(self.parent, 'portOverride'):
            return self.parent.portOverride
        return self.config['port']
    def soundOn(self):
        return self.config['soundOn']
    def chatSound(self):
        return self.config['chatSound']
    def memoSound(self):
        return self.config['memoSound']
    def memoPing(self):
        return self.config['pingSound']
    def nameSound(self):
        return self.config['nameSound']
    def volume(self):
        return self.config['volume']
    def trayMessage(self):
        return self.config['traymsg']
    def set(self, item, setting):
        self.config[item] = setting
    def availableThemes(self):
        themes = []
        # Load user themes.
        for dirname, dirnames, filenames in os.walk(_datadir+'themes'):
            for d in dirnames:
                themes.append(d)
        # Also load embedded themes.
        if _datadir:
            for dirname, dirnames, filenames in os.walk('themes'):
                for d in dirnames:
                    if d not in themes:
                        themes.append(d)
        themes.sort()
        return themes
    def availableProfiles(self):
        self.cur.execute("SELECT * FROM Profiles ORDER BY Name")
        return [userProfile(p) for p in self.cur.fetchall()]

class userProfile(object):
    def __init__(self, user):
        self.profiledir = _datadir+"profiles"

        if type(user) is PesterProfile:
            self.chat = user
            self.userprofile = {"handle":user.handle,
                                "color": unicode(user.color.name()),
                                "quirks": [],
                                "theme": "pesterchum"}
            self.theme = pesterTheme("pesterchum")
            self.chat.mood = Mood(self.theme["main/defaultmood"])
            self.lastmood = self.chat.mood.value()
            self.quirks = pesterQuirks([])
            self.randoms = False
            initials = self.chat.initials()
            if len(initials) >= 2:
                initials = (initials, "%s%s" % (initials[0].lower(), initials[1]), "%s%s" % (initials[0], initials[1].lower()))
                self.mentions = [r"\b(%s)\b" % ("|".join(initials))]
            else:
                self.mentions = []
        else:
            fp = open("%s/%s.js" % (self.profiledir, user))
            self.userprofile = json.load(fp)
            fp.close()
            try:
                self.theme = pesterTheme(self.userprofile["theme"])
            except ValueError, e:
                self.theme = pesterTheme("pesterchum")
            self.lastmood = self.userprofile.get('lastmood', self.theme["main/defaultmood"])
            self.chat = PesterProfile(self.userprofile["handle"],
                                      QtGui.QColor(self.userprofile["color"]),
                                      Mood(self.lastmood))
            self.quirks = pesterQuirks(self.userprofile["quirks"])
            if "randoms" not in self.userprofile:
                self.userprofile["randoms"] = False
            self.randoms = self.userprofile["randoms"]
            if "mentions" not in self.userprofile:
                initials = self.chat.initials()
                if len(initials) >= 2:
                    initials = (initials, "%s%s" % (initials[0].lower(), initials[1]), "%s%s" % (initials[0], initials[1].lower()))
                    self.userprofile["mentions"] = [r"\b(%s)\b" % ("|".join(initials))]
                else:
                    self.userprofile["mentions"] = []
            self.mentions = self.userprofile["mentions"]

    def setMood(self, mood):
        self.chat.mood = mood
    def setTheme(self, theme):
        self.theme = theme
        self.userprofile["theme"] = theme.name
        self.save()
    def setColor(self, color):
        self.chat.color = color
        self.userprofile["color"] = unicode(color.name())
        self.save()
    def setQuirks(self, quirks):
        self.quirks = quirks
        self.userprofile["quirks"] = self.quirks.plainList()
        self.save()
    def getRandom(self):
        return self.randoms
    def setRandom(self, random):
        self.randoms = random
        self.userprofile["randoms"] = random
        self.save()
    def getMentions(self):
        return self.mentions
    def setMentions(self, mentions):
        try:
            for (i,m) in enumerate(mentions):
                re.compile(m)
        except re.error, e:
            logging.error("#%s Not a valid regular expression: %s" % (i, e))
        else:
            self.mentions = mentions
            self.userprofile["mentions"] = mentions
            self.save()
    def getLastMood(self):
        return self.lastmood
    def setLastMood(self, mood):
        self.lastmood = mood.value()
        self.userprofile["lastmood"] = self.lastmood
        self.save()
    def getTheme(self):
        return self.theme
    def save(self):
        handle = self.chat.handle
        if handle[0:12] == "pesterClient":
            # dont save temp profiles
            return
        try:
            jsonoutput = json.dumps(self.userprofile)
        except ValueError, e:
            raise e
        fp = open("%s/%s.js" % (self.profiledir, handle), 'w')
        fp.write(jsonoutput)
        fp.close()
    @staticmethod
    def newUserProfile(chatprofile):
        if os.path.exists("%s/%s.js" % (_datadir+"profiles", chatprofile.handle)):
            newprofile = userProfile(chatprofile.handle)
        else:
            newprofile = userProfile(chatprofile)
            newprofile.save()
        return newprofile

class PesterProfileDB(dict):
    def __init__(self):
        self.logpath = _datadir+"logs"

        if not os.path.exists(self.logpath):
            os.makedirs(self.logpath)
        try:
            fp = open("%s/chums.js" % (self.logpath), 'r')
            chumdict = json.load(fp)
            fp.close()
        except IOError:
            chumdict = {}
            fp = open("%s/chums.js" % (self.logpath), 'w')
            json.dump(chumdict, fp)
            fp.close()
        except ValueError:
            chumdict = {}
            fp = open("%s/chums.js" % (self.logpath), 'w')
            json.dump(chumdict, fp)
            fp.close()

        u = []
        for (handle, c) in chumdict.iteritems():
            options = dict()
            if 'group' in c:
                options['group'] = c['group']
            if 'notes' in c:
                options['notes'] = c['notes']
            if 'color' not in c:
                c['color'] = "#000000"
            if 'mood' not in c:
                c['mood'] = "offline"
            u.append((handle, PesterProfile(handle, color=QtGui.QColor(c['color']), mood=Mood(c['mood']), **options)))
        converted = dict(u)
        self.update(converted)

    def save(self):
        try:
            fp = open("%s/chums.js" % (self.logpath), 'w')
            chumdict = dict([p.plaindict() for p in self.itervalues()])
            json.dump(chumdict, fp)
            fp.close()
        except Exception, e:
            raise e
    def getColor(self, handle, default=None):
        if not self.has_key(handle):
            return default
        else:
            return self[handle].color
    def setColor(self, handle, color):
        if self.has_key(handle):
            self[handle].color = color
        else:
            self[handle] = PesterProfile(handle, color)
    def getGroup(self, handle, default="Chums"):
        if not self.has_key(handle):
            return default
        else:
            return self[handle].group
    def setGroup(self, handle, theGroup):
        if self.has_key(handle):
            self[handle].group = theGroup
        else:
            self[handle] = PesterProfile(handle, group=theGroup)
        self.save()
    def getNotes(self, handle, default=""):
        if not self.has_key(handle):
            return default
        else:
            return self[handle].notes
    def setNotes(self, handle, notes):
        if self.has_key(handle):
            self[handle].notes = notes
        else:
            self[handle] = PesterProfile(handle, notes=notes)
        self.save()
    def __setitem__(self, key, val):
        dict.__setitem__(self, key, val)
        self.save()

class pesterTheme(dict):
    def __init__(self, name, default=False):
        possiblepaths = (_datadir+"themes/%s" % (name),
                         "themes/%s" % (name),
                         _datadir+"themes/pesterchum",
                         "themes/pesterchum")
        self.path = "themes/pesterchum"
        for p in possiblepaths:
            if os.path.exists(p):
                self.path = p
                break

        self.name = name
        try:
            fp = open(self.path+"/style.js")
            theme = json.load(fp, object_hook=self.pathHook)
            fp.close()
        except IOError:
            theme = json.loads("{}")
        self.update(theme)
        if self.has_key("inherits"):
            self.inheritedTheme = pesterTheme(self["inherits"])
        if not default:
            self.defaultTheme = pesterTheme("pesterchum", default=True)
    def __getitem__(self, key):
        keys = key.split("/")
        try:
            v = dict.__getitem__(self, keys.pop(0))
        except KeyError, e:
                if hasattr(self, 'inheritedTheme'):
                    return self.inheritedTheme[key]
                if hasattr(self, 'defaultTheme'):
                    return self.defaultTheme[key]
                else:
                    raise e
        for k in keys:
            try:
                v = v[k]
            except KeyError, e:
                if hasattr(self, 'inheritedTheme'):
                    return self.inheritedTheme[key]
                if hasattr(self, 'defaultTheme'):
                    return self.defaultTheme[key]
                else:
                    raise e
        return v
    def pathHook(self, d):
        for (k, v) in d.iteritems():
            if type(v) is unicode:
                s = Template(v)
                d[k] = s.safe_substitute(path=self.path)
        return d
    def get(self, key, default):
        keys = key.split("/")
        try:
            v = dict.__getitem__(self, keys.pop(0))
            for k in keys:
                v = v[k]
            return default if v is None else v
        except KeyError:
            if hasattr(self, 'inheritedTheme'):
                return self.inheritedTheme.get(key, default)
            else:
                return default

    def has_key(self, key):
        keys = key.split("/")
        try:
            v = dict.__getitem__(self, keys.pop(0))
            for k in keys:
                v = v[k]
            return False if v is None else True
        except KeyError:
            if hasattr(self, 'inheritedTheme'):
                return self.inheritedTheme.has_key(key)
            else:
                return False
