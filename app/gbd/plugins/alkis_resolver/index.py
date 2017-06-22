# coding=utf8

import xml.etree.ElementTree as ElementTree
import re
import os
import zipfile

from gbd.core import db, shell, config, log, htable, util, debug
from gbd.core.util import inline_format as _f

values_index = htable.SCHEMA + '.rx_val_index'
places_index = htable.SCHEMA + '.rx_place_index'

place_tables = {
    'land': 'ax_bundesland',
    'regierungsbezirk': 'ax_regierungsbezirk',
    'kreis': 'ax_kreisregion',
    'gemeinde': 'ax_gemeinde',
    'gemarkungsnummer': 'ax_gemarkung',
    'bezirk': 'ax_buchungsblattbezirk',
    'stelle': 'ax_dienststelle',
}

place_fields = {
    'land': ['land'],
    'regierungsbezirk': ['regierungsbezirk', 'land'],
    'kreis': ['kreis', 'regierungsbezirk', 'land'],
    'gemeinde': ['gemeinde', 'kreis', 'regierungsbezirk', 'land'],
    'gemarkungsnummer': ['gemarkungsnummer', 'land'],
    'bezirk': ['bezirk', 'land'],
    'stelle': ['stelle', 'land']
}

col_labels = {
    'abbaugut': u'Abbaugut',
    'abmarkung_marke': u'Abmarkung (Marke)',
    'administrativefunktion': u'administrative Funktion',
    'advstandardmodell': u'AdV Standard Modell',
    'anlass': u'Anlass',
    'anlassdesprozesses': u'Anlass des Prozesses',
    'anrede': u'Anrede',
    'anzahlderstreckengleise': u'Anzahl der Streckengleise',
    'archaeologischertyp': u'archäologischer Typ',
    'art': u'Art',
    'artderaussparung': u'Art der Aussparung',
    'artderbebauung': u'Art der Bebauung',
    'artderfestlegung': u'Art der Festlegung',
    'artderflurstuecksgrenze': u'Art der Flurstücksgrenze',
    'artdergebietsgrenze': u'Art der Gebietsgrenze',
    'artdergelaendekante': u'Art der Geländekante',
    'artdergeripplinie': u'Art der Geripplinie',
    'artdergewaesserachse': u'Art der Gewässerachse',
    'artdernichtgelaendepunkte': u'Art der Nicht Geländepunkte',
    'artderrechtsgemeinschaft': u'Art der Rechtsgemeinschaft',
    'artderstrukturierung': u'Art der Strukturierung',
    'artderverbandsgemeinde': u'Art der Verbandsgemeinde',
    'artdesmarkantenpunktes': u'Art des Markanten Punktes',
    'artdesnullpunktes': u'Art des Nullpunktes',
    'artdespolders': u'Art des Polders',
    'ausgabeform': u'Ausgabeform',
    'ausgabemedium': u'Ausgabemedium',
    'bahnhofskategorie': u'Bahnhofskategorie',
    'bahnkategorie': u'Bahnkategorie',
    'bauart': u'Bauart',
    'bauweise': u'Bauweise',
    'bauwerksfunktion': u'Bauwerksfunktion',
    'bedeutung': u'Bedeutung',
    'befestigung': u'Befestigung',
    'bemerkungzurabmarkung': u'Bemerkung zur Abmarkung',
    'berechnungsmethode': u'Berechnungsmethode',
    'berechnungsmethodehoehenlinie': u'Berechnungsmethode Höhenlinie',
    'beschaffenheit': u'Beschaffenheit',
    'besondereartdergewaesserbegrenzung': u'besondere Art der Gewässerbegrenzung',
    'besonderebedeutung': u'besondere Bedeutung',
    'besonderefahrstreifen': u'besondere Fahrstreifen',
    'besonderefunktion': u'besondere Funktion',
    'bewuchs': u'Bewuchs',
    'bezeichnungart': u'Bezeichnung (Art)',
    'blattart': u'Blattart',
    'bodenart': u'Bodenart',
    'buchungsart': u'Buchungsart',
    'dachform': u'Dachform',
    'dachgeschossausbau': u'Dachgeschossausbau',
    'darstellung': u'Darstellung',
    'dateityp': u'Datei Typ',
    'datenerhebung': u'Datenerhebung',
    'datenformat': u'Datenformat',
    'description': u'Description',
    'dimension': u'Dimension',
    'eigentuemerart': u'Eigentümerart',
    'elektrifizierung': u'Elektrifizierung',
    'entstehungsartoderklimastufewasserverhaeltnisse': u'Entstehungsart oder Klimastufe/Wasserverhältnisse',
    'fahrbahntrennung': u'Fahrbahntrennung',
    'foerdergut': u'Fördergut',
    'funktion': u'Funktion',
    'funktionhgr': u'Funktion HGR',
    'funktionoa': u'Funktion OA',
    'gebaeudefunktion': u'Gebäudefunktion',
    'genauigkeitsstufe': u'Genauigkeitsstufe',
    'geologischestabilitaet': u'geologische Stabilität',
    'gnsstauglichkeit': u'GNSS Tauglichkeit',
    'gruendederausgesetztenabmarkung': u'Gründe der ausgesetzten Abmarkung',
    'grundwasserschwankung': u'Grundwasserschwankung',
    'grundwasserstand': u'Grundwasserstand',
    'guetedesbaugrundes': u'Güte des Baugrundes',
    'guetedesvermarkungstraegers': u'Güte des Vermarkungsträgers',
    'hafenkategorie': u'Hafenkategorie',
    'hierarchiestufe3d': u'Hierarchiestufe3D',
    'hoehenstabilitaetauswiederholungsmessungen': u'Höhenstabilität aus Wiederholungsmessungen',
    'horizontaleausrichtung': u'horizontale Ausrichtung',
    'horizontfreiheit': u'Horizontfreiheit',
    'hydrologischesmerkmal': u'hydrologisches Merkmal',
    'identifikation': u'Identifikation',
    'impliziteloeschungderreservierung': u'implizite Löschung der Reservierung',
    'internationalebedeutung': u'internationale Bedeutung',
    'klassifizierung': u'Klassifizierung',
    'klassifizierunggr': u'Klassifizierung GR',
    'klassifizierungobg': u'Klassifizierung OBG',
    'konstruktionsmerkmalbauart': u'Konstruktionsmerkmal Bauart',
    'koordinatenstatus': u'Koordinatenstatus',
    'kulturart': u'Kulturart',
    'lagergut': u'Lagergut',
    'lagezurerdoberflaeche': u'Lage zur Erdoberfläche',
    'lagezuroberflaeche': u'Lage zur Oberfläche',
    'landschaftstyp': u'Landschaftstyp',
    'letzteabgabeart': u'Letzte Abgabe Art',
    'levelofdetail': u'level of detail',
    'liniendarstellung': u'Liniendarstellung',
    'markierung': u'Markierung',
    'merkmal': u'Merkmal',
    'messmethode': u'Messmethode',
    'nutzung': u'Nutzung',
    'oberflaechenmaterial': u'Oberflächenmaterial',
    'ordnung': u'Ordnung',
    'primaerenergie': u'Primärenergie',
    'produkt': u'Produkt',
    'punktart': u'Punktart',
    'punktstabilitaet': u'Punktstabilität',
    'punktvermarkung': u'Punktvermarkung',
    'qualitaetsangaben': u'Qualitätsangaben',
    'rechtszustand': u'Rechtszustand',
    'reservierungsart': u'Reservierungsart',
    'schifffahrtskategorie': u'Schifffahrtskategorie',
    'schwerestatus': u'Schwerestatus',
    'schweresystem': u'Schweresystem',
    'selektionsmassstab': u'Selektionsmassstab',
    'skizzenart': u'Skizzenart',
    'sonstigeangaben': u'Sonstige Angaben',
    'speicherinhalt': u'Speicherinhalt',
    'sportart': u'Sportart',
    'spurweite': u'Spurweite',
    'stellenart': u'Stellenart',
    'tidemerkmal': u'Tidemerkmal',
    'topographieundumwelt': u'Topographie und Umwelt',
    'ueberschriftimfortfuehrungsnachweis': u'Überschrift im Fortführungsnachweis',
    'ursprung': u'Ursprung',
    'vegetationsmerkmal': u'Vegetationsmerkmal',
    'verarbeitungsart': u'Verarbeitungsart',
    'verkehrsbedeutunginneroertlich': u'Verkehrsbedeutung Innerörtlich',
    'verkehrsbedeutungueberoertlich': u'Verkehrsbedeutung Ueberörtlich',
    'vermarkung_marke': u'Vermarkung (Marke)',
    'vermutetehoehenstabilitaet': u'Vermutete Höhenstabilität',
    'vertikaleausrichtung': u'Vertikale Ausrichtung',
    'vertrauenswuerdigkeit': u'Vertraünswürdigkeit',
    'verwendeteinstanzenthemen': u'Verwendete Instanzenthemen',
    'verwendeteobjekte': u'Verwendete Objekte',
    'verwendetethemen': u'Verwendete Themen',
    'weiteregebaeudefunktion': u'Weitere Gebäudefunktion',
    'wertigkeit': u'Wertigkeit',
    'widmung': u'Widmung',
    'wirtschaftsart': u'Wirtschaftsart',
    'zone': u'Zone',
    'zugriffsartfortfuehrungsanlass': u'Zugriffsart Fortführungsanlass',
    'zugriffsartproduktkennungbenutzung': u'Zugriffsart Produktkennung Benutzung',
    'zugriffsartproduktkennungfuehrung': u'Zugriffsart Produktkennung Führung',
    'zustand': u'Zustand',
    'zustandsstufeoderbodenstufe': u'Zustandsstufe oder Bodenstufe',

    'land': u'Bundesland',
    'regierungsbezirk': u'Regierungsbezirk',
    'kreis': u'Kreis',
    'gemeinde': u'Gemeinde',
    'bezirk': u'Buchungsblattbezirk',
    'stelle': u'Dienststelle'
}

