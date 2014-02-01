from PyQt5.QtCore import QStandardPaths, QUrl
from PyQt5.QtGui import QDesktopServices
import os, sys, shutil
import platform
from os import getcwd, rename, rmdir, chdir
from os.path import dirname, isdir, abspath
from shutil import move, copy2, rmtree
from sys import argv, platform

def isOSX(): return platform == 'darwin'
def isWin32(): return platform == 'win32'
def isLinux(): return platform.startswith('linux')
def isOSXBundle(): return isOSX() and (os.path.abspath('.').find('.app') != -1)
def isOSXLeopard(): return isOSX() and platform.mac_ver()[0].startswith('10.5')

def shortPlatform():
    if isLinux():
        return "linux"
    elif isOSX():
        return "mac"
    elif isWin32():
        return "win32"
    return platform
    
def osVer():
    if isWin32():
        return " ".join(platform.win32_ver())
    elif isOSX():
        ver = platform.mac_ver();
        return " ".join((ver[0], " (", ver[2], ")"))
    elif isLinux():
        return " ".join(platform.linux_distribution())

def getDataDir():
    # Temporary fix for non-ascii usernames
    # If username has non-ascii characters, just store userdata
    # in the Pesterchum install directory (like before)
    try:
        if isOSX():
            return os.path.join(str(QStandardPaths.writableLocation(QStandardPaths.DataLocation)), "Pesterchum/")
        elif isLinux():
            return os.path.join(str(QStandardPaths.writeableLocation(QStandardPaths.HomeLocation)), ".pesterchum/")
        else:
            return os.path.join(str(QStandardPaths.writableLocation(QStandardPaths.DataLocation)), "pesterchum/")
    except UnicodeDecodeError:
        return ''

def join(*args):
    if args[-1][0]==".":
        args = args[0:-2] + ((args[-2] + args[-1]),)
    return os.path.join(*args)

def exists(*args): return os.path.exists(join(*args))
def listdir(*args): return os.listdir(join(*args))
def mkdir(*args): return os.mkdir(join(*args))
def makedirs(*args): return os.makedirs(join(*args))
def remove(*args): return os.mkdir(join(*args))
def walk(*args): return os.walk(join(*args))

def basename(filename,giveExt=False):
    basename_list = os.path.basename(filename).rsplit('.',1)
    if giveExt:
        return (basename_list[0], basename_list[1][1:])
    return basename_list[0]

def openLocalUrl(*args):
    return QDesktopServices.openUrl(QUrl("file:///"+join(*args), QUrl.TolerantMode))

