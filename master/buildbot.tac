
from twisted.application import service
from buildbot.master import BuildMaster

basedir = r'/srv/bb-master/BuildBot/master'
configfile = r'master.cfg'

application = service.Application('buildmaster')

from twisted.python.logfile import LogFile
from twisted.python.log import ILogObserver, FileLogObserver
logfile = LogFile.fromFullPath("twistd.log", maxRotatedFiles=10)
application.setComponent(ILogObserver, FileLogObserver(logfile).emit)

BuildMaster(basedir, configfile).setServiceParent(application)

