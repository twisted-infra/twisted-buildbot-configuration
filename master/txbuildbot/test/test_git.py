import mock
from twisted.trial.unittest import TestCase
from buildbot.test.util import sourcesteps
from buildbot.steps.source.git import Git
from buildbot.status.results import SUCCESS

from txbuildbot.git import TwistedGit

class TestTwistedGit(sourcesteps.SourceStepMixin, TestCase):
    """
    Tests for L{TwistedGit}.
    """

    def setUp(self):
        return self.setUpSourceStep()

    def tearDown(self):
        return self.tearDownSourceStep()

    def assertStartVCMunges(self, providedBranch, expectedBranch):
        def startVC_sideeffect(step, branch, revision, patch):
            self.assertEqual(branch, expectedBranch)
            step.finish(SUCCESS)
        git_startVC = mock.Mock(spec=Git.startVC, side_effect=startVC_sideeffect)
        self.patch(Git, 'startVC', git_startVC)
        self.setupStep(TwistedGit(repourl='git://twisted', branch='trunk'),
                       {'branch': providedBranch})
        self.expectOutcome(result=SUCCESS, status_text=['update'])
        return self.runStep()

    def test_startVC_mungeTrunk(self):
        return self.assertStartVCMunges('trunk', 'trunk')

    def test_startVC_mungesBranch(self):
        return self.assertStartVCMunges('/branches/test-branch-1234', 'test-branch-1234')

    def test_startVC_mungesBranch_withoutSlash(self):
        return self.assertStartVCMunges('branches/test-branch-1234', 'test-branch-1234')
