from buildbot.steps.source.git import Git


class TwistedGit(Git):
    """
    This should be *very* temporary; it's to support people trying to force
    builds against /branches/foo and letting it work on the git builders.
    People should start switching to just "foo", but while we have both
    SVN-based and git-based builders going it'll be impossible to force
    builds on all bots at the same time with the same command.
    """

    def startVC(self, branch, revision, patch):
        """
        If a branch name starts with /branches/, cut it off before referring
        to it in git commands.
        """
        for cutoff in ['/branches/', 'branches/']:
            if branch.startswith(cutoff):
                branch = branch[len(cutoff):]
                break
        return Git.startVC(self, branch, revision, patch)
