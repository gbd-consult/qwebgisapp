"""Helper tables for gbd indexes."""

import db, config, util, log, debug
from gbd.core.util import inline_format as _f

SCHEMA = 'gbd'
meta_table = SCHEMA + '.meta'


def _qname(name):
    if '.' in name:
        _, name = name.split('.')
    return SCHEMA + '.' + name


def ensure_meta():
    db.run_many(_f('''
        CREATE SCHEMA IF NOT EXISTS {SCHEMA};
        CREATE TABLE IF NOT EXISTS {meta_table} (
            name CHARACTER VARYING PRIMARY KEY,
            version INT
        )
    '''))


def lock_meta():
    db.run(_f('LOCK TABLE {meta_table} IN ACCESS EXCLUSIVE MODE'))


def ensure_permissions():
    user = config.get('db.user')
    ensure_meta()
    with db.transaction():
        lock_meta()
        db.run(_f('GRANT USAGE ON SCHEMA {SCHEMA} TO {user}'))
        db.run(_f('GRANT ALL ON ALL TABLES IN SCHEMA {SCHEMA} TO {user}'))


def create(name, sql):
    name = _qname(name)
    ensure_meta()
    with db.transaction():
        lock_meta()
        db.run(_f('''
            DROP TABLE IF EXISTS {name};
            CREATE TABLE {name} (
            {sql}
            );
        '''))


def drop(name):
    name = _qname(name)
    ensure_meta()
    with db.transaction():
        lock_meta()
        db.run_many([
            _f('DROP TABLE IF EXISTS {name}'),
            [_f('DELETE FROM {meta_table} WHERE name=%s'), [name]]
        ])


def version(name):
    name = _qname(name)

    if not db.exists(name):
        drop(name)
        return 0

    ensure_meta()
    rs = db.select(_f('SELECT version FROM {meta_table} WHERE name=%s'), [name])
    for r in rs:
        return int(r['version'])

    return 0


def bump(name, ver):
    name = _qname(name)
    ensure_meta()
    with db.transaction():
        lock_meta()
        db.run(_f('DELETE FROM {meta_table} WHERE name=%s'), [name])
        db.run(_f('INSERT INTO {meta_table}(name, version) VALUES(%s,%s)'), [name, ver])


def check(tables, force, creator):
    ver = util.app_version(as_number=True)

    if not force:
        faults = 0
        for t in tables:
            v = version(t)
            if v == ver:
                log.info(_f('check index: {t}({v}) ok'))
            else:
                log.info(_f('check index: {t}({v}) FAULT'))
                faults += 1
        if not faults:
            ensure_permissions()
            return True

    for t in tables:
        drop(t)

    creator()

    for t in tables:
        bump(t, ver)

    ensure_permissions()
    return False
