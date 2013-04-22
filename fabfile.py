import os

from fabric.api import settings, run, env, cd, puts

from braid import git, cron, pip
from braid import fails
from braid.twisted import service
from braid import config

class Buildbot(service.Service):
    def task_install(self):
        """
        Install buildbot.
        """
        self.bootstrap()

        with settings(user=self.serviceUser):
            pip.install('sqlalchemy==0.7.10')
            self.task_update(_installDeps=True)
            run('ln -nsf {}/start {}/start'.format(self.configDir, self.binDir))
            # TODO: install dependencies
            # TODO: install private.py
            with cd(os.path.join(self.configDir, 'master')):
                if (env.get('environment') != 'production' and
                    fails('[ -f private.py ]')):
                    puts('Using sample private.py')
                    run('cp private.py.sample private.py')
            run('~/.local/bin/buildbot upgrade-master {}'.format(os.path.join(self.configDir, 'master')))
            cron.install(self.serviceUser, '{}/crontab'.format(self.configDir))

    def task_update(self, _installDeps=False):
        """
        Update
        """
        with settings(user=self.serviceUser):
            git.branch('https://github.com/twisted-infra/twisted-buildbot-configuration', self.configDir)
            buildbotSource = os.path.join(self.configDir, 'buildbot-source')
            git.branch('https://github.com/twisted-infra/buildbot', buildbotSource)
            if _installDeps:
                pip.install('{}'.format(os.path.join(buildbotSource, 'master')),
                        python='python')
            else:
                pip.install('--no-deps --upgrade {}'.format(os.path.join(buildbotSource, 'master')),
                        python='python')

globals().update(Buildbot('bb-master').getTasks())
