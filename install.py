#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2022 Detlev Offenbach <detlev@die-offenbachs.de>
#
# This is the install script for eric.

"""
Installation script for the eric IDE and all eric related tools.
"""

import compileall
import contextlib
import datetime
import fnmatch
import getpass
import glob
import io
import json
import os
import py_compile
import re
import shlex
import shutil
import subprocess  # secok
import time
import sys

# Define the globals.
progName = None
currDir = os.getcwd()
modDir = None
pyModDir = None
platBinDir = None
platBinDirOld = None
distDir = None
apisDir = None
installApis = True
doCleanup = True
doCleanDesktopLinks = False
forceCleanDesktopLinks = False
doCompile = True
yes2All = False
withPyqt6Tools = False
verbose = False
cfg = {}
progLanguages = ["MicroPython", "Python3", "QSS"]
sourceDir = "eric"
eric7SourceDir = ""
configName = "eric7config.py"
defaultMacAppBundleName = "eric7.app"
defaultMacAppBundlePath = "/Applications"
defaultMacPythonExe = "{0}/Resources/Python.app/Contents/MacOS/Python".format(
    sys.exec_prefix
)
if not os.path.exists(defaultMacPythonExe):
    defaultMacPythonExe = ""
macAppBundleName = defaultMacAppBundleName
macAppBundlePath = defaultMacAppBundlePath
macPythonExe = defaultMacPythonExe

createInstallInfoFile = True
installInfoName = "eric7install.json"
installInfo = {}
installCwd = ""

# Define blacklisted versions of the prerequisites
BlackLists = {
    "sip": [],
    "PyQt6": [],
    "QScintilla2": [],
}
PlatformsBlackLists = {
    "windows": {
        "sip": [],
        "PyQt6": [],
        "QScintilla2": [],
    },
    "linux": {
        "sip": [],
        "PyQt6": [],
        "QScintilla2": [],
    },
    "mac": {
        "sip": [],
        "PyQt6": [],
        "QScintilla2": [],
    },
}


def exit(rcode=0):
    """
    Exit the install script.

    @param rcode result code to report back (integer)
    """
    global currDir

    print()

    if sys.platform.startswith(("win", "cygwin")):
        with contextlib.suppress(EOFError):
            input("Press enter to continue...")  # secok

    os.chdir(currDir)

    sys.exit(rcode)


def usage(rcode=2):
    """
    Display a usage message and exit.

    @param rcode the return code passed back to the calling process.
    """
    global progName, modDir, distDir, apisDir
    global macAppBundleName, macAppBundlePath, macPythonExe

    print()
    print("Usage:")
    if sys.platform == "darwin":
        print(
            "    {0} [-chvxz] [-a dir] [-b dir] [-d dir] [-f file] [-i dir]"
            " [-m name] [-n path] [-p python] [--help] [--no-apis]"
            " [--no-info] [--no-tools] [--verbose] [--yes]".format(progName)
        )
    elif sys.platform.startswith(("win", "cygwin")):
        print(
            "    {0} [-chvxz] [-a dir] [-b dir] [-d dir] [-f file]"
            " [--clean-desktop] [--help] [--no-apis] [--no-info]"
            " [--no-tools] [--verbose] [--yes]".format(progName)
        )
    else:
        print(
            "    {0} [-chvxz] [-a dir] [-b dir] [-d dir] [-f file] [-i dir]"
            " [--help] [--no-apis] [--no-info] [--no-tools] [--verbose]"
            " [--yes]".format(progName)
        )
    print("where:")
    print("    -h, --help display this help message")
    print("    -a dir     where the API files will be installed")
    if apisDir:
        print("               (default: {0})".format(apisDir))
    else:
        print("               (no default value)")
    print("    --no-apis  don't install API files")
    print("    -b dir     where the binaries will be installed")
    print("               (default: {0})".format(platBinDir))
    print("    -d dir     where eric python files will be installed")
    print("               (default: {0})".format(modDir))
    print("    -f file    configuration file naming the various installation" " paths")
    if not sys.platform.startswith(("win", "cygwin")):
        print("    -i dir     temporary install prefix")
        print("               (default: {0})".format(distDir))
    if sys.platform == "darwin":
        print("    -m name    name of the Mac app bundle")
        print("               (default: {0})".format(macAppBundleName))
        print("    -n path    path of the directory the Mac app bundle will")
        print("               be created in")
        print("               (default: {0})".format(macAppBundlePath))
        print("    -p python  path of the python executable")
        print("               (default: {0})".format(macPythonExe))
    print("    -c         don't cleanup old installation first")
    print("    -v, --verbose print some more information")
    print("    -x         don't perform dependency checks (use on your own" " risk)")
    print("    -z         don't compile the installed python files")
    print("    --yes      answer 'yes' to all questions")
    print()
    if sys.platform.startswith(("win", "cygwin")):
        print("    --clean-desktop delete desktop links before installation")
    print("    --no-info  don't create the install info file")
    print("    --with-tools don't install qt6-applications")
    print()
    print("The file given to the -f option must be valid Python code" " defining a")
    print(
        "dictionary called 'cfg' with the keys 'ericDir', 'ericPixDir',"
        " 'ericIconDir',"
    )
    print("'ericDTDDir', 'ericCSSDir', 'ericStylesDir', 'ericThemesDir',")
    print(" 'ericDocDir', ericExamplesDir',")
    print("'ericTranslationsDir', 'ericTemplatesDir', 'ericCodeTemplatesDir',")
    print("'ericOthersDir','bindir', 'mdir' and 'apidir.")
    print(
        "These define the directories for the installation of the various"
        " parts of eric."
    )

    exit(rcode)


def initGlobals():
    """
    Module function to set the values of globals that need more than a
    simple assignment.
    """
    global platBinDir, modDir, pyModDir, apisDir, platBinDirOld

    import sysconfig

    if sys.platform.startswith(("win", "cygwin")):
        platBinDir = sys.exec_prefix
        if platBinDir.endswith("\\"):
            platBinDir = platBinDir[:-1]
        platBinDirOld = platBinDir
        platBinDir = os.path.join(platBinDir, "Scripts")
        if not os.path.exists(platBinDir):
            platBinDir = platBinDirOld
    else:
        pyBinDir = os.path.normpath(os.path.dirname(sys.executable))
        if os.access(pyBinDir, os.W_OK):
            # install the eric scripts along the python executable
            platBinDir = pyBinDir
        else:
            # install them in the user's bin directory
            platBinDir = os.path.expanduser("~/bin")
        if platBinDir != "/usr/local/bin" and os.access("/usr/local/bin", os.W_OK):
            platBinDirOld = "/usr/local/bin"

    modDir = sysconfig.get_path("platlib")
    pyModDir = modDir

    pyqtDataDir = os.path.join(modDir, "PyQt6")
    if os.path.exists(os.path.join(pyqtDataDir, "qsci")):
        # it's the installer
        qtDataDir = pyqtDataDir
    elif os.path.exists(os.path.join(pyqtDataDir, "Qt6", "qsci")):
        # it's the wheel
        qtDataDir = os.path.join(pyqtDataDir, "Qt6")
    else:
        # determine dynamically
        try:
            from PyQt6.QtCore import QLibraryInfo

            qtDataDir = QLibraryInfo.path(QLibraryInfo.LibraryPath.DataPath)
        except ImportError:
            qtDataDir = None
    apisDir = os.path.join(qtDataDir, "qsci", "api") if qtDataDir else None


def copyToFile(name, text):
    """
    Copy a string to a file.

    @param name the name of the file.
    @param text the contents to copy to the file.
    """
    with open(name, "w") as f:
        f.write(text)


def copyDesktopFile(src, dst):
    """
    Modify a desktop file and write it to its destination.

    @param src source file name (string)
    @param dst destination file name (string)
    """
    global cfg, platBinDir

    with open(src, "r", encoding="utf-8") as f:
        text = f.read()

    text = text.replace("@BINDIR@", platBinDir)
    text = text.replace("@MARKER@", "")
    text = text.replace("@PY_MARKER@", "")

    dstPath = os.path.dirname(dst)
    if not os.path.isdir(dstPath):
        os.makedirs(dstPath)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(text)
    os.chmod(dst, 0o644)


def copyAppStreamFile(src, dst):
    """
    Modify an appstream file and write it to its destination.

    @param src source file name (string)
    @param dst destination file name (string)
    """
    if os.path.exists(os.path.join("eric", "src", "eric7", "UI", "Info.py")):
        # Installing from installer archive
        from eric.src.eric7.UI.Info import Version
    elif os.path.exists(os.path.join("src", "eric7", "UI", "Info.py")):
        # Installing from source tree
        from src.eric7.UI.Info import Version
    else:
        Version = "Unknown"

    with open(src, "r", encoding="utf-8") as f:
        text = f.read()

    text = (
        text.replace("@MARKER@", "")
        .replace("@VERSION@", Version.split(None, 1)[0])
        .replace("@DATE@", time.strftime("%Y-%m-%d"))
    )

    dstPath = os.path.dirname(dst)
    if not os.path.isdir(dstPath):
        os.makedirs(dstPath)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(text)
    os.chmod(dst, 0o644)


