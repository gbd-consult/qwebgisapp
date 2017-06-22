# coding=utf8

"""Tools for better templating.

This module is available as '_' in mako templates.
"""

import re, cgi
from gbd.core import debug


def get(obj, path, default=None):
    for k in path.split('.'):
        if obj is None:
            return default
        if k.isdigit():
            k = int(k)
        try:
            obj = obj[k]
        except (KeyError, IndexError):
            return default

    return default if obj is None else obj


def val(obj, path, default=''):
    r = get(obj, path, default)
    return r


def get_int(obj, path):
    r = get(obj, path)
    try:
        return str(int(r))
    except TypeError:
        return ''


def area(v, suffix=True):
    try:
        s = str(int(round(float(v))))
        if s == '0':
            s = '%.1f' % v
        if suffix:
            s += ' m²'
        return s
    except TypeError:
        return '-'


def format(obj, fmt):
    repl = {}
    for m in re.findall(r'{.*?}', fmt):
        path = m[1:-1]
        repl[m] = get(obj, path, '') if path else obj
    for k, v in repl.items():
        fmt = fmt.replace(k, cgi.escape(str(v)))
    return fmt


def br(s):
    s = [x.strip() for x in s.strip().splitlines() if x.strip()]
    return '<br>'.join(s)


class PropertySheet:
    def __init__(self, base):
        self.base = base
        self.sections = []

    def section(self, head):
        sec = {
            'head': head,
            'items': []
        }
        self.sections.append(sec)

    def get(self, a, b=None):
        return get(a, b) if b else get(self.base, a)

    def val(self, a, b=None):
        return val(a, b) if b else get(self.base, a)

    def list(self, a, b=None):
        return self.get(a, b) or []

    def row(self, head, val, fmt='{}', default=None):
        if val is None:
            val = default
        if val is not None:
            html = br(format(val, fmt))
            if html:
                self.sections[-1]['items'].append({'head': head, 'html': html})

    def line(self):
        self.sections[-1]['items'].append({'head': None})

    def attributes(self, val):
        for attr in get(val, 'attributes', []):
            self.row(get(attr, 'label'), get(attr, 'text'))

    def area(self, a, b=None):
        return area(self.get(a, b))

    @property
    def html(self):
        return '\n'.join(self.render())

    def render(self):
        yield '<table cellspacing="3" cellpadding="5">'
        for sec in self.sections:
            for s in self.render_section(sec):
                yield s
        yield '</table>'

    def render_section(self, sec):

        def strip_delim(items):
            state = 0
            for x in items:
                if x['head'] is not None:
                    if state == 1:
                        yield {'head': None}
                    yield x
                    state = 2
                else:
                    state = state and 1

        items = list(strip_delim(sec['items']))

        if not items:
            return

        yield format(sec['head'], '<tr><th colspan="2">{}</th></tr>')

        for item in items:
            if item['head'] is None:
                yield '<tr><td colspan="2" class="delim">&nbsp;</td></tr>'
            else:
                yield ('<tr>' +
                       format(item, '<td>{head}</td>') +
                       '<td>' + item['html'] +
                       '</td></tr>')


class CSV:
    def __init__(self, **kwargs):
        self.headers = None
        self.row_delimiter = '\n'
        self.field_delimiter = ';'
        self.rows = []
        for k, v in kwargs.items():
            setattr(self, k, v)

    def format_value(self, val):
        if val is None:
            val = ''
        val = unicode(val)
        val = val.strip()
        val = val.replace('"', '""')
        return val

    def format(self, values):
        return self.field_delimiter.join('"%s"' % self.format_value(v) for v in values)

    def row(self, *args):
        headers, values = args[::2], args[1::2]
        if not self.headers:
            self.headers = headers
        self.rows.append(dict(zip(headers, values)))

    def text(self):
        out = [self.format(self.headers)]
        for r in self.rows:
            out.append(self.format(r.get(h) for h in self.headers))
        return self.row_delimiter.join(out).encode('utf8')
