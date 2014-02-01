import urllib
import re
import time
try:
    import tarfile
except:
    tarfile = None
import zipfile
import ostools

USER_TYPE = "edge"
                  # user - for normal people
                  # beta - for the original beta testers
                  # dev  - used to be for git users, now it's anyone with the 3.41 beta
                  # edge - new git stuff. bleeding edge, do not try at home (kiooeht version)

INSTALL_TYPE = "source"
                  # installer - Windows/Mac installer     (exe/dmg)
                  # zip       - Windows zip               (zip)
                  # source    - Win/Linux/Mac source code (zip/tar)

OS_TYPE =  ostools.shortPlatform()# win32, linux, darwin

_pcMajor = "3.41"
_pcMinor = "5"
_pcStatus = "dev"
                # dev = Still in development
                # A  = alpha
                # B  = beta
                # RC = release candidate
                # None = public release
_pcRevision = ""
_pcVersion = ""

def pcVerCalc():
    global _pcVersion
    if _pcStatus:
        _pcVersion = "%s.%s-%s%s" % (_pcMajor, _pcMinor, _pcStatus, _pcRevision)
    else:
        _pcVersion = "%s.%s.%s" % (_pcMajor, _pcMinor, _pcRevision)

def lexVersion(short=False):
    if not _pcStatus:
        return "%s.%s" % (_pcMajor, _pcMinor)

    utype = ""
    if USER_TYPE == "edge":
        utype = "E"

    if short:
        return "%s.%s%s%s%s" % (_pcMajor, _pcMinor, _pcStatus, _pcRevision, utype);

    stype = ""
    if _pcStatus == "A":
        stype = "Alpha"
    elif _pcStatus == "B":
        stype = "Beta"
    elif _pcStatus == "RC":
        stype = "Release Candidate"

    if utype == "E":
        utype = " Bleeding Edge"

    return "%s.%s %s %s%s" % (_pcMajor, _pcMinor, stype, _pcRevision, utype);

# Naughty I know, but it lets me grab it from the bash script.
if __name__ == "__main__":
    print((lexVersion()))

def verStrToNum(ver):
    w = re.match("(\d+\.?\d+)\.(\d+)-?([A-Za-z]{0,2})\.?(\d*):(\S+)", ver)
    if not w:
        print("Update check Failure: 3"); return
    full = ver[:ver.find(":")]
    return full,w.group(1),w.group(2),w.group(3),w.group(4),w.group(5)

def updateCheck(q):
    time.sleep(3)
    data = urllib.parse.urlencode({"type" : USER_TYPE, "os" : OS_TYPE, "install" : INSTALL_TYPE})
    try:
        f = urllib.request.urlopen("http://distantsphere.com/pesterchum.php?" + data)
    except:
        print("Update check Failure: 1"); return q.put((False,1))
    newest = f.read()
    f.close()
    if not newest or newest[0] == "<":
        print("Update check Failure: 2"); return q.put((False,2))
    try:
        (full, major, minor, status, revision, url) = verStrToNum(newest)
    except TypeError:
        return q.put((False,3))
    print(full)
    if major <= _pcMajor:
        if minor <= _pcMinor:
            if status:
                if status <= _pcStatus:
                    if revision <= _pcRevision:
                        return q.put((False,0))
            else:
                if not _pcStatus:
                    if revision <= _pcRevision:
                        return q.put((False,0))
    print("A new version of Pesterchum is avaliable!")
    q.put((full,url))


def removeCopies(path):
    for f in ostools.listdir(path):
        filePath = ostools.join(path, f)
        if not ostools.isdir(filePath):
            if ostools.exists(filePath[7:]):
                ostools.remove(filePath[7:])
        else:
            removeCopies(filePath)

def copyUpdate(path):
    for f in ostools.listdir(path):
        filePath = ostools.join(path, f)
        if not ostools.isdir(filePath):
            ostools.copy2(filePath, filePath[7:])
        else:
            if not ostools.exists(filePath[7:]):
                ostools.mkdir(filePath[7:])
            copyUpdate(filePath)

def updateExtract(url, extension):
    if extension:
        fn = "update" + extension
        urllib.request.urlretrieve(url, fn)
    else:
        fn = urllib.request.urlretrieve(url)[0]
        if tarfile and tarfile.is_tarfile(fn):
            extension = ".tar.gz"
        elif zipfile.is_zipfile(fn):
            extension = ".zip"
        else:
            try:
                mime = magic.from_file(fn, mime=True)
                if mime == 'application/octet-stream':
                    extension = ".exe"
            except:
                pass

    print((url, fn, extension))

    if extension == ".exe":
        pass
    elif extension == ".zip" or extension.startswith(".tar"):
        if extension == ".zip":
            print("Opening .zip")
        elif tarfile and extension.startswith(".tar"):
            print("Opening .tar")
        else:
            return

        if is_updatefile(fn):
            update = openupdate(fn, 'r')
            if ostools.exists("tmp"):
                ostools.rmtree("tmp")
            ostools.mkdir("tmp")
            update.extractall("tmp")
            tmp = ostools.listdir("tmp")
            if ostools.exists("update"):
                ostools.rmtree("update")
            if len(tmp) == 1 and \
               ostools.isdir("tmp/"+tmp[0]):
                ostools.move("tmp/"+tmp[0], "update")
            else:
                ostools.move("tmp", "update")
            ostools.rmdir("tmp")
            ostools.remove(fn)
            removeCopies("update")
            copyUpdate("update")
            ostools.rmtree("update")

def updateDownload(url):
    extensions = [".exe", ".zip", ".tar.gz", ".tar.bz2"]
    found = False
    for e in extensions:
        if url.endswith(e):
            found = True
            updateExtract(url, e)
    if not found:
        if url.startswith("https://github.com/") and url.count('/') == 4:
            updateExtract(url+"/tarball/master", None)
        else:
            updateExtract(url, None)
