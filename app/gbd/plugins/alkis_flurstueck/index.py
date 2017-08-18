"""ALKIS Flurstuecke -- indexer."""

import json, collections, re

from gbd.core import db, log, util, debug, config, htable
from gbd.core.util import f as _f

from gbd.plugins import (
    alkis_resolver as resolver,
    alkis_adresse as adresse,
    alkis_grundbuch as grundbuch,
    alkis_nutzung as nutzung
)

main_index = htable.SCHEMA + '.fsi_main'
name_index = htable.SCHEMA + '.fsi_name'

_cache = None


def as_json(s):
    return json.dumps(s, ensure_ascii=False, indent=4, sort_keys=True)


def _nutzung_cache():
    nlist = {}

    for r in nutzung.get_all():
        fs_id = r['fs_id']

        if fs_id not in nlist:
            nlist[fs_id] = {}

        nu = {
            'type': r['type'],
            'type_id': r['type_id'],
            'area': r['area'],
            'a_area': r['a_area'],
            'gml_id': r['nu_id'],
            'count': 1
        }

        if r['attributes']:
            nu.update(json.loads(r['attributes']))

        k = (nu['type_id'], nu['key_id'])

        if k not in nlist[fs_id]:
            nlist[fs_id][k] = nu
        else:
            nlist[fs_id][k]['area'] += nu['area']
            nlist[fs_id][k]['a_area'] += nu['a_area']
            nlist[fs_id][k]['count'] += 1

    for fs_id in nlist:
        nlist[fs_id] = sorted(nlist[fs_id].values(), key=lambda x: -x['area'])

    return nlist


def _init_cache():
    global _cache

    _cache = util.struct([
        'nutzung',
        'stelle',
        'addr',
        'gebaeude',
        'gemarkung',
        'addr',
        'name',
    ])

    log.info('fs index: nutzung cache')

    _cache.nutzung = _nutzung_cache()

    log.info('fs index: grundbuch cache')

    _cache.stelle = grundbuch.get_all_buchungsstelle()

    log.info('fs index: adresse cache')

    _cache.addr = collections.defaultdict(list)

    for r in db.select(_f('SELECT * FROM {adresse.addr_index}')):
        fs_id = r.pop('fs_id')
        _cache.addr[fs_id].append(r)

    _cache.gemarkung = {}

    for r in db.select(_f('SELECT DISTINCT gemarkung_id, gemarkung_v FROM {adresse.addr_index}')):
        _cache.gemarkung[r['gemarkung_id']] = r['gemarkung_v']

    log.info('fs index: gebaeude cache')

    _cache.gebaeude = collections.defaultdict(list)

    for r in db.select(_f('SELECT gml_id, fs_id, attributes, area FROM {adresse.geb_index}')):
        if r['attributes']:
            r.update(json.loads(r.pop('attributes')))
        fs_id = r.pop('fs_id')
        _cache.gebaeude[fs_id].append(r)

    _cache.name = []


def _init_tables():
    srid = config.get('alkis.crs').split(':')[1]

    htable.create(main_index, _f('''
            gml_id CHARACTER(16) NOT NULL,

            land CHARACTER VARYING,
            regierungsbezirk CHARACTER VARYING,
            kreis CHARACTER VARYING,
            gemeinde CHARACTER VARYING,
            gemarkung_id CHARACTER VARYING,
            gemarkung CHARACTER VARYING,
            gemarkung_v CHARACTER VARYING,
            anlass CHARACTER VARYING,
            endet CHARACTER VARYING,
            zeitpunktderentstehung CHARACTER VARYING,
            amtlicheflaeche FLOAT,
            flurnummer INTEGER,
            zaehler INTEGER,
            nenner CHARACTER VARYING,
            zaehlernenner CHARACTER VARYING,
            flurstuecksfolge CHARACTER VARYING,
            flurstueckskennzeichen CHARACTER(20),

            lage CHARACTER VARYING,
            c_lage INTEGER,

            gebaeude CHARACTER VARYING,
            gebaeude_area FLOAT,
            c_gebaeude INTEGER,

            buchung CHARACTER VARYING,
            c_buchung INTEGER,

            nutzung CHARACTER VARYING,
            c_nutzung INTEGER,

            wkb_geometry geometry(GEOMETRY, {srid}),
            wkt_geometry CHARACTER VARYING,
            x FLOAT,
            y FLOAT
    '''))

    htable.create(name_index, _f('''
            fs_id CHARACTER(16) NOT NULL,
            vorname CHARACTER VARYING,
            nachname CHARACTER VARYING
    '''))