def wrapperNames(dname, wfile):
    """
    Create the platform specific names for the wrapper script.

    @param dname name of the directory to place the wrapper into
    @param wfile basename (without extension) of the wrapper script
    @return the names of the wrapper scripts
    """
    wnames = (
        (dname + "\\" + wfile + ".cmd", dname + "\\" + wfile + ".bat")
        if sys.platform.startswith(("win", "cygwin"))
        else (dname + "/" + wfile,)
    )

    return wnames


def createPyWrapper(pydir, wfile, saveDir, isGuiScript=True):
    """
    Create an executable wrapper for a Python script.

    @param pydir the name of the directory where the Python script will
        eventually be installed (string)
    @param wfile the basename of the wrapper (string)
    @param saveDir directory to save the file into (string)
    @param isGuiScript flag indicating a wrapper script for a GUI
        application (boolean)
    @return the platform specific name of the wrapper (string)
    """
    # all kinds of Windows systems
    if sys.platform.startswith(("win", "cygwin")):
        wname = wfile + ".cmd"
        if isGuiScript:
            wrapper = (
                """@echo off\n"""
                '''start "" "{2}\\pythonw.exe"'''
                ''' "{0}\\{1}.pyw"'''
                """ %1 %2 %3 %4 %5 %6 %7 %8 %9\n""".format(
                    pydir, wfile, os.path.dirname(sys.executable)
                )
            )
        else:
            wrapper = (
                '''@"{0}" "{1}\\{2}.py"'''
                """ %1 %2 %3 %4 %5 %6 %7 %8 %9\n""".format(sys.executable, pydir, wfile)
            )

    # Mac OS X
    elif sys.platform == "darwin":
        major = sys.version_info.major
        pyexec = "{0}/bin/pythonw{1}".format(sys.exec_prefix, major)
        if not os.path.exists(pyexec):
            pyexec = "{0}/bin/python{1}".format(sys.exec_prefix, major)
        wname = wfile
        wrapper = (
            """#!/bin/sh\n"""
            """\n"""
            """exec "{0}" "{1}/{2}.py" "$@"\n""".format(pyexec, pydir, wfile)
        )

    # *nix systems
    else:
        wname = wfile
        wrapper = (
            """#!/bin/sh\n"""
            """\n"""
            """exec "{0}" "{1}/{2}.py" "$@"\n""".format(sys.executable, pydir, wfile)
        )

    wname = os.path.join(saveDir, wname)
    copyToFile(wname, wrapper)
    os.chmod(wname, 0o755)  # secok

    return wname


def copyTree(src, dst, filters, excludeDirs=None, excludePatterns=None):
    """
    Copy Python, translation, documentation, wizards configuration,
    designer template files and DTDs of a directory tree.

    @param src name of the source directory
    @param dst name of the destination directory
    @param filters list of filter pattern determining the files to be copied
    @param excludeDirs list of (sub)directories to exclude from copying
    @param excludePatterns list of filter pattern determining the files to
        be skipped
    """
    if excludeDirs is None:
        excludeDirs = []
    if excludePatterns is None:
        excludePatterns = []
    try:
        names = os.listdir(src)
    except OSError:
        # ignore missing directories (most probably the i18n directory)
        return

    for name in names:
        skipIt = False
        for excludePattern in excludePatterns:
            if fnmatch.fnmatch(name, excludePattern):
                skipIt = True
                break
        if not skipIt:
            srcname = os.path.join(src, name)
            dstname = os.path.join(dst, name)
            for fileFilter in filters:
                if fnmatch.fnmatch(srcname, fileFilter):
                    if not os.path.isdir(dst):
                        os.makedirs(dst)
                    shutil.copy2(srcname, dstname)
                    os.chmod(dstname, 0o644)
                    break
            else:
                if os.path.isdir(srcname) and srcname not in excludeDirs:
                    copyTree(srcname, dstname, filters, excludePatterns=excludePatterns)


def createGlobalPluginsDir():
    """
    Create the global plugins directory, if it doesn't exist.
    """
    global cfg, distDir

    pdir = os.path.join(cfg["mdir"], "eric7plugins")
    fname = os.path.join(pdir, "__init__.py")
    if not os.path.exists(fname):
        if not os.path.exists(pdir):
            os.mkdir(pdir, 0o755)
        with open(fname, "w") as f:
            f.write(
                '''# -*- coding: utf-8 -*-

"""
Package containing the global plugins.
"""
'''
            )
        os.chmod(fname, 0o644)


def cleanupSource(dirName):
    """
    Cleanup the sources directory to get rid of leftover files
    and directories.

    @param dirName name of the directory to prune (string)
    """
    # step 1: delete all Ui_*.py files without a corresponding
    #         *.ui file
    dirListing = os.listdir(dirName)
    for formName, sourceName in [
        (f.replace("Ui_", "").replace(".py", ".ui"), f)
        for f in dirListing
        if fnmatch.fnmatch(f, "Ui_*.py")
    ]:
        if not os.path.exists(os.path.join(dirName, formName)):
            os.remove(os.path.join(dirName, sourceName))
            if os.path.exists(os.path.join(dirName, sourceName + "c")):
                os.remove(os.path.join(dirName, sourceName + "c"))

    # step 2: delete the __pycache__ directory and all remaining *.pyc files
    if os.path.exists(os.path.join(dirName, "__pycache__")):
        shutil.rmtree(os.path.join(dirName, "__pycache__"))
    for name in [f for f in os.listdir(dirName) if fnmatch.fnmatch(f, "*.pyc")]:
        os.remove(os.path.join(dirName, name))

    # step 3: delete *.orig files
    for name in [f for f in os.listdir(dirName) if fnmatch.fnmatch(f, "*.orig")]:
        os.remove(os.path.join(dirName, name))

    # step 4: descent into subdirectories and delete them if empty
    for name in os.listdir(dirName):
        name = os.path.join(dirName, name)
        if os.path.isdir(name):
            cleanupSource(name)
            if len(os.listdir(name)) == 0:
                os.rmdir(name)


def cleanUp():
    """
    Uninstall the old eric files.
    """
    global platBinDir, platBinDirOld

    try:
        from eric7config import getConfig
    except ImportError:
        # eric wasn't installed previously
        return
    except SyntaxError:
        # an incomplete or old config file was found
        return

    global pyModDir, progLanguages

    # Remove the menu entry for Linux systems
    if sys.platform.startswith("linux"):
        cleanUpLinuxSpecifics()
    # Remove the Desktop and Start Menu entries for Windows systems
    elif sys.platform.startswith(("win", "cygwin")):
        cleanUpWindowsLinks()

    # Remove the wrapper scripts
    rem_wnames = [
        "eric7_api",
        "eric7_browser",
        "eric7_compare",
        "eric7_configure",
        "eric7_diff",
        "eric7_doc",
        "eric7_editor",
        "eric7_hexeditor",
        "eric7_iconeditor",
        "eric7_plugininstall",
        "eric7_pluginrepository",
        "eric7_pluginuninstall",
        "eric7_qregularexpression",
        "eric7_re",
        "eric7_shell",
        "eric7_snap",
        "eric7_sqlbrowser",
        "eric7_testing",
        "eric7_tray",
        "eric7_trpreviewer",
        "eric7_uipreviewer",
        "eric7_virtualenv",
        "eric7",
        # obsolete scripts below
        "eric7_unittest",
    ]

    try:
        dirs = [platBinDir, getConfig("bindir")]
        if platBinDirOld:
            dirs.append(platBinDirOld)
        for rem_wname in rem_wnames:
            for d in dirs:
                for rwname in wrapperNames(d, rem_wname):
                    if os.path.exists(rwname):
                        os.remove(rwname)

        # Cleanup our config file(s)
        for name in ["eric7config.py", "eric7config.pyc", "eric7.pth"]:
            e6cfile = os.path.join(pyModDir, name)
            if os.path.exists(e6cfile):
                os.remove(e6cfile)
            e6cfile = os.path.join(pyModDir, "__pycache__", name)
            path, ext = os.path.splitext(e6cfile)
            for f in glob.glob("{0}.*{1}".format(path, ext)):
                os.remove(f)

        # Cleanup the install directories
        for name in [
            "ericExamplesDir",
            "ericDocDir",
            "ericDTDDir",
            "ericCSSDir",
            "ericIconDir",
            "ericPixDir",
            "ericTemplatesDir",
            "ericCodeTemplatesDir",
            "ericOthersDir",
            "ericStylesDir",
            "ericThemesDir",
            "ericDir",
        ]:
            with contextlib.suppress(AttributeError):
                if os.path.exists(getConfig(name)):
                    shutil.rmtree(getConfig(name), True)

        # Cleanup translations
        for name in glob.glob(
            os.path.join(getConfig("ericTranslationsDir"), "eric7_*.qm")
        ):
            if os.path.exists(name):
                os.remove(name)

        # Cleanup API files
        with contextlib.suppress(AttributeError):
            apidir = getConfig("apidir")
            for progLanguage in progLanguages:
                for name in getConfig("apis"):
                    # step 1: programming language as given
                    apiname = os.path.join(apidir, progLanguage, name)
                    if os.path.exists(apiname):
                        os.remove(apiname)
                    # step 2: programming language as lowercase
                    apiname = os.path.join(apidir, progLanguage.lower(), name)
                    if os.path.exists(apiname):
                        os.remove(apiname)
                for apiname in glob.glob(
                    os.path.join(apidir, progLanguage, "*.bas")
                ) + glob.glob(os.path.join(apidir, progLanguage.lower(), "*.bas")):
                    os.remove(apiname)

                # remove empty directories
                with contextlib.suppress(FileNotFoundError, OSError):
                    os.rmdir(os.path.join(apidir, progLanguage))
                with contextlib.suppress(FileNotFoundError, OSError):
                    os.rmdir(os.path.join(apidir, progLanguage.lower()))

        if sys.platform == "darwin":
            # delete the Mac app bundle
            cleanUpMacAppBundle()
    except OSError as msg:
        sys.stderr.write("Error: {0}\nTry install with admin rights.\n".format(msg))
        exit(7)


