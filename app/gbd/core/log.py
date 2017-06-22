"""Logger."""

import logging, os, sys, traceback, time
from gbd.core import config

_data = {
    'logger': None
}


def _caller(skip):
    try:
        fname, line, func, _ = traceback.extract_stack()[-(skip + 1)]
        x = [''] + fname.replace('.py', '').split('/')
        dir, f = x[-2:]
        return {'caller': '%s/%s:%s:%s ' % (dir, '' if f == '__init__' else f, func, line)}
    except Exception as e:
        return {'caller': str(e)}


def _logger():
    if not _data['logger']:
        logger = logging.getLogger('gbd')
        logger.setLevel(logging.DEBUG)

        if sys.stdout.isatty():
            h = logging.StreamHandler()
        else:
            h = logging.FileHandler(os.path.join(config.get('paths.log'), 'app.log'))
            formatter = logging.Formatter('%(asctime)s %(process)d %(levelname)s %(caller)s %(message)s')
            h.setFormatter(formatter)

        logger.addHandler(h)

        _data['logger'] = logger

    return _data['logger']


def _prepare(args):
    return ', '.join(map(repr, args))


def exception():
    t, exc, tb = sys.exc_info()
    if not t:
        return
    if getattr(t, '__module__') == 'exceptions':
        t = getattr(t, '__name__')
    else:
        t = getattr(t, '__module__') + '.' + getattr(t, '__name__')

    s = '((EXCEPTION: ' + t + ': ' + str(exc) + '\n' + ''.join(traceback.format_tb(tb)).rstrip() + '\n))'
    _logger().error(s, extra=_caller(2))


def error(*args):
    _logger().error(_prepare(args), extra=_caller(2))


def info(*args):
    _logger().info(_prepare(args), extra=_caller(2))


def warning(*args):
    _logger().warning(_prepare(args), extra=_caller(2))


def debug(*args):
    _logger().debug(_prepare(args), extra=_caller(2))


_timers = {}


def time_start(s):
    _timers[s] = time.time()
    _logger().debug(_prepare([s]), extra=_caller(2))


def time_end(s):
    if s in _timers:
        s += ' (time=%.2fms)' % (time.time() - _timers.pop(s))
        _logger().debug(_prepare([s]), extra=_caller(2))


def raw(*args):
    for a in args:
        if not isinstance(a, basestring):
            a = str(a)
        _logger().debug(a, extra=_caller(3))
