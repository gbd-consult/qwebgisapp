#coding=utf8

"""Interface for Objektartengruppe:Personen- und Bestandsdaten."""

from gbd.core import db, log, util, debug
from gbd.plugins import alkis_resolver as resolver


def _anteil(r):
    if r['nenner'] is None:
        return None
    return '%d/%d' % (r['zaehler'] or 0, r['nenner'] or 0)


def get_all_person():
    rs = db.select('''
        SELECT
            gml_id,
            ort_post,
            ortsteil,
            postleitzahlpostzustellung,
            strasse,
            hausnummer,
            telefon
        FROM ax_anschrift
        WHERE endet IS NULL
    ''')

    addr = dict((r['gml_id'], util.strip_none(r)) for r in rs)
    pers = {}

    anrede = {
        1000: 'Frau',
        2000: 'Herr',
        3000: 'Firma'
    }

    rs = db.select('''
        SELECT
            gml_id,
            anrede,
            akademischergrad,
            geburtsdatum,
            nachnameoderfirma,
            vorname,
            hat
        FROM ax_person
        WHERE endet IS NULL        
    ''')

    for r in rs:
        ad = map(addr.get, r.pop('hat') or [])
        if ad:
            r['anschrift'] = ad[0]
        r['anrede'] = anrede.get(r['anrede'])
        r['akademischergrad'] = r['akademischergrad']
        pers[r['gml_id']] = util.strip_none(r)

    return pers


def get_all_buchungsblatt():
    persons = get_all_person()
    blatts = {}

    for r in db.select('SELECT * FROM ax_buchungsblatt WHERE endet IS NULL'):
        bb = {
            'gml_id': r['gml_id'],
            'buchungsblattkennzeichen': r['buchungsblattkennzeichen'],
            'buchungsblattnummermitbuchstabenerweiterung': r['buchungsblattnummermitbuchstabenerweiterung'],
            'owner': [],
        }
        bb.update(resolver.resolve_places(r))
        bb.update(resolver.attributes('ax_buchungsblatt', r))
        blatts[r['gml_id']] = util.strip_none(bb)

    for r in db.select('SELECT * FROM ax_namensnummer WHERE endet IS NULL'):
        if r['istbestandteilvon'] in blatts:
            ow = {
                'anteil': _anteil(r),
                'gml_id': r['gml_id'],
                'laufendenummernachdin1421': r['laufendenummernachdin1421'],
                'person': persons.get(r['benennt'])
            }
            ow.update(resolver.attributes('ax_namensnummer', r))
            blatts[r['istbestandteilvon']]['owner'].append(util.strip_none(ow))

    return blatts


def get_all_buchungsstelle():
    blatt = get_all_buchungsblatt()
    stelle = {}

    for r in db.select('SELECT * FROM ax_buchungsstelle WHERE endet IS NULL'):
        bb = blatt.get(r['istbestandteilvon'], {})
        st = {
            'gml_id': r['gml_id'],
            'beginnt': r['beginnt'],
            'endet': r['endet'],
            'laufendenummer': r['laufendenummer'],
            'an': r['an'],
            'owner': bb.get('owner', []),
            'buchungsblatt': dict((k, v) for k, v in bb.iteritems() if k != 'owner'),
            'anteil': _anteil(r),
        }
        st.update(resolver.resolve_places(r))
        st.update(resolver.attributes('ax_buchungsstelle', r))
        stelle[r['gml_id']] = util.strip_none(st)

    # resolve 'an' dependencies
    # Eine 'Buchungsstelle' verweist mit 'an' auf eine andere 'Buchungsstelle' auf einem anderen Buchungsblatt.
    # Die Buchungsstelle kann ein Recht (z.B. Erbbaurecht) oder einen Miteigentumsanteil 'an' der anderen Buchungsstelle haben
    # Die Relation zeigt stets vom begünstigten Recht zur belasteten Buchung
    # (z.B. Erbbaurecht hat ein Recht 'an' einem Grundstück).

    for r in stelle.itervalues():
        for id in r.get('an', []):
            if id is None:
                continue
            if id not in stelle:
                log.warning('invalid "an" reference: ' + str(id))
                continue
            target = stelle[id]
            if '_an' not in target:
                target['_an'] = []
            target['_an'].append(r['gml_id'])

    # for each 'buchungsstelle.gml_id', create a list of 'buchungsstelle'
    # + its 'an' dependants, recursively

    def _make_list(r, ids):
        if r['gml_id'] in ids:
            log.warning('circular dependency: ' + r['gml_id'])
            return []
        slist = [r]
        ids.add(r['gml_id'])
        for id in r.get('_an', []):
            slist.extend(_make_list(stelle[id], ids))
        return slist

    slist_map = {}
    for r in stelle.itervalues():
        slist_map[r['gml_id']] = _make_list(r, set())

    return slist_map