def _split_hausnummer(hnr):
    if not hnr:
        return None, ''
    m = re.match(r'(\d+)(\D*)', str(hnr))
    return int(m.group(1)), m.group(2)


def _fs_data(fs):
    d = util.pick(fs, [
        'gml_id',
        'flurnummer',
        'zaehler',
        'nenner',
        'flurstueckskennzeichen',
        'flurstuecksfolge',
        'gemarkungsnummer',
        'amtlicheflaeche',
        'zeitpunktderentstehung',

        'wkb_geometry',
        'x',
        'y',
        'wkt_geometry'
    ])

    fs_id = fs['gml_id']

    d['zaehlernenner'] = str(d['zaehler'])
    if d['nenner']:
        d['zaehlernenner'] += '/' + d['nenner']

    d.update(resolver.resolve_places(fs))
    d['gemarkung_v'] = _cache.gemarkung.get(d.get('gemarkung_id')) or d.get('gemarkung')

    p = _cache.addr.get(fs_id, [])
    p.sort(key=lambda x: x.get('strasse_v'))
    d['lage'] = as_json(p)
    d['c_lage'] = len(p)

    p = _cache.gebaeude.get(fs_id, [])
    p.sort(key=lambda x: -x.get('area'))
    d['gebaeude'] = as_json(p)
    d['c_gebaeude'] = len(p)
    d['gebaeude_area'] = sum(x['area'] for x in p)

    buchung = _cache.stelle.get(fs['istgebucht'], [])

    for r in buchung:
        for ow in r.get('owner', []):
            if 'person' in ow:
                _cache.name.append({
                    'fs_id': fs_id,
                    'nachname': ow['person'].get('nachnameoderfirma'),
                    'vorname': ow['person'].get('vorname'),
                })

    d['c_buchung'] = len(buchung)
    d['buchung'] = as_json(buchung)

    p = _cache.nutzung.get(fs_id, [])
    d['nutzung'] = as_json(p)
    d['c_nutzung'] = len(p)

    return d


def _update_gemarkung():
    rs = db.select(_f('SELECT gemeinde, gemarkungsnummer, gemarkung FROM {main_index}'))
    gemeinde = {}
    ids = collections.defaultdict(set)

    for r in rs:
        gemeinde[r['gemarkungsnummer']] = r['gemeinde']
        ids[r['gemarkung']].add(r['gemarkungsnummer'])

    sql = []

    for name, nrs in ids.items():
        if len(nrs) < 2:
            continue
        for nr in nrs:
            v = '%s (%s)' % (name, gemeinde[nr])
            sql.append(_f('''
                UPDATE {main_index}
                    SET gemarkung_v = '{v}'
                    WHERE gemarkungsnummer = '{nr}'
            '''))

    db.run_many(sql)


def _create():
    _init_tables()
    _init_cache()

    fs_sql = '''
        SELECT *,
            ST_AsText(wkb_geometry) AS wkt_geometry,
            ST_X(ST_Centroid(wkb_geometry)) AS x,
            ST_Y(ST_Centroid(wkb_geometry)) AS y
        FROM ax_flurstueck
        WHERE endet IS NULL
    '''

    excl = config.get_list('alkis.exclude_gemarkung')
    if excl:
        # exclude a list of "gemarkungsnummer" (string)
        excl = ','.join("'%d'" % int(x) for x in excl)
        fs_sql += _f(' AND gemarkungsnummer NOT IN ({excl})')

    rs = db.select(fs_sql)
    step = 1000

    with util.ProgressIndicator('main index', db.count('ax_flurstueck')) as pi:
        for chunk in util.chunked(rs, step):
            data = [_fs_data(fs) for fs in chunk]
            db.insert(main_index, data)
            pi.update(step)

    step = 1000

    with util.ProgressIndicator('name index', len(_cache.name)) as pi:
        for data in util.chunked(_cache.name, step):
            db.insert(name_index, data)
            pi.update(step)


def create():
    _create()

    log.time_start('fs index: vacuum')
    db.vacuum(main_index)
    db.vacuum(name_index)
    log.time_end('fs index: vacuum')


def check(force):
    htable.check([main_index, name_index], force, create)
