import mock
from twisted.trial.unittest import TestCase
from buildbot.test.util import sourcesteps
from buildbot.steps.source.git import Git
from buildbot.status.results import SUCCESS, SKIPPED
from buildbot.test.fake.remotecommand import ExpectShell

from txbuildbot.git import TwistedGit, MergeForward

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

    def test_startVCUsesGitRevision(self):
        """
        TwistedGit.startVC honors the "git_revision" property of the Change
        object to know which git revision to use when performing a post-commit
        build.
        """
        class FakeBuild(object):
            def getSourceStamp(self, id):
                return FakeSourceStamp()

        class FakeChange(object):
            properties = {"git_revision": "abcdef"}

        class FakeSourceStamp(object):
            changes = [FakeChange()]

        def startVC_replacement(step, branch, revision, patch):
            gitStartVC.append((step, branch, revision, patch))        

        self.patch(Git, 'startVC', startVC_replacement)
        tgit = TwistedGit(repourl='git://twisted', branch="")
        tgit.build = FakeBuild()
        gitStartVC = []
        tgit.startVC("", 195, "")

        self.assertEqual(gitStartVC[0][2], "abcdef")


class TestMergeForward(sourcesteps.SourceStepMixin, TestCase):
    """
    Tests for L{MergeForward}.
    """

    def setUp(self):
        return self.setUpSourceStep()

    def tearDown(self):
        return self.tearDownSourceStep()


    def buildStep(self, branch):
        self.setupStep(MergeForward(repourl='git://twisted'),
                       {'branch': branch})

    def assertMerge(self, branch):
        self.buildStep(branch)
        self.expectCommands(
                ExpectShell(workdir='wkdir',
                            command=['git', 'pull', '--no-ff',
                                '-mMerge forward.', 'git://twisted', 'trunk'],
                            usePTY='slave-config')
                + 0,
        )
        self.expectOutcome(result=SUCCESS, status_text=['merge', 'forward'])
        return self.runStep()

    def assertSkipped(self, branch):
        self.buildStep(branch)
        self.expectOutcome(result=SKIPPED, status_text=['merge', 'forward', 'skipped'])
        self.expectHidden(True)
        return self.runStep()

    def test_mergeBranch(self):
        return self.assertMerge('/branches/radical-feature-9999')

    def test_skipTrunk(self):
        return self.assertSkipped('/trunk')

    def test_skipEmpty(self):
        return self.assertSkipped('')

    def test_skipNone(self):
        return self.assertSkipped(None)

    def test_skipReleases(self):
        return self.assertSkipped('/branches/releases/release-28.0-9999')
