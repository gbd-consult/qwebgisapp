# coding=utf8

import re, json, collections

from gbd.core import db, log, util, config, htable, debug
from gbd.core.util import inline_format as _f
from gbd.plugins import alkis_resolver as resolver

addr_index = htable.SCHEMA + '.adr_main'
geb_index = htable.SCHEMA + '.adr_gebaeude'


def normalize_hausnummer(hn):
    # it's always "13 a" in alkis, but we allow 13a
    m = re.match(r'(\d+)(\D*)', str(hn).strip())
    if not m:
        return None
    if m.group(2):
        return m.group(1) + ' ' + m.group(2).strip()
    return m.group(1)


def int_hausnummer(hn):
    m = re.match(r'(\d+)(\D*)', str(hn or '').strip())
    if not m:
        return None
    return int(m.group(1))


def street_name_key(s):
    s = s.strip().lower()

    s = s.replace(u'ä', 'ae')
    s = s.replace(u'ë', 'ee')
    s = s.replace(u'ö', 'oe')
    s = s.replace(u'ü', 'ue')
    s = s.replace(u'ß', 'ss')

    s = re.sub(r'\W+', ' ', s)

    # s = re.sub(r'(?<=\d)\s+', '', s)
    # s = re.sub(r'\s+(?=\d)', '', s)

    s = re.sub(r'\s?str\.$', '.strasse', s)
    s = re.sub(r'\s?pl\.$', '.platz', s)
    s = re.sub(r'\s?(strasse|allee|damm|gasse|pfad|platz|ring|steig|wall|weg|zeile)$', r'.\1', s)

    s = s.replace(' ', '.')

    return s


_lage_tables = (
    'ax_lagebezeichnungohnehausnummer',
    'ax_lagebezeichnungmithausnummer',
    'ax_lagebezeichnungmitpseudonummer')


def as_json(s):
    if s is None:
        return None
    return json.dumps(s, ensure_ascii=False, indent=4, sort_keys=True)


