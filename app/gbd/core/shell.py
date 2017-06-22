import subprocess
import platform


def run(cmd, input=None, echo=False, env=None):
    args = {
        'stdin': subprocess.PIPE if input is not None else None,
        'stdout': None if echo else subprocess.PIPE,
        'stderr': None if echo else subprocess.PIPE,
        'shell': True,
        'bufsize': 0 if echo else -1
    }
    if env:
        args['env'] = env
    p = subprocess.Popen(cmd, **args)
    out, err = p.communicate(input)
    if p.returncode:
        raise ValueError('command failed', cmd, p.returncode, out, err)
    return out, err


def runl(cmds, input=None, echo=False):
    for cmd in cmds.strip().splitlines():
        cmd = cmd.strip()
        if cmd:
            run(cmd, input, echo)


def mkdir(name, user=None, perms='755'):
    run('mkdir -p %s' % name)
    run('chmod %s %s' % (perms, name))
    if user:
        run('chown %s %s' % (user, name))


def osname():
    name, ver, arch = platform.linux_distribution()
    if 'suse' in name.lower():
        return 'suse'
    if 'ubuntu' in name.lower():
        return 'ubuntu'
    if 'debian' in name.lower():
        return 'debian'
