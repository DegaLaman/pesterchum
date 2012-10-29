import os
import sqlite3 as lite
import json
import array
import re
import ostools

config_columns   = ("Id INTEGER PRIMARY KEY,"
                    "DefaultProfile INT DEFAULT NULL,"
                    "HideOfflineChums BOOL DEFAULT 0,"
                    "Tabs BOOL DEFAULT 1,"
                    "TabMemos BOOL DEFAULT 1,"
                    "ShowTimeStamps BOOL DEFAULT 1,"
                    "Time12Format BOOL DEFAULT 1,"
                    "ShowSeconds BOOL DEFAULT 0,"
                    "UseGroups BOOL DEFAULT 0,"
                    "SortMethod INT DEFAULT 0,"
                    "EmptyGroups BOOL DEFAULT 0,"
                    "OnlineNumbers BOOL DEFAULT 0,"
                    "LogPesters INT DEFAULT 3,"
                    "LogMemos INT DEFAULT 1,"
                    "UserLinks BOOL DEFAULT 1,"
                    "IdleTime INT DEFAULT 10,"
                    "MiniAction INT DEFAULT 0,"
                    "CloseAction INT DEFAULT 1,"
                    "OpVMessages BOOL DEFAULT 1,"
                    "Animations BOOL DEFAULT 1,"
                    "CheckUpdates INT DEFAULT 0,"
                    "LastUCheck INT DEFAULT 0,"
                    "Mspa BOOL DEFAULT 0,"
                    "Blink INT DEFAULT 3,"
                    "Notify BOOL DEFAULT 1,"
                    "NotifyType TEXT DEFAULT 'default',"
                    "NotifyOptions INT DEFAULT 29,"
                    "LowBandwidth BOOL DEFAULT 0,"
                    "Ghostchum BOOL DEFAULT 0,"
                    "Server TEXT DEFAULT 'irc.mindfang.org',"
                    "Port INT DEFAULT 6667,"
                    "SoundOn BOOL DEFAULT 1,"
                    "ChatSound BOOL DEFAULT 1,"
                    "MemoSound BOOL DEFAULT 1,"
                    "PingSound BOOL DEFAULT 1,"
                    "NameSound BOOL DEFAULT 1,"
                    "Volume INT DEFAULT 100 CHECK (Volume >= 0 AND Volume <= 100),"
                    "TrayMsg BOOL DEFAULT 1,"
                    "FOREIGN KEY(DefaultProfile) REFERENCES Profiles(Id)"
                   )
chums_columns    = ("Id INTEGER PRIMARY KEY,"
                    "Person INT UNIQUE,"
                    "[Group] INT DEFAULT 1,"
                    "FOREIGN KEY(Person) REFERENCES People(Id),"
                    "FOREIGN KEY([Group]) REFERENCES Groups(Id)"
                   )
blocked_columns  = ("Id INTEGER PRIMARY KEY,"
                    "Person INT UNIQUE,"
                    "FOREIGN KEY(Person) REFERENCES People(Id)"
                   )
people_columns   = ("Id INTEGER PRIMARY KEY,"
                    "Name TEXT UNIQUE,"
                    "Color TEXT DEFAULT '#000000',"
                    "Mood INT DEFAULT 0"
                   )
groups_columns   = ("Id INTEGER PRIMARY KEY,"
                    "Name TEXT UNIQUE,"
                    "Open BOOL DEFAULT 1,"
                    "Ordering INT UNIQUE"
                   )
profiles_columns = ("Id INTEGER PRIMARY KEY,"
                    "Name TEXT UNIQUE,"
                    "Color TEXT DEFAULT '#000000',"
                    "LastMood INT,"
                    "LastUCheck Int DEFAULT 0,"
                    "Theme TEXT DEFAULT 'pesterchum',"
                    "Randoms BOOL DEFAULT 0"
                   )
quirks_columns   = ("Id INTEGER PRIMARY KEY,"
                    "[Group] TEXT DEFAULT 'Miscellaneous',"
                    "Type TEXT,"
                    "[From] TEXT,"
                    "[To] TEXT,"
                    "Value TEXT"
                   )
quirk_profile_columns = \
                   ("Id INTEGER PRIMARY KEY,"
                    "Quirk INT,"
                    "Profile INT,"
                    "Ordering INT,"
                    "FOREIGN KEY(Quirk) REFERENCES Quirks(Id),"
                    "FOREIGN KEY(Profile) REFERENCES Profiles(Id)"
                   )
