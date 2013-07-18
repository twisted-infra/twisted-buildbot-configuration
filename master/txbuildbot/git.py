from twisted.python import log

from buildbot.process import buildstep
from buildbot.steps.source.git import Git
from buildbot.steps.source import Source
from buildbot.status.results import SUCCESS


class TwistedGit(Git):
    """
    Temporary support for the transitionary stage between SVN and Git.
    """

    def startVC(self, branch, revision, patch):
        """
        * If a branch name starts with /branches/, cut it off before referring
          to it in git commands.
        * If a "git_revision" property is provided in the Change, use it
          instead of the base revision number.
        """
        for cutoff in ['/branches/', 'branches/', '/']:
            if branch.startswith(cutoff):
                branch = branch[len(cutoff):]
                break
        id = self.getRepository()
        s = self.build.getSourceStamp(id)
        if s.changes:
            latest_properties = s.changes[-1].properties
            if "git_revision" in latest_properties:
                revision = latest_properties["git_revision"]
        return Git.startVC(self, branch, revision, patch)



class MergeForward(Source):
    """
    Merge with trunk.
    """
    name = 'merge-forward'
    description = ['merging', 'forward']
    descriptionDone = ['merge', 'forward']
    haltOnFailure = True


    def __init__(self, repourl, branch, **kwargs):
        kwargs['env'] = {
                'GIT_MERGE_AUTOEDIT': 'no',
                'GIT_AUTHOR_EMAIL': 'buildbot@twistedmatrix.com',
                'GIT_AUTHOR_NAME': 'Twisted Buildbot',
                'GIT_COMMITTER_EMAIL': 'buildbot@twistedmatrix.com',
                'GIT_COMMITTER_NAME': 'Twisted Buildbot',
                }
        Source.__init__(self, **kwargs)
        self.addFactoryArguments(repourl=repourl, branch=branch)


    def startVC(self, branch, revision, patch):
        branch = self.mungeBranch(branch)

        self.stdio_log = self.addLog('stdio')

        d = self._fetch()
        if self.shouldMerge(branch):
            d.addCallback(lambda _: self._merge())
        if self.isTrunk(branch):
            d.addCallback(lambda _: self._getPreviousVersion())
        else:
            d.addCallback(lambda _: self._getMergeBase())
        d.addCallback(self._setLintVersion)

        d.addCallback(lambda _: SUCCESS)
        d.addCallbacks(self.finished, self.checkDisconnect)
        d.addErrback(self.failed)

    def _fetch(self):
        return self._dovccmd(['fetch', self.repourl, 'trunk'])

    def _merge(self):
        return self._dovccmd(['merge',
                              '--no-ff', '--no-stat',
                              'FETCH_HEAD'])

    def _getPreviousVersion(self):
        return self._dovccmd(['rev-parse', 'FETCH_HEAD'],
                              collectStdout=True)

    def _getMergeBase(self):
        return self._dovccmd(['merge-base', 'HEAD', 'FETCH_HEAD'],
                              collectStdout=True)

    def _setLintVersion(self, version):
        self.setProperty("lint_version", version, "merge-forward")

    def isTrunk(self, branch):
        return branch in ('', 'trunk')


    def mungeBranch(self, branch):
        if branch is None:
            branch = ''

        for cutoff in ['/branches/', 'branches/', '/']:
            if branch.startswith(cutoff):
                branch = branch[len(cutoff):]
                break
        return branch


    def shouldMerge(self, branch):
        """
        Don't merge if building trunk or a release.
        """
        if self.isTrunk(branch):
            return False

        if branch.startswith('releases/'):
            return False

        return True


    def _dovccmd(self, command, abandonOnFailure=True, collectStdout=False, extra_args={}, env = None):
        cmd = buildstep.RemoteShellCommand(self.workdir, ['git'] + command,
                                           env=self.env,
                                           logEnviron=self.logEnviron,
                                           collectStdout=collectStdout,
                                           **extra_args)
        cmd.useLog(self.stdio_log, False)
        d = self.runCommand(cmd)
        def evaluateCommand(cmd):
            if abandonOnFailure and cmd.rc != 0:
                log.msg("Source step failed while running command %s" % cmd)
                raise buildstep.BuildStepFailed()
            if collectStdout:
                return cmd.stdout
            else:
                return cmd.rc
        d.addCallback(lambda _: evaluateCommand(cmd))
        return d
