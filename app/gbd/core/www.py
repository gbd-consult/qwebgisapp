"""Web frontend for the app."""

import os, random, json, urlparse, urllib, re, zlib, time
import requests
from flup.server.fcgi import WSGIServer

from gbd.core import log, config, plugin, debug, qgis, util, auth


def render_login_block(request):
    if not auth.enabled():
        return ''
    return util.render_template(
            config.get_path('www.login_template', 'gbd/core/login.html.tpl'),
            {
                'status': 'not_logged_in' if request.user.is_guest() else 'logged_in',
                'request': request
            })


def do_index(request):
    """Render the index page."""

    projects = [
        (name, path)
        for name, path in config.all_projects()
        if request.user.can_open(path)
        ]
    login_block = render_login_block(request)

    html = util.render_template(
            config.get_path('www.index_template', 'gbd/core/index.html.tpl'),
            locals())

    return 200, [('Content-Type', 'text/html; charset=utf-8')], html


def do_map(request):
    """Render the map page (qgiswebclient)."""

    dev_mode = config.get('app.dev_mode')

    def _randomize(url):
        if dev_mode:
            return url + '?_rnd=' + str(random.randint(0, 100000))
        return url

    app_root = config.app_root()

    p = config.get_path('www.global_options', 'gbd/www/GlobalOptions.js')
    with open(p) as fp:
        global_options = fp.read()

    qwc_root = config.get_path('www.qwc_root', '/QGIS-Web-Client/site')
    rand = str(random.randint(0, 100000))

    js_options = {
        'project.authid': qgis.project(request.args['map']).crs('authid'),
        'project.map': request.args['map']
    }

    plugins_js = []
    plugins_css = []

    for p in config.get_list('plugins.required'):

        src = app_root + '/gbd/plugins/' + p

        if os.path.exists(src + '/main.js'):
            plugins_js.append(_randomize('/gbd/plugins/' + p + '/main.js'))

        if os.path.exists(src + '/main.css'):
            plugins_css.append(_randomize('/gbd/plugins/' + p + '/main.css'))

        for k, v in config.plugin_js_options(p).items():
            js_options[p + '.' + k] = v

    user_js = []
    user_css = []

    for p in config.get_list('www.user_assets'):
        if p.endswith('.js'):
            user_js.append(_randomize(p))
        if p.endswith('.css'):
            user_css.append(_randomize(p))

    qwc_components = ['Translations', 'GetUrlParams', 'TriStateTree', 'GUI',
                      'QGISExtensions', 'GeoNamesSearchCombo', 'FeatureInfoDisplay', 'LegendAndMetadataDisplay',
                      'DXFExport', 'WebgisInit']

    js_options = json.dumps(js_options, indent=4)
    login_block = render_login_block(request)

    html = util.render_template(
            config.get_path('www.map_template', 'gbd/core/map.html.tpl'),
            locals())

    return 200, [('Content-Type', 'text/html; charset=utf-8')], html


def do_plugin(request):
    return plugin.load_and_run(request.args['plugin'], request)


def do_temp_file(uid, mime):
    if re.search(r'\W', uid):
        raise ValueError('invalid uid ' + uid)
    path = config.get('paths.temp') + '/' + uid + '.' + mime[-3:]
    with open(path) as fp:
        return 200, [('Content-Type', mime + '; charset=utf-8')], fp.read()


def unauthorized_project_access():
    url = config.get('auth.error_redirect')
    if url:
        return 302, [('Location', str(url))], ''
    html = util.render_template(
            config.get_path('www.error_template', 'gbd/core/error.html.tpl'),
            {'error': 403})
    return 403, [('Content-Type', 'text/html; charset=utf-8')], html


######

http_status = {
    100: '100 Continue',
    101: '101 Switching Protocols',
    200: '200 OK',
    201: '201 Created',
    202: '202 Accepted',
    203: '203 Non-Authoritative Information',
    204: '204 No Content',
    205: '205 Reset Content',
    206: '206 Partial Content',
    300: '300 Multiple Choices',
    301: '301 Moved Permanently',
    302: '302 Found',
    303: '303 See Other',
    304: '304 Not Modified',
    305: '305 Use Proxy',
    307: '307 Temporary Redirect',
    400: '400 Bad Request',
    401: '401 Unauthorized',
    402: '402 Payment Required',
    403: '403 Forbidden',
    404: '404 Not Found',
    405: '405 Method Not Allowed',
    406: '406 Not Acceptable',
    407: '407 Proxy Authentication Required',
    408: '408 Request Timeout',
    409: '409 Conflict',
    410: '410 Gone',
    411: '411 Length Required',
    412: '412 Precondition Failed',
    413: '413 Request Entity Too Large',
    414: '414 Request-URI Too Long',
    415: '415 Unsupported Media Type',
    416: '416 Requested Range Not Satisfiable',
    417: '417 Expectation Failed',
    500: '500 Internal Server Error',
    501: '501 Not Implemented',
    502: '502 Bad Gateway',
    503: '503 Service Unavailable',
    504: '504 Gateway Timeout',
    505: '505 HTTP Version Not Supported',
}


