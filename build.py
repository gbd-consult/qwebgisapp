#!/usr/bin/env python

"""
    Build a client package.

    build.py config_path build_root

"""

import sys, os

sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)) + '/app')

from gbd.core import config as cf, shell as sh, plugin, setup, util

def main(config_path, build_root):
    cf.load(os.path.abspath(config_path))
    cwd = os.path.abspath(build_root)

    if not os.path.exists(cwd + '/QGIS-Web-Client'):
        print 'ERROR: QGIS-Web-Client not found, please download'
        print 'git clone https://github.com/gbd-consult/QGIS-Web-Client'
        return

    if not os.path.exists(cwd + '/qwebgisapp'):
        print 'ERROR: qwebgisapp not found'
        return

    app_id = cf.get('app.id')
    app_name = cf.get('app.name')
    target = cwd + '/' + app_id
    src = cwd + '/QWC4GBDClients/app'
    dst = target + '/app'
    
    sh.runl(util.f("""
        rm -fr {target}        

        mkdir -p {dst}/gbd
        mkdir -p {dst}/www        
        
        cp -r {src}/gbd/core {dst}/gbd
        cp -r {src}/gbd/bin  {dst}/gbd
        cp -r {src}/gbd/www  {dst}/gbd

        cp -r {src}/VERSION  {dst}/

        mkdir {dst}/www/QGIS-Web-Client
        cp -r {cwd}/QGIS-Web-Client/site {dst}/www/QGIS-Web-Client      
        cp    {src}/www/index.fcgi       {dst}/www
                              
        mkdir -p {dst}/gbd/plugins
        cp {src}/gbd/__init__.py   {dst}/gbd
        cp {src}/gbd/plugins/__init__.py   {dst}/gbd/plugins

    """))
    
    qwc_delete = [
        'gis-project_listing.xsl',
        'index.html',
        'index.php',
        'index.xml.tmpl',
        'qgiswebclient.html',
        'thumbnails'
    ]

    for p in qwc_delete:
        sh.run(util.f('rm -fr {dst}/www/QGIS-Web-Client/site/{p}'))

    deps = plugin.resolve(cf.get_list('plugins.active'), src)

    with open(dst + '/pip.lst', 'w') as fp:
        fp.write('\n'.join(deps['pips']) + '\n\n')
    with open(dst + '/apt.lst', 'w') as fp:
        fp.write('\n'.join(deps['apts']) + '\n\n')

    cf.put('plugins.required', deps['required'])
    cf.put('plugins.active', deps['active'])

    for p in deps['required']:
        sh.run(util.f('cp -r {src}/gbd/plugins/{p} {dst}/gbd/plugins'))

    sh.run(util.f("find {target}/* -name '*pyc' -delete"))

    with open(util.f('{dst}/config.ini'), 'w') as fp:
        cf.write(fp)

    sh.run(util.f('cd {target} && zip -r {app_id} app'))
    sh.run(util.f('mv {target}/{app_id}.zip {build_root}'))

    with open(util.f('{build_root}/{app_name}-update.sh'), 'w') as fp:
        fp.write(setup.bootstrap_script(app_id))

main(sys.argv[1], sys.argv[2])
