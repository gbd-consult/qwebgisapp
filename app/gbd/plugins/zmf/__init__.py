from gbd.core import plugin


class Plugin(plugin.Base):
    def command(self, cmd, request):

        enabled = request.user.can('ZMF')

        if cmd == 'check_enabled':
            return self.as_json({
                'enabled': enabled
            })

        if not enabled:
            return 403

    def run(self, request):
        return self.command(request.args.get('cmd'), request)