def index_gebaeude():
    schema = htable.SCHEMA
    srid = config.get('alkis.crs').split(':')[1]
    min_area = 0.5

    fsx_temp = htable.SCHEMA + '.geb_fsx'
    geb_temp = htable.SCHEMA + '.geb_geb'

    htable.create(fsx_temp, _f('''
            id SERIAL PRIMARY KEY,
            gml_id CHARACTER VARYING,
            isvalid BOOLEAN,
            wkb_geometry geometry(GEOMETRY, {srid})
    '''))

    htable.create(geb_temp, _f('''
            id SERIAL PRIMARY KEY,
            gml_id CHARACTER VARYING,
            attributes CHARACTER VARYING,
            isvalid BOOLEAN,
            wkb_geometry geometry(GEOMETRY, {srid})
    '''))

    htable.create(geb_index, _f('''
            id SERIAL PRIMARY KEY,
            gml_id CHARACTER VARYING,
            fs_id CHARACTER VARYING,
            attributes CHARACTER VARYING,
            area FLOAT,
            fs_wkb geometry(GEOMETRY, {srid}),
            gb_wkb geometry(GEOMETRY, {srid})
    '''))

    log.info('gebaeude: copying')

    db.run(_f('''
        INSERT INTO {fsx_temp}(gml_id,wkb_geometry)
        SELECT
            gml_id,
            wkb_geometry
        FROM ax_flurstueck
    '''))

    rs = db.select('''
        SELECT
            gml_id,
            gebaeudefunktion,
            weiteregebaeudefunktion,
            name,
            bauweise,
            anzahlderoberirdischengeschosse,
            anzahlderunterirdischengeschosse,
            hochhaus,
            objekthoehe,
            dachform,
            zustand,
            geschossflaeche,
            grundflaeche,
            umbauterraum,
            lagezurerdoberflaeche,
            dachart,
            dachgeschossausbau,
            description,
            art,
            individualname,
            baujahr,
            wkb_geometry
        FROM ax_gebaeude
    ''')

    gebs = []

    for r in rs:
        r = util.strip_none(r)
        r.update(resolver.attributes('ax_gebaeude', r))
        gebs.append({
            'gml_id': r.pop('gml_id'),
            'wkb_geometry': r.pop('wkb_geometry'),
            'attributes': as_json(r)

        })

    db.insert(geb_temp, gebs)

    db.run(_f('''
        DROP INDEX IF EXISTS {schema}.geb_fsx_gist;
        CREATE INDEX geb_fsx_gist ON {fsx_temp} USING GIST(wkb_geometry);
        DROP INDEX IF EXISTS {schema}.geb_geb_gist;
        CREATE INDEX geb_geb_gist ON {geb_temp} USING GIST(wkb_geometry)
    '''))

    log.info('gebaeude: validating')

    db.run(_f('UPDATE {geb_temp} SET isvalid = ST_IsValid(wkb_geometry)'))
    db.run(_f('UPDATE {fsx_temp} SET isvalid = ST_IsValid(wkb_geometry)'))

    for tab in geb_temp, fsx_temp:
        rs = db.select(_f('SELECT gml_id, ST_IsValidReason(wkb_geometry) AS reason FROM {tab} WHERE NOT isvalid'))
        for r in rs:
            log.warning(_f('gml_id={r[gml_id]} error={r[reason]}'))
        db.run(_f('DELETE FROM {tab} WHERE NOT isvalid'))

    cnt = db.count(geb_temp)
    step = 1000

    with util.ProgressIndicator('gebaeude: search', cnt) as pi:
        for n in range(0, cnt, step):
            n1 = n + step
            db.run(_f('''
                INSERT INTO {geb_index} (gml_id, fs_id, attributes, fs_wkb, gb_wkb)
                    SELECT
                        gb.gml_id,
                        fs.gml_id,
                        gb.attributes,
                        fs.wkb_geometry,
                        gb.wkb_geometry
                    FROM
                        {geb_temp} AS gb,
                        {fsx_temp} AS fs
                    WHERE
                        {n} < gb.id AND gb.id <= {n1}
                        AND ST_Intersects(gb.wkb_geometry, fs.wkb_geometry)
            '''))
            pi.update(step)

    cnt = db.count(geb_index)
    step = 1000

    with util.ProgressIndicator('gebaeude: areas', cnt) as pi:
        for n in range(0, cnt, step):
            n1 = n + step
            db.run(_f('''
                UPDATE {geb_index}
                    SET area = ST_Area(ST_Intersection(fs_wkb, gb_wkb))
                    WHERE
                        {n} < id AND id <= {n1}
            '''))
            pi.update(step)

    log.info('gebaeude: cleanup')

    db.run(_f('DELETE FROM {geb_index} WHERE area < %s'), [min_area])


