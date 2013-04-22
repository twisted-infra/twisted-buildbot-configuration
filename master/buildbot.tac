
from twisted.application import service
from buildbot.master import BuildMaster

basedir = r'.'
configfile = r'master.cfg'

if basedir == '.':
    import os.path
    basedir = os.path.abspath(os.path.dirname(__file__))

application = service.Application('buildmaster')

BuildMaster(basedir, configfile).setServiceParent(application)

