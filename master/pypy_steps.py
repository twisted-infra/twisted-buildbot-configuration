
"""
Steps for translating PyPy.
"""

from buildbot.steps.shell import ShellCommand

class Translate(ShellCommand):
    name = "translate"
    description = ["Translating"]
    descriptionDone = ["Translation"]

    command = ["../../../../pypy", "translate.py", "--batch"]
    translationTarget = "targetpypystandalone"
    haltOnFailure = False

    def __init__(self, translationArgs, targetArgs,
                 workdir="build/pypy/translator/goal",
                 *a, **kw):
        self.command = self.command + translationArgs + [self.translationTarget] + targetArgs
        ShellCommand.__init__(self, workdir, *a, **kw)
