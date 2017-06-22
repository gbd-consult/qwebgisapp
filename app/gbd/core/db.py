"""Postgresql wrappers and helpers."""

import psycopg2
from contextlib import contextmanager

from gbd.core import config, util, log, debug

psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)

_connection = None

Error = psycopg2.Error


def connect(**kwargs):
    global _connection

    if _connection:
        return _connection

    p = {}
    p.update(config.get_all('db'))
    p.update(kwargs)

    if kwargs.get('admin') and 'admin_user' in p:
        p['user'] = p['admin_user']
        p['password'] = p['admin_password']

    _connection = psycopg2.connect(
            database=p['database'],
            user=p['user'],
            password=p['password'],
            host=p['host'],
            port=p['port'],
            application_name='QWC4GBDClients'
    )

    _connection.autocommit = True
    return _connection


def disconnect():
    global _connection

    if _connection:
        _connection.close()
        _connection = None


def cursor():
    return connect().cursor()


def select(sql, params=None):
    cur = cursor()

    try:
        cur.execute(sql, params)
    except psycopg2.Error:
        log.debug(sql)
        raise

    cnames = [c.name for c in cur.description]

    try:
        for rec in cur:
            yield dict(zip(cnames, rec))

    finally:
        cur.close()


def select_row(sql, params=None):
    for r in select(sql, params):
        return r


def select_value(sql, params=None):
    r = select_row(sql, params)
    return r.values()[0] if r else None


def run(sql, params=None):
    cur = cursor()

    try:
        cur.execute(sql, params)
        return cur.connection
    except psycopg2.Error:
        log.debug(sql)
        raise
    finally:
        cur.close()


def run_many(stmts):
    cur = cursor()

    if isinstance(stmts, basestring):
        stmts = stmts.split(';')

    for s in stmts:
        if isinstance(s, basestring):
            s = s.strip()
            if not s:
                continue
            params = []
        else:
            s, params = s
        try:
            cur.execute(s, params)
        except psycopg2.Error:
            log.debug(s)
            raise

    return cur.connection


@contextmanager
def transaction():
    run('BEGIN')
    try:
        yield
    except:
        run('ROLLBACK')
        raise
    run('COMMIT')


def vacuum(table):
    return run('VACUUM ANALYZE %s' % table)


####

class SelectStatement(object):
    """A dead-simple SELECT builder/runner."""

    def __init__(self):
        self._columns = []
        self._tables = []
        self._joins = []
        self._where = []
        self._sort = []
        self._limit = None
        self._distinct = False
        self._params = []
        self._options = ''

    def tables(self, *args):
        self._tables = []
        for a in args:
            self.add_table(a)
        return self

    def add_table(self, name, alias=None):
        if alias:
            name += ' AS ' + alias
        self._tables.append(name)
        return self

    def columns(self, *args):
        self._columns = []
        for a in args:
            self.add_column(a)
        return self

    def add_column(self, name):
        self._columns.append(name)
        return self

    def add_geometry_for(self, col='wkb_geometry'):
        self.add_column('ST_AsText(%s) AS _wkt' % col)
        self.add_column('ST_X(ST_Centroid(%s)) AS _x' % col)
        self.add_column('ST_Y(ST_Centroid(%s)) AS _y' % col)
        return self

    def join(self, *args):
        self._joins = []
        for a in args:
            self.add_join(a)
        return self

    def add_join(self, expr):
        self._joins.append(expr)
        return self

    def where(self, *args):
        self._where = []
        self._params = []
        for a in args:
            self.add_where(a)
        return self

    def add_where(self, cond, *args):
        if isinstance(cond, (tuple, list)):
            args = cond[1:]
            cond = cond[0]
        self._where.append(cond)
        self._params.extend(args)
        return self

    def options(self, opts):
        self._options = opts
        return self

    def distinct(self, val):
        self._distinct = val
        return self

    def add_sort(self, columns):
        self._sort.extend(columns)
        return self

    def limit(self, limit, offset=None):
        self._limit = [int(limit), int(offset) if offset else None]
        return self

    def merge(self, other):
        self._tables.extend(other._tables)
        self._columns.extend(other._columns)
        self._where.extend(other._where)
        self._params.extend(other._params)
        return self

    def sql(self):

        def _dedupe(ls):
            seen, r = set(), []
            for x in ls:
                if x not in seen:
                    seen.add(x)
                    r.append(x)
            return r

        def _clist(s):
            if isinstance(s, basestring):
                return s
            return ',\n'.join(_dedupe(s))

        sql = [
            'SELECT' + (' DISTINCT' if self._distinct else ''),
            _clist(self._columns) if self._columns else '*',
        ]

        if self._tables:
            sql.append('FROM')
            sql.append(_clist(self._tables))

        if self._joins:
            sql.append(_clist(self._joins))

        if self._where:
            sql.append('WHERE')
            sql.append('\nAND '.join(_dedupe(self._where)))

        if self._sort:
            sql.append('ORDER BY ' + _clist(self._sort))

        if self._limit:
            limit, offset = self._limit
            s = 'LIMIT %d' % limit
            if offset is not None:
                s += ' OFFSET %d' % offset
            sql.append(s)

        if self._options:
            sql.append(self._options)

        return '\n'.join(sql)

    def fetch(self):
        for rec in select(self.sql(), self._params):
            yield rec

    def fetch_one(self):
        for rec in select(self.sql(), self._params):
            return rec


