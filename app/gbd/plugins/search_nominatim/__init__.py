# http://wiki.openstreetmap.org/wiki/Nominatim

import requests
import urllib
import json

from gbd.core import config, util, gis, plugin, debug


class Plugin(plugin.Base):
    def text(self, r):
        # The result is something like below, so the problem is there's no fixed key for
        # the 'name'. Worked around by removing keys we know and do a text search for the rest

        if 'address' not in r:
            return r['display_name']

        a = r['address']

        a1 = (a.get('road', '') or a.get('pedestrian', '')) + ' ' + a.get('house_number', '')
        a2 = a.get('postcode', '') + ' ' + a.get('town', '')

        s = (a1.strip() + '\n' + a2.strip()).strip()

        known_keys = [
            'country',
            'country_code',
            'county',
            'house_number',
            'pedestrian',
            'road'
            'postcode',
            'state',
            'state_district',
            'suburb',
            'town'
        ]

        for k in known_keys:
            a.pop(k, None)

        for k, v in a.items():
            if r['display_name'].startswith(v):
                s = v + '\n' + s

        return s.strip()

    def convert_result(self, r):
        # {u'address': {u'country': u'Deutschland',
        #               u'country_code': u'de',
        #               u'county': u'Kreis Unna',
        #               u'house_number': u'6',
        #               u'pedestrian': u'Rathausplatz',
        #               u'postcode': u'59174',
        #               u'public_building': u'ARGE Kreis Unna',
        #               u'state': u'Nordrhein-Westfalen',
        #               u'state_district': u'Regierungsbezirk Arnsberg',
        #               u'suburb': u'Kamen-Mitte',
        #               u'town': u'Kamen'},
        #  u'boundingbox': [u'51.5868799', u'51.5872737', u'7.6629592', u'7.6638423'],
        #  u'class': u'amenity',
        #  u'display_name': u'ARGE Kreis Unna, 6, Rathausplatz, Kamen-Mitte, Kamen, Kreis Unna, Regierungsbezirk Arnsberg, Nordrhein-Westfalen, 59174, Deutschland',
        #  u'geotext': u'POLYGON((7.6629592 51.....
        #  u'importance': 0.101,
        #  u'lat': u'51.5870525',
        #  u'licence': u'Data \xa9 OpenStreetMap contributors, ODbL 1.0. http://www.openstreetmap.org/copyright',
        #  u'lon': u'7.66359055218127',
        #  u'osm_id': u'231622250',
        #  u'osm_type': u'way',
        #  u'place_id': u'116871348',
        #  u'type': u'public_building',
        #  'wkt': u'POLYGON((407371.271973 5715...
        #

        cls = r['class']
        if cls == 'place':
            cls = r.get('type')
        if not cls:
            return
        return {
            'text': self.text(r),
            'category': cls,
            'wkt': r['wkt'],
        }

    def command(self, cmd, request):

        if cmd == 'search':

            q = request.args.get('query', '').strip()
            if not q:
                return []

            params = {
                'q': q,
                'viewbox': request.args.get('viewbox'),
                'addressdetails': 1,
                'limit': config.get('plugin:search_nominatim.limit'),
                'accept-language': config.get('plugin:search_nominatim.language', 'de'),
                'countrycodes': config.get('plugin:search_nominatim.country', 'de')
            }

            out = {}

            for r in gis.nominatim_query(request.args['crs'], params):
                r = self.convert_result(r)
                if not r or q.lower() not in r['text'].lower():
                    continue
                key = r['category'] + '/' + r['text']
                out[key] = r

            return out.values()

    def run(self, request):
        return self.as_json(self.command(request.args.get('cmd'), request))
