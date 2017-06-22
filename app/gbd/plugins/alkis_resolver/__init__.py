"""Resolve ALKIS numeric keys into values."""

from gbd.core import db, debug
from gbd.core.util import f as _f
from . import index

_values = {}
_places = {}
_columns = {}


def _cols_for_table(table):
    if not _columns:
        rs = db.select(_f('SELECT DISTINCT stab, scol FROM {index.values_index}'))
        for r in rs:
            t = r['stab']
            if t not in _columns:
                _columns[t] = []
            _columns[t].append(r['scol'])

    return _columns.get(table, [])


def vmap(table, col):
    kk = (table, col)

    if kk not in _values:
        rs = db.select(_f('''
            SELECT skey, sval FROM {index.values_index} WHERE stab=%s AND scol=%s
        '''), [table, col])
        _values[kk] = dict((r['skey'], r['sval']) for r in rs)

    return _values[kk]


def resolve(table, col, key):
    return vmap(table, col).get(str(key))


def resolve_places(rec):
    if not _places:
        rs = db.select(_f('SELECT skey, sval FROM {index.places_index}'))
        for r in rs:
            _places[r['skey']] = r['sval']

    d = {}

    for name, fields in index.place_fields.items():
        key = ','.join('%s=%s' % (f, rec.get(f, '')) for f in fields)
        if key in _places:
            s = 'gemarkung' if name == 'gemarkungsnummer' else name
            d[s] = _places[key]
            d[s + '_id'] = rec[name]

    return d


def attributes(table, rec):
    ls = {}

    for name in _cols_for_table(table):
        if name not in rec:
            continue
        v = resolve(table, name, rec[name])
        if v is not None:
            ls[name] = v
            ls[name + '_id'] = rec[name]

    return ls


def alkis_definitions():
    return list(index.alkis_defs())


def nutzungsarten():
    return index.nutzung


def nutzung_key(type_id, rec):
    key = index.nutzung_keys.get(type_id, 'funktion')

    if rec.get(key):
        return {
            'key': rec[key],
            'key_id': rec[key + '_id'],
            'key_label': index.col_labels[key]
        }


def install(options):
    index.check(options.get('force'))
