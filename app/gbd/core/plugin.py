"""Plugin baseclass and utilities."""

import sys, imp, json, os, datetime

from gbd.core import config, log, debug


def json_encode_datetime(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat(' ')
    raise TypeError(repr(obj) + " is not JSON serializable")


class Base(object):
    def _encode(self, s):
        if not s:
            s = ''
        if not isinstance(s, str):
            return s.encode('utf8')
        return str(s)

    def as_text(self, s):
        return 200, [('Content-Type', 'text/plain; charset=utf-8')], self._encode(s)

    def as_html(self, s):
        return 200, [('Content-Type', 'text/html; charset=utf-8')], self._encode(s)

    def as_json(self, s):
        return 200, [('Content-Type', 'application/json; charset=utf-8')], json.dumps(s, indent=4, default=json_encode_datetime)

    def as_pdf(self, s):
        return 200, [('Content-Type', 'application/pdf; charset=utf-8')], self._encode(s)


def _load(name, plugins_root):
    if name not in sys.modules:
        path = config.app_root() + plugins_root
        fp, path, desc = imp.find_module(name, [path])
        imp.load_module(name, fp, path, desc)
    return sys.modules[name]


def load(name, plugins_root):
    try:
        return _load(name, plugins_root)
    except ImportError as e:
        log.debug('load FAILED', name, e)


def run(name, request):
    mod = sys.modules[name]
    if not hasattr(mod, 'Plugin'):
        log.error('Plugin class not found', name)
        return 404
    plugin = mod.Plugin()
    return plugin.run(request)


def load_and_run(name, request):
    if name not in config.get_list('plugins.active'):
        log.error('inactive plugin called', name)
        return 404

    if not load(name, '/gbd/plugins'):
        log.error('plugin not found', name)
        return 404

    return run(name, request)


def install(name, options=None):
    try:
        mod = _load(name, '/gbd/plugins')
    except ImportError as e:
        return
    if not hasattr(mod, 'install'):
        return
    return mod.install(options or {})


def topsort(graph):
    # https://en.wikipedia.org/wiki/Topological_sorting#Depth-first_search

    nodes = set(x for x, y in graph) | set(y for x, y in graph)
    res = []
    temp = set()

    def visit(n):
        if n in temp:
            raise ValueError, 'cyclic dependency: %s' % n
        if n not in res:
            temp.add(n)
            for x, y in graph:
                if x == n:
                    visit(y)
            temp.remove(n)
            res.append(n)

    while nodes:
        visit(nodes.pop())

    return res


def resolve(active_plugins, app_dir):
    """Create a list of required plugins."""

    pips = set()
    apts = set()
    seen = set()
    graph = set()
    plist = ['_core'] + list(active_plugins)

    while plist:

        p = plist.pop(0)

        if p in seen:
            continue

        seen.add(p)
        if p != '_core':
            graph.add((p, '_core'))

        conf = config.plugin_config(None if p == '_core' else p, app_dir)
        deps = conf.get('dependencies')
        if not deps:
            continue

        pips.update(deps.get('pip', []))
        apts.update(deps.get('apt', []))

        for dep in deps.get('gbd', []):
            d = str(dep)
            graph.add((p, d))
            plist.append(d)

    required = topsort(graph)
    required.remove('_core')

    return {
        'pips': pips,
        'apts': apts,
        'active': active_plugins,
        'required': required
    }
