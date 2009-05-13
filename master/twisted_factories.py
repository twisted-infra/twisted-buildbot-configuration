"""
Build classes specific to the Twisted codebase
"""

from buildbot.process.properties import WithProperties
from buildbot.process.base import Build
from buildbot.process.factory import BuildFactory
from buildbot.scheduler import Scheduler
from buildbot.steps import shell, transfer
from buildbot.steps.shell import ShellCommand
from buildbot.steps.source import SVN, Bzr

from twisted_steps import ProcessDocs, ReportPythonModuleVersions, \
    Trial, RemovePYCs, CheckDocumentation, LearnVersion
from pypy_steps import Translate

TRIAL_FLAGS = ["--reporter=bwverbose"]
WARNING_FLAGS = ["--unclean-warnings"]
FORCEGC_FLAGS = ["--force-gc"]

class TwistedBuild(Build):
    workdir = "Twisted" # twisted's bin/trial expects to live in here



class TwistedScheduler(Scheduler):
    def fileIsImportant(self, change):
        for filename in change.files:
            if not filename.startswith("doc/fun/"):
                return 1
        return 0



class TwistedTrial(Trial):
    tests = "twisted"
    # the Trial in Twisted >=2.1.0 has --recurse on by default, and -to
    # turned into --reporter=bwverbose .
    recurse = False
    trialMode = TRIAL_FLAGS
    testpath = None
    trial = "./bin/trial"

class TwistedBaseFactory(BuildFactory):
    """
    @ivar python: The path to the Python executable to use.  This is a
        list, to allow additional arguments to be passed.
    """
    buildClass = TwistedBuild
    # bin/trial expects its parent directory to be named "Twisted": it uses
    # this to add the local tree to PYTHONPATH during tests
    workdir = "Twisted"

    forceGarbageCollection = False

    def __init__(self, python, source, uncleanWarnings, trialMode=None):
        BuildFactory.__init__(self, [source])

        if type(python) is str:
            python = [python]

        self.python = python
        self.uncleanWarnings = uncleanWarnings
        self.trialMode = trialMode

        self.addStep(
            ReportPythonModuleVersions, 
            python=self.python,
            moduleInfo=[("OpenSSL", "OpenSSL.__version__"),
                        ("Crypto", "Crypto.__version__"),
                        ("gmpy", "gmpy.version()"),
                        ("SOAPpy", "SOAPpy.__version__"),
                        ("ctypes", "ctypes.__version__"),
                        ("gtk", "gtk.gtk_version"),
                        ("gtk", "gtk.pygtk_version"),
                        ("win32api", 
                         "win32api.GetFileVersionInfo(win32api.__file__, chr(92))['FileVersionLS'] >> 16")])


    def addTrialStep(self, **kw):
        if self.trialMode is not None:
            trialMode = self.trialMode
        else:
            trialMode = TRIAL_FLAGS

        if self.uncleanWarnings:
            trialMode = trialMode + WARNING_FLAGS
        if self.forceGarbageCollection:
            trialMode = trialMode + FORCEGC_FLAGS
        self.addStep(TwistedTrial, python=self.python, trialMode=trialMode, **kw)


class TwistedDocumentationBuildFactory(TwistedBaseFactory):
    treeStableTimer = 5 * 60

    def __init__(self, source, python="python"):
        TwistedBaseFactory.__init__(self, python, source, False)
        self.addStep(CheckDocumentation)
        self.addStep(ProcessDocs)
        self.addStep(
            shell.ShellCommand,
            command=['/bin/tar', 'cjf', 'apidocs.tar.bz2', 'apidocs'])
        self.addStep(
            transfer.FileUpload,
            workdir='.',
            slavesrc='./Twisted/apidocs.tar.bz2',
            masterdest=WithProperties(
                'public_html/builds/apidocs-%(got_revision)s.tar.bz2'))



