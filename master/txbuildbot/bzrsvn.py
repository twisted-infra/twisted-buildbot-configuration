import re

from twisted.python import log

from buildbot.process import buildstep
from buildbot.steps.source import Source
from buildbot.status.results import SUCCESS


class BzrSvn(Source):
    name = "bzr-svn"

    def __init__(self, baseURL, branch, forceSharedRepo=True, **kwargs):
        Source.__init__(self, **kwargs)
        self.branch = branch
        self.baseURL = baseURL
        self.forceSharedRepo = forceSharedRepo

        self.addFactoryArguments(branch=branch,
                                 baseURL=baseURL,
                                 forceSharedRepo=forceSharedRepo)
                                                

    def _checkBzrSvnInstalled(self):
        d = self._dovccmd(["plugins"], collectStdout=True)
        @d.addCallback
        def check(stdout):
            if re.search('^svn', stdout, re.MULTILINE):
                self.has_bzr_svn = True
            else:
                self.has_bzr_svn = False
            return self.has_bzr_svn
        return d

    def _update(self, branch, revision, patch):
        if self.has_bzr_svn and revision is not None:
            self.args['revision'] = 'svn:%s' % revision
        self.args['repourl'] = self.baseURL + branch
        self.args['patch'] = patch
        self.args['forceSharedRepo'] = self.forceSharedRepo
        cmd = buildstep.RemoteCommand('bzr', self.args)
        cmd.useLog(self.stdio_log, False)
        d = self.runCommand(cmd)
        d.addCallback(lambda _: self.commandComplete(cmd))
        return d

    def _revert(self):
        return self._dovccmd(['revert', '--no-backup'])

    def _cleanTree(self):
        return self._dovccmd(['clean-tree', '--force', '--ignored', '--detritus'])

    _revno_re = re.compile("^svn-revno: ([0-9]*)$", re.MULTILINE)
    def _maybeGetSvnRevision(self):
        if self.has_bzr_svn:
            d = self._dovccmd(['version-info'], collectStdout=True)
            @d.addCallback
            def _extractRevno(stdout):
                match = self._revno_re.search(stdout)
                if match:
                    self.setProperty("got_revision", match.group(1), "source")
                return SUCCESS
            return d
        else:
            return SUCCESS

    def finished(self, results):
        if results == SUCCESS:
            self.step_status.setText(['update'])
        return Source.finished(self, results)

    def startVC(self, branch, revision, patch):
        self.stdio_log = self.addLog("stdio")
        d = self._checkBzrSvnInstalled() 
        d.addCallback(lambda _: self._update(branch, revision, patch))
        d.addCallback(lambda _: self._revert())
        d.addCallback(lambda _: self._cleanTree())
        d.addCallback(lambda _: self._maybeGetSvnRevision())
        d.addCallbacks(self.finished, self.checkDisconnect)
        d.addErrback(self.failed)
        return d

    def _dovccmd(self, command, abandonOnFailure=True, collectStdout=False, extra_args={}):
        cmd = buildstep.RemoteShellCommand(self.workdir, ['bzr'] + command,
                                           env=self.env,
                                           logEnviron=self.logEnviron,
                                           collectStdout=collectStdout,
                                           **extra_args)
        cmd.useLog(self.stdio_log, False)
        log.msg("Starting bzr command : bzr %s" % (" ".join(command), ))
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