def tables(schema=None):
    sel = select_statement().tables(
            'information_schema.tables'
    ).columns(
            'table_name'
    ).where(
            ['table_schema=%s', schema or 'public']
    )
    return [r['table_name'] for r in sel.fetch()]


def columns(table):
    sel = select_statement().tables(
            'information_schema.columns'
    ).columns(
            'column_name',
            'data_type'
    )

    if '.' in table:
        schema, table = table.split('.')
        sel.add_where(['table_schema=%s', schema])

    sel.add_where(['table_name=%s', table])

    return dict((r['column_name'], r['data_type']) for r in sel.fetch())


def exists(table, column=None):
    sel = select_statement()
    sel.add_column('COUNT(*) AS c')
    sel.tables('information_schema.' + ('columns' if column else 'tables'))

    if '.' in table:
        schema, table = table.split('.')
        sel.add_where(['table_schema=%s', schema])
    sel.add_where(['table_name=%s', table])

    if column:
        sel.add_where(['column_name=%s', column])

    for r in sel.fetch():
        return int(r['c'])


def all_columns(table, alias=None):
    """alias all columns with a table name for Select."""

    alias = alias or table
    return ', '.join(
            '%s.%s AS "%s.%s"' % (alias, col, alias, col)
            for col in columns(table)
    )


def star_like(key, value):
    """Replace the meta-char * with %."""

    value = value.replace('%', '').replace('_', '').replace('*', '%')

    if '%' in value:
        return [key + ' LIKE %s', value]
    return [key + '=%s', value]


def select_statement():
    return SelectStatement()


def load(tables, where, **kwargs):
    return list(select_statement(kwargs).tables(tables).where(where).fetch())


def load_one(tables, where):
    return select_statement().tables(tables).where(where).fetch_one()


def insert(table, data):
    all_cols = columns(table)

    for ds in util.chunked(data, 127):
        keys = set(k for rec in ds for k in rec)
        keys = sorted(keys.intersection(all_cols))

        cols = ','.join('"%s"' % k for k in keys)
        vals = '(' + ','.join(['%s'] * len(keys)) + ')'
        vals = ',\n'.join([vals] * len(ds))

        params = [rec.get(k) for rec in ds for k in keys]

        sql = 'INSERT INTO %s (%s) VALUES\n%s' % (table, cols, vals)
        run(sql, params)


def count(table):
    for r in select('SELECT COUNT(*) AS cnt FROM %s' % table):
        return r['cnt']


def update(table, values, where):
    upd = []
    params = []

    for k, v in values.items():
        if isinstance(v, (list, tuple)):
            fmt, val = v
        else:
            fmt, val = '%s', v

        upd.append('"%s"=%s' % (k, fmt))
        params.append(v)

    sql = 'UPDATE %s SET %s' % (table, ', '.join(upd))
    if where:
        fmt, val = where
        sql += ' WHERE ' + fmt
        params.append(val)

    run(sql, params)
