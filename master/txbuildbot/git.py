from buildbot.steps.source.git import Git


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
        for cutoff in ['/branches/', 'branches/']:
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
