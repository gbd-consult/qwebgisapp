"""Access the program configuration."""

import os, re, json, threading

try:
    from collections import OrderedDict
except ImportError:
    from gbd.core.ordered_dict import OrderedDict


def _debug(s):
    with open('/var/gbd/log/app.log', 'ab') as fp:
        fp.write('CONFIG: %s:%s %s\n' % (os.getpid(), threading.current_thread().ident, repr(s)))


_confdata = None
_confpath = None

_parse_cache = {}

_local = threading.local()


def _bool(s):
    if s == 'YES': return True
    if s == 'NO': return False
    return s


def _parse_ini(fpath):
    conf = OrderedDict()
    section = None
    uid = 0

    with open(fpath) as fp:
        for n, ln in enumerate(fp, 1):
            ln = ln.strip().decode('utf8')
            if not ln or ln.startswith((';', '#')):
                continue
            m = re.match(r'\[(.+?)\]', ln)
            if m:
                section = m.group(1).strip()
                continue
            m = re.match(r'(.+?)=(.*)', ln)
            if m:
                if not section:
                    raise ValueError('No header in %s line %d' % (fpath, n))
                if section not in conf:
                    conf[section] = OrderedDict()
                key = m.group(1).strip()
                if key.startswith('+'):
                    key = key[1:] + str(uid)
                    uid += 1
                conf[section][key] = _bool(m.group(2).strip())
                continue
            raise ValueError('Syntax error in %s line %d' % (fpath, n))

    return conf


def _parse_ini_cached(fpath):
    if fpath not in _parse_cache:
        _parse_cache[fpath] = _parse_ini(fpath)
    return _parse_cache[fpath]


def _merge(c1, c2):
    r = dict(c1)
    r.update(c2)
    return r


def path():
    return _confpath


def load(fpath=None):
    global _confdata, _confpath

    if fpath is None:
        if 'GBD_CONFIG_PATH' not in os.environ:
            raise ValueError('No config file found')
        fpath = os.environ['GBD_CONFIG_PATH']

    _confpath = fpath
    _confdata = _parse_ini_cached(fpath)


def _main_conf():
    if _confdata is None:
        load()
    return _confdata


def load_extra(fpath):
    _local.conf = _merge(_main_conf(), _parse_ini_cached(fpath))


def unload_extra():
    if hasattr(_local, 'conf'):
        delattr(_local, 'conf')


def init():
    global _confdata
    _confdata = {}


def _conf():
    if hasattr(_local, 'conf'):
        return _local.conf
    return _main_conf()


def sections():
    return _conf().keys()


def get(key, default=None):
    c = _conf()
    sec, name = key.split('.')
    return default if sec not in c else c[sec].get(name, default)


def get_all(section):
    return _conf().get(section, {})


def keys(key):
    sec, prefix = key.split('.')
    return sorted(sec + '.' + k for k in get_all(sec) if k.startswith(prefix))


def get_list(key, limit=None):
    c = get(key)
    if not c:
        return []

    if limit is None:
        limit = 9999

    rx = r'''(?x)
        \s*
        (
            " ( (?: \\. | [^"]) *) "
            |
            ([^,]+?)
        )
        \s*
        (?: , | $)
    '''

    rs = []

    for m in re.finditer(rx, c):
        rs.append(
                json.loads(m.group(1)) if m.group(1).startswith('"') else _bool(m.group(3))
        )
        if len(rs) == limit:
            rs.append(c[m.end():].strip())
            break

    return rs


def put(key, value):
    c = _conf()
    sec, name = key.split('.')
    if sec not in c:
        c[sec] = OrderedDict()
    if isinstance(value, (list, tuple)):
        value = ','.join([json.dumps(x) for x in value])
    c[sec][name] = value


def write_section(fp, title, pairs):
    fp.write('[%s]\n' % unicode(title).encode('utf8'))
    for k, v in pairs.items():
        k = unicode(k).encode('utf8')
        v = unicode(v).encode('utf8')
        fp.write(k + '=' + v + '\n')
    fp.write('\n')


def write(fp):
    for sec, pairs in _conf().items():
        write_section(fp, sec, pairs)


def app_root():
    return os.path.abspath(
            os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    '..',
                    '..'
            )
    )


def get_path(key, default=None):
    p = get(key, default)
    if p is None:
        return None
    if os.path.isabs(p):
        return p
    return os.path.join(app_root(), p)


def all_projects():
    """Enumerate projects' paths from the config."""

    def fname(fpath):
        return os.path.splitext(os.path.basename(fpath))[0]

    for fpath in get_list('projects.paths'):
        fpath = fpath.encode('utf8')
        if os.path.isfile(fpath):
            yield fname(fpath), fpath
        else:
            for root, _, files in os.walk(fpath):
                for f in files:
                    if f.endswith('.qgs'):
                        yield fname(f), os.path.join(root, f)


def plugin_config(name, app_dir=None):
    cpath = (app_dir or app_root()) + '/gbd/' + ('core' if not name else 'plugins/' + name) + '/__config__.json'
    if not os.path.exists(cpath):
        return {}
    with open(cpath) as fp:
        return json.load(fp)


def plugin_js_options(name, app_dir=None):
    c = plugin_config(name, app_dir)
    if 'js_options' not in c:
        return {}

    rs = {}

    for opt in c['js_options']:
        v = get('plugin:' + name + '.' + opt)
        if v is not None:
            rs[opt] = v

    return rs
