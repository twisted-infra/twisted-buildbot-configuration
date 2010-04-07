"""
Build classes specific to the Twisted codebase
"""

from buildbot.process.properties import WithProperties
from buildbot.process.base import Build
from buildbot.process.factory import BuildFactory, s
from buildbot.scheduler import Scheduler
from buildbot.steps import shell, transfer, master
from buildbot.steps.shell import ShellCommand
from buildbot.steps.source import SVN, Bzr
from buildbot.steps.python import PyFlakes

from twisted_steps import ProcessDocs, ReportPythonModuleVersions, \
    Trial, RemovePYCs, CheckDocumentation, LearnVersion, SetBuildProperty
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

    def __init__(self, python, source, uncleanWarnings, trialTests=None, trialMode=None):
        BuildFactory.__init__(self, [source])

        if type(python) is str:
            python = [python]

        self.python = python
        self.uncleanWarnings = uncleanWarnings
        self.trialMode = trialMode
        if trialTests is None:
            trialTests = ["twisted"]
        self.trialTests = trialTests

        self.addStep(
            ReportPythonModuleVersions,
            python=self.python,
            moduleInfo=[
                ("Python", "sys", "sys.version"),
                ("OpenSSL", "OpenSSL", "OpenSSL.__version__"),
                ("PyCrypto", "Crypto", "Crypto.__version__"),
                ("gmpy", "gmpy", "gmpy.version()"),
                ("SOAPpy", "SOAPpy", "SOAPpy.__version__"),
                ("ctypes", "ctypes", "ctypes.__version__"),
                ("gtk", "gtk", "gtk.gtk_version"),
                ("pygtk", "gtk", "gtk.pygtk_version"),
                ("pywin32", "win32api",
                 "win32api.GetFileVersionInfo(win32api.__file__, chr(92))['FileVersionLS'] >> 16"),
                ("pyasn1", "pyasn1", "pyasn1.majorVersionId"),
                ],
            pkg_resources=[
                ("subunit", "subunit"),
                ("zope.interface", "zope.interface"),
                ])


    def addTrialStep(self, **kw):
        if self.trialMode is not None:
            trialMode = self.trialMode
        else:
            trialMode = TRIAL_FLAGS

        if self.uncleanWarnings:
            trialMode = trialMode + WARNING_FLAGS
        if self.forceGarbageCollection:
            trialMode = trialMode + FORCEGC_FLAGS
        if 'tests' not in kw:
            kw['tests'] = self.trialTests
        self.addStep(TwistedTrial, python=self.python, trialMode=trialMode, **kw)



class PyFlakesBuildFactory(BuildFactory):
    """
    A build factory which just runs PyFlakes over the specified source.
    """
    def __init__(self, source):
        BuildFactory.__init__(self, [source])
        self.addStep(
            PyFlakes,
            descriptionDone="PyFlakes", flunkOnFailure=True,
            command=["pyflakes", "."])



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
                 uncleanWarnings=True, trialMode=None,
                 trialTests=None, buildExtensions=True):
        TwistedBaseFactory.__init__(self, python, source, uncleanWarnings, trialTests=trialTests, trialMode=trialMode)

        assert isinstance(compileOpts, list)
        assert isinstance(compileOpts2, list)

        if buildExtensions:
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

    def __init__(self, source, python="python",
                 processDocs=False, runTestsRandomly=False,
                 compileOpts=[], compileOpts2=[],
                 uncleanWarnings=True,
                 extraTrialArguments={},
                 forceGarbageCollection=False):
        TwistedBaseFactory.__init__(self, python, source, uncleanWarnings)
        self.forceGarbageCollection = forceGarbageCollection
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


