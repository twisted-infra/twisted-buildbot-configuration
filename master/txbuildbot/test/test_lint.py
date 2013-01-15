from twisted.trial import unittest
from buildbot.status.results import SUCCESS, FAILURE
from buildbot.test.util.steps import BuildStepMixin
from buildbot.test.fake.remotecommand import ExpectShell

from txbuildbot.lint import LintStep, CheckDocumentation, CheckCodesByTwistedChecker

class FakeLintStep(LintStep):
    name = 'test-lint-step'
    command = [ 'lint-command' ]
    description = [ 'lint', 'desc' ]
    descriptionDone = [ 'lint', 'done' ]
    lintChecker = 'test-lint'

    def __init__(self, oldErrors, newErrors):
        LintStep.__init__(self)
        self.factory[1].clear()
        self.addFactoryArguments(oldErrors=oldErrors, newErrors=newErrors)
        self.oldErrors = oldErrors
        self.newErrors = newErrors

    def computeErrors(self, logText):
        if logText == 'old':
            return self.oldErrors
        else:
            return self.newErrors

    def formatErrors(self, newErrors):
        return ['%r' % newErrors]

## TODO: Add tests for getLastBuild/getPreviousLog

class TestLintStep(BuildStepMixin, unittest.TestCase):

    def setUp(self):
        return self.setUpBuildStep()

    def tearDown(self):
        return self.tearDownBuildStep()

    def setupStep(self, step):
        BuildStepMixin.setupStep(self, step)
        self.step.getPreviousLog = lambda: 'old'
        self.expectCommands(
                ExpectShell(command=['lint-command'], workdir='wkdir', usePTY='slave-config')
                + ExpectShell.log('stdio', stdout='new')
                + 0
        )

    def test_newErrors(self):
        self.setupStep(FakeLintStep(
            oldErrors={'old': set(['a', 'b', 'c']), 'new': set(['a', 'b'])},
            newErrors={'old': set(['a', 'b']), 'new': set(['a', 'b', 'c'])}))
        self.expectOutcome(result=FAILURE, status_text=['lint', 'done', 'failed'])
        self.expectLogfile('test-lint errors', 'new')
        self.expectLogfile('new test-lint errors', '%r' % {'new': set(['c'])})
        return self.runStep()

    def test_fixedErrors(self):
        self.setupStep(FakeLintStep(
            oldErrors={'old': set(['a', 'b', 'c']), 'new': set(['a', 'b'])},
            newErrors={'old': set(['a', 'b']), 'new': set(['a', 'b'])}))
        self.expectOutcome(result=SUCCESS, status_text=['lint', 'done'])
        self.expectLogfile('test-lint errors', 'new')
        return self.runStep()

    def test_sameErrors(self):
        self.setupStep(FakeLintStep(
            oldErrors={'old': set(['a', 'b', 'c']), 'new': set(['a', 'b'])},
            newErrors={'old': set(['a', 'b', 'c']), 'new': set(['a', 'b'])}))
        self.expectOutcome(result=SUCCESS, status_text=['lint', 'done'])
        self.expectLogfile('test-lint errors', 'new')
        return self.runStep()
