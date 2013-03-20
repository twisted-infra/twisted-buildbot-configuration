from fabric.api import run, cd, task, hosts

bb_master = hosts('bb-master@cube.twistedmatrix.com')

@task
@bb_master
def check():
    with cd('Buildbot-0.8.6'):
        run('bzr missing', pty=False)

@task
@bb_master
def update_master():
    with cd('Buildbot-0.8.6'):
        run('bzr pull', pty=False)
        run('./start-master')
    pass
