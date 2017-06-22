<h1>Flurstück</h1>

<%
s = _.PropertySheet(flurstueck)

s.section('Basisdaten')

s.row('Flurnummer', s.get('flurnummer'))
s.row('Zähler', s.get('zaehler'))
s.row('Nenner', s.get('nenner'), default='-')
s.row('Fläche', s.area('area.total'))
s.row('ges. Gebäudefläche', s.area('area.gebaeude'))
s.row('Flurstücksfläche abz. Gebäudefläche', s.area('area.diff'))

s.section('Lage')

s.row('Gemeinde', s.get('gemeinde'))
s.row('Gemarkung', s.get('gemarkung'))

for lage in s.list('lage'):
    s.row('Adresse', lage, '{strasse} {hausnummer}')

s.section('Gebäudenachweis')

for geb in s.list('gebaeude'):
    s.row('Funktion', s.get(geb, 'gebaeudefunktion'))
    s.row('Fläche', s.area(geb, 'area'))
    s.line()


for bs in s.list('buchung'):

    s.section('Buchungssatz')

    s.row('Buchungsart', s.get(bs, 'buchungsart'))
    s.row('Anteil', s.get(bs, 'anteil'))

    for owner in s.list(bs, 'owner'):
        s.row('Eigentümer\n' + s.val(owner, 'anteil'), owner.get('person'), '''
            {vorname} {nachnameoderfirma}
            {anschrift.strasse} {anschrift.hausnummer}
            {anschrift.postleitzahlpostzustellung} {anschrift.ort_post}
        ''')


s.section('Nutzung')

for nu in s.list('nutzung'):
    h = s.get(nu, 'type')
    if s.get(nu, 'key') != s.get(nu, 'type'):
        h += ' (' + s.get(nu, 'key') + ')'
    s.row(h, s.area(nu, 'a_area'))
%>

${s.html}