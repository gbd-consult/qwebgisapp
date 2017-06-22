from gbd.core import plugin, util, config, gis, qgis, debug
from gbd.plugins import alkis_flurstueck as flurstueck

class Plugin(plugin.Base):

    def command(self, cmd, request):

        if cmd == 'print':
            tpl = config.get_path('plugin:selection.print_template', 'gbd/plugins/selection/print_template.qgs')
            prj = qgis.project(tpl)

            for c in prj.findall('.//ComposerHtml'):
                c.attrib['html'] = c.attrib['html'].replace('${html}', request.body['html'])

            src = qgis.project(request.body['map'])
            uid = src.print_to_pdf(prj.find('.//Composer'), request.body)

            return self.as_json({'uid': uid})

    def run(self, request):
        return self.command(request.args.get('cmd'), request)
