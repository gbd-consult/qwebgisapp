# coding=utf8

"""Interface for Objektbereich:Tatsächliche Nutzung"""

import json

from gbd.core import db, htable, config, util, log, debug
from gbd.core.util import inline_format as _f
from gbd.plugins import alkis_resolver as resolver

main_index = htable.SCHEMA + '.nu_index'
all_index = htable.SCHEMA + '.nu_all'

fsx_temp = htable.SCHEMA + '.nu_fsx_temp'
min_area = 0.01


def as_json(s):
    if s is None:
        return None
    return json.dumps(s, ensure_ascii=False, indent=4, sort_keys=True)


def create_fsx_temp():
    schema = htable.SCHEMA
    srid = config.get('alkis.crs').split(':')[1]

    db.run(_f('''
        DROP TABLE IF EXISTS {fsx_temp} CASCADE;

        CREATE TABLE {fsx_temp} (
            id SERIAL PRIMARY KEY,
            gml_id CHARACTER VARYING,
            area DOUBLE PRECISION,
            a_area DOUBLE PRECISION,
            area_factor DOUBLE PRECISION,
            isvalid BOOLEAN,
            wkb_geometry geometry(GEOMETRY, {srid})
        );

        INSERT INTO {fsx_temp}(gml_id,area,a_area,wkb_geometry)
            SELECT
                gml_id,
                ST_Area(wkb_geometry),
                amtlicheflaeche,
                wkb_geometry
            FROM ax_flurstueck
            WHERE endet IS NULL
            ;

        DROP INDEX IF EXISTS {schema}.nu_fsx_gist;
        CREATE INDEX nu_fsx_gist ON {fsx_temp} USING GIST(wkb_geometry);

        DROP INDEX IF EXISTS {schema}.nu_fsx_gml;
        CREATE INDEX nu_fsx_gml ON {fsx_temp} USING BTREE(gml_id)
    '''))


def create_all_index():
    schema = htable.SCHEMA
    srid = config.get('alkis.crs').split(':')[1]

    db.run(_f('''
        DROP TABLE IF EXISTS {all_index} CASCADE;

        CREATE TABLE {all_index} (
            id SERIAL PRIMARY KEY,
            gml_id CHARACTER VARYING,
            type CHARACTER VARYING,
            type_id INTEGER,
            attributes CHARACTER VARYING,
            isvalid BOOLEAN,
            wkb_geometry geometry(GEOMETRY, {srid})
        )
    '''))

    data = []
    tables = db.tables()

    for type_id, table, type in resolver.nutzungsarten():
        if table not in tables:
            continue

        rs = db.select(_f('SELECT * FROM {table} WHERE endet IS NULL'))
        for r in rs:
            a = resolver.attributes(table, r)
            k = resolver.nutzung_key(type_id, a) or {'key': type, 'key_id': type_id, 'key_label': 'Typ'}
            a.update(k)

            data.append({
                'gml_id': r['gml_id'],
                'type': type,
                'type_id': type_id,
                'wkb_geometry': r['wkb_geometry'],
                'attributes': as_json(a)
            })

    db.insert(all_index, data)

    db.run(_f('''
        DROP INDEX IF EXISTS {schema}.nu_all_gist;
        CREATE INDEX nu_all_gist ON {all_index} USING GIST(wkb_geometry);

        DROP INDEX IF EXISTS {schema}.nu_all_gml;
        CREATE INDEX nu_all_gml ON {all_index} USING BTREE(gml_id)
    '''))


def validate():
    db.run(_f('UPDATE {all_index} SET isvalid = ST_IsValid(wkb_geometry)'))
    db.run(_f('UPDATE {fsx_temp} SET isvalid = ST_IsValid(wkb_geometry)'))

    for tab in all_index, fsx_temp:
        rs = db.select(_f('SELECT gml_id, ST_IsValidReason(wkb_geometry) AS reason FROM {tab} WHERE NOT isvalid'))
        for r in rs:
            log.warning(_f('gml_id={r[gml_id]} error={r[reason]}'))
        db.run(_f('DELETE FROM {tab} WHERE NOT isvalid'))


