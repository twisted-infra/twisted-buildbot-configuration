import os

from fabric.api import settings, run, env, cd, puts, abort
from fabric.contrib import files

from braid import git, cron, pip
from braid.twisted import service
from braid import config

_hush_pyflakes = [config]

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
            run('mkdir -p ~/data')
            run('mkdir -p ~/data/build_products')
            run('ln -nsf ~/data/build_products {}/master/public_html/builds')

            # TODO: install dependencies
            # TODO: install private.py
            if env.get('environment') == 'production':
                self.task_testInit()

            cron.install(self.serviceUser, '{}/crontab'.format(self.configDir))

    def task_testInit(self, force=None):
        """
        Do test environment setup (with fake passwords, etc).
        """
        if env.get('environment') == 'production':
           abort("Don't use testInit in production.")

        with (settings(user=self.serviceUser),
             cd(os.path.join(self.configDir, 'master'))):
            if force or not files.exists('private.py'):
                puts('Using sample private.py')
                run('cp private.py.sample private.py')

            if force or not files.exists('state.sqlite'):
                run('~/.local/bin/buildbot upgrade-master')

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
