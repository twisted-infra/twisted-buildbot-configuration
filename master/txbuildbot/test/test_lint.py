from twisted.trial import unittest
from buildbot.status.results import SUCCESS, FAILURE
from buildbot.test.util.steps import BuildStepMixin
from buildbot.test.fake.remotecommand import ExpectShell

from txbuildbot.lint import LintStep

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

class TestComputeDiffference(unittest.TestCase):
    """
    Tests for L{LintStep.computeDifference}.
    """

    
    def test_emptyPrevious(self):
        """
        When given an C{previous} dict that is empty, and a C{current} dict,
        C{computeDifference} returns a dictionary identical to C{current}.
        """
        current = {'stuff': set(['a', 'b']), 'other': set(['x', 'y'])}
        diff = LintStep.computeDifference(current, {})
        self.assertEqual(diff, current)

    def test_emptyCurrent(self):
        """
        When given an C{current} dict that is empty, and a C{previous} dict,
        C{computeDifference} returns an empty dict.
        """
        previous = {'stuff': set(['a', 'b']), 'other': set(['x', 'y'])}
        diff = LintStep.computeDifference({}, previous)
        self.assertEqual(diff, {})

    def test_newKey(self):
        """
        When given a C{current} dict that has a key that isn't in C{previous} dict,
        C{computeDifference} returns a dict with everything in that key.
        """
        previous = {'stuff': set(['a', 'b'])}
        current = {'stuff': set(['a', 'b']), 'other': set(['x', 'y'])}
        diff = LintStep.computeDifference(current, previous)
        self.assertEqual(diff, {'other': set(['x', 'y'])})

    def test_lessKeys(self):
        """
        When given a C{current} dict that is missing keys from C{previous},
        C{computeDifference} returns a dict with only the keys from C{current}.
        """
        current = {'stuff': set(['a', 'b'])}
        previous = {'stuff': set(['a']), 'other': set(['x', 'y'])}
        diff = LintStep.computeDifference(current, previous)
        self.assertEqual(diff, {'stuff': set(['a'])})

    def test_sameKey(self):
        """
        When given a C{current} dict with a key whose contents is identical to C{previous},
        C{computeDifference} returns a dict without that key.
        """
        current = {'stuff': set(['a', 'b'])}
        previous = {'stuff': set(['a', 'b'])}
        diff = LintStep.computeDifference(current, previous)
        self.assertEqual(diff, {})



class TestLintStep(BuildStepMixin, unittest.TestCase):
    """
    Tests for L{LintStep}
    """

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