def cleanUpLinuxSpecifics():
    """
    Clean up Linux specific files.
    """
    if os.getuid() == 0:
        for name in [
            "/usr/share/applications/eric7.desktop",
            "/usr/share/appdata/eric7.appdata.xml",
            "/usr/share/metainfo/eric7.appdata.xml",
            "/usr/share/pixmaps/eric.png",
            "/usr/share/icons/eric.png",
            "/usr/share/applications/eric7_browser.desktop",
            "/usr/share/pixmaps/ericWeb.png",
            "/usr/share/icons/ericWeb.png",
        ]:
            if os.path.exists(name):
                os.remove(name)
    elif os.getuid() >= 1000:
        # it is assumed that user ids start at 1000
        for name in [
            "~/.local/share/applications/eric7.desktop",
            "~/.local/share/appdata/eric7.appdata.xml",
            "~/.local/share/metainfo/eric7.appdata.xml",
            "~/.local/share/pixmaps/eric.png",
            "~/.local/share/icons/eric.png",
            "~/.local/share/applications/eric7_browser.desktop",
            "~/.local/share/pixmaps/ericWeb.png",
            "~/.local/share/icons/ericWeb.png",
        ]:
            path = os.path.expanduser(name)
            if os.path.exists(path):
                os.remove(path)


def cleanUpMacAppBundle():
    """
    Uninstall the macOS application bundle.
    """
    from eric7config import getConfig

    try:
        macAppBundlePath = getConfig("macAppBundlePath")
        macAppBundleName = getConfig("macAppBundleName")
    except AttributeError:
        macAppBundlePath = defaultMacAppBundlePath
        macAppBundleName = defaultMacAppBundleName
    for bundlePath in [
        os.path.join(defaultMacAppBundlePath, macAppBundleName),
        os.path.join(macAppBundlePath, macAppBundleName),
    ]:
        if os.path.exists(bundlePath):
            shutil.rmtree(bundlePath)


def cleanUpWindowsLinks():
    """
    Clean up the Desktop and Start Menu entries for Windows.
    """
    global doCleanDesktopLinks, forceCleanDesktopLinks

    try:
        from pywintypes import com_error  # __IGNORE_WARNING__
    except ImportError:
        # links were not created by install.py
        return

    regPath = (
        "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer"
        + "\\User Shell Folders"
    )

    if doCleanDesktopLinks or forceCleanDesktopLinks:
        # 1. cleanup desktop links
        regName = "Desktop"
        desktopEntry = getWinregEntry(regName, regPath)
        if desktopEntry:
            desktopFolder = os.path.normpath(os.path.expandvars(desktopEntry))
            for linkName in windowsDesktopNames():
                linkPath = os.path.join(desktopFolder, linkName)
                if os.path.exists(linkPath):
                    try:
                        os.remove(linkPath)
                    except OSError:
                        # maybe restrictions prohibited link removal
                        print("Could not remove '{0}'.".format(linkPath))

    # 2. cleanup start menu entry
    regName = "Programs"
    programsEntry = getWinregEntry(regName, regPath)
    if programsEntry:
        programsFolder = os.path.normpath(os.path.expandvars(programsEntry))
        eric7EntryPath = os.path.join(programsFolder, windowsProgramsEntry())
        if os.path.exists(eric7EntryPath):
            try:
                shutil.rmtree(eric7EntryPath)
            except OSError:
                # maybe restrictions prohibited link removal
                print("Could not remove '{0}'.".format(eric7EntryPath))


def shutilCopy(src, dst, perm=0o644):
    """
    Wrapper function around shutil.copy() to ensure the permissions.

    @param src source file name (string)
    @param dst destination file name or directory name (string)
    @param perm permissions to be set (integer)
    """
    shutil.copy(src, dst)
    if os.path.isdir(dst):
        dst = os.path.join(dst, os.path.basename(src))
    os.chmod(dst, perm)


def installEric():
    """
    Actually perform the installation steps.

    @return result code (integer)
    """
    global distDir, doCleanup, cfg, progLanguages, sourceDir, configName
    global installApis

    # Create the platform specific wrappers.
    scriptsDir = "install_scripts"
    if not os.path.isdir(scriptsDir):
        os.mkdir(scriptsDir)
    wnames = []
    for name in ["eric7_api", "eric7_doc"]:
        wnames.append(createPyWrapper(cfg["ericDir"], name, scriptsDir, False))
    for name in [
        "eric7_browser",
        "eric7_compare",
        "eric7_configure",
        "eric7_diff",
        "eric7_editor",
        "eric7_hexeditor",
        "eric7_iconeditor",
        "eric7_plugininstall",
        "eric7_pluginrepository",
        "eric7_pluginuninstall",
        "eric7_qregularexpression",
        "eric7_re",
        "eric7_shell",
        "eric7_snap",
        "eric7_sqlbrowser",
        "eric7_tray",
        "eric7_trpreviewer",
        "eric7_uipreviewer",
        "eric7_testing",
        "eric7_virtualenv",
        "eric7",
    ]:
        wnames.append(createPyWrapper(cfg["ericDir"], name, scriptsDir))

    # set install prefix, if not None
    if distDir:
        for key in list(cfg.keys()):
            cfg[key] = os.path.normpath(os.path.join(distDir, cfg[key].lstrip(os.sep)))

    try:
        # Install the files
        # make the install directories
        for key in cfg:
            if cfg[key] and not os.path.isdir(cfg[key]):
                os.makedirs(cfg[key])

        # copy the eric config file
        if distDir:
            shutilCopy(configName, cfg["mdir"])
            if os.path.exists(configName + "c"):
                shutilCopy(configName + "c", cfg["mdir"])
        else:
            shutilCopy(configName, modDir)
            if os.path.exists(configName + "c"):
                shutilCopy(configName + "c", modDir)

        # copy the various parts of eric
        copyTree(
            eric7SourceDir,
            cfg["ericDir"],
            ["*.py", "*.pyc", "*.pyo", "*.pyw"],
            excludePatterns=["eric7config.py*"],
        )
        copyTree(
            os.path.join(eric7SourceDir, "Plugins"),
            os.path.join(cfg["ericDir"], "Plugins"),
            ["*.svgz", "*.svg", "*.png", "*.style", "*.tmpl", "*.txt"],
        )
        copyTree(
            os.path.join(eric7SourceDir, "Documentation"),
            cfg["ericDocDir"],
            ["*.html", "*.qch"],
        )
        copyTree(os.path.join(eric7SourceDir, "CSSs"), cfg["ericCSSDir"], ["*.css"])
        copyTree(
            os.path.join(eric7SourceDir, "Styles"),
            cfg["ericStylesDir"],
            ["*.qss", "*.ehj"],
        )
        copyTree(
            os.path.join(eric7SourceDir, "Themes"), cfg["ericThemesDir"], ["*.ethj"]
        )
        copyTree(
            os.path.join(eric7SourceDir, "i18n"), cfg["ericTranslationsDir"], ["*.qm"]
        )
        copyTree(
            os.path.join(eric7SourceDir, "icons"),
            cfg["ericIconDir"],
            ["*.svgz", "*.svg", "*.png", "LICENSE*.*", "readme.txt"],
        )
        copyTree(
            os.path.join(eric7SourceDir, "pixmaps"),
            cfg["ericPixDir"],
            ["*.svgz", "*.svg", "*.png", "*.xpm", "*.ico", "*.gif"],
        )
        copyTree(
            os.path.join(eric7SourceDir, "DesignerTemplates"),
            cfg["ericTemplatesDir"],
            ["*.tmpl"],
        )
        copyTree(
            os.path.join(eric7SourceDir, "CodeTemplates"),
            cfg["ericCodeTemplatesDir"],
            ["*.tmpl"],
        )
        copyTree(
            os.path.join(eric7SourceDir, "DebugClients", "Python", "coverage"),
            os.path.join(cfg["ericDir"], "DebugClients", "Python", "coverage"),
            ["*.js", "*.html", "*.png", "*.css", "*.scss", "*.txt", "*.rst"],
        )

        # copy some data files needed at various places
        copyTree(
            os.path.join(eric7SourceDir, "data"),
            os.path.join(cfg["ericDir"], "data"),
            ["*.txt"],
        )
        copyTree(
            os.path.join(eric7SourceDir, "EricNetwork", "data"),
            os.path.join(cfg["ericDir"], "EricNetwork", "data"),
            ["*.dat", "*.txt"],
        )
        copyTree(
            os.path.join(eric7SourceDir, "IconEditor", "cursors"),
            os.path.join(cfg["ericDir"], "IconEditor", "cursors"),
            ["*.xpm"],
        )
        copyTree(
            os.path.join(eric7SourceDir, "UI", "data"),
            os.path.join(cfg["ericDir"], "UI", "data"),
            ["*.css"],
        )
        copyTree(
            os.path.join(eric7SourceDir, "WebBrowser"),
            os.path.join(cfg["ericDir"], "WebBrowser"),
            ["*.xbel", "*.xml", "*.html", "*.png", "*.gif", "*.js"],
        )

        # copy the wrappers
        for wname in wnames:
            shutilCopy(wname, cfg["bindir"], perm=0o755)
            os.remove(wname)
        shutil.rmtree(scriptsDir)

        # copy the license file
        shutilCopy(os.path.join(sourceDir, "docs", "LICENSE.GPL3"), cfg["ericDir"])

        # create the global plugins directory
        createGlobalPluginsDir()

    except OSError as msg:
        sys.stderr.write("Error: {0}\nTry install with admin rights.\n".format(msg))
        return 7

    # copy some text files to the doc area
    for name in ["LICENSE.GPL3", "THANKS", "changelog"]:
        try:
            shutilCopy(os.path.join(sourceDir, "docs", name), cfg["ericDocDir"])
        except OSError:
            print(
                "Could not install '{0}'.".format(os.path.join(sourceDir, "docs", name))
            )
    for name in glob.glob(os.path.join(sourceDir, "docs", "README*.*")):
        try:
            shutilCopy(name, cfg["ericDocDir"])
        except OSError:
            print("Could not install '{0}'.".format(name))

    # copy some more stuff
    for name in ("default.ekj", "default_Mac.ekj", "default.e4k", "default_Mac.e4k"):
        try:
            shutilCopy(os.path.join(sourceDir, "others", name), cfg["ericOthersDir"])
        except OSError:
            print(
                "Could not install '{0}'.".format(
                    os.path.join(sourceDir, "others", name)
                )
            )

    # install the API file
    if installApis:
        if os.access(cfg["apidir"], os.W_OK):
            for progLanguage in progLanguages:
                apidir = os.path.join(cfg["apidir"], progLanguage)
                print("Installing {0} API files to '{1}'.".format(progLanguage, apidir))
                if not os.path.exists(apidir):
                    os.makedirs(apidir)
                for apiName in glob.glob(
                    os.path.join(eric7SourceDir, "APIs", progLanguage, "*.api")
                ):
                    shutilCopy(apiName, apidir)
                for apiName in glob.glob(
                    os.path.join(eric7SourceDir, "APIs", progLanguage, "*.bas")
                ):
                    shutilCopy(apiName, apidir)
        else:
            print("The API directory '{0}' is not writable.".format(cfg["apidir"]))
            print("Use the API files provided by the 'API Files' plug-in.")

    # Create menu entry for Linux systems
    if sys.platform.startswith("linux"):
        createLinuxSpecifics()

    # Create Desktop and Start Menu entries for Windows systems
    elif sys.platform.startswith(("win", "cygwin")):
        createWindowsLinks()

    # Create a Mac application bundle
    elif sys.platform == "darwin":
        createMacAppBundle(cfg["ericDir"])

    return 0


