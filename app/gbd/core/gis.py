"""Misc GIS support utils."""

import re
import pyproj
import requests
import urllib
import json

from gbd.core import config, log, debug


def _proj(s):
    if not isinstance(s, basestring):
        return s
    if s == 'latlong':
        return pyproj.Proj(proj='latlong')
    return pyproj.Proj(init=s)


def transform_bounds(src, dst, bounds):
    """Transform [l,t,r,b] bounds between projections."""

    t = pyproj.transform(_proj(src), _proj(dst), [bounds[0], bounds[2]], [bounds[1], bounds[3]])
    return [t[0][0], t[1][0], t[0][1], t[1][1]]


def bounds(wkt, expand=0):
    # @TODO use proper parsing

    points = re.findall(r'''(?x)
        (?: -? \d+\.?\d* | \.\d+)
        \s+
        (?: -? \d+\.?\d* | \.\d+)
        (?= [,)])
    ''', wkt)

    xs, ys = [], []

    for p in points:
        x, y = p.split()
        xs.append(float(x))
        ys.append(float(y))

    # [ext.left, ext.top, ext.right, ext.bottom]
    return [min(xs) - expand, min(ys) - expand, max(xs) + expand, max(ys) + expand]


def transform_wkt(src, dst, wkt):
    """Transform a wkt between projections."""

    # @TODO use proper parsing

    points = re.findall(r'''(?x)
        (?: -? \d+\.?\d* | \.\d+)
        \s+
        (?: -? \d+\.?\d* | \.\d+)
        (?= [,)])
    ''', wkt)

    xs, ys = [], []

    for p in points:
        x, y = p.split()
        xs.append(float(x))
        ys.append(float(y))

    xs, ys = pyproj.transform(_proj(src), _proj(dst), xs, ys)

    for n, p in enumerate(points):
        wkt = wkt.replace(p, '%f %f' % (xs[n], ys[n]))

    return wkt


def wkt_type(geom):
    geom = geom.strip()
    return geom[:geom.index('(')].upper()


def nominatim_query(crs, params):
    """Make a query to nominatim."""

    for k, v in params.items():
        if isinstance(v, unicode):
            params[k] = v.encode('utf8')

    if crs and 'viewbox' in params:
        v = params['viewbox']
        if isinstance(params['viewbox'], basestring):
            v = map(float, v.split(','))
        v = transform_bounds(crs, 'latlong', v)
        params['viewbox'] = ','.join(map(str, v))

    params.update({
        'format': 'json',
        'bounded': 1,
        'polygon_text': 1
    })

    base = 'http://nominatim.openstreetmap.org/search?'
    url = base + urllib.urlencode(params)

    log.debug(url)

    try:
        resp = requests.get(url)
    except requests.RequestException as e:
        log.error('request error', e)
        return

    try:
        js = json.loads(resp.content)
    except ValueError as e:
        log.error('decode error', e, resp.content)
        return

    for r in js:
        if crs:
            r['wkt'] = transform_wkt('latlong', crs, r['geotext'])
        else:
            r['wkt'] = r['geotext']
        yield r


def arc2wkt(geom):
    """Convert ArcGis geometries to WKT.

        see http://resources.arcgis.com/en/help/rest/apiref/geometry.html

        completely ignore Z and M coords.
    """

    comma = ','

    if 'x' in geom:
        # point
        # "x" : <x>, "y" : <y>, ....
        return 'POINT(%s %s)' % (geom['x'], geom['y'])

    if 'points' in geom:
        # multipoint:
        # "points" : [ [ <x1>, <y1>, <z1>, <m1> ] , [ <x2>, <y2>...

        if not geom['points']:
            return None

        points = comma.join('%s %s' % (p[0], p[1]) for p in geom['points'])
        return 'MULTIPOINT(%s)' % points

    if 'paths' in geom:
        # polyline:
        # "paths" : [
        #   [ [<x11>, <y11>, <z11>, <m11>], [<x12>, <y12>, <z12>, <m12>] ],
        #   [ [<x21>, <y21>, <z21>, <m21>], [<x22>, <y22>, <z22>, <m22>] ]

        if not geom['paths']:
            return None

        ps = [
            comma.join('%s %s' % (p[0], p[1]) for p in path)
            for path in geom['paths']
            ]

        if len(ps) == 1:
            return 'LINESTRING(%s)' % ps[0]

        return 'MULTILINESTRING(%s)' % comma.join('(%s)' % p for p in ps)

    if 'rings' in geom:
        # polygon:
        # "rings" : [
        #  [ [<x11>, <y11>, <z11>, <m11>], [<x12>, <y12>, <z12>, <m12>], ..., [<x11>, <y11>, <z11>, <m11>] ],
        #  [ [<x21>, <y21>, <z21>, <m21>], [<x22>, <y22>, <z22>, <m22>], ..., [<x21>, <y21>, <z21>, <m21>] ]

        if not geom['rings']:
            return None

        ps = [
            comma.join('%s %s' % (p[0], p[1]) for p in ring)
            for ring in geom['rings']
            ]

        return 'POLYGON(%s)' % comma.join('(%s)' % p for p in ps)
