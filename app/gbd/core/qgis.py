"""QGIS specific tools."""

import collections, os, urllib, time, threading, re
import xml.etree.ElementTree as ElementTree
from xml.sax.saxutils import escape

import requests

from gbd.core import config, log, gis, util, shell, debug
from gbd.core.util import inline_format as _f


def _asdict(node):
    return dict((n.tag, n.text) for n in node)


def _querystring(params):
    def _enc(s):
        if isinstance(s, unicode):
            s = s.encode('utf8')
        return str(s)

    p = {}
    for k, v in params.items():
        if isinstance(v, (list, tuple)):
            v = ','.join(map(_enc, v))
        if isinstance(v, unicode):
            v = v.encode('utf8')
        p[k] = v
    return urllib.urlencode(p)


def _toelem(s):
    if isinstance(s, basestring):
        return ElementTree.fromstring(s)
    return s


class QGISProject(object):
    def __init__(self, path):
        self.path = path
        with open(self.path) as fp:
            self.et = ElementTree.ElementTree(file=fp)

    def write_to(self, path):
        with open(path, 'w') as fp:
            self.et.write(fp, encoding='utf-8')  # , xml_declaration=True

    def save_as(self, path):
        self.write_to(path)
        self.path = path

    def save(self):
        self.save_as(self.path)

    def find(self, xpath):
        return self.et.find(xpath)

    def findall(self, xpath):
        return self.et.findall(xpath)

    def find_as_xml(self, xpath):
        e = self.et.find(xpath)
        return ElementTree.tostring(e, encoding='utf-8')

    def insert_before(self, xpath, tag, elem):
        e = self.et.find(xpath)
        for n, c in enumerate(e):
            if c.tag == tag:
                e.insert(n, _toelem(elem))
                return

    def append_to(self, xpath, elem):
        e = self.et.find(xpath)
        e.append(_toelem(elem))

    # <Variables>
    #   <variableNames type="QStringList">
    #     <value>....</value>
    #     <value>...</value>
    # </variableNames>
    # <variableValues type="QStringList">
    #     <value>....</value>
    #     <value>....</value>
    # </variableValues>
    # </Variables>

    def get_vars(self):
        return dict(zip(
                [x.text for x in self.findall('.//Variables/variableNames/value')],
                [x.text for x in self.findall('.//Variables/variableValues/value')]
        ))

    def add_vars(self, vars):

        def mklist(tag, xs):
            e = self.find('//Variables/' + tag)
            for c in list(e):
                e.remove(c)
            for x in xs:
                t = ElementTree.Element('value')
                t.text = x
                e.append(t)

        vs = self.get_vars()
        vs.update(vars)
        vs = vs.items()

        mklist('variableNames', [k for k, v in vs])
        mklist('variableValues', [v for k, v in vs])

    def crs(self, key=None):
        n = self.et.find('mapcanvas/destinationsrs/spatialrefsys')
        try:
            d = _asdict(n)
            return d[key] if key else d
        except TypeError:
            return None

    def template_layer(self, plugin, gtype):
        """ Process 'print_layer' template for the current plugin.
            the template is supposed to contain a layer for each geometry type."""

        tpl_path = config.get_path(
                'plugin:' + plugin + '.print_layer',
                'gbd/plugins/' + plugin + '/print_layer.qgs'
        )

        with open(tpl_path) as fp:
            tpl_doc = ElementTree.ElementTree(file=fp)

        for layer in tpl_doc.findall('./projectlayers/maplayer'):
            if layer.attrib.get('geometry') == gtype:
                return layer

    def add_extra_features(self, flist, base_path):
        extra_layers = {}

        # values for <maplayer> geometry attribute
        wkt2qgis = {
            'POINT': 'Point',
            'POLYGON': 'Polygon',
            'LINESTRING': 'Line'
        }

        features = collections.defaultdict(list)
        for f in flist:
            g = gis.wkt_type(f['wkt'])
            if g not in wkt2qgis:
                log.error('unsupported geometry', g)
                continue
            key = f['plugin'] + '_' + wkt2qgis[g]
            features[key].append(f)

        layer_template = '''
            <maplayer minimumScale="0" maximumScale="1e+08" simplifyDrawingHints="1"
                    minLabelScale="0" maxLabelScale="1e+08" simplifyDrawingTol="1" geometry="${gtype}"
                    simplifyMaxScale="1" type="vector" hasScaleBasedVisibilityFlag="0" simplifyLocal="1" scaleBasedLabelVisibilityFlag="0">
                <id>${name}</id>
                <datasource>file://${datapath}?type=csv&amp;delimiter=;&amp;useHeader=Yes&amp;wktField=WKT&amp;spatialIndex=no&amp;subsetIndex=no&amp;watchFile=no</datasource>
                <layername>${name}</layername>
                <srs>${spatialrefsys}</srs>
                <provider encoding="UTF-8">delimitedtext</provider>
            </maplayer>
        '''

        for key, features_sublist in features.items():
            plugin, gtype = key.split('_')

            csv = ['WKT;Label']
            for f in features_sublist:
                label = f.get('label', '')
                # should be <property key="labeling/wrapChar" value="~"/> in the layers template
                label = label.replace('\n', '~')
                label = label.replace(';', ',')
                csv.append('%s;%s' % (f['wkt'], label))

            csv_path = base_path + '_' + key + '.csv'
            with open(csv_path, 'w') as fp:
                fp.write('\n'.join(csv).encode('utf8'))

            layer_xml = util.render_from_string(layer_template, {
                'name': key,
                'gtype': gtype,
                'datapath': csv_path,
                'spatialrefsys': self.find_as_xml('./mapcanvas/destinationsrs/spatialrefsys')
            })
            layer = ElementTree.fromstring(layer_xml)
            tags = set(x.tag for x in layer)

            tlayer = self.template_layer(plugin, gtype)

            if tlayer is None:
                log.error('cannot find template layer', gtype)
            else:
                for p in tlayer:
                    if p.tag not in tags:
                        layer.append(p)

            extra_layers[key] = csv_path
            self.append_to('./projectlayers', layer)

        return extra_layers

    def print_to_pdf(self, composer, args):
        """Clone the project, add our extras and ask mapserv to create a pdf."""

        def _crop_extent(extent, composer):
            # correct the map extent so that it fits in the composer map

            ce = composer.find('./Composition/ComposerMap/Extent')

            if ce is None:  # 'not ce' doesn't work for some reason
                return extent

            try:
                w = float(ce.attrib['xmax']) - float(ce.attrib['xmin'])
                h = float(ce.attrib['ymax']) - float(ce.attrib['ymin'])
            except (KeyError, ValueError):
                return extent

            extent[1] = extent[3] - (extent[2] - extent[0]) / w * h

        params = {
            'SERVICE': 'WMS',
            'VERSION': '1.3',
            'REQUEST': 'GetPrint',
            'FORMAT': 'pdf',
            'EXCEPTIONS': 'application/vnd.ogc.se_inimage',
            'TRANSPARENT': 'true',
            'TEMPLATE': None,
            'SRS': self.crs('authid'),
            'DPI': '300',
        }

        for k, v in args.items():
            if k in params or k.startswith('map0'):
                params[k] = v

        if composer:
            composer = _toelem(composer)
            params['TEMPLATE'] = composer.attrib.get('title')
            self.insert_before('.', 'projectlayers', composer)

            if 'map0:extent' in params:
                # normalize extent independently of the axis order
                e = params['map0:extent']
                e = [
                    min(e[0], e[2]),
                    min(e[1], e[3]),
                    max(e[0], e[2]),
                    max(e[1], e[3])
                ]
                _crop_extent(e, composer)
                params['map0:extent'] = e

        uid = util.uid('p')
        base_path = config.get('paths.temp') + '/' + uid

        if 'extra_features' in args:
            extra_layers = self.add_extra_features(args['extra_features'], base_path)
            if extra_layers:
                args['layers'].extend(extra_layers.keys())

        vs = self.get_vars()

        if 'print_title' in args:
            vs['print_title'] = args['print_title']

        # for some reason, [% @xxx %] doesn't work with custom vars

        def replace_vars(s):
            return re.sub(
                    r'\[%\s*@(\w+)\s*%\]',
                    lambda m: vs.get(m.group(1), m.group(0)),
                    s)

        for c in self.findall('.//ComposerLabel'):
            if c.attrib.get('labelText'):
                c.attrib['labelText'] = replace_vars(c.attrib['labelText'])

        for c in self.findall('.//ComposerHtml'):
            if c.attrib.get('html'):
                c.attrib['html'] = replace_vars(c.attrib['html'])

        self.save_as(base_path + '.qgs')

        params['map'] = self.path
        params['LAYERS'] = args['layers']

        headers, out = call_server(params)
        if headers.get('content-type') != 'application/pdf':
            log.error(out)
            raise ValueError('unexpected content-type')

        with open(base_path + '.pdf', 'w') as fp:
            fp.write(out)

        return uid