def createLinuxSpecifics():
    """
    Install Linux specific files.
    """
    global distDir, sourceDir

    dataSourceDir = os.path.join(eric7SourceDir, "data", "linux")

    if distDir:
        dst = os.path.normpath(os.path.join(distDir, "usr/share/icons"))
        if not os.path.exists(dst):
            os.makedirs(dst)
        shutilCopy(
            os.path.join(eric7SourceDir, "pixmaps", "eric_icon.png"),
            os.path.join(dst, "eric.png"),
        )
        shutilCopy(
            os.path.join(eric7SourceDir, "pixmaps", "ericWeb48_icon.png"),
            os.path.join(dst, "ericWeb.png"),
        )

        dst = os.path.normpath(
            os.path.join(distDir, "usr/share/icons/hicolor/48x48/apps")
        )
        if not os.path.exists(dst):
            os.makedirs(dst)
        shutilCopy(
            os.path.join(eric7SourceDir, "pixmaps", "eric48_icon.png"),
            os.path.join(dst, "eric.png"),
        )
        shutilCopy(
            os.path.join(eric7SourceDir, "pixmaps", "ericWeb48_icon.png"),
            os.path.join(dst, "ericWeb.png"),
        )

        dst = os.path.normpath(os.path.join(distDir, "usr/share/applications"))
        if not os.path.exists(dst):
            os.makedirs(dst)
        copyDesktopFile(
            os.path.join(dataSourceDir, "eric7.desktop.in"),
            os.path.join(dst, "eric7.desktop"),
        )
        copyDesktopFile(
            os.path.join(dataSourceDir, "eric7_browser.desktop.in"),
            os.path.join(dst, "eric7_browser.desktop"),
        )

        dst = os.path.normpath(os.path.join(distDir, "usr/share/metainfo"))
        if not os.path.exists(dst):
            os.makedirs(dst)
        copyAppStreamFile(
            os.path.join(dataSourceDir, "eric7.appdata.xml.in"),
            os.path.join(dst, "eric7.appdata.xml"),
        )
    elif os.getuid() == 0:
        shutilCopy(
            os.path.join(eric7SourceDir, "pixmaps", "eric_icon.png"),
            "/usr/share/icons/eric.png",
        )
        shutilCopy(
            os.path.join(eric7SourceDir, "pixmaps", "eric48_icon.png"),
            "/usr/share/icons/hicolor/48x48/apps/eric.png",
        )
        copyDesktopFile(
            os.path.join(dataSourceDir, "eric7.desktop.in"),
            "/usr/share/applications/eric7.desktop",
        )
        if os.path.exists("/usr/share/metainfo"):
            copyAppStreamFile(
                os.path.join(dataSourceDir, "eric7.appdata.xml.in"),
                "/usr/share/metainfo/eric7.appdata.xml",
            )
        elif os.path.exists("/usr/share/appdata"):
            copyAppStreamFile(
                os.path.join(dataSourceDir, "eric7.appdata.xml.in"),
                "/usr/share/appdata/eric7.appdata.xml",
            )
        shutilCopy(
            os.path.join(eric7SourceDir, "pixmaps", "ericWeb48_icon.png"),
            "/usr/share/icons/ericWeb.png",
        )
        shutilCopy(
            os.path.join(eric7SourceDir, "pixmaps", "ericWeb48_icon.png"),
            "/usr/share/icons/hicolor/48x48/apps/ericWeb.png",
        )
        copyDesktopFile(
            os.path.join(dataSourceDir, "eric7_browser.desktop.in"),
            "/usr/share/applications/eric7_browser.desktop",
        )
    elif os.getuid() >= 1000:
        # it is assumed, that user ids start at 1000
        localPath = os.path.join(os.path.expanduser("~"), ".local", "share")
        # create directories first
        for directory in [
            os.path.join(localPath, name)
            for name in (
                "icons",
                "icons/hicolor/48x48/apps",
                "applications",
                "metainfo",
                "appdata",
            )
        ]:
            if not os.path.isdir(directory):
                os.makedirs(directory)
        # now copy the files
        shutilCopy(
            os.path.join(eric7SourceDir, "pixmaps", "eric_icon.png"),
            os.path.join(localPath, "icons", "eric.png"),
        )
        shutilCopy(
            os.path.join(eric7SourceDir, "pixmaps", "eric48_icon.png"),
            os.path.join(localPath, "icons/hicolor/48x48/apps", "eric.png"),
        )
        copyDesktopFile(
            os.path.join(dataSourceDir, "eric7.desktop.in"),
            os.path.join(localPath, "applications", "eric7.desktop"),
        )
        copyAppStreamFile(
            os.path.join(dataSourceDir, "eric7.appdata.xml.in"),
            os.path.join(localPath, "metainfo", "eric7.appdata.xml"),
        )
        copyAppStreamFile(
            os.path.join(dataSourceDir, "eric7.appdata.xml.in"),
            os.path.join(localPath, "appdata", "eric7.appdata.xml"),
        )
        shutilCopy(
            os.path.join(eric7SourceDir, "pixmaps", "ericWeb48_icon.png"),
            os.path.join(localPath, "icons", "ericWeb.png"),
        )
        shutilCopy(
            os.path.join(eric7SourceDir, "pixmaps", "ericWeb48_icon.png"),
            os.path.join(localPath, "icons/hicolor/48x48/apps", "ericWeb.png"),
        )
        copyDesktopFile(
            os.path.join(dataSourceDir, "eric7_browser.desktop.in"),
            os.path.join(localPath, "applications", "eric7_browser.desktop"),
        )