class FullTwistedBuildFactory(TwistedBaseFactory):
    treeStableTimer = 5*60

    def __init__(self, source, python="python",
                 runTestsRandomly=False,
                 compileOpts=[], compileOpts2=[],
                 uncleanWarnings=True, trialMode=None):
        TwistedBaseFactory.__init__(self, python, source, uncleanWarnings, trialMode=trialMode)

        assert isinstance(compileOpts, list)
        assert isinstance(compileOpts2, list)
        cmd = (python + compileOpts + ["setup.py", "build_ext"]
               + compileOpts2 + ["-i"])

        self.addStep(shell.Compile, command=cmd, flunkOnFailure=True)
        self.addStep(RemovePYCs)
        self.addTrialStep(randomly=runTestsRandomly)


class Win32RemovePYCs(ShellCommand):
    name = "remove-.pyc"
    command = 'del /s *.pyc'
    description = ["removing", ".pyc", "files"]
    descriptionDone = ["remove", ".pycs"]


class GoodTwistedBuildFactory(TwistedBaseFactory):
    treeStableTimer = 5 * 60

    forceGarbageCollection = True

    def __init__(self, source, python="python",
                 processDocs=False, runTestsRandomly=False,
                 compileOpts=[], compileOpts2=[],
                 uncleanWarnings=True,
                 extraTrialArguments={}):
        TwistedBaseFactory.__init__(self, python, source, uncleanWarnings)
        if processDocs:
            self.addStep(ProcessDocs)

        assert isinstance(compileOpts, list)
        assert isinstance(compileOpts2, list)
        cmd = (self.python + compileOpts + ["setup.py", "build_ext"]
               + compileOpts2 + ["-i"])

        self.addStep(shell.Compile, command=cmd, flunkOnFailure=True)
        self.addStep(RemovePYCs)
        self.addTrialStep(randomly=runTestsRandomly, **extraTrialArguments)


class TwistedReactorsBuildFactory(TwistedBaseFactory):
    treeStableTimer = 5*60

    def __init__(self, source, RemovePYCs=RemovePYCs,
                 python="python", compileOpts=[], compileOpts2=[],
                 reactors=["select"], uncleanWarnings=True):
        TwistedBaseFactory.__init__(self, python, source, uncleanWarnings)

        assert isinstance(compileOpts, list)
        assert isinstance(compileOpts2, list)
        cmd = (self.python + compileOpts + ["setup.py", "build_ext"]
               + compileOpts2 + ["-i"])

        self.addStep(shell.Compile, command=cmd, warnOnFailure=True)

        for reactor in reactors:
            self.addStep(RemovePYCs)
            self.addTrialStep(
                name=reactor, reactor=reactor, flunkOnFailure=True,
                warnOnFailure=False)


class TwistedEasyInstallFactory(TwistedBaseFactory):
    treeStableTimer = 5*60

    def __init__(self, source, uncleanWarnings, python="python",
                 reactor="epoll", easy_install="easy_install"):
        TwistedBaseFactory.__init__(self, python, source, uncleanWarnings)

        setupCommands = [
            ["rm", "-rf", "install"],
            ["mkdir", "-p", "install/bin", "install/lib"],
            [easy_install, "--install-dir", "install/lib",
                           "--script-dir", "install/bin",
                           "."],
            ]
        for command in setupCommands:
            self.addStep(shell.ShellCommand, command=command,
                         env={"PYTHONPATH": "install/lib"},
                         haltOnFailure=True)
        self.addTrialStep(
            name=reactor,
            reactor=reactor, flunkOnFailure=True,
            warnOnFailure=False, workdir="Twisted/install",
            env={"PYTHONPATH": "lib"})



class PyPyTranslationFactory(BuildFactory):
    def __init__(self, translationArguments, targetArguments, *a, **kw):
        BuildFactory.__init__(self, *a, **kw)

        self.addStep(
            SVN,
            workdir="build/pypy-src",
            baseURL="http://codespeak.net/svn/pypy/",
            defaultBranch="trunk",
            mode="copy")
        self.addStep(
            Translate,
            translationArgs=translationArguments,
            targetArgs=targetArguments)



