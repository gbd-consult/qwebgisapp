"""ALKIS Flurstuecke."""

import json, time
from gbd.core import db, log, util, config, debug
from gbd.plugins import alkis_adresse as adresse
from gbd.core.util import inline_format as _f
from . import index


def count():
    return db.count(index.main_index)


def list_gemarkung():
    rs = db.select(_f('''
        SELECT DISTINCT gemarkung_id, gemarkung_v
        FROM {index.main_index}
        ORDER BY gemarkung_v
    '''))
    return [(r['gemarkung_id'], r['gemarkung_v']) for r in rs]


def list_strasse(gemarkung_id):
    rs = db.select(_f('''
            SELECT DISTINCT strasse
            FROM {adresse.addr_index}
            WHERE gemarkung_id = %s
            ORDER BY strasse
        '''), [gemarkung_id]
                   )
    return [r['strasse'] for r in rs]


def list_strasse_all():
    rs = db.select(_f('''
            SELECT strasse, gemarkung_id
            FROM {adresse.addr_index}
            WHERE strasse NOT IN ('ohne Lage')
        '''))

    str2gem = {}

    for r in rs:
        if r['strasse'] not in str2gem:
            str2gem[r['strasse']] = set()
        str2gem[r['strasse']].add(int(r['gemarkung_id'] or 0))

    ls = []
    for strasse, gms in str2gem.iteritems():
        ls.append([strasse, sorted(gms)])

    return ls


_uses_flurnummer = None


def uses_flurnummer():
    # some DB's use flurnummers, while other don't

    global _uses_flurnummer

    if _uses_flurnummer is None:
        rs = db.select(_f('''
                SELECT COUNT(*) AS c
                FROM {index.main_index}
                WHERE flurnummer IS NOT NULL
            '''))
        for r in rs:
            _uses_flurnummer = r['c'] > 0
        log.debug('uses_flurnummer=' + str(_uses_flurnummer))

    return _uses_flurnummer


def _add_fsnumber(sel, val):
    params = []
    conds = []
    for f in val:
        c = []
        for p, q in f.items():
            c.append(p + '=%s')
            params.append(q)
        conds.append('(' + ' AND '.join(c) + ')')

    conds = '(' + ' OR '.join(conds) + ')'
    sel.add_where([conds] + params)


def find(params, columns=None, limit=None, sort=None):
    srid = config.get('alkis.crs').split(':')[1]

    sel = db.select_statement()
    sel.add_table(index.main_index, 'fs')
    joins = 0

    if columns:
        for col in columns:
            sel.add_column('fs.' + col)
    else:
        sel.add_column('fs.*')

    for k, v in params.items():

        if k == 'gml_id':
            if isinstance(v, (tuple, list)):
                cond = ','.join('%s' for _ in v)
                sel.add_where(['fs.gml_id IN (' + cond + ')'] + list(v))
            elif v is not None:
                sel.add_where(['fs.gml_id = %s', v])
            else:
                sel.add_where('fs.gml_id is NULL')

        elif k in ('gemarkungsnummer', 'flurnummer', 'zaehler', 'nenner', 'flurstuecksfolge'):

            if k == 'gemarkungsnummer':
                k = 'gemarkung_id'

            if v is not None:
                sel.add_where(['fs.' + k + '= %s', v])
            else:
                sel.add_where('fs.' + k + ' is NULL')

        elif k == '_fsnumber':
            _add_fsnumber(sel, v)

        elif k == 'gemeinde':
            sel.add_where(db.star_like('fs.gemeinde', v))

        elif k == 'strasse':
            sel.add_where('addr.fs_id = fs.gml_id')
            adresse.add_filter(sel, 'addr', util.pick(params, ['strasse', 'hausnummer']))
            joins += 1

        elif k == 'nachnameoderfirma':

            sel.add_table(index.name_index, 'na')
            sel.add_where('na.fs_id = fs.gml_id')
            sel.add_where(db.star_like('na.nachname', v))

            if 'vorname' in params:
                sel.add_where(db.star_like('na.vorname', params['vorname']))

            joins += 1

        elif k == 'minflaeche':
            sel.add_where(['amtlicheflaeche >= %s', v])

        elif k == 'maxflaeche':
            sel.add_where(['amtlicheflaeche <= %s', v])

        elif k in ('bounds', 'bounds_within'):
            # WKB or WKT?
            if v.startswith((chr(0), chr(1), '0')):
                expr = '%s'
            else:
                expr = _f('ST_GeomFromText(%s,{srid})')
            verb = 'ST_Within' if k == 'bounds_within' else 'ST_Intersects'
            sel.add_where([_f('{verb}(wkb_geometry,{expr})'), v])

        elif k == 'x':
            try:
                x = float(params['x'])
                y = float(params['y'])
            except (KeyError, ValueError):
                x = y = 0
            point = _f("ST_GeomFromText('POINT({x} {y})',{srid})", x, y)
            sel.add_where(_f('ST_Contains(wkb_geometry,{point})'))

    if joins:
        sel.distinct(True)

    if sort:
        sel.add_sort(sort)

    if limit:
        sel.limit(limit)

    # debug.pp(sel.sql())

    for r in sel.fetch():
        for f in 'buchung', 'nutzung', 'nutzung_areas', 'lage', 'gebaeude':
            if f in r:
                r[f] = json.loads(r[f])
        if 'wkt_geometry' in r:
            r['geometry'] = r['wkt_geometry']

        yield r


def find_one(params, columns=None, sort=None):
    for fs in find(params, columns=columns, sort=sort, limit=1):
        return fs


def install(options):
    index.check(options.get('force'))