def createWindowsLinks():
    """
    Create Desktop and Start Menu links.
    """
    try:
        # check, if pywin32 is available
        from win32com.client import Dispatch  # __IGNORE_WARNING__
    except ImportError:
        installed = pipInstall(
            "pywin32",
            "\nThe Python package 'pywin32' could not be imported.",
            force=False,
        )
        if installed:
            # create the links via an external script to get around some
            # startup magic done by pywin32.pth
            args = [
                sys.executable,
                os.path.join(os.path.dirname(__file__), "create_windows_links.py"),
            ]
            subprocess.run(args)  # secok
        else:
            print(
                "\nThe Python package 'pywin32' is not installed. Desktop and"
                " Start Menu entries will not be created."
            )
        return

    regPath = (
        "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer"
        + "\\User Shell Folders"
    )

    # 1. create desktop shortcuts
    regName = "Desktop"
    desktopEntry = getWinregEntry(regName, regPath)
    if desktopEntry:
        desktopFolder = os.path.normpath(os.path.expandvars(desktopEntry))
        for linkName, targetPath, iconPath in windowsDesktopEntries():
            linkPath = os.path.join(desktopFolder, linkName)
            createWindowsShortcut(linkPath, targetPath, iconPath)

    # 2. create start menu entry and shortcuts
    regName = "Programs"
    programsEntry = getWinregEntry(regName, regPath)
    if programsEntry:
        programsFolder = os.path.normpath(os.path.expandvars(programsEntry))
        eric7EntryPath = os.path.join(programsFolder, windowsProgramsEntry())
        if not os.path.exists(eric7EntryPath):
            try:
                os.makedirs(eric7EntryPath)
            except OSError:
                # maybe restrictions prohibited link creation
                return

        for linkName, targetPath, iconPath in windowsDesktopEntries():
            linkPath = os.path.join(eric7EntryPath, linkName)
            createWindowsShortcut(linkPath, targetPath, iconPath)


def createMacAppBundle(pydir):
    """
    Create a Mac application bundle.

    @param pydir the name of the directory where the Python script will
        eventually be installed
    @type str
    """
    global cfg, macAppBundleName, macPythonExe, macAppBundlePath

    directories = {
        "contents": "{0}/{1}/Contents/".format(macAppBundlePath, macAppBundleName),
        "exe": "{0}/{1}/Contents/MacOS".format(macAppBundlePath, macAppBundleName),
        "icns": "{0}/{1}/Contents/Resources".format(macAppBundlePath, macAppBundleName),
    }
    for directory in directories.values():
        if not os.path.exists(directory):
            os.makedirs(directory)

    if macPythonExe == defaultMacPythonExe and macPythonExe:
        starter = os.path.join(directories["exe"], "eric")
        os.symlink(macPythonExe, starter)
    else:
        starter = "python{0}".format(sys.version_info.major)

    wname = os.path.join(directories["exe"], "eric7")

    # determine entry for DYLD_FRAMEWORK_PATH
    dyldLine = ""
    try:
        from PyQt6.QtCore import QLibraryInfo

        qtLibraryDir = QLibraryInfo.path(QLibraryInfo.LibraryPath.LibrariesPath)
    except ImportError:
        qtLibraryDir = ""
    if qtLibraryDir:
        dyldLine = "DYLD_FRAMEWORK_PATH={0}\n".format(qtLibraryDir)

    # determine entry for PATH
    pathLine = ""
    path = os.getenv("PATH", "")
    if path:
        pybin = os.path.join(sys.exec_prefix, "bin")
        pathlist = path.split(os.pathsep)
        pathlist_n = [pybin]
        for path_ in pathlist:
            if path_ and path_ not in pathlist_n:
                pathlist_n.append(path_)
        pathLine = "PATH={0}\n".format(os.pathsep.join(pathlist_n))

    # create the wrapper script
    wrapper = (
        """#!/bin/sh\n"""
        """\n"""
        """{0}"""
        """{1}"""
        """exec "{2}" "{3}/{4}.py" "$@"\n""".format(
            pathLine, dyldLine, starter, pydir, "eric7"
        )
    )
    copyToFile(wname, wrapper)
    os.chmod(wname, 0o755)  # secok

    shutilCopy(
        os.path.join(eric7SourceDir, "pixmaps", "eric_2.icns"),
        os.path.join(directories["icns"], "eric.icns"),
    )

    if os.path.exists(os.path.join("eric", "eric7", "UI", "Info.py")):
        # Installing from archive
        from eric.eric7.UI.Info import Version, CopyrightShort
    elif os.path.exists(os.path.join("eric7", "UI", "Info.py")):
        # Installing from source tree
        from eric7.UI.Info import Version, CopyrightShort
    else:
        Version = "Unknown"
        CopyrightShort = "(c) 2002 - 2022 Detlev Offenbach"

    copyToFile(
        os.path.join(directories["contents"], "Info.plist"),
        """<?xml version="1.0" encoding="UTF-8"?>\n"""
        """<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"\n"""
        """          "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n"""
        """<plist version="1.0">\n"""
        """<dict>\n"""
        """    <key>CFBundleExecutable</key>\n"""
        """    <string>eric7</string>\n"""
        """    <key>CFBundleIconFile</key>\n"""
        """    <string>eric.icns</string>\n"""
        """    <key>CFBundleInfoDictionaryVersion</key>\n"""
        """    <string>{1}</string>\n"""
        """    <key>CFBundleName</key>\n"""
        """    <string>{0}</string>\n"""
        """    <key>CFBundleDisplayName</key>\n"""
        """    <string>{0}</string>\n"""
        """    <key>CFBundlePackageType</key>\n"""
        """    <string>APPL</string>\n"""
        """    <key>CFBundleSignature</key>\n"""
        """    <string>ERIC-IDE</string>\n"""
        """    <key>CFBundleVersion</key>\n"""
        """    <string>{1}</string>\n"""
        """    <key>CFBundleGetInfoString</key>\n"""
        """    <string>{1}, {2}</string>\n"""
        """    <key>CFBundleIdentifier</key>\n"""
        """    <string>org.python-projects.eric-ide</string>\n"""
        """    <key>NSRequiresAquaSystemAppearance</key>\n"""
        """    <string>false</string>\n"""
        """    <key>LSEnvironment</key>\n"""
        """    <dict>\n"""
        """        <key>LANG</key>\n"""
        """        <string>en_US.UTF-8</string>\n"""
        """        <key>LC_ALL</key>\n"""
        """        <string>en_US.UTF-8</string>\n"""
        """        <key>LC_CTYPE</key>\n"""
        """        <string>en_US.UTF-8</string>\n"""
        """    </dict>\n"""
        """</dict>\n"""
        """</plist>\n""".format(
            macAppBundleName.replace(".app", ""),
            Version.split(None, 1)[0],
            CopyrightShort,
        ),
    )


def createInstallConfig():
    """
    Create the installation config dictionary.
    """
    global modDir, platBinDir, cfg, apisDir, installApis

    ericdir = os.path.join(modDir, "eric7")
    cfg = {
        "ericDir": ericdir,
        "ericPixDir": os.path.join(ericdir, "pixmaps"),
        "ericIconDir": os.path.join(ericdir, "icons"),
        "ericDTDDir": os.path.join(ericdir, "DTDs"),
        "ericCSSDir": os.path.join(ericdir, "CSSs"),
        "ericStylesDir": os.path.join(ericdir, "Styles"),
        "ericThemesDir": os.path.join(ericdir, "Themes"),
        "ericDocDir": os.path.join(ericdir, "Documentation"),
        "ericExamplesDir": os.path.join(ericdir, "Examples"),
        "ericTranslationsDir": os.path.join(ericdir, "i18n"),
        "ericTemplatesDir": os.path.join(ericdir, "DesignerTemplates"),
        "ericCodeTemplatesDir": os.path.join(ericdir, "CodeTemplates"),
        "ericOthersDir": ericdir,
        "bindir": platBinDir,
        "mdir": modDir,
    }
    if installApis:
        if apisDir:
            cfg["apidir"] = apisDir
        else:
            cfg["apidir"] = os.path.join(ericdir, "api")
    else:
        cfg["apidir"] = ""


configLength = 16


def createConfig():
    """
    Create a config file with the respective config entries.
    """
    global cfg, macAppBundlePath, configName

    apis = []
    if installApis:
        for progLanguage in progLanguages:
            for apiName in sorted(
                glob.glob(os.path.join(eric7SourceDir, "APIs", progLanguage, "*.api"))
            ):
                apis.append(os.path.basename(apiName))

    macConfig = (
        (
            """    'macAppBundlePath': r'{0}',\n"""
            """    'macAppBundleName': r'{1}',\n"""
        ).format(macAppBundlePath, macAppBundleName)
        if sys.platform == "darwin"
        else ""
    )
    config = (
        """# -*- coding: utf-8 -*-\n"""
        """#\n"""
        """# This module contains the configuration of the individual eric"""
        """ installation\n"""
        """#\n"""
        """\n"""
        """_pkg_config = {{\n"""
        """    'ericDir': r'{0}',\n"""
        """    'ericPixDir': r'{1}',\n"""
        """    'ericIconDir': r'{2}',\n"""
        """    'ericDTDDir': r'{3}',\n"""
        """    'ericCSSDir': r'{4}',\n"""
        """    'ericStylesDir': r'{5}',\n"""
        """    'ericThemesDir': r'{6}',\n"""
        """    'ericDocDir': r'{7}',\n"""
        """    'ericExamplesDir': r'{8}',\n"""
        """    'ericTranslationsDir': r'{9}',\n"""
        """    'ericTemplatesDir': r'{10}',\n"""
        """    'ericCodeTemplatesDir': r'{11}',\n"""
        """    'ericOthersDir': r'{12}',\n"""
        """    'bindir': r'{13}',\n"""
        """    'mdir': r'{14}',\n"""
        """    'apidir': r'{15}',\n"""
        """    'apis': {16},\n"""
        """{17}"""
        """}}\n"""
        """\n"""
        """def getConfig(name):\n"""
        """    '''\n"""
        """    Module function to get a configuration value.\n"""
        """\n"""
        """    @param name name of the configuration value"""
        """    @type str\n"""
        """    @exception AttributeError raised to indicate an invalid"""
        """ config entry\n"""
        """    '''\n"""
        """    try:\n"""
        """        return _pkg_config[name]\n"""
        """    except KeyError:\n"""
        """        pass\n"""
        """\n"""
        """    raise AttributeError(\n"""
        """        '"{{0}}" is not a valid configuration value'"""
        """.format(name))\n"""
    ).format(
        cfg["ericDir"],
        cfg["ericPixDir"],
        cfg["ericIconDir"],
        cfg["ericDTDDir"],
        cfg["ericCSSDir"],
        cfg["ericStylesDir"],
        cfg["ericThemesDir"],
        cfg["ericDocDir"],
        cfg["ericExamplesDir"],
        cfg["ericTranslationsDir"],
        cfg["ericTemplatesDir"],
        cfg["ericCodeTemplatesDir"],
        cfg["ericOthersDir"],
        cfg["bindir"],
        cfg["mdir"],
        cfg["apidir"],
        sorted(apis),
        macConfig,
    )
    copyToFile(configName, config)


