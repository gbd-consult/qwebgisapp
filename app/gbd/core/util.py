"""Misc utilities."""

import sys, string, time, os, math, itertools, random, datetime
import mako.template, mako.exceptions

from gbd.core import config, log, templatetools


def f(s, *args, **kwargs):
    frame = sys._getframe(1)
    d = {}
    d.update(frame.f_globals)
    d.update(frame.f_locals)
    d.update(kwargs)
    return string.Formatter().vformat(s, args, d)


def inline_format(s, *args, **kwargs):
    frame = sys._getframe(1)
    d = {}
    d.update(frame.f_globals)
    d.update(frame.f_locals)
    d.update(kwargs)
    return string.Formatter().vformat(s, args, d)


class Struct(object):
    def __init__(self, d):
        if isinstance(d, dict):
            for k, v in d.items():
                setattr(self, k, v)
        elif isinstance(d, (list, tuple)):
            for k in d:
                setattr(self, k, None)


def struct(d):
    return Struct(d)


def encode_all(d, coding='utf8'):
    if isinstance(d, unicode):
        return d.encode(coding)
    if isinstance(d, dict):
        return dict((encode_all(k, coding), encode_all(v, coding)) for k, v in d.items())
    if isinstance(d, list):
        return [encode_all(v, coding) for v in d]
    if isinstance(d, tuple):
        return tuple(encode_all(v, coding) for v in d)
    return d


def render_from_string(src, args=None):
    try:
        # we use 'disable_unicode' to avoid u"" strings in the template
        # so all input must be preencoded to utf8
        tpl = mako.template.Template(encode_all(src), disable_unicode=True, input_encoding='utf-8')
        args = encode_all(args or {})
        args['_'] = templatetools
        return tpl.render(**args)
    except:
        err = mako.exceptions.text_error_template().render()
        for s in err.strip().splitlines():
            log.error(s)
        raise


def render_template(path, args=None):
    with open(path) as fp:
        return render_from_string(fp.read(), args)


_app_version = None


def app_version(as_number=False):
    global _app_version

    if _app_version is None:
        with open(os.path.join(config.app_root(), 'VERSION')) as fp:
            _app_version = fp.read().strip()

    if as_number:
        v = _app_version.split('.')
        return int(v[0]) * 1000000 + int(v[1]) * 1000 + int(v[2])

    return _app_version


def strip_none(d):
    return dict((k, v) for k, v in d.items() if v is not None and v != [None])


def split_dict(d):
    r = {}
    for k, v in d.items():
        k = k.split('.')
        q = r
        for sub in k[:-1]:
            if sub not in q:
                q[sub] = {}
            q = q[sub]
        q[k[-1]] = v
    return r


def pick(d, keys, skip_none=False):
    r = {}
    is_dict = isinstance(keys, dict)
    for k in keys:
        p = keys[k] if is_dict else k
        if d.get(k) is not None:
            r[p] = d[k]
        elif not skip_none:
            r[p] = None
    return r


def chunked(it, size):
    it = iter(it)
    while True:
        p = tuple(itertools.islice(it, size))
        if not p:
            break
        yield p


def randstr(chars, size):
    return ''.join(chars[random.randint(0, len(chars) - 1)] for _ in range(size))


def uid(prefix=''):
    r = randstr('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz', 64)
    return prefix + r


def now():
    return datetime.datetime.now()


class ProgressIndicator(object):
    def __init__(self, title, total, resolution=10):
        self.console = sys.stderr.isatty()
        self.resolution = resolution
        self.title = title
        self.total = total
        self.progress = 0
        self.lastd = 0

    def __enter__(self):
        self.write('START (total=%d)' % self.total)
        self.starttime = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.write('\n')
        else:
            t = time.time() - self.starttime
            self.write('END (time=%.2f rps=%.1f)' % (t, self.total / t))

    def update(self, add=1):
        self.progress += add
        p = math.floor(self.progress * 100.0 / self.total)
        if p > 100:
            p = 100
        d = round(p / self.resolution) * self.resolution
        if d > self.lastd:
            self.write('%d%%' % d)
        self.lastd = d

    def write(self, s):
        log.info(self.title + ': ' + s)