def project(path):
    return QGISProject(path)


def call_server(params):
    """Call the mapserv via the loopback interface."""

    url = 'http://127.0.0.1/cgi-bin/qgis_mapserv.fcgi'
    host = config.get('app.loopback_host', 'gbd.local')

    log.debug('START', params)

    data = {}
    for k, v in params.items():
        if isinstance(v, list):
            v = ','.join(map(unicode, v))
        data[k] = v

    ts = time.time()
    r = requests.post(
        url,
        data,
        headers={'host': host, 'accept-encoding': 'identity'},
        stream=False)
    ts = time.time() - ts

    if r.status_code != 200:
        raise ValueError('server error', r.status_code, r.content)

    h = dict((k.lower(), v) for k, v in r.headers.items())
    if h.get('transfer-encoding') == 'chunked':
        h.pop('transfer-encoding')

    log.debug('END', round(ts, 2))

    return h, r.content


def preload(path, workers=10):
    def preload_one(url):
        requests.get(url)

    server = config.get('www.server_name')
    url = _f('http://{server}/cgi-bin/qgis_mapserv.fcgi?map={path}&SERVICE=WMS&VERSION=1.3&REQUEST=GetProjectSettings')

    log.debug(_f('START preload with {workers} workers'))

    ths = [threading.Thread(target=preload_one, args=(path, url)) for _ in range(workers)]
    for t in ths:
        t.start()

    ts = time.time()
    while True:
        alive = sum(t.is_alive() for t in ths)
        if not alive:
            break
        log.debug(_f('preload: {alive} workers running...'))
        time.sleep(5)

    log.debug(_f('END preload in {0:.2f}s', time.time() - ts))