def createInstallInfo():
    """
    Record information about the way eric was installed.
    """
    global createInstallInfoFile, installInfo, installCwd, cfg

    if createInstallInfoFile:
        installDateTime = datetime.datetime.now(tz=None)
        try:
            installInfo["sudo"] = os.getuid() == 0
        except AttributeError:
            installInfo["sudo"] = False
        installInfo["user"] = getpass.getuser()
        installInfo["exe"] = sys.executable
        installInfo["argv"] = " ".join(shlex.quote(a) for a in sys.argv[:])
        installInfo["install_cwd"] = installCwd
        installInfo["eric"] = cfg["ericDir"]
        installInfo["virtualenv"] = installInfo["eric"].startswith(
            os.path.expanduser("~")
        )
        installInfo["installed"] = True
        installInfo["installed_on"] = installDateTime.strftime("%Y-%m-%d %H:%M:%S")
        installInfo["guessed"] = False
        installInfo["edited"] = False
        installInfo["pip"] = False
        installInfo["remarks"] = ""
        installInfo["install_cwd_edited"] = False
        installInfo["exe_edited"] = False
        installInfo["argv_edited"] = False
        installInfo["eric_edited"] = False


def pipInstall(packageName, message, force=True):
    """
    Install the given package via pip.

    @param packageName name of the package to be installed
    @type str
    @param message message to be shown to the user
    @type str
    @param force flag indicating to perform the installation
        without asking the user
    @type bool
    @return flag indicating a successful installation
    @rtype bool
    """
    global yes2All

    ok = False
    if yes2All or force:
        answer = "y"
    else:
        print(
            "{0}\nShall '{1}' be installed using pip? (Y/n)".format(
                message, packageName
            ),
            end=" ",
        )
        answer = input()  # secok
    if answer in ("", "Y", "y"):
        exitCode = subprocess.run(  # secok
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--prefer-binary",
                "--upgrade",
                packageName,
            ]
        ).returncode
        ok = exitCode == 0

    return ok


def isPipOutdated():
    """
    Check, if pip is outdated.

    @return flag indicating an outdated pip
    @rtype bool
    """
    try:
        pipOut = (
            subprocess.run(  # secok
                [sys.executable, "-m", "pip", "list", "--outdated", "--format=json"],
                check=True,
                capture_output=True,
                text=True,
            )
            .stdout.strip()
            .splitlines()[0]
        )
        # only the first line contains the JSON data
    except (OSError, subprocess.CalledProcessError):
        pipOut = "[]"  # default empty list
    try:
        jsonList = json.loads(pipOut)
    except Exception:
        jsonList = []
    for package in jsonList:
        if isinstance(package, dict) and package["name"] == "pip":
            print(
                "'pip' is outdated (installed {0}, available {1})".format(
                    package["version"], package["latest_version"]
                )
            )
            return True

    return False


def updatePip():
    """
    Update the installed pip package.
    """
    global yes2All

    if yes2All:
        answer = "y"
    else:
        print("Shall 'pip' be updated (recommended)? (Y/n)", end=" ")
        answer = input()  # secok
    if answer in ("", "Y", "y"):
        subprocess.run(  # secok
            [sys.executable, "-m", "pip", "install", "--upgrade", "pip"]
        )


def versionToStr(version):
    """
    Function to convert a version number into a version string.

    @param version version number to convert
    @type int
    @return version string
    @rtype str
    """
    parts = []
    while version:
        parts.append(version & 0xFF)
        version >>= 8
    return ".".join(str(p) for p in reversed(parts))