# s. ALKIS_OK_6_0.html#_3DFA354A0193
# kennung - table - label
nutzung = [
    (41001, 'ax_wohnbauflaeche', u'Wohnbaufläche'),
    (41002, 'ax_industrieundgewerbeflaeche', u'Industrie- und Gewerbefläche'),
    (41003, 'ax_halde', u'Halde'),
    (41004, 'ax_bergbaubetrieb', u'Bergbaubetrieb'),
    (41005, 'ax_tagebaugrubesteinbruch', u'Tagebau, Grube, Steinbruch'),
    (41006, 'ax_flaechegemischternutzung', u'Fläche gemischter Nutzung'),
    (41007, 'ax_flaechebesondererfunktionalerpraegung', u'Fläche besonderer funktionaler Prägung'),
    (41008, 'ax_sportfreizeitunderholungsflaeche', u'Sport-, Freizeit- und Erholungsfläche'),
    (41009, 'ax_friedhof', u'Friedhof'),
    (41010, 'ax_siedlungsflaeche', u'Siedlungsfläche'),
    (42001, 'ax_strassenverkehr', u'Straßenverkehr'),
    (42002, 'ax_strasse', u'Straße'),
    (42003, 'ax_strassenachse', u'Straßenachse'),
    (42005, 'ax_fahrbahnachse', u'Fahrbahnachse'),
    (42006, 'ax_weg', u'Weg'),
    (42008, 'ax_fahrwegachse', u'Fahrwegachse'),
    (42009, 'ax_platz', u'Platz'),
    (42010, 'ax_bahnverkehr', u'Bahnverkehr'),
    (42014, 'ax_bahnstrecke', u'Bahnstrecke'),
    (42015, 'ax_flugverkehr', u'Flugverkehr'),
    (42016, 'ax_schiffsverkehr', u'Schiffsverkehr'),
    (43001, 'ax_landwirtschaft', u'Landwirtschaft'),
    (43002, 'ax_wald', u'Wald'),
    (43003, 'ax_gehoelz', u'Gehölz'),
    (43004, 'ax_heide', u'Heide'),
    (43005, 'ax_moor', u'Moor'),
    (43006, 'ax_sumpf', u'Sumpf'),
    (43007, 'ax_unlandvegetationsloseflaeche', u'Unland/Vegetationslose Fläche'),
    (43008, 'ax_flaechezurzeitunbestimmbar', u'Fläche zur Zeit unbestimmbar'),
    (44001, 'ax_fliessgewaesser', u'Fließgewässer'),
    (44002, 'ax_wasserlauf', u'Wasserlauf'),
    (44003, 'ax_kanal', u'Kanal'),
    (44004, 'ax_gewaesserachse', u'Gewässerachse'),
    (44005, 'ax_hafenbecken', u'Hafenbecken'),
    (44006, 'ax_stehendesgewaesser', u'Stehendes Gewässer'),
    (44007, 'ax_meer', u'Meer'),
]