def dispatch(request):
    if 'map' in request.args and not request.user.can_open(request.args['map']):
        return unauthorized_project_access()

    if request.environ.get('PATH_INFO', '').startswith('/proxy'):
        m = re.match(r'/proxy/(https?)/(.+)', request.environ['REQUEST_URI'])
        if not m:
            raise ValueError('invalid proxy url format')

        url = m.group(1) + '://' + m.group(2)
        p = urlparse.urlparse(url)

        log.debug('PROXY_START', url)
        ts = time.time()
        try:
            r = requests.get(url,
                             headers={'accept-encoding': 'identity'},
                             verify=False,
                             stream=False,
                             timeout=(5, 5))
        except:
            log.error('PROXY_ERROR: http error')
            return 400

        ts = time.time() - ts

        if r.status_code != 200:
            log.error('PROXY_ERROR: server error', r.status_code, r.content)
            return 400

        h = dict((k.lower(), v) for k, v in r.headers.items())
        if h.get('transfer-encoding') == 'chunked':
            h.pop('transfer-encoding')

        c = r.content.strip()
        if c.startswith('<'):
            c = re.sub(
                    p.scheme + '://' + p.netloc,
                    'http://' + request.environ['SERVER_NAME'] + '/proxy/' + p.scheme + '/' + p.netloc,
                    c)

        log.debug('PROXY_END', round(ts, 2))

        return 200, h.items(), c

    if request.environ.get('PATH_INFO', '').startswith('/_gbd_.cgi'):

        if request.method == 'POST':
            args = request.body
        else:
            args = request.args

        headers, content = qgis.call_server(args)

        return 200, headers.items(), content

    if 'plugin' in request.args:
        return do_plugin(request)

    if 'map' in request.args:
        return do_map(request)

    m = re.search(r'^/download/(\w+).pdf$', request.environ.get('PATH_INFO'))
    if m:
        return do_temp_file(m.group(1), 'application/pdf')

    return do_index(request)


def handle(request, response):
    if auth.enabled():
        res = auth.check_web_auth(request, response)

        if res == 'login_success':
            response.status = 302
            response.headers.append(('Location', request.environ.get('REQUEST_URI', '/')))
            return

        if res == 'logout_success':
            response.status = 302
            response.headers.append(('Location', request.environ.get('REQUEST_URI', '/')))
            return

        if res == 'login_failure':
            html = util.render_template(
                    config.get_path('www.login_template', 'gbd/core/login.html.tpl'),
                    {'status': 'login_failed', 'request': request})
            response.status = 200
            response.headers.append(('Content-Type', 'text/html; charset=utf-8'))
            response.body = html
            return

    resp = dispatch(request)

    if isinstance(resp, (list, tuple)):
        response.status = resp[0]
        if len(resp) > 1:
            response.headers.extend(resp[1])
        if len(resp) > 2:
            response.body = resp[2]
    else:
        response.status = resp


def parse_qs(s, as_list=True, encoding='utf8'):
    qs = urlparse.parse_qs(s)
    for k in qs:
        for n, v in enumerate(qs[k]):
            qs[k][n] = qs[k][n].decode(encoding)
    if as_list:
        return qs
    return dict((k.strip(), v[0].strip()) for k, v in qs.items())


def prepare(environ):
    qs = environ.get('QUERY_STRING', '')

    request = util.struct({
        'method': environ['REQUEST_METHOD'].upper(),
        'environ': environ,
        'osenv': os.environ,
        'query': parse_qs(qs, True),
        'args': parse_qs(qs, False),
        'body': {},
        'raw_body': '',
        'user': auth.guest()
    })

    clen = int(environ.get('CONTENT_LENGTH', '0'))
    log.debug('REQUEST', environ.get('REMOTE_ADDR'), environ.get('QUERY_STRING'), clen)

    if clen:
        body = environ['wsgi.input'].read(clen)
        request.raw_body = body

        if 'application/json' in environ.get('CONTENT_TYPE'):
            request.body = json.loads(body)
        elif 'application/x-www-form-urlencoded' in environ.get('CONTENT_TYPE'):
            request.body = parse_qs(body, False)
        # NB: QWC incorrectly sets application/xml for WFS requests
        elif 'application/xml' in environ.get('CONTENT_TYPE') and body[0] != '<':
            request.body = parse_qs(body, False)

    response = util.struct({
        'status': None,
        'headers': [],
        'body': ''
    })

    return request, response


def app(environ, start_response):
    """
        Application entry point.

        If the query string contains `map`, render the client.
        If the query string contains `plugin`, import the plugin module and invoke its `main`.
        Otherwise, render the index page.
    """

    try:
        request, response = prepare(environ)
        # debug.pp(request, response)

        if 'map' in request.args:
            for k in config.keys('projects.project'):
                c = config.get_list(k)  # id, path, config
                if c[1] == request.args['map'] and len(c) > 2:
                    log.debug('loading project-specific config: ' + c[2])
                    config.load_extra(c[2])

        handle(request, response)

        if isinstance(response.status, int):
            response.status = http_status[response.status]

        if not isinstance(response.body, basestring):
            response.body = ''.join(response.body)

        if isinstance(response.body, unicode):
            response.body = response.body.encode('utf8')

        response.headers.append(('Content-Length', str(len(response.body))))

        for key in config.keys('www.http_header'):
            h = str(config.get(key)).split(':', 1)
            response.headers.append(tuple(h))

        log.debug('RESPONSE', response.status)

        start_response(response.status, response.headers)
        yield response.body

        config.unload_extra()

    except:
        log.exception()
        start_response(http_status[500], [('Content-Type', 'text/plain')])
        yield 'Internal Server Error'


def main():
    WSGIServer(app).run()