def doDependancyChecks():
    """
    Perform some dependency checks.
    """
    global verbose

    requiredVersions = {
        "pyqt6": 0x60200,  # v6.2.0
        "pyqt6-charts": 0x60200,  # v6.2.0
        "pyqt6-webengine": 0x60200,  # v6.2.0
        "pyqt6-qscintilla": 0x20D00,  # v2.13.0
        "sip": 0x60100,  # v6.1.0
    }

    try:
        isSudo = os.getuid() == 0 and sys.platform != "darwin"
        # disregard sudo installs on macOS
    except AttributeError:
        isSudo = False

    print("Checking dependencies")

    # update pip first even if we don't need to install anything
    if not isSudo and isPipOutdated():
        updatePip()
        print("\n")

    # perform dependency checks
    if sys.version_info < (3, 7, 0) or sys.version_info >= (3, 12, 0):
        print("Sorry, you must have Python 3.7.0 or higher, but less 3.12.0.")
        print("Yours is {0}.".format(".".join(str(v) for v in sys.version_info[:3])))
        exit(5)

    try:
        import xml.etree  # __IGNORE_WARNING__
    except ImportError:
        print("Your Python installation is missing the XML module.")
        print("Please install it and try again.")
        exit(5)

    try:
        from PyQt6.QtCore import qVersion
    except ImportError as err:
        msg = "'PyQt6' could not be detected.{0}".format(
            "\nError: {0}".format(err) if verbose else ""
        )
        installed = not isSudo and pipInstall(
            "PyQt6>={0}".format(versionToStr(requiredVersions["pyqt6"])), msg
        )
        if installed:
            # try to import it again
            try:
                from PyQt6.QtCore import qVersion
            except ImportError as msg:
                print("Sorry, please install PyQt6.")
                print("Error: {0}".format(msg))
                exit(1)
        else:
            print("Sorry, please install PyQt6.")
            print("Error: {0}".format(msg))
            exit(1)
    print("Found PyQt6")

    try:
        pyuic = "pyuic6"
        from PyQt6 import uic  # __IGNORE_WARNING__
    except ImportError as err:
        print("Sorry, {0} is not installed.".format(pyuic))
        if verbose:
            print("Error: {0}".format(err))
        exit(1)
    print("Found {0}".format(pyuic))

    try:
        from PyQt6 import QtWebEngineWidgets  # __IGNORE_WARNING__
    except ImportError as err:
        if isSudo:
            print("Optional 'PyQt6-WebEngine' could not be detected.")
        else:
            msg = "Optional 'PyQt6-WebEngine' could not be detected.{0}".format(
                "\nError: {0}".format(err) if verbose else ""
            )
            pipInstall(
                "PyQt6-WebEngine>={0}".format(
                    versionToStr(requiredVersions["pyqt6-webengine"])
                ),
                msg,
            )

    try:
        from PyQt6 import QtCharts  # __IGNORE_WARNING__
    except ImportError as err:
        if isSudo:
            print("Optional 'PyQt6-Charts' could not be detected.")
        else:
            msg = "Optional 'PyQt6-Charts' could not be detected.{0}".format(
                "\nError: {0}".format(err) if verbose else ""
            )
            pipInstall(
                "PyQt6-Charts>={0}".format(
                    versionToStr(requiredVersions["pyqt6-charts"])
                ),
                msg,
            )
    print("Found PyQt6-Charts")

    try:
        from PyQt6 import Qsci  # __IGNORE_WARNING__
    except ImportError as err:
        msg = "'PyQt6-QScintilla' could not be detected.{0}".format(
            "\nError: {0}".format(err) if verbose else ""
        )
        installed = not isSudo and pipInstall(
            "PyQt6-QScintilla>={0}".format(
                versionToStr(requiredVersions["pyqt6-qscintilla"])
            ),
            msg,
        )
        if installed:
            # try to import it again
            try:
                from PyQt6 import Qsci  # __IGNORE_WARNING__

                message = None
            except ImportError as msg:
                message = str(msg)
        else:
            message = "PyQt6-QScintilla could not be installed."
        if message:
            print("Sorry, please install QScintilla2 and")
            print("its PyQt6 wrapper.")
            print("Error: {0}".format(message))
            exit(1)
    print("Found PyQt6-QScintilla")

    pyqt6BaseModulesList = [
        "PyQt6.QtGui",
        "PyQt6.QtNetwork",
        "PyQt6.QtPrintSupport",
        "PyQt6.QtSql",
        "PyQt6.QtSvg",
        "PyQt6.QtSvgWidgets",
        "PyQt6.QtWidgets",
    ]
    requiredModulesList = {
        # key is pip project name
        # value is tuple of package name, pip install constraint
        "tomlkit": ("tomlkit", ""),
        "asttokens": ("asttokens", ""),
        "EditorConfig": ("editorconfig", ""),
        "Pygments": ("pygments", ""),
        "parso": ("parso", ""),
        "jedi": ("jedi", ""),
        "packaging": ("packaging", ""),
        "cyclonedx-python-lib": ("cyclonedx", ""),
        "cyclonedx-bom": ("cyclonedx_py", ""),
        "trove-classifiers": ("trove_classifiers", ""),
        "black": ("black", ">=22.6.0"),
    }
    optionalModulesList = {
        # key is pip project name
        # value is tuple of package name, pip install constraint
        "docutils": ("docutils", ""),
        "Markdown": ("markdown", ""),
        "pyyaml": ("yaml", ""),
        "chardet": ("chardet", ""),
        "Send2Trash": ("send2trash", ""),
        "pyenchant": ("enchant", ""),
        "wheel": ("wheel", ""),
    }
    if withPyqt6Tools:
        optionalModulesList["qt6-applications"] = ("qt6_applications", "")

    # check mandatory PyQt6 modules
    modulesOK = True
    for pyqt6BaseModule in pyqt6BaseModulesList:
        name = pyqt6BaseModule.split(".")[1]
        try:
            __import__(pyqt6BaseModule)
            print("Found", name)
        except ImportError as err:
            print("Sorry, please install {0}.".format(name))
            if verbose:
                print("Error: {0}".format(err))
            modulesOK = False
    if not modulesOK:
        exit(1)

    # check required modules
    requiredMissing = False
    for requiredPackage in requiredModulesList:
        try:
            __import__(requiredModulesList[requiredPackage][0])
            print("Found", requiredPackage)
        except ImportError as err:
            if isSudo:
                print("Required '{0}' could not be detected.".format(requiredPackage))
                requiredMissing = True
            else:
                msg = "Required '{0}' could not be detected.{1}".format(
                    requiredPackage, "\nError: {0}".format(err) if verbose else ""
                )
                pipInstall(
                    requiredPackage + requiredModulesList[requiredPackage][1],
                    msg,
                    force=True,
                )
    if requiredMissing:
        print("Some required packages are missing and could not be installed.")
        print("Install them manually with:")
        print("    {0} install-dependencies.py --required".format(sys.executable))

    # check optional modules
    optionalMissing = False
    for optPackage in optionalModulesList:
        try:
            __import__(optionalModulesList[optPackage][0])
            print("Found", optPackage)
        except ImportError as err:
            if isSudo:
                print("Optional '{0}' could not be detected.".format(optPackage))
                optionalMissing = True
            else:
                msg = "Optional '{0}' could not be detected.{1}".format(
                    optPackage, "\nError: {0}".format(err) if verbose else ""
                )
                pipInstall(optPackage + optionalModulesList[optPackage][1], msg)
    if optionalMissing:
        print("Some optional packages are missing and could not be installed.")
        print("Install them manually with:")
        print("    {0} install-dependencies.py --optional".format(sys.executable))

    if requiredMissing and optionalMissing:
        print("Alternatively you may install all of them with:")
        print("    {0} install-dependencies.py --all".format(sys.executable))

    # determine the platform dependent black list
    if sys.platform.startswith(("win", "cygwin")):
        PlatformBlackLists = PlatformsBlackLists["windows"]
    elif sys.platform.startswith("linux"):
        PlatformBlackLists = PlatformsBlackLists["linux"]
    else:
        PlatformBlackLists = PlatformsBlackLists["mac"]

    print("\nVersion Information")
    print("-------------------")

    print("Python: {0:d}.{1:d}.{2:d}".format(*sys.version_info[:3]))

    # check version of Qt
    # ===================
    qtMajor = int(qVersion().split(".")[0])
    qtMinor = int(qVersion().split(".")[1])
    print("Qt6: {0}".format(qVersion().strip()))
    if qtMajor == 6 and qtMinor < 1:
        print("Sorry, you must have Qt version 6.1.0 or better.")
        exit(2)

    # check version of sip
    # ====================
    with contextlib.suppress(ImportError, AttributeError):
        try:
            from PyQt6 import sip
        except ImportError:
            import sip
        print("sip:", sip.SIP_VERSION_STR.strip())
        # always assume, that snapshots or dev versions are new enough
        if "snapshot" not in sip.SIP_VERSION_STR and "dev" not in sip.SIP_VERSION_STR:
            if sip.SIP_VERSION < requiredVersions["sip"]:
                print(
                    "Sorry, you must have sip {0} or higher or"
                    " a recent development release.".format(
                        versionToStr(requiredVersions["sip"])
                    )
                )
                exit(3)
            # check for blacklisted versions
            for vers in BlackLists["sip"] + PlatformBlackLists["sip"]:
                if vers == sip.SIP_VERSION:
                    print(
                        "Sorry, sip version {0} is not compatible with eric.".format(
                            versionToStr(vers)
                        )
                    )
                    print("Please install another version.")
                    exit(3)

    # check version of PyQt6
    # ======================
    from PyQt6.QtCore import PYQT_VERSION, PYQT_VERSION_STR

    print("PyQt6:", PYQT_VERSION_STR.strip())
    # always assume, that snapshots or dev versions are new enough
    if "snapshot" not in PYQT_VERSION_STR and "dev" not in PYQT_VERSION_STR:
        if PYQT_VERSION < requiredVersions["pyqt6"]:
            print(
                "Sorry, you must have PyQt {0} or better or"
                " a recent development release.".format(
                    versionToStr(requiredVersions["pyqt6"])
                )
            )
            exit(4)
        # check for blacklisted versions
        for vers in BlackLists["PyQt6"] + PlatformBlackLists["PyQt6"]:
            if vers == PYQT_VERSION:
                print(
                    "Sorry, PyQt version {0} is not compatible with eric.".format(
                        versionToStr(vers)
                    )
                )
                print("Please install another version.")
                exit(4)

    # check version of QScintilla
    # ===========================
    from PyQt6.Qsci import QSCINTILLA_VERSION, QSCINTILLA_VERSION_STR

    print("PyQt6-QScintilla:", QSCINTILLA_VERSION_STR.strip())
    # always assume, that snapshots or dev versions are new enough
    if "snapshot" not in QSCINTILLA_VERSION_STR and "dev" not in QSCINTILLA_VERSION_STR:
        if QSCINTILLA_VERSION < requiredVersions["pyqt6-qscintilla"]:
            print(
                "Sorry, you must have PyQt6-QScintilla {0} or higher or"
                " a recent development release.".format(
                    versionToStr(requiredVersions["pyqt6-qscintilla"])
                )
            )
            exit(5)
        # check for blacklisted versions
        for vers in BlackLists["QScintilla2"] + PlatformBlackLists["QScintilla2"]:
            if vers == QSCINTILLA_VERSION:
                print(
                    "Sorry, QScintilla2 version {0} is not compatible with"
                    " eric.".format(versionToStr(vers))
                )
                print("Please install another version.")
                exit(5)

    # print version info for additional modules
    with contextlib.suppress(NameError, AttributeError):
        print("PyQt6-Charts:", QtCharts.PYQT_CHART_VERSION_STR)

    with contextlib.suppress(ImportError, AttributeError):
        from PyQt6 import QtWebEngineCore

        print("PyQt6-WebEngine:", QtWebEngineCore.PYQT_WEBENGINE_VERSION_STR)

    print()
    print("All dependencies ok.")
    print()


def __pyName(py_dir, py_file):
    """
    Local function to create the Python source file name for the compiled
    .ui file.

    @param py_dir suggested name of the directory (string)
    @param py_file suggested name for the compile source file (string)
    @return tuple of directory name (string) and source file name (string)
    """
    return py_dir, "Ui_{0}".format(py_file)


def compileUiFiles():
    """
    Compile the .ui files to Python sources.
    """
    from PyQt6.uic import compileUiDir

    compileUiDir(eric7SourceDir, True, __pyName)


def prepareInfoFile(fileName):
    """
    Function to prepare an Info.py file when installing from source.

    @param fileName name of the Python file containing the info (string)
    """
    if not fileName:
        return

    with contextlib.suppress(OSError):
        os.rename(fileName, fileName + ".orig")
    localHg = (
        os.path.join(sys.exec_prefix, "Scripts", "hg.exe")
        if sys.platform.startswith(("win", "cygwin"))
        else os.path.join(sys.exec_prefix, "bin", "hg")
    )
    for hg in (localHg, "hg"):
        with contextlib.suppress(OSError, subprocess.CalledProcessError):
            hgOut = subprocess.run(  # secok
                [hg, "identify", "-i"], check=True, capture_output=True, text=True
            ).stdout
            if hgOut:
                break
    else:
        hgOut = ""
    if hgOut:
        hgOut = hgOut.strip()
        if hgOut.endswith("+"):
            hgOut = hgOut[:-1]
        with open(fileName + ".orig", "r", encoding="utf-8") as f:
            text = f.read()
        text = text.replace("@@REVISION@@", hgOut).replace(
            "@@VERSION@@", "rev_" + hgOut
        )
        copyToFile(fileName, text)
    else:
        shutil.copy(fileName + ".orig", fileName)