# for other tables it's assumed to be 'funktion'

nutzung_keys = {
    41003: 'lagergut',
    41004: 'abbaugut',
    41005: 'abbaugut',
    43001: 'vegetationsmerkmal',
    43002: 'vegetationsmerkmal',
    43003: 'vegetationsmerkmal',
}


def _parse_defs_file(fp):
    xml = fp.read()
    xml = re.sub(r'\b(xmlns|codeSpace)=".*?"', '', xml)
    doc = ElementTree.XML(xml)

    """
        Examples of tags:

        Normal prop:

        <PropertyDefinition gml:id="S.084.0120.07.783">
          <identifier>urn:x-ogc:def:propertyType:GeoInfoDok::adv:6.0:AX_Buchungsstelle:beschreibungDesSondereigentums</identifier>
          <name>beschreibungDesSondereigentums</name>
          <cardinality>0..1</cardinality>
          <valueTypeName>CharacterString</valueTypeName>
          <type>attribute</type>
        </PropertyDefinition>

        Reference:

        <PropertyDefinition gml:id="G.344">
            <identifier>urn:x-ogc:def:propertyType:GeoInfoDok::adv:6.0:AX_Flurstueck:istGebucht</identifier>
            <name>istGebucht</name>
            <cardinality>1</cardinality>
            <valueTypeRef xlink:href="urn:x-ogc:def:featureType:GeoInfoDok::adv:6.0:AX_Buchungsstelle"/>
            <type>associationRole</type>
        </PropertyDefinition>

        ListedValue:

        <ListedValueDefinition gml:id="S.084.0120.08.528_S.084.0120.08.532">
          <identifier>urn:x-ogc:def:propertyType:GeoInfoDok::adv:6.0:AX_Wald:vegetationsmerkmal:1100</identifier>
          <name>Laubholz</name>
        </ListedValueDefinition>

    """

    def node_to_dict(node):
        d = {'tag': node.tag}

        for sub in node:
            if sub.tag == 'dictionaryEntry':
                continue
            if sub.tag in ('supertypeRef', 'valueTypeRef'):
                # for ref tags the value is their (only) href attr
                d[sub.tag] = sub.attrib.values()[0]
            elif sub.text:
                d[sub.tag] = sub.text

        for k, v in d.items():
            m = re.match(r'urn:x-ogc:def:.+?:GeoInfoDok::adv:[^:]+:(.+)', v)
            if m:
                d[k] = m.group(1).lower()

        return d

    for node in doc.findall('.//PropertyDefinition'):
        yield node_to_dict(node)

    for node in doc.findall('.//ListedValueDefinition'):
        yield node_to_dict(node)


