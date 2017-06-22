# coding=utf8

"""ALKIS addresses."""

import re

from gbd.core import db, util, htable, log, debug
from gbd.core.util import inline_format as _f
from gbd.plugins import alkis_resolver as resolver
from . import index

from index import addr_index, geb_index, street_name_key


def normalize_hausnummer(hn):
    # it's always "13 a" in alkis, but we allow 13a
    m = re.match(r'(\d+)(\D*)', str(hn).strip())
    if not m:
        return None
    if m.group(2):
        return m.group(1) + ' ' + m.group(2).strip()
    return m.group(1)


def add_filter(select, name, params):
    select.add_table(index.addr_index, name)

    for k, v in params.items():

        if select == 'gemeinde':
            select.add_column(name + '.gemeinde')
            select.add_where(db.star_like(name + '.gemeinde', v))

        elif k == 'strasse':

            select.add_column(name + '.strasse_k')
            select.add_where([name + '.strasse_k = %s', street_name_key(v)])

            hnr = params.get('hausnummer')

            if hnr == '*':
                select.add_column(name + '.hausnummer')
                select.add_where(name + '.hausnummer IS NOT NULL')
            elif hnr:
                select.add_column(name + '.hausnummer')
                select.add_where([name + '.hausnummer = %s', normalize_hausnummer(hnr)])
            else:
                # if no hausnummer, sort by hnr
                select.add_column(name + '.hausnummer_n')
                select.add_sort([name + '.hausnummer_n'])


def find(params, limit=None, sort=None):
    sel = db.select_statement()
    add_filter(sel, 'addr', params)
    sel.add_column('addr.*')
    if limit:
        sel.limit(limit)
    if sort:
        sel.add_sort(sort)
    return sel.fetch()


def find_one(params, sort=None):
    for a in find(params, limit=1, sort=sort):
        return a


def install(options):
    index.check(options.get('force'))
