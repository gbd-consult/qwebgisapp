import re

from gbd.core import plugin, config, qgis, debug


def do_temp_file(request, mime):
    uid = request.args['uid']
    if re.search(r'\W', uid):
        raise ValueError('invalid uid ' + uid)
    path = config.get('paths.temp') + '/' + uid + '.' + mime[-3:]
    with open(path) as fp:
        return 200, [('Content-Type', mime + '; charset=utf-8')], fp.read()


class Plugin(plugin.Base):
    def command(self, cmd, request):

        if cmd == 'print':
            src = qgis.project(request.body['map'])
            uid = src.print_to_pdf(None, request.body)
            return self.as_json({'uid': uid})

        if cmd == 'pdf':
            return do_temp_file(request, 'application/pdf')

    def run(self, request):
        return self.command(request.args.get('cmd'), request)