def create_main():
    srid = config.get('alkis.crs').split(':')[1]

    htable.create(main_index, _f('''
            id SERIAL PRIMARY KEY,
            fs_id CHARACTER VARYING,
            nu_id CHARACTER VARYING,
            type CHARACTER VARYING,
            type_id INTEGER,
            attributes CHARACTER VARYING,
            area float,
            a_area float,
            fs_wkb geometry(GEOMETRY, {srid}),
            nu_wkb geometry(GEOMETRY, {srid}),
            int_wkb geometry(GEOMETRY, {srid})
    '''))

    cnt = db.count(all_index)
    step = 1000

    with util.ProgressIndicator('nutzung: search', cnt) as pi:
        for n in range(0, cnt, step):
            n1 = n + step
            db.run(_f('''
                INSERT INTO {main_index} (fs_id, nu_id, type, type_id, attributes, fs_wkb, nu_wkb)
                    SELECT
                        fs.gml_id,
                        nu.gml_id,
                        nu.type,
                        nu.type_id,
                        nu.attributes,
                        fs.wkb_geometry,
                        nu.wkb_geometry
                    FROM
                        {all_index} AS nu,
                        {fsx_temp} AS fs
                    WHERE
                        {n} < nu.id AND nu.id <= {n1}
                        AND ST_Intersects(nu.wkb_geometry, fs.wkb_geometry)
            '''))
            pi.update(step)

    cnt = db.select_value(_f('SELECT MAX(id) + 1 FROM {main_index}'))
    step = 1000

    with util.ProgressIndicator('nutzung: intersections', cnt) as pi:
        for n in range(0, cnt, step):
            n1 = n + step
            db.run(_f('''
                UPDATE {main_index} AS nu
                    SET int_wkb = ST_Intersection(fs_wkb, nu_wkb)
                    WHERE {n} < nu.id AND nu.id <= {n1}
            '''))
            pi.update(step)

    with util.ProgressIndicator('nutzung: areas', cnt) as pi:
        for n in range(0, cnt, step):
            n1 = n + step
            db.run(_f('''
                UPDATE {main_index} AS nu
                    SET area = ST_Area(int_wkb)
                    WHERE {n} < nu.id AND nu.id <= {n1}
            '''))
            pi.update(step)

    cnt_all = db.select_value(_f('SELECT COUNT(*) FROM {main_index}'))
    cnt_nul = db.select_value(_f('SELECT COUNT(*) FROM {main_index} WHERE area < {min_area}'))

    log.info(_f('nutzung: {cnt_all} areas, {cnt_nul} empty'))

    if cnt_nul:
        db.run(_f('DELETE FROM {main_index} WHERE area < {min_area}'))

    # compute "amtliche" nutzung areas
    # see norbit/alkisimport/alkis-nutzung-und-klassifizierung.sql:445
    # nu[a_area] = nu[area] * (fs[a_area] / fs[area])

    log.info(_f('nutzung: correcting areas'))

    db.run(_f('''
        UPDATE {fsx_temp}
            SET area_factor = a_area / area
    '''))

    cnt = db.select_value(_f('SELECT MAX(id) + 1 FROM {main_index}'))
    step = 1000

    with util.ProgressIndicator('nutzung: correcting', cnt) as pi:
        for n in range(0, cnt, step):
            n1 = n + step
            db.run(_f('''
                UPDATE {main_index} AS nu
                    SET a_area = nu.area * fs.area_factor
                    FROM {fsx_temp} AS fs
                    WHERE {n} < nu.id AND nu.id <= {n1}
                        AND nu.fs_id = fs.gml_id
            '''))
            pi.update(step)

    cnt_all = db.select_value(_f('SELECT COUNT(*) FROM {main_index}'))
    cnt_nul = db.select_value(_f('SELECT COUNT(*) FROM {main_index} WHERE a_area < {min_area}'))

    log.info(_f('nutzung(corrected): {cnt_all} areas, {cnt_nul} empty'))

    if cnt_nul:
        db.run(_f('DELETE FROM {main_index} WHERE a_area < {min_area}'))


def create():
    log.info('nutzung: copying')
    create_fsx_temp()

    log.info('nutzung: preparing')
    create_all_index()

    log.info('nutzung: validating geometries')
    validate()

    create_main()

    db.run(_f('DROP TABLE IF EXISTS {fsx_temp} CASCADE'))

    log.time_start('nutzung: vacuum')
    db.vacuum(all_index)
    db.vacuum(main_index)
    log.time_end('nutzung: vacuum')


def check(force):
    htable.check([main_index, all_index], force, create)
