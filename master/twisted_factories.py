"""
Build classes specific to the Twisted codebase
"""

from buildbot.process.base import Build
from buildbot.process.factory import BuildFactory
from buildbot.steps import shell
from buildbot.steps.shell import ShellCommand

from twisted_steps import HLint, ProcessDocs, BuildDebs, \
    Trial, RemovePYCs, CheckDocumentation


TRIAL_FLAGS = ["--reporter=bwverbose"]
WARNING_FLAGS = ["--unclean-warnings"]
FORCEGC_FLAGS = ["--force-gc"]

class TwistedBuild(Build):
    workdir = "Twisted" # twisted's bin/trial expects to live in here
    def isFileImportant(self, filename):
        if filename.startswith("doc/fun/"):
            return 0
        if filename.startswith("sandbox/"):
            return 0
        return 1

class TwistedTrial(Trial):
    tests = "twisted"
    # the Trial in Twisted >=2.1.0 has --recurse on by default, and -to
    # turned into --reporter=bwverbose .
    recurse = False
    trialMode = TRIAL_FLAGS
    testpath = None
    trial = "./bin/trial"

class TwistedBaseFactory(BuildFactory):
    buildClass = TwistedBuild
    # bin/trial expects its parent directory to be named "Twisted": it uses
    # this to add the local tree to PYTHONPATH during tests
    workdir = "Twisted"

    forceGarbageCollection = False

    def __init__(self, source, uncleanWarnings):
        BuildFactory.__init__(self, [source])
        self.uncleanWarnings = uncleanWarnings

    def addTrialStep(self, **kw):
        trialMode = TRIAL_FLAGS
        if self.uncleanWarnings:
            trialMode = trialMode + WARNING_FLAGS
        if self.forceGarbageCollection:
            trialMode = trialMode + FORCEGC_FLAGS
        self.addStep(TwistedTrial, trialMode=trialMode, **kw)


class QuickTwistedBuildFactory(TwistedBaseFactory):
    treeStableTimer = 30
    useProgress = 0

    def __init__(self, source, python="python", uncleanWarnings=True):
        TwistedBaseFactory.__init__(self, source, uncleanWarnings)
        if type(python) is str:
            python = [python]
        self.addStep(HLint, python=python[0])
        self.addStep(RemovePYCs)
        for p in python:
            cmd = [p, "setup.py", "build_ext", "-i"]
            self.addStep(shell.Compile, command=cmd, flunkOnFailure=True)
            self.addTrialStep(python=p, testChanges=True)



class TwistedDocumentationBuildFactory(TwistedBaseFactory):
    treeStableTimer = 5 * 60

    def __init__(self, source, python="python"):
        TwistedBaseFactory.__init__(self, source, False)
        self.addStep(CheckDocumentation)
        self.addStep(ProcessDocs)



class FullTwistedBuildFactory(TwistedBaseFactory):
    treeStableTimer = 5*60

    def __init__(self, source, python="python",
                 runTestsRandomly=False,
                 compileOpts=[], compileOpts2=[],
                 uncleanWarnings=True):
        TwistedBaseFactory.__init__(self, source, uncleanWarnings)

        if type(python) == str:
            python = [python]
        assert isinstance(compileOpts, list)
        assert isinstance(compileOpts2, list)
        cmd = (python + compileOpts + ["setup.py", "build_ext"]
               + compileOpts2 + ["-i"])

        self.addStep(shell.Compile, command=cmd, flunkOnFailure=True)
        self.addStep(RemovePYCs)
        self.addTrialStep(python=python, randomly=runTestsRandomly)


class TwistedDebsBuildFactory(TwistedBaseFactory):
    treeStableTimer = 10*60

    def __init__(self, source, python="python"):
        TwistedBaseFactory.__init__(self, source)
        self.addStep(ProcessDocs, haltOnFailure=True)
        self.addStep(BuildDebs, warnOnWarnings=True)


class TwistedReactorsBuildFactory(TwistedBaseFactory):
    treeStableTimer = 5*60

    def __init__(self, source,
                 python="python", compileOpts=[], compileOpts2=[],
                 reactors=None, uncleanWarnings=True):
        TwistedBaseFactory.__init__(self, source, uncleanWarnings)

        if type(python) == str:
            python = [python]
        assert isinstance(compileOpts, list)
        assert isinstance(compileOpts2, list)
        cmd = (python + compileOpts + ["setup.py", "build_ext"]
               + compileOpts2 + ["-i"])

        self.addStep(shell.Compile, command=cmd, warnOnFailure=True)

        if reactors == None:
            reactors = [
                'gtk2',
                'gtk',
                #'kqueue',
                'poll',
                'c',
                'qt',
                #'win32',
                ]
        for reactor in reactors:
            flunkOnFailure = 1
            warnOnFailure = 0
            #if reactor in ['c', 'qt', 'win32']:
            #    # these are buggy, so tolerate failures for now
            #    flunkOnFailure = 0
            #    warnOnFailure = 1
            self.addStep(RemovePYCs) # TODO: why?
            self.addTrialStep(
                name=reactor, python=python,
                reactor=reactor, flunkOnFailure=flunkOnFailure,
                warnOnFailure=warnOnFailure)


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
                 uncleanWarnings=True):
        TwistedBaseFactory.__init__(self, source, uncleanWarnings)
        if processDocs:
            self.addStep(ProcessDocs)

        if type(python) == str:
            python = [python]
        assert isinstance(compileOpts, list)
        assert isinstance(compileOpts2, list)
        cmd = (python + compileOpts + ["setup.py", "build_ext"]
               + compileOpts2 + ["-i"])

        self.addStep(shell.Compile, command=cmd, flunkOnFailure=True)
        self.addStep(RemovePYCs)
        self.addTrialStep(python=python, randomly=runTestsRandomly)


class TwistedReactorsBuildFactory(TwistedBaseFactory):
    treeStableTimer = 5*60

    def __init__(self, source, RemovePYCs=RemovePYCs,
                 python="python", compileOpts=[], compileOpts2=[],
                 reactors=["select"], uncleanWarnings=True):
        TwistedBaseFactory.__init__(self, source, uncleanWarnings)

        if type(python) == str:
            python = [python]
        assert isinstance(compileOpts, list)
        assert isinstance(compileOpts2, list)
        cmd = (python + compileOpts + ["setup.py", "build_ext"]
               + compileOpts2 + ["-i"])

        self.addStep(shell.Compile, command=cmd, warnOnFailure=True)

        for reactor in reactors:
            self.addStep(RemovePYCs)
            self.addTrialStep(
                name=reactor, python=python,
                reactor=reactor, flunkOnFailure=True,
                warnOnFailure=False)
