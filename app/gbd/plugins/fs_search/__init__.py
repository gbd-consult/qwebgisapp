import re

from gbd.core import log, config, plugin, debug
from gbd.plugins import alkis_flurstueck as flurstueck


def _parse_fsnumber(s):
    """
        fsnumber input grammar:

        fsnumber = num [, num]*

        if uses_flurnummer = True:
            num =
                flurnummer (- (zaehler | zaehler / nenner) ) ?
                | zaehler / nenner ?

        if uses_flurnummer = False:
            num = zaehler (/ nenner ?) ?

    """
    formats = {
        True: [
            r'^(?P<flurnummer>\w+)$',
            r'^(?P<flurnummer>\w+)-(?P<zaehler>\w+)/?$',
            r'^(?P<flurnummer>\w+)-(?P<zaehler>\w+)/(?P<nenner>\w+)$',
            r'^(?P<zaehler>\w+)/$',
            r'^(?P<zaehler>\w+)/(?P<nenner>\w+)$',
        ],
        False: [
            r'^(?P<zaehler>\w+)/?$',
            r'^(?P<zaehler>\w+)/(?P<nenner>\w+)$',
        ]
    }

    s = re.sub(r'\s+', '', s)
    out = []
    fs = formats[flurstueck.uses_flurnummer()]

    for x in s.split(','):
        for f in fs:
            m = re.match(f, x)
            if m:
                out.append(m.groupdict())
                break
        else:
            log.warning('invalid input: ' + x)

    return out


class Plugin(plugin.Base):
    def command(self, cmd, request):

        enabled_owner = request.user.can('FS_SEARCH_VIEW_OWNER')
        enabled = enabled_owner or request.user.can('FS_SEARCH')

        if cmd == 'check_enabled':
            return {
                'enabled': enabled,
                'enabled_owner': enabled_owner
            }

        if not enabled:
            return 403

        if cmd == 'details':
            params = {}
            for k, v in request.args.items():
                if v.strip() and v.strip() != '0':
                    params[k] = v
            for r in flurstueck.find(params, limit=1):
                return r

        if cmd == 'gemarkungen':
            return flurstueck.list_gemarkung()

        if cmd == 'strassen':
            return flurstueck.list_strasse(request.args['gemarkungsnummer'])

        if cmd == 'strasse_all':
            return flurstueck.list_strasse_all()

        if cmd == 'find':
            if '_fsnumber' in request.args:
                s = request.args.pop('_fsnumber')
                if s.startswith('DE'):
                    request.args['gml_id'] = s
                else:
                    p = _parse_fsnumber(s)
                    if not p:
                        return []
                    request.args['_fsnumber'] = p

            if not enabled_owner:
                request.args.pop('nachnameoderfirma', '')
                request.args.pop('vorname', '')

            rs = list(flurstueck.find(
                    request.args,
                    limit=config.get('plugin:fs_search.limit') or 100,
                    columns=['gml_id', 'flurstueckskennzeichen', 'flurnummer', 'zaehler', 'nenner', 'gemarkung',
                             'wkt_geometry'],
                    sort=['gemarkung', 'flurstueckskennzeichen']
            ))
            log.info('found', len(rs))

            if 'geomonly' in request.args:
                rs = [
                    {'gml_id': r['gml_id'], 'wkt_geometry': r['wkt_geometry']}
                    for r in rs
                ]

            return rs

        if cmd == 'count':
            return {'count': flurstueck.count()}

    def run(self, request):
        return self.as_json(self.command(request.args.get('cmd'), request))