def getWinregEntry(name, path):
    """
    Function to get an entry from the Windows Registry.

    @param name variable name
    @type str
    @param path registry path of the variable
    @type str
    @return value of requested registry variable
    @rtype any
    """
    try:
        import winreg
    except ImportError:
        return None

    try:
        registryKey = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(registryKey, name)
        winreg.CloseKey(registryKey)
        return value
    except WindowsError:
        return None


def createWindowsShortcut(linkPath, targetPath, iconPath):
    """
    Create Windows shortcut.

    @param linkPath path of the shortcut file
    @type str
    @param targetPath path the shortcut shall point to
    @type str
    @param iconPath path of the icon file
    @type str
    """
    from win32com.client import Dispatch
    from pywintypes import com_error

    with contextlib.suppress(com_error):
        shell = Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(linkPath)
        shortcut.Targetpath = targetPath
        shortcut.WorkingDirectory = os.path.dirname(targetPath)
        shortcut.IconLocation = iconPath
        shortcut.save()


def windowsDesktopNames():
    """
    Function to generate the link names for the Windows Desktop.

    @return list of desktop link names
    @rtype list of str
    """
    return [e[0] for e in windowsDesktopEntries()]


def windowsDesktopEntries():
    """
    Function to generate data for the Windows Desktop links.

    @return list of tuples containing the desktop link name,
        the link target and the icon target
    @rtype list of tuples of (str, str, str)
    """
    global cfg

    majorVersion, minorVersion = sys.version_info[:2]
    entriesTemplates = [
        (
            "eric7 (Python {0}.{1}).lnk",
            os.path.join(cfg["bindir"], "eric7.cmd"),
            os.path.join(cfg["ericPixDir"], "eric7.ico"),
        ),
        (
            "eric7 Browser (Python {0}.{1}).lnk",
            os.path.join(cfg["bindir"], "eric7_browser.cmd"),
            os.path.join(cfg["ericPixDir"], "ericWeb48.ico"),
        ),
    ]

    return [
        (e[0].format(majorVersion, minorVersion), e[1], e[2]) for e in entriesTemplates
    ]


def windowsProgramsEntry():
    """
    Function to generate the name of the Start Menu top entry.

    @return name of the Start Menu top entry
    @rtype str
    """
    majorVersion, minorVersion = sys.version_info[:2]
    return "eric7 (Python {0}.{1})".format(majorVersion, minorVersion)


def main(argv):
    """
    The main function of the script.

    @param argv list of command line arguments
    @type list of str
    """
    import getopt

    # Parse the command line.
    global progName, modDir, doCleanup, doCompile, distDir, cfg, apisDir
    global sourceDir, eric7SourceDir, configName
    global macAppBundlePath, macAppBundleName, macPythonExe
    global installApis, doCleanDesktopLinks, yes2All
    global createInstallInfoFile, installCwd
    global withPyqt6Tools
    global verbose

    if sys.version_info < (3, 7, 0) or sys.version_info > (3, 99, 99):
        print("Sorry, eric requires at least Python 3.7 for running.")
        exit(5)

    progName = os.path.basename(argv[0])

    installCwd = os.getcwd()

    if os.path.dirname(argv[0]):
        os.chdir(os.path.dirname(argv[0]))

    initGlobals()

    try:
        if sys.platform.startswith(("win", "cygwin")):
            optlist, args = getopt.getopt(
                argv[1:],
                "chvxza:b:d:f:",
                ["help", "no-apis", "no-info", "no-tools", "verbose", "yes"],
            )
        elif sys.platform == "darwin":
            optlist, args = getopt.getopt(
                argv[1:],
                "chvxza:b:d:f:i:m:n:p:",
                ["help", "no-apis", "no-info", "no-tools", "verbose", "yes"],
            )
        else:
            optlist, args = getopt.getopt(
                argv[1:],
                "chvxza:b:d:f:i:",
                ["help", "no-apis", "no-info", "no-tools", "verbose", "yes"],
            )
    except getopt.GetoptError as err:
        print(err)
        usage()

    global platBinDir

    depChecks = True

    for opt, arg in optlist:
        if opt in ["-h", "--help"]:
            usage(0)
        elif opt == "-a":
            apisDir = arg
        elif opt == "-b":
            platBinDir = arg
        elif opt == "-d":
            modDir = arg
        elif opt == "-i":
            distDir = os.path.normpath(arg)
        elif opt == "-x":
            depChecks = False
        elif opt == "-c":
            doCleanup = False
        elif opt == "-z":
            doCompile = False
        elif opt == "-f":
            with open(arg) as f:
                try:
                    exec(compile(f.read(), arg, "exec"), globals())
                    # secok
                    if len(cfg) != configLength:
                        print(
                            "The configuration dictionary in '{0}' is"
                            " incorrect. Aborting".format(arg)
                        )
                        exit(6)
                except Exception:
                    cfg = {}
        elif opt == "-m":
            macAppBundleName = arg
        elif opt == "-n":
            macAppBundlePath = arg
        elif opt == "-p":
            macPythonExe = arg
        elif opt == "--no-apis":
            installApis = False
        elif opt == "--clean-desktop":
            doCleanDesktopLinks = True
        elif opt == "--yes":
            yes2All = True
        elif opt == "--with-tools":
            withPyqt6Tools = True
        elif opt == "--no-info":
            createInstallInfoFile = False
        elif opt in ["-v", "--verbose"]:
            verbose = True

    infoName = ""
    installFromSource = not os.path.isdir(sourceDir)

    # check dependencies
    if depChecks:
        doDependancyChecks()

    if installFromSource:
        sourceDir = os.path.abspath("..")

    eric7SourceDir = (
        os.path.join(sourceDir, "src", "eric7")
        if os.path.exists(os.path.join(sourceDir, "src", "eric7"))
        else os.path.join(sourceDir, "eric7")
    )

    # cleanup source if installing from source
    if installFromSource:
        print("Cleaning up source ...")
        cleanupSource(sourceDir)
        print()

        configName = os.path.join(eric7SourceDir, "eric7config.py")
        if os.path.exists(os.path.join(sourceDir, ".hg")):
            # we are installing from source with repo
            infoName = os.path.join(eric7SourceDir, "UI", "Info.py")
            prepareInfoFile(infoName)

    if len(cfg) == 0:
        createInstallConfig()

    # get rid of development config file, if it exists
    with contextlib.suppress(OSError):
        if installFromSource:
            os.rename(configName, configName + ".orig")
            configNameC = configName + "c"
            if os.path.exists(configNameC):
                os.remove(configNameC)
        os.remove(configName)

    # cleanup old installation
    print("Cleaning up old installation ...")
    try:
        if doCleanup:
            if distDir:
                shutil.rmtree(distDir, True)
            else:
                cleanUp()
    except OSError as msg:
        sys.stderr.write("Error: {0}\nTry install as root.\n".format(msg))
        exit(7)

    # Create a config file and delete the default one
    print("\nCreating configuration file ...")
    createConfig()

    createInstallInfo()

    # Compile .ui files
    print("\nCompiling user interface files ...")
    # step 1: remove old Ui_*.py files
    for root, _, files in os.walk(sourceDir):
        for file in [f for f in files if fnmatch.fnmatch(f, "Ui_*.py")]:
            os.remove(os.path.join(root, file))
    # step 2: compile the forms
    compileUiFiles()

    if doCompile:
        print("\nCompiling source files ...")
        skipRe = re.compile(r"DebugClients[\\/]Python[\\/]")
        sys.stdout = io.StringIO()
        if distDir:
            compileall.compile_dir(
                eric7SourceDir,
                ddir=os.path.join(distDir, modDir, cfg["ericDir"]),
                rx=skipRe,
                quiet=True,
            )
            py_compile.compile(
                configName, dfile=os.path.join(distDir, modDir, "eric7config.py")
            )
        else:
            compileall.compile_dir(
                eric7SourceDir,
                ddir=os.path.join(modDir, cfg["ericDir"]),
                rx=skipRe,
                quiet=True,
            )
            py_compile.compile(configName, dfile=os.path.join(modDir, "eric7config.py"))
        sys.stdout = sys.__stdout__
    print("\nInstalling eric ...")
    res = installEric()

    if createInstallInfoFile:
        with open(
            os.path.join(cfg["ericDir"], installInfoName), "w"
        ) as installInfoFile:
            json.dump(installInfo, installInfoFile, indent=2)

    # do some cleanup
    with contextlib.suppress(OSError):
        if installFromSource:
            os.remove(configName)
            configNameC = configName + "c"
            if os.path.exists(configNameC):
                os.remove(configNameC)
            os.rename(configName + ".orig", configName)
    with contextlib.suppress(OSError):
        if installFromSource and infoName:
            os.remove(infoName)
            infoNameC = infoName + "c"
            if os.path.exists(infoNameC):
                os.remove(infoNameC)
            os.rename(infoName + ".orig", infoName)

    print("\nInstallation complete.")
    print()

    exit(res)


if __name__ == "__main__":
    try:
        main(sys.argv)
    except SystemExit:
        raise
    except Exception:
        print(
            """An internal error occured.  Please report all the output"""
            """ of the program,\nincluding the following traceback, to"""
            """ eric-bugs@eric-ide.python-projects.org.\n"""
        )
        raise

#
# eflag: noqa = M801
