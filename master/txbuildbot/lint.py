from twisted.python import log, util
from buildbot.status.builder import FAILURE
from buildbot.steps.shell import ShellCommand

try:
    import cStringIO
    StringIO = cStringIO
except ImportError:
    import StringIO
import re

class LintStep(ShellCommand):
    def createSummary(self, logObj):
        logText = logObj.getText()
        self.addCompleteLog('%s errors' % self.lintChecker, logText)

        currentErrors = self.computeErrors(logText)
        previousErrors = self.computeErrors(self.getPreviousLog())
        newErrors = {}

        for errorType in currentErrors:
            errors = (
                currentErrors[errorType] - 
                previousErrors.get(errorType, set()))
            log.msg("Found %d new errors of type %s" % (len(errors), errorType))
            if errors:
                newErrors[errorType] = errors

        if newErrors:
            allNewErrors = self.formatErrors(newErrors)
            self.addCompleteLog('new %s errors' % self.lintChecker, '\n'.join(allNewErrors))
            self.worse = True
            log.msg("Build is worse with respect to %s errors" % self.lintChecker)
        else:
            log.msg("Build is not worse with respect to %s errors" % self.lintChecker)
            self.worse = False


    def computeErrors(self, logText):
        raise NotImplementedError("Must implement computeErrors for a Lint step")

    def formatErrors(self, newErrors):
        raise NotImplementedError("Must implement formatErrors for a Lint step")


    def getPreviousLog(self):
        build = self.getLastBuild()
        if build is None:
            log.msg("Found no previous build, returning empty error log")
            return ""
        for logObj in build.getLogs():
            if logObj.name == '%s errors' % self.lintChecker:
                text = logObj.getText()
                log.msg("Found error log, returning %d bytes" % (len(text),))
                return text
        log.msg("Did not find error log, returning empty error log")
        return ""


    def getLastBuild(self):
        status = self.build.build_status
        number = status.getNumber()
        if number == 0:
            log.msg("last result is undefined because this is the first build")
            return None
        builder = status.getBuilder()
        for i in range(1, 11):
            build = builder.getBuild(number - i)
            if not build:
                continue
            branch = build.getProperty("branch")
            if not branch:
                log.msg("Found build on default branch at %d" % (number - i,))
                return build
            else:
                log.msg("skipping build-%d because it is on branch %r" % (i, branch))
        log.msg("falling off the end")
        return None


    def evaluateCommand(self, cmd):
        if self.worse:
            return FAILURE
        return ShellCommand.evaluateCommand(self, cmd)



class CheckDocumentation(LintStep):
    """
    Run Pydoctor over the source to check for errors in API
    documentation.
    """
    name = 'api-documentation'
    command = (
        'python '
        '~/Projects/pydoctor/trunk/bin/pydoctor '
        '--quiet '
        '--introspect-c-modules '
        '--make-html '
        '--system-class pydoctor.twistedmodel.TwistedSystem '
        '--add-package `pwd`/twisted')
    description = ["checking", "api", "docs"]
    descriptionDone = ["api", "docs"]

    lintChecker = 'pydoctor'

    def computeErrors(self, logText):
        errors = {}
        for line in StringIO.StringIO(logText):
            # Mostly get rid of the trailing \n
            line = line.strip()
            if 'invalid ref to' in line:
                key = 'invalid ref'
                # Discard the line number since it's pretty unstable
                # over time
                fqpnlineno, rest = line.split(' ', 1)
                fqpn, lineno = fqpnlineno.split(':')
                value = '%s: %s' % (fqpn, rest)
            elif 'found unknown field on' in line:
                key = 'unknown fields'
                value = line
            else:
                continue
            errors.setdefault(key, set()).add(value)
        return errors


    def formatErrors(self, newErrors):
        allNewErrors = []
        for errorType in newErrors:
            allNewErrors.extend(newErrors[errorType])
            self.setProperty("new " + errorType, len(newErrors[errorType]))
        allNewErrors.sort()
        return newErrors


    def getText(self, cmd, results):
        if results == FAILURE:
            return ["api", "docs"]
        return ShellCommand.getText(self, cmd, results)


class TwistedCheckerError(util.FancyEqMixin, object):
    regex = re.compile(r"^(?P<type>[WCEFR]\d{4}):(?P<line>\s*\d+),(?P<indent>\d+):(?P<text>)")
    compareAttributes = ('type', 'text')

    def __init__(self, msg):
        self.msg = msg
        m = self.regex.match(msg)
        if m:
            d = m.groupdict()
            self.type = d['type']
            self.line = d['line']
            self.indent = d['indent']
            self.text = d['text']
        else:
            self.type = "UXXXX"
            self.line = "9999"
            self.indent = "9"
            self.text = "Unparseable"

    def __hash__(self):
        return hash((self.type, self.text))

    def __str__(self):
        return self.msg

    def __repr__(self):
        return ("<TwistedCheckerError type=%s line=%d indent=%d, text=%r>" %
            (self.type, int(self.line), int(self.indent), self.text))


class CheckCodesByTwistedChecker(LintStep):
    """
    Run TwistedChecker over source codes to check for new warnings
    involved in the lastest build.
    """
    name = 'run-twistedchecker'
    command = ('twistedchecker twisted')
    description = ["checking", "codes"]
    descriptionDone = ["check", "results"]
    prefixModuleName = "************* Module "
    regexLineStart = "^[WCEFR]\d{4}\:"

    lintChecker = 'twistedchecker'


    def computeErrors(self, logText):
        warnings = {}
        currentModule = None
        warningsCurrentModule = []
        for line in StringIO.StringIO(logText):
            # Mostly get rid of the trailing \n
            line = line.strip("\n")
            if line.startswith(self.prefixModuleName):
                # Save results for previous module
                if currentModule:
                    warnings[currentModule] = set(map(TwistedCheckerError, warningsCurrentModule))
                # Initial results for current module
                moduleName = line.replace(self.prefixModuleName, "")
                currentModule = moduleName
                warningsCurrentModule = []
            elif re.search(self.regexLineStart, line):
                warningsCurrentModule.append(line)
            else:
                if warningsCurrentModule:
                    warningsCurrentModule[-1] += "\n" + line
                else:
                    log.msg("Bad result format for %s" % currentModule)
        # Save warnings for last module
        if currentModule:
            warnings[currentModule] = set(map(TwistedCheckerError, warningsCurrentModule))
        return warnings


    def formatErrors(self, newErrors):
        allNewErrors = []
        for modulename in newErrors:
            allNewErrors.append(self.prefixModuleName + modulename)
            allNewErrors.extend(newErrors[modulename])
            self.setProperty("new in " + modulename, len(newErrors[modulename]))
        return allNewErrors