def alkis_defs():
    # see http://www.adv-online.de/AAA-Modell/Dokumente-der-GeoInfoDok/GeoInfoDok-6.0/

    nas_url = 'http://www.adv-online.de/AAA-Modell/Dokumente-der-GeoInfoDok/GeoInfoDok-6.0/binarywriterservlet?imgUid=b2c23fd2-1153-911a-3b21-718a438ad1b2&uBasVariant=11111111-1111-1111-1111-111111111111&isDownload=true'
    nas_path = config.app_root() + '/../NAS_6.0.zip'

    if not os.path.exists(nas_path):
        log.info('downloading the ALKIS/NAS archive')
        # they require a "browser" for downloads
        ua = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/534.30 (KHTML, like Gecko) Chrome/12.0.742.112 Safari/534.30'
        shell.run(_f('curl -s -A "{ua}" -o "{nas_path}" "{nas_url}"'))

    zf = zipfile.ZipFile(nas_path)
    for fi in zf.infolist():
        # we only need Axxx.definitions.xml from the definitions folder
        if re.search(r'/definitions/A.+?.definitions.xml', fi.filename):
            for d in _parse_defs_file(zf.open(fi)):
                yield d


def create_values_index(defs):
    htable.create(values_index, '''
            id SERIAL PRIMARY KEY,
            stab CHARACTER VARYING,
            scol CHARACTER VARYING,
            skey CHARACTER VARYING,
            sval CHARACTER VARYING
    ''')

    values = []

    for d in defs:
        # e.g.  {'identifier': 'ax_polder:artdespolders:1000', 'name': 'Sommerpolder', 'tag': 'ListedValueDefinition'},
        if d['tag'] == 'ListedValueDefinition':
            s = d['identifier'].split(':')
            values.append({
                'stab': s[0],
                'scol': s[1],
                'skey': s[2],
                'sval': d['name'],
            })

    db.insert(values_index, values)


def create_places_index():
    htable.create(places_index, '''
            id SERIAL PRIMARY KEY,
            stab CHARACTER VARYING,
            skey CHARACTER VARYING,
            sid  CHARACTER VARYING,
            sval CHARACTER VARYING
    ''')

    idx = []

    for key, table in place_tables.items():
        fields = place_fields[key]
        fs = ','.join(fields)

        for r in db.select(_f('SELECT bezeichnung, {fs} FROM {table}')):
            idx.append({
                'stab': table,
                'skey': ','.join('%s=%s' % (f, r[f]) for f in fields),
                'sid': r[fields[0]],
                'sval': r['bezeichnung']

            })

    db.insert(places_index, idx)


indexes = [values_index, places_index]


def create():
    defs = list(alkis_defs())

    log.info('resolver: values')
    create_values_index(defs)

    log.info('resolver: places')
    create_places_index()

    for t in indexes:
        db.vacuum(t)


def check(force):
    htable.check(indexes, force, create)
