"""Setup the application on the target host."""

import os, time
from gbd.core import config, util, plugin, log, shell as sh, db, debug


def vhost_config():
    config_path = config.path()
    server_name = config.get('www.server_name')
    server_port = config.get('www.server_port', '80')
    is_https = str(server_port) == '443'
    htpasswd_path = config.get('www.htpasswd_path')
    basic_auth = bool(htpasswd_path)

    app_name = config.get('app.name');
    app_root = config.app_root()
    log_dir = config.get('paths.log')
    home_dir = config.get('paths.home')

    python_path = os.environ.get('PYTHONPATH', '')
    python_path = (python_path + ':' + app_root).strip(':')

    media_types = ['js', 'json', 'png', 'gif', 'jpg', 'css', 'html', 'ico', 'svg', 'eot', 'woff', 'woff2']
    media_types = '|'.join(sorted(set(media_types)))

    osname = sh.osname()
    xvfb_display = int(config.get('app.xvfb_display', 99))

    loopback_host = config.get('app.loopback_host', 'gbd.local')

    aliases = [
        ['/gbd', config.app_root() + '/gbd']
    ]

    qwc_root = config.get_path('www.qwc_root', '/QGIS-Web-Client/site')

    for key in config.keys('www.alias'):
        aliases.append(config.get_list(key))

    extra_config = '\n'.join(config.get(k) for k in config.keys('www.vhost_conf'))

    return util.render_template(
        config.get_path('www.vhost_template', 'gbd/core/vhost.conf.tpl'),
        locals())


def config_pretty_print(text):
    res = []
    indent = 0

    for s in text.strip().splitlines():
        s = s.strip()
        if not s or s.startswith('#'):
            continue
        if s.startswith('</'):
            indent -= 1
        res.append(' ' * (indent * 4) + s)
        if s.startswith('<') and not s.startswith('</'):
            indent += 1

    return '\n'.join(res) + '\n'


def make_dirs():
    usr = config.get('www.user')
    sh.mkdir(config.get('paths.temp'), usr)
    sh.mkdir(config.get('paths.log'), usr)
    sh.mkdir(config.get('paths.home'), usr)


def empty_temp():
    temp = config.get('paths.temp')
    if os.path.exists(temp) and 'temp' in temp:
        sh.run('rm -rf ' + temp + '/*')


def setup_vhost():
    if sh.osname() in ('debian', 'ubuntu'):
        write_vhost_config('/etc/apache2/sites-available')
        sh.run('a2ensite ' + config.get('www.server_name'))
        sh.run('a2enmod rewrite')
        sh.run('a2enmod fcgid')
        sh.run('service apache2 restart')
    if sh.osname() == 'suse':
        write_vhost_config('/etc/apache2/vhosts.d')
        sh.run('a2enmod rewrite')
        sh.run('a2enmod fcgid')
        sh.run('/usr/sbin/rcapache2 restart')


def setup_plugins(options):
    for p in config.get_list('plugins.required'):
        plugin.install(p, options)


def write_vhost_config(target_dir):
    s = config_pretty_print(vhost_config())
    path = config.get('www.server_name') + '.conf'
    with open(os.path.join(target_dir, path), 'w') as fp:
        fp.write(s)


def copy_qgis_options():
    h = config.get('paths.home')
    usr = config.get('www.user')

    sh.mkdir(h + '/.config', usr)
    sh.mkdir(h + '/.config/QGIS', usr)

    cache_dir = config.get('qgis:cache.directory')
    if cache_dir:
        sh.mkdir(cache_dir, usr)

    with open(h + '/.config/QGIS/QGIS2.conf', 'w') as fp:
        for sec in config.sections():
            if sec.startswith('qgis:'):
                _, title = sec.split(':')
                config.write_section(fp, title, config.get_all(sec))


def bootstrap_script(appid):
    return util.render_template(
        config.get_path('app.update_script', 'gbd/core/update.sh.tpl'),
        locals())


def main(options):
    db.connect(admin=True)
    ts = time.time()
    log.info('setting up...')
    make_dirs()
    empty_temp()
    setup_vhost()
    copy_qgis_options()
    setup_plugins(options)
    db.disconnect()
    log.info('done in %.2f sec' % (time.time() - ts))
