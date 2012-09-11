
from twisted.application import service
from buildbot.master import BuildMaster

basedir = r'.'
configfile = r'master.cfg'

if basedir == '.':
    import os.path
    basedir = os.path.abspath(os.path.dirname(__file__))

application = service.Application('buildmaster')

from twisted.python.logfile import LogFile
from twisted.python.log import ILogObserver, FileLogObserver
logfile = LogFile.fromFullPath("twistd.log", maxRotatedFiles=10)
application.setComponent(ILogObserver, FileLogObserver(logfile).emit)

BuildMaster(basedir, configfile).setServiceParent(application)

