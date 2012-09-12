from twisted.trial import unittest
from buildbot.status.results import SUCCESS
from buildbot.test.util import sourcesteps
from buildbot.test.fake.remotecommand import ExpectShell, Expect

from txbuildbot.bzrsvn import BzrSvn

class TestBzrSvn(sourcesteps.SourceStepMixin, unittest.TestCase):

    def setUp(self):
        return self.setUpSourceStep()

    def tearDown(self):
        return self.tearDownSourceStep()

    def test_checkout_no_bzrsvn(self):
        self.setupStep(BzrSvn(baseURL="/some/bzr/repo/", branch='trunk', forceSharedRepo=True))
        self.expectCommands(
                ExpectShell(workdir='wkdir',
                           command=['bzr', 'plugins'])
                + ExpectShell.log('stdio', stdout="something not containg ^svn")
                + 0,
                Expect('bzr', dict(workdir='wkdir',
                                   repourl="/some/bzr/repo/trunk",
                                   logEnviron=True,
                                   patch=None,
                                   env=None,
                                   forceSharedRepo=True,
                                   mode='update',
                                   timeout=20*60,
                                   retry=None))
                + Expect.update('got_revision', 1234)
                + 0,
                ExpectShell(workdir='wkdir',
                            command=['bzr', 'revert', '--no-backup'])
                + 0,
                ExpectShell(workdir='wkdir',
                            command=["bzr", "clean-tree", "--force", "--ignored", "--detritus"])
                + 0
        )
        self.expectOutcome(result=SUCCESS, status_text=['update'])
        self.expectProperty('got_revision', '1234')
        return self.runStep()

    def test_checkout_no_bzrsvn_revsion(self):
        self.setupStep(BzrSvn(baseURL="/some/bzr/repo/", branch='trunk', forceSharedRepo=True),
                dict(revision=9999))
        self.expectCommands(
                ExpectShell(workdir='wkdir',
                           command=['bzr', 'plugins'])
                + ExpectShell.log('stdio', stdout="something not containg ^svn")
                + 0,
                Expect('bzr', dict(workdir='wkdir',
                                   repourl="/some/bzr/repo/trunk",
                                   logEnviron=True,
                                   patch=None,
                                   env=None,
                                   forceSharedRepo=True,
                                   mode='update',
                                   timeout=20*60,
                                   retry=None))
                + Expect.update('got_revision', 1234)
                + 0,
                ExpectShell(workdir='wkdir',
                            command=['bzr', 'revert', '--no-backup'])
                + 0,
                ExpectShell(workdir='wkdir',
                            command=["bzr", "clean-tree", "--force", "--ignored", "--detritus"])
                + 0
        )
        self.expectOutcome(result=SUCCESS, status_text=['update'])
        self.expectProperty('got_revision', '1234')
        return self.runStep()

    def test_checkout_bzrsvn(self):
        self.setupStep(BzrSvn(baseURL="/some/bzr/repo/", branch='trunk', forceSharedRepo=True))
        self.expectCommands(
                ExpectShell(workdir='wkdir',
                           command=['bzr', 'plugins'])
                + ExpectShell.log('stdio', stdout="launchpad 1234\nsvn 2345")
                + 0,
                Expect('bzr', dict(workdir='wkdir',
                                   repourl="/some/bzr/repo/trunk",
                                   logEnviron=True,
                                   patch=None,
                                   env=None,
                                   forceSharedRepo=True,
                                   mode='update',
                                   timeout=20*60,
                                   retry=None))
                + Expect.update('got_revision', 1234)
                + 0,
                ExpectShell(workdir='wkdir',
                            command=['bzr', 'revert', '--no-backup'])
                + 0,
                ExpectShell(workdir='wkdir',
                            command=["bzr", "clean-tree", "--force", "--ignored", "--detritus"])
                + 0,
                ExpectShell(workdir='wkdir',
                            command=['bzr', 'version-info'])
                + Expect.log('stdio', stdout='svn-revno: 9999')
                + 0
        )
        self.expectOutcome(result=SUCCESS, status_text=['update'])
        self.expectProperty('got_revision', '9999')
        return self.runStep()

    def test_checkout_bzrsvn_revision(self):
        self.setupStep(BzrSvn(baseURL="/some/bzr/repo/", branch='trunk', forceSharedRepo=True),
                dict(revision='9999'))
        self.expectCommands(
                ExpectShell(workdir='wkdir',
                           command=['bzr', 'plugins'])
                + ExpectShell.log('stdio', stdout="launchpad 1234\nsvn 2345")
                + 0,
                Expect('bzr', dict(workdir='wkdir',
                                   repourl="/some/bzr/repo/trunk",
                                   logEnviron=True,
                                   patch=None,
                                   revision='svn:9999',
                                   env=None,
                                   forceSharedRepo=True,
                                   mode='update',
                                   timeout=20*60,
                                   retry=None))
                + Expect.update('got_revision', 1234)
                + 0,
                ExpectShell(workdir='wkdir',
                            command=['bzr', 'revert', '--no-backup'])
                + 0,
                ExpectShell(workdir='wkdir',
                            command=["bzr", "clean-tree", "--force", "--ignored", "--detritus"])
                + 0,
                ExpectShell(workdir='wkdir',
                            command=['bzr', 'version-info'])
                + Expect.log('stdio', stdout='svn-revno: 9999')
                + 0
        )
        self.expectOutcome(result=SUCCESS, status_text=['update'])
        self.expectProperty('got_revision', '9999')
        return self.runStep()