def index_addr():
    htable.create(addr_index, _f('''
        gml_id CHARACTER(16) NOT NULL,
        fs_id  CHARACTER(16),

        land CHARACTER VARYING,
        land_id CHARACTER VARYING,
        regierungsbezirk CHARACTER VARYING,
        regierungsbezirk_id CHARACTER VARYING,
        kreis  CHARACTER VARYING,
        kreis_id CHARACTER VARYING,
        gemeinde CHARACTER VARYING,
        gemeinde_id CHARACTER VARYING,
        gemarkung  CHARACTER VARYING,
        gemarkung_v  CHARACTER VARYING,
        gemarkung_id CHARACTER VARYING,

        strasse CHARACTER VARYING,
        strasse_k CHARACTER VARYING,
        hausnummer CHARACTER VARYING,
        hausnummer_n INTEGER,

        lage_id CHARACTER(16),
        lage_schluesselgesamt  CHARACTER VARYING,

        x FLOAT,
        y FLOAT,
        xysrc  CHARACTER VARYING
    '''))

    def _key(r):
        # schluesselgesamt should be equal to land+regierungsbezirk+kreis+gemeinde+lage
        # but sometimes it is not... so lets use our own key
        return r['land'], r['regierungsbezirk'], r['kreis'], r['gemeinde'], r['lage']

    lage_catalog = {}
    for r in db.select('SELECT * FROM ax_lagebezeichnungkatalogeintrag'):
        lage_catalog[_key(r)] = [r['gml_id'], r['schluesselgesamt'], r['bezeichnung']]

    lage = {}

    for tab in _lage_tables:
        for la in db.select(_f('SELECT * FROM {tab}')):
            if la['unverschluesselt']:
                la['strasse'] = la['unverschluesselt']
            else:
                lg = lage_catalog.get(_key(la))
                if lg:
                    la['lage_id'] = lg[0]
                    la['lage_schluesselgesamt'] = lg[1]
                    la['strasse'] = lg[2]

            if 'strasse' not in la or la['strasse'] == 'ohne Lage':
                continue

            for hnr in 'hausnummer', 'pseudonummer', 'laufendenummer':
                if la.get(hnr):
                    la['hausnummer'] = la[hnr]
                    la['hausnummer_type'] = hnr
                    break

            lage[la['gml_id']] = la

    step = 1000
    rs = db.select('''
        SELECT
            gml_id,
            weistauf,
            zeigtauf,
            land,
            gemarkungsnummer,
            gemeinde,
            regierungsbezirk,
            kreis,
            ST_X(ST_Centroid(wkb_geometry)) AS x,
            ST_Y(ST_Centroid(wkb_geometry)) AS y
        FROM ax_flurstueck
    ''')

    with util.ProgressIndicator('address index', db.count('ax_flurstueck')) as pi:
        for chunk in util.chunked(rs, step):
            for fs in chunk:
                fs_id = fs.pop('gml_id')

                for lage_id in (fs['zeigtauf'] or []) + (fs['weistauf'] or []):

                    if lage_id not in lage:
                        continue

                    la = lage[lage_id]

                    if 'fs_ids' not in la:
                        la['fs_ids'] = []
                    la['fs_ids'].append(fs_id)

                    if not la.get('gemarkungsnummer'):
                        la.update(fs)

                    la['x'] = fs['x']
                    la['y'] = fs['y']
                    la['xysrc'] = 'fs'

            pi.update(step)

    log.debug('address: coordinates')

    rs = db.select(_f('''
        SELECT
            dientzurdarstellungvon,
            ST_X(ST_Centroid(wkb_geometry)) AS x,
            ST_Y(ST_Centroid(wkb_geometry)) AS y
        FROM ap_pto
        WHERE art='HNR'
    '''))

    for r in rs:
        for lage_id in (r['dientzurdarstellungvon'] or []):
            if lage_id in lage:
                lage[lage_id]['x'] = r['x']
                lage[lage_id]['y'] = r['y']
                lage[lage_id]['xysrc'] = 'pto'

    log.debug('address: normalize gemarkung')

    gg = collections.defaultdict(set)

    for la in lage.itervalues():
        la.update(resolver.resolve_places(la))
        if 'gemarkung' in la:
            gg[la['gemarkung']].add(la['gemeinde'])

    gu = {}

    for gemarkung, gemeinde_list in gg.items():
        if len(gemeinde_list) < 2:
            continue
        for gemeinde in gemeinde_list:
            gu[gemarkung, gemeinde] = '%s (%s)' % (gemarkung, gemeinde.replace('Stadt ', ''))

    for la in lage.itervalues():
        if 'gemarkung' in la:
            k = la['gemarkung'], la['gemeinde']
            if k in gu:
                la['gemarkung_v'] = gu[k]
            else:
                la['gemarkung_v'] = la['gemarkung']

    log.debug('address: normalize strasse')

    hnr = collections.defaultdict(list)

    for la in lage.itervalues():
        if 'strasse' in la:
            la['strasse'] = re.sub(r'\s+', ' ', la['strasse'].strip())
            la['strasse_k'] = street_name_key(la['strasse'])
            la['hausnummer_n'] = int_hausnummer(la.get('hausnummer'))

    log.debug('address: writing')

    la_buf = []

    for la in lage.itervalues():
        if 'fs_ids' in la:
            for fs_id in la['fs_ids']:
                d = dict(la)
                d['fs_id'] = fs_id
                la_buf.append(d)

    db.insert(addr_index, la_buf)


def create():
    index_addr()
    index_gebaeude()

    log.time_start('address: vacuum')
    db.vacuum(addr_index)
    db.vacuum(geb_index)
    log.time_end('address: vacuum')


def check(force):
    htable.check([addr_index, geb_index], force, create)