class TwistedBdistMsiFactory(TwistedBaseFactory):
    treeStableTimer = 5*60

    uploadBase = 'public_html/builds/'
    def __init__(self, source, uncleanWarnings, platform, pyVersion):
        python = self.python(pyVersion)
        TwistedBaseFactory.__init__(self, python, source, uncleanWarnings)
        self.addStep(
            LearnVersion, python=python, package='twisted', workdir='source')

        def transformVersion(build):
            return build.getProperty("version").split("+")[0].split("pre")[0]
        self.addStep(
            SetBuildProperty, property_name='versionMsi', value=transformVersion)
        self.addStep(shell.ShellCommand,
                command=[python, "-c", WithProperties(
                     'version = \'%(versionMsi)s\'; '
                     'f = file(\'twisted\copyright.py\', \'at\'); '
                     'f.write(\'version = \' + repr(version)); '
                     'f.close()')],
                     haltOnFailure=True)
        if pyVersion >= "2.5":
            self.addStep(shell.ShellCommand, command=[python, "setup.py", "bdist_msi"],
                         haltOnFailure=True)
            self.addStep(
                transfer.FileUpload,
                slavesrc=WithProperties('dist/Twisted-%(versionMsi)s.win32-py' + pyVersion + '.msi'),
                masterdest=WithProperties(
                    self.uploadBase + 'Twisted-%%(version)s.%s-py%s.msi' % (platform, pyVersion)))
        else:
            self.addStep(shell.ShellCommand, command=[python, "setup.py", "bdist_wininst"],
                         haltOnFailure=True)
            self.addStep(
                transfer.FileUpload,
                slavesrc=WithProperties('dist/Twisted-%(versionMsi)s.win32-py' + pyVersion + '.exe'),
                masterdest=WithProperties(
                    self.uploadBase + 'Twisted-%%(version)s.%s-py%s.exe' % (platform, pyVersion)))

    def python(self, pyVersion):
        return (
            "c:\\python%s\\python.exe" % (
                pyVersion.replace('.', ''),))


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


class TwistedIronPythonBuildFactory(FullTwistedBuildFactory):
    def __init__(self, source, *a, **kw):
        FullTwistedBuildFactory.__init__(
            self, source, ["ipy"], buildExtensions=False, *a, **kw)


pyOpenSSLSource = s(
    Bzr,
    baseURL="http://bazaar.launchpad.net/~exarkun/pyopenssl/",
    defaultBranch="trunk",
    mode="copy")


class PyOpenSSLBuildFactoryBase(BuildFactory):
    """
    Build and test PyOpenSSL.
    """
    def __init__(self):
        BuildFactory.__init__(self, [pyOpenSSLSource])
        self.uploadBase = 'public_html/builds/'
        self.addStep(
            LearnVersion, python=self.python("2.5"), package='version',
            workdir='source')


    def addTestStep(self, pyVersion):
        self.addStep(
            Trial,
            workdir="build/build/lib.%s-%s" % (
                self.platform(pyVersion), pyVersion),
            python=self.python(pyVersion),
            trial=self.trial(pyVersion),
            tests="OpenSSL",
            testpath=None)



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
            self.addTestStep(pyVersion)
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
        if self.osxVersion == "10.6":
            return "/usr/bin/trial"
        return "/usr/local/bin/trial"


    def platform(self, version):
        if self.osxVersion == "10.4":
            # OS X, you are a hilarious trainwreck of stupidity.
            return "macosx-10.3-i386"
        elif version == "2.5":
            return "macosx-10.5-ppc"
        elif version == "2.4":
            return "macosx-10.5-fat"
        elif self.osxVersion == "10.6":
            return "macosx-10.6-universal"
        else:
            return "UNKNOWN"



class Win32PyOpenSSLBuildFactory(PyOpenSSLBuildFactoryBase):
    """
    Build and test a Win32 PyOpenSSL package.
    """
    def python(self, pyVersion):
        return (
            "c:\\python%s\\python.exe" % (
                pyVersion.replace('.', ''),))


    def addTestStep(self, pyVersion):
        self.addStep(
            ShellCommand,
            timeout=30,
            workdir="build/build/lib.%s-%s/" % (
                self.platform(pyVersion), pyVersion),
            command=[self.python(pyVersion), "-u", "-c", "import discover; discover.main()", "-v", "OpenSSL\\test\\"])


    def __init__(self, platform, compiler, pyVersion, opensslPath):
        PyOpenSSLBuildFactoryBase.__init__(self)
        python = self.python(pyVersion)
        buildCommand = [
            python, "setup.py",
            "build_ext", "--compiler", compiler, "--with-openssl", opensslPath,
            "build", "bdist", "bdist_wininst"]
        if pyVersion >= "2.5":
            buildCommand.append("bdist_msi")

        self.addStep(
            shell.Compile,
            command=buildCommand,
            flunkOnFailure=True)

        self.addTestStep(pyVersion)

        self.addStep(
            transfer.FileUpload,
            slavesrc=WithProperties('dist/pyOpenSSL-%(version)s.win32.zip'),
            masterdest=WithProperties(
                self.uploadBase + 'pyOpenSSL-%(version)s.' + platform + '-py' + pyVersion + '.zip'))

        self.addStep(
            transfer.FileUpload,
            slavesrc=WithProperties('dist/pyOpenSSL-%(version)s.win32-py' + pyVersion + '.exe'),
            masterdest=WithProperties(
                self.uploadBase + 'pyOpenSSL-%%(version)s.%s-py%s.exe' % (platform, pyVersion)))

        if pyVersion >= "2.5":
            self.addStep(
                transfer.FileUpload,
                slavesrc=WithProperties('dist/pyOpenSSL-%(version)s.win32-py' + pyVersion + '.msi'),
                masterdest=WithProperties(
                    self.uploadBase + 'pyOpenSSL-%%(version)s.%s-py%s.msi' % (platform, pyVersion)))

        self.addStep(
            shell.Compile,
            command=[python, "-c",
                     "import sys, setuptools; sys.argv[0] = 'setup.py'; execfile('setup.py', {'__file__': 'setup.py'})",
                     "build_ext", "--with-openssl", opensslPath, "bdist_egg"],
            flunkOnFailure=True)

        eggName = 'pyOpenSSL-%(version)s-py' + pyVersion + '-win32.egg'
        self.addStep(
            transfer.FileUpload,
            slavesrc=WithProperties('dist/' + eggName),
            masterdest=WithProperties(self.uploadBase + eggName))


    def platform(self, pyVersion):
        return "win32"


    def trial(self, pyVersion):
        return "c:\\python%s\\scripts\\trial" % (pyVersion.replace('.', ''),)



