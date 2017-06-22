from gbd.core import plugin, util, config, gis, qgis, debug
from gbd.plugins import alkis_flurstueck as flurstueck

class Plugin(plugin.Base):

    def fs_area(self, fs):
        area = {
            'total': fs.get('amtlicheflaeche', 0)
        }

        geb_area = 0
        for geb in fs.get('gebaeude', []):
            geb_area += geb.get('grundflaeche', 0)

        if fs['gebaeude_area']:
            area['gebaeude'] = fs['gebaeude_area']
            area['diff'] = area['total'] - fs['gebaeude_area']

        return area


    def command(self, cmd, request):

        enabled_owner = request.user.can('FS_SEARCH_VIEW_OWNER') or request.user.can('SEARCH_STRASSENBAU')
        enabled = enabled_owner or request.user.can('FS_SEARCH')

        if not enabled:
            return 403

        fs = flurstueck.find_one({'gml_id': request.args['gml_id']})

        if not enabled_owner:
            fs.pop('buchung', '')

        fs['area'] = self.fs_area(fs)

        if cmd == 'infobox':
            tpl = config.get_path('plugin:fs_details.infobox_template', 'gbd/plugins/fs_details/infobox.html.tpl')
            html = util.render_template(tpl, {'flurstueck': fs})
            return self.as_json({'html': html})

        if cmd == 'info':
            return self.as_json(fs)

        if cmd == 'print':
            tpl = config.get_path('plugin:fs_details.print_template', 'gbd/plugins/fs_details/print_template.qgs')
            prj = qgis.project(tpl)

            # render all ComposerLabels als mako templates

            for c in prj.findall('.//ComposerLabel'):
                txt = util.render_from_string(c.attrib.get('labelText', ''), {'flurstueck': fs})
                c.attrib['labelText'] = txt.decode('utf8')

            for c in prj.findall('.//ComposerHtml'):
                txt = util.render_from_string(c.attrib.get('html', ''), {'flurstueck': fs})
                c.attrib['html'] = txt.decode('utf8')

            # make sure the fs is in the middle
            # @TODO this doesn't work properly
            # request.body['map0:extent'] = gis.bounds(fs['wkt_geometry'], expand=2)

            src = qgis.project(request.body['map'])
            uid = src.print_to_pdf(prj.find('.//Composer'), request.body)

            return self.as_json({'uid': uid})

    def run(self, request):
        return self.command(request.args.get('cmd'), request)