mentions_columns = ("Id INTEGER PRIMARY KEY,"
                    "Value TEXT")
mention_profile_columns = \
                   ("Id INTEGER PRIMARY KEY,"
                    "Mention INT,"
                    "Profile INT,"
                    "FOREIGN KEY(Mention) REFERENCES Mentions(Id),"
                    "FOREIGN KEY(Profile) REFERENCES Profiles(Id)"
                   )
profile_chums_columns = \
                   ("Id INTEGER PRIMARY KEY,"
                    "Profile INT,"
                    "Person INT,"
                    "[Group] INT,"
                    "FOREIGN KEY(Profile) REFERENCES Profiles(Id),"
                    "FOREIGN KEY(Person) REFERENCES People(Id),"
                    "FOREIGN KEY([Group]) REFERENCES Groups(Id)"
                    )

# case insensitive dict
class idict(dict):
    def __init__(self, d=None):
        d = dict((k.lower(), d[k]) for k in d.keys())
        super(idict, self).__init__(d)
    def __setitem__(self, key, value):
        super(idict, self).__setitem__(key.lower(), value)

    def __getitem__(self, key):
        return super(idict, self).__getitem__(key.lower())

    def __contains__(self, key):
        return super(idict, self).__contains__(key.lower())

def create_table(cur, table_name, columns):
    cur.execute("CREATE TABLE IF NOT EXISTS %s (%s)" % (table_name, columns))

def get_chums(cur, handle):
    cur.execute("SELECT People.Name AS Handle, Color, Mood, Groups.Name AS [Group] FROM People, Chums, Groups ON Chums.Person = People.Id AND Chums.[Group] = Groups.Id ORDER BY [Group], Handle")
    #cur.execute("SELECT People.Name AS Handle, People.Color, Mood, Groups.Name AS [Group] FROM People, Groups, ProfileChums, Profiles ON Profiles.Id = ProfileChums.Profile AND ProfileChums.Person = People.Id AND ProfileChums.[Group] = Groups.Id WHERE Profiles.Name = ? ORDER BY [Group], Handle", (handle,))
    return [idict(x) for x in cur.fetchall()]

def get_quirks(cur, handle):
    cur.execute("SELECT Ordering, [Group], Type, [From], [To], Value FROM QuirkProfiles, Profiles, Quirks ON QuirkProfiles.Profile=Profiles.Id AND QuirkProfiles.Quirk=Quirks.Id WHERE Name=? ORDER BY [Group], Ordering", (handle,))
    return cur.fetchall()

def get_color(cur, handle):
    cur.execute("SELECT Color FROM People WHERE Name=?", (handle,))
    return cur.fetchone()[0]

def get_mood(cur, handle):
    cur.execute("SELECT Mood FROM People WHERE Name=?", (handle,))
    return cur.fetchone()[0]

def get_groups(cur):
    cur.execute("SELECT Name, Open FROM Groups ORDER BY Ordering ASC")
    groups = cur.fetchall()
    return [[name, bool(b)] for name,b in groups]

def get_blocked(cur):
    cur.execute("SELECT Name FROM Blocked, People ON People.Id = Blocked.Person")
    return [handle[0] for handle in  cur.fetchall()]

def is_blocked(cur, handle):
    cur.execute("SELECT Name FROM Blocked, People On People.Id = Blocked.Person WHERE People.Name=?", (handle,))
    return not (cur.fetchone() == None)

def get_mentions(cur, handle):
    cur.execute("SELECT Value FROM Mentions, Profiles, MentionProfiles ON MentionProfiles.Profile = Profiles.Id AND MentionProfiles.Mention = Mentions.Id WHERE Name=?", (handle,))
    return [x[0] for x in cur.fetchall()]

class Config(object):
    def __init__(self, cur):
        self.cur = cur

    def __getattr__(self, name):
        name = name.lower()
        try:
            self.cur.execute("SELECT %s FROM Config" % (name))
        except lite.OperationalError:
            raise AttributeError
        value = self.cur.fetchone()[name]
        self.cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='Config'")
        row = self.cur.fetchone()
        sql = row['sql']
        sql = [x.lower() for x in re.split(' |,', sql)]
        if sql[sql.index(name)+1] == 'bool':
            return bool(value)
        else:
            return value

if os.path.exists('test.db'):
    db_exists = True
else:
    db_exists = False

