"""Support QGIS copyright labels."""

from gbd.core import plugin, qgis, debug


# see qgsdecorationitem.h

class Placement:
    BottomLeft = 0
    TopLeft = 1
    TopRight = 2
    BottomRight = 3


def to_dict(node):
    d = {}
    for c in node.children():
        d[c.tag] = c.text


mm_per_inch = 25.4
default_ppi = 90


def mm_to_px(v):
    return round((float(v) / mm_per_inch) * default_ppi)


def label_style(lab):
    unit = lab.get('marginunit', 'pixel').lower()
    if unit == 'pixel':
        unit = 'px'
    if unit == 'percentage':
        unit = '%'
    if unit == 'mm':
        unit = 'mm'

    x = '%d%s' % (int(lab.get('marginh', 0)), unit)
    y = '%d%s' % (int(lab.get('marginv', 0)), unit)

    css = {
        'position': 'absolute',
        'z-index': '9999'
    }
    pc = int(lab.get('placement', 0))

    if pc == Placement.BottomLeft:
        css['left'] = x
        css['bottom'] = y
    if pc == Placement.TopLeft:
        css['left'] = x
        css['top'] = y
    if pc == Placement.TopRight:
        css['right'] = x
        css['top'] = y
    if pc == Placement.BottomRight:
        css['right'] = x
        css['bottom'] = y

    css['color'] = lab.get('color', 'black')

    return css


def label_props(path):
    prj = qgis.project(path)

    lab = prj.find('properties/CopyrightLabel')
    if not lab:
        return

    lab = {c.tag.lower(): c.text for c in lab}
    if lab.get('enabled', '').lower() != 'true':
        return

    return {
        'style': label_style(lab),
        'html': lab.get('label', '')
    }


class Plugin(plugin.Base):
    def command(self, cmd, request):
        if cmd == 'label':
            return self.as_json(label_props(request.args.get('map')))

    def run(self, request):
        return self.command(request.args.get('cmd'), request)