class TwistedPyPyBuildFactory(BuildFactory):
    def __init__(self, *a, **kw):
        BuildFactory.__init__(self, *a, **kw)
        self.addStep(
            SVN,
            workdir="build/Twisted-src",
            baseURL="svn://svn.twistedmatrix.com/svn/Twisted/",
            defaultBranch="trunk",
            mode="copy")
        self.addStep(
            Trial,
            workdir="build/pypy-src/pypy/translator/goal",
            python=["pypy-c"],
            testpath=None,
            trial="../../../../Twisted-src/bin/trial",
            tests=["twisted"],
            env={"PATH": "/usr/bin:.",
                 # PyPy doesn't currently find this on its own.
                 "PYTHONPATH": "/usr/lib/python2.5/site-packages"})



class PyOpenSSLBuildFactoryBase(BuildFactory):
    """
    Build and test PyOpenSSL.
    """
    def __init__(self):
        BuildFactory.__init__(self, [])
        self.uploadBase = 'public_html/builds/'
        self.addStep(
             Bzr,
             baseURL="http://bazaar.launchpad.net/~exarkun/pyopenssl/",
             defaultBranch="trunk",
             mode="copy")
        self.addStep(
            LearnVersion, python=self.python("2.5"), package='version',
            workdir='source')



class LinuxPyOpenSSLBuildFactory(PyOpenSSLBuildFactoryBase):
    """
    Build and test a Linux (or Linux-like) PyOpenSSL package.
    """
    def __init__(self, versions, source, platform=None, bdistEnv=None):
        PyOpenSSLBuildFactoryBase.__init__(self)
        self._platform = platform
        self.bdistEnv = bdistEnv
        if source:
            self.addStep(
                shell.Compile,
                # Doesn't matter what Python gets used for sdist
                command=["python", "setup.py", "sdist"],
                flunkOnFailure=True)
            self.addStep(
                transfer.FileUpload,
                slavesrc=WithProperties('dist/pyOpenSSL-%(version)s.tar.gz'),
                masterdest=WithProperties(self.uploadBase + 'pyOpenSSL-%(version)s.tar.gz'))
        for pyVersion in versions:
            python = self.python(pyVersion)
            platform = self.platform(pyVersion)
            self.addStep(
                shell.Compile,
                command=[python, "setup.py", "bdist"],
                env=self.bdistEnv,
                flunkOnFailure=True)
            self.addStep(
                Trial,
                workdir="build/build/lib.%s-%s" % (platform, pyVersion),
                python=python,
                trial=self.trial(pyVersion),
                tests="OpenSSL",
                testpath=None)
            self.addStep(
                transfer.FileUpload,
                # This is the name of the file "setup.py bdist" writes.
                slavesrc=WithProperties(
                    'dist/pyOpenSSL-%(version)s.' + platform + '.tar.gz'),
                masterdest=WithProperties(
                    self.uploadBase + '/pyOpenSSL-%(version)s.py' +
                    pyVersion + '.' + platform + '.tar.gz'))


    def trial(self, version):
        """
        Return the path to the trial script for the given version of
        Python.
        """
        return "/usr/bin/trial"


    def platform(self, version):
        return self._platform


    def python(self, version):
        return "python" + version



class DebianPyOpenSSLBuildFactory(LinuxPyOpenSSLBuildFactory):
    """
    Build and test a Debian (or Debian-derivative) PyOpenSSL package.
    """
    def __init__(self, versions, source, platform, distro, packageFiles, **kw):
        LinuxPyOpenSSLBuildFactory.__init__(self, versions, source, platform, **kw)
        self.addStep(
            shell.ShellCommand,
            command=["cp", "-a", distro, "debian"])
        self.addStep(
            shell.ShellCommand,
            command=["fakeroot", "make", "-f", "debian/rules", "binary"])
        for fileName in packageFiles:
            self.addStep(
                transfer.FileUpload,
                slavesrc="../" + fileName,
                masterdest=self.uploadBase + fileName)