with lite.connect('test.db') as con:
    con.row_factory = lite.Row
    cur = con.cursor()
    cur.execute('SELECT SQLITE_VERSION()')
    data = cur.fetchone()
    print "SQLite version: %s" % (data[0])


    if not db_exists:
        create_table(cur, "Config",     config_columns)
        create_table(cur, "Chums",      chums_columns)
        create_table(cur, "Blocked",    blocked_columns)
        create_table(cur, "People",     people_columns)
        create_table(cur, "Groups",     groups_columns)
        create_table(cur, "Profiles",   profiles_columns)
        create_table(cur, "Quirks",     quirks_columns)
        create_table(cur, "QuirkProfiles", quirk_profile_columns)
        create_table(cur, "Mentions",   mentions_columns)
        create_table(cur, "MentionProfiles", mention_profile_columns)

        # Time to trigger some shit
        # Delete a person? Delete references in Chums and Blocked
        cur.execute("CREATE TRIGGER IF NOT EXISTS delete_person AFTER DELETE ON People\
                     BEGIN\
                       DELETE FROM Chums WHERE Person=OLD.Id;\
                       DELETE FROM Blocked WHERE Person=OLD.Id;\
                     END;")
        # Delete a Group? Update any Chums to be in default group
        cur.execute("CREATE TRIGGER IF NOT EXISTS delete_group AFTER DELETE ON Groups\
                     BEGIN\
                       UPDATE Chums SET [Group]=1;\
                     END;")
        # Delete a Quirk? Delete references in QuirkProfiles
        cur.execute("CREATE TRIGGER IF NOT EXISTS delete_quirk AFTER DELETE ON Quirks\
                     BEGIN\
                       DELETE FROM QuirkProfiles WHERE Quirk=OLD.Id;\
                     END;")
        # Delete a Mention? Delete references in MentionProfiles
        cur.execute("CREATE TRIGGER IF NOT EXISTS delete_mention AFTER DELETE ON Mentions\
                     BEGIN\
                       DELETE FROM MentionProfiles WHERE Mention=OLD.Id;\
                     END;")
        # Delete a Profile? Delete references in QuirkProfiles, MentionProfiles and Update references in Config
        cur.execute("CREATE TRIGGER IF NOT EXISTS delete_profile AFTER DELETE ON Profiles\
                     BEGIN\
                       DELETE FROM QuirkProfiles WHERE Profile=OLD.Id;\
                       DELETE FROM MentionProfiles WHERE Profile=OLD.Id;\
                       UPDATE Config SET DefaultProfile=NULL WHERE DefaultProfile=OLD.Id;\
                     END;")

        cur.execute("INSERT INTO Groups (Id, Name, Open) VALUES(1, 'Chums', 1)")

        # Convert Groups
        try:
            with open(os.path.join(ostools.getDataDir(), "logs/groups.js")) as f:
                groups = json.load(f)
                for i, g in enumerate(groups['groups']):
                    try:
                        cur.execute("INSERT INTO Groups (Name, Open, Ordering) VALUES(?, ?, ?)", (g[0], int(g[1]), i))
                    except lite.IntegrityError:
                        cur.execute("UPDATE Groups SET Ordering=? WHERE Name=?", (i, g[0]))
        except IOError:
            print "No groups to convert"
        else:
            print "Groups converted"

        # Convert People
        try:
            with open(os.path.join(ostools.getDataDir(), "logs/chums.js")) as f:
                chums = json.load(f)
                #print json.dumps(j, indent=4)
                for (h,chum) in chums.iteritems():
                    cur.execute("INSERT INTO People (Name, Color, Mood) VALUES(?, ?, ?)", (chum['handle'], chum['color'], 0))
        except IOError:
            print "No people to convert"
            chums = []
        else:
            print "People converted"

        # Convert Chums and Block
        chums = []
        try:
            with open(os.path.join(ostools.getDataDir(), "pesterchum.js")) as f:
                config = json.load(f)
                #print json.dumps(j, indent=4)
                for chum in config['chums']:
                    if chum in chums:
                        group = chums[chum]['group']
                    else:
                        group = 'Chums'
                    cur.execute("SELECT Id FROM Groups WHERE Name=?", (group,))
                    group = cur.fetchone()
                    cur.execute("SELECT Id FROM People WHERE Name=?", (chum,))
                    person = cur.fetchone()
                    if person == None:
                        cur.execute("INSERT INTO People (Name) VALUES(?)", (chum,))
                        person = (cur.lastrowid,)
                    if group == None:
                        group = (1,) # GroupId 1 should always be 'Chums' group

                    cur.execute("INSERT INTO Chums (Person, [Group]) VALUES(?, ?)", (person[0], group[0]))

                print "Chums converted"

                for c in config['block']:
                    cur.execute("SELECT Id FROM People WHERE Name=?", (c,))
                    person = cur.fetchone()
                    if person == None:
                        cur.execute("INSERT INTO People (Name) VALUES(?)", (c,))
                        person = (cur.lastrowid,)
                    cur.execute("INSERT INTO Blocked (Person) VALUES(?)", person)

                print "Block list converted"
        except IOError:
            print "No chums to convert"

        # Convert Profiles and Quirks and Mentions
        try:
            for file in os.listdir(os.path.join(ostools.getDataDir(), "profiles/")):
                with open(os.path.join(ostools.getDataDir(), "profiles/", file)) as f:
                    profile = json.load(f)
                    #print json.dumps(profile, indent=4)
                    quirks = []
                    for quirk in profile['quirks']:
                        #cur.execute("INSERT INTO Quirks (Type, [From], [To]) VALUES(?, ?, ?)", (quirk['type'], quirk['from'], quirk['to']))
                        if quirk['type'] == 'prefix' or quirk['type'] == 'suffix':
                            cur.execute("INSERT INTO Quirks (Type, Value) VALUES(?, ?)", (quirk['type'], quirk['value']))
                        elif quirk['type'] == 'replace' or quirk['type'] == 'regexp':
                            cur.execute("INSERT INTO Quirks (Type, [From], [To]) VALUES(?, ?, ?)", (quirk['type'], quirk['from'], quirk['to']))
                        elif quirk['type'] == 'random':
                            a = array.array('u', quirk['randomlist'])
                            cur.execute("INSERT INTO Quirks (Type, Value) VALUES(?, ?)", (quirk['type'], a.tounicode()))
                        if quirk['on']:
                            quirks.append(cur.lastrowid)
                    #print profile['handle'], quirks
                    cur.execute("INSERT INTO Profiles (Name, Color, LastMood, LastUCheck, Theme, Randoms) VALUES(?, ?, ?, ?, ?, ?)", (profile['handle'], profile.get('color', "#000000"), profile.get('lastmood', 0), profile.get('lastUCheck', 0), profile.get('theme', "pesterchum"), int(profile.get('randoms', False))))
                    profileid = cur.lastrowid
                    for i,q in enumerate(quirks):
                        cur.execute("INSERT INTO QuirkProfiles (Quirk, Profile, Ordering) VALUES(?, ?, ?)", (q, profileid, i))
                    for m in profile.get('mentions', []):
                        cur.execute("INSERT INTO Mentions (Value) VALUES(?)", (m,))
                        cur.execute("INSERT INTO MentionProfiles (Mention, Profile) VALUES(?, ?)", (cur.lastrowid, profileid))
        except IOError:
            print "No profiles to convert"
            print "Warning: Failed to convert chums properly (Step 2/2)"
        else:
            print "Profiles converted"

        # Convert Config
        try:
            with open(os.path.join(ostools.getDataDir(), "pesterchum.js")) as f:
                config = json.load(f)
                #print json.dumps(config, indent=4)
                cur.execute("INSERT INTO Config (DefaultProfile) VALUES(NULL)")
                row = cur.lastrowid
                for k,v in config.iteritems():
                    if k == 'chums' or k == 'block':
                        continue
                    if k == 'defaultprofile':
                        cur.execute("SELECT Id FROM Profiles WHERE Name=?", (v,))
                        defaultprofile = cur.fetchone()
                        print defaultprofile
                        cur.execute("UPDATE Config SET DefaultProfile=? WHERE Id=?", (defaultprofile[0], row))
                    elif type(v) == type(bool()):
                        cur.execute("UPDATE Config SET %s=? WHERE Id=?" % (k), (int(v), row))
                    else:
                        cur.execute("UPDATE Config SET %s=? WHERE Id=?" % (k), (v, row))
        except IOError:
            print "No config to convert"
        else:
            print "Config converted"

    c = Config(cur)
    print c.memosound
    print c.server
    print c.port
    quirks = get_quirks(cur,'welcomeBack')
    for q in quirks:
        print dict(q)
    print get_mentions(cur,'evacipatedBox')
    print get_chums(cur, 'evacipatedBox')

