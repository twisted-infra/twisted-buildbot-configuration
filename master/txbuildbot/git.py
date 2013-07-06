from buildbot.steps.source.git import Git
from buildbot.steps.shell import ShellCommand
from buildbot.status.results import SKIPPED


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



class MergeForward(ShellCommand):
    """

    """
    name = 'merge-forward'
    description = ['merging', 'forward']
    descriptionDone = ['merge', 'forward']


    def __init__(self, repourl, **kwargs):
        kwargs['command'] = ['git', 'pull',
                             '--no-ff', '--no-stat', '--no-edit',
                             repourl, 'trunk']
        ShellCommand.__init__(self, **kwargs)
        self.addFactoryArguments(repourl=repourl)


    def doStepIf(self, _):
        """
        Don't merge if building trunk or a release.
        """
        stamp = self.build.getSourceStamp(None)
        branch = stamp.branch

        if branch is None:
            return False

        for cutoff in ['/branches/', 'branches/', '/']:
            if branch.startswith(cutoff):
                branch = branch[len(cutoff):]
                break

        if branch in ('', 'trunk'):
            return False

        if branch.startswith('releases/'):
            return False

        return True


    def hideStepIf(self, result, _):
        return result == SKIPPED