class OSXPyOpenSSLBuildFactory(LinuxPyOpenSSLBuildFactory):
    """
    Build and test an OS-X PyOpenSSL package.
    """
    def __init__(self, versions, osxVersion, **kw):
        self.osxVersion = osxVersion
        LinuxPyOpenSSLBuildFactory.__init__(self, versions, **kw)


    def trial(self, version):
        """
        Return the path to the trial script in the framework.
        """
        return "/usr/local/bin/trial"


    def platform(self, version):
        if self.osxVersion == "10.4":
            # OS X, you are a hilarious trainwreck of stupidity.
            return "macosx-10.3-i386"
        elif version == "2.5":
            return "macosx-10.5-ppc"
        elif version == "2.4":
            return "macosx-10.5-fat"



class Win32PyOpenSSLBuildFactory(PyOpenSSLBuildFactoryBase):
    """
    Build and test a Win32 PyOpenSSL package.
    """
    def python(self, pyVersion):
        return (
            "c:\\python%s\\python.exe" % (
                pyVersion.replace('.', ''),))


    def __init__(self, platform, compiler, pyVersion, extraInclude=None, extraLib=None):
        PyOpenSSLBuildFactoryBase.__init__(self)
        python = self.python(pyVersion)
        buildCommand = [
            python, "setup.py", "build_ext", "--compiler", compiler]
        if extraInclude is not None:
            buildCommand.extend(["-I", extraInclude])
        if extraLib is not None:
            buildCommand.extend(["-L", extraLib])
        self.addStep(
            shell.Compile,
            command=buildCommand,
            flunkOnFailure=True)
        self.addStep(
            shell.Compile,
            command=[python, "setup.py", "bdist"],
            flunkOnFailure=True)
        self.addStep(
            transfer.FileUpload,
            slavesrc=WithProperties('dist/pyOpenSSL-%(version)s.win32.zip'),
            masterdest=WithProperties(
                self.uploadBase + 'pyOpenSSL-%(version)s.' + platform + '-py' + pyVersion + '.zip'))
        self.addStep(
            shell.Compile,
            command=[python, "setup.py", "bdist_wininst"],
            flunkOnFailure=True)
        self.addStep(
            transfer.FileUpload,
            slavesrc=WithProperties('dist/pyOpenSSL-%(version)s.win32-py' + pyVersion + '.exe'),
            masterdest=WithProperties(
                self.uploadBase + 'pyOpenSSL-%%(version)s.%s-py%s.exe' % (platform, pyVersion)))
        if pyVersion >= "2.5":
            self.addStep(
                shell.Compile,
                command=[python, "setup.py", "bdist_msi"],
                flunkOnFailure=True)
            self.addStep(
                transfer.FileUpload,
                slavesrc=WithProperties('dist/pyOpenSSL-%(version)s.win32-py' + pyVersion + '.msi'),
                masterdest=WithProperties(
                    self.uploadBase + 'pyOpenSSL-%%(version)s.%s-py%s.msi' % (platform, pyVersion)))

        self.addStep(
            shell.Compile,
            command=[python, "-c", "import sys, setuptools; sys.argv[0] = 'setup.py'; execfile('setup.py')", "bdist_egg"],
            flunkOnFailure=True)
        self.addStep(
            transfer.FileUpload,
            slavesrc=WithProperties('dist/pyOpenSSL-%(version)s-py' + pyVersion + '-win32.egg'),
            masterdest=WithProperties(
                self.uploadBase + 'pyOpenSSL-%%(version)s.py%s-%s.egg' % (pyVersion, platform)))