class GCoverageFactory(TwistedBaseFactory):
    buildClass = Build

    def __init__(self, python, source):
        TwistedBaseFactory.__init__(self, python, source, False)

        # Clean up any pycs left over since they might be wrong and
        # mess up the test run.
        self.addStep(RemovePYCs)

        # Build the extensions with the necessary gcc tracing flags
        self.addStep(
            shell.Compile,
            # PyOpenSSL doesn't need -i, because it is going to
            # install anyway.  Twisted does, though.
            command=python + ["setup.py", "build_ext"] + self.BUILD_OPTIONS,
            env={'CFLAGS': '-fprofile-arcs -ftest-coverage'},
            flunkOnFailure=True)

        # Run the tests.
        self.addTestSteps(python)

        # Run geninfo and genhtml - together these generate the coverage report
        self.addStep(
            shell.ShellCommand,
            command=["geninfo", "-b", ".", "."])
        self.addStep(
            shell.ShellCommand,
            command=["bash", "-c", 'genhtml -o coverage-report `find . -name *.info`'])

        # Bundle up the report
        self.addStep(
            shell.ShellCommand,
            command=["tar", "czf", "coverage.tar.gz", "coverage-report"])

        # Upload it to the master
        self.addStep(
            transfer.FileUpload,
            slavesrc='coverage.tar.gz',
            masterdest=WithProperties(
                'public_html/builds/%(project)s-coverage-%%(got_revision)s.tar.gz' % {
                    'project': self.PROJECT}))

        # Unarchive it so it can be viewed directly.  WithProperties
        # is not supported by MasterShellCommand.  Joy.  Unbounded joy.
        self.addStep(
            master.MasterShellCommand,
            command=[
                'bash', '-c',
                ('fname=`echo public_html/builds/%(project)s-coverage-*.tar.gz`; '
                 'tar xzf $fname; ' +
                 ('rev=${fname:%s}; ' % (len(self.PROJECT) + 29,)) +
                 'rev=${rev/%%.tar.gz/}; '
                 'rm -rf public_html/builds/%(project)s-coverage-report-r$rev; '
                 'mv coverage-report public_html/builds/%(project)s-coverage-report-r$rev; '
                 'rm $fname; ') % {'project': self.PROJECT}])



class PyOpenSSLGCoverageFactory(GCoverageFactory):
    PROJECT = 'pyopenssl'
    TESTS = 'OpenSSL'
    BUILD_OPTIONS = []

    def __init__(self, python):
        GCoverageFactory.__init__(self, python, pyOpenSSLSource)


    def addTestSteps(self, python):
        # Install it so the tests can be run
        self.addStep(
            shell.ShellCommand,
            command=python + ["setup.py", "install", "--prefix", "installed"])

        # Run the tests against the installed version
        self.addTrialStep(
            trial="/usr/bin/trial",
            tests=self.TESTS,
            env={'PYTHONPATH':
                     'installed/lib/python2.5/site-packages'})



class TwistedGCoverageFactory(GCoverageFactory):
    PROJECT = 'twisted'
    TESTS = ['twisted.test.test_epoll',
             'twisted.web.test.test_http',
             'twisted.python.test.test_util']
    BUILD_OPTIONS = ["-i"]

    def addTestSteps(self, python):
        self.addTrialStep(tests=self.TESTS)
