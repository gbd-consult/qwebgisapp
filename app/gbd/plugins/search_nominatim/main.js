/// Nominatim support for search box

(function () {

    var STRINGS = {
        // http://wiki.openstreetmap.org/wiki/DE:Map_Features
        categoryNames: {
            "aerialway": "Seilbahn",
            "aeroway": "Flughafen",
            "amenity": "Einrichtung",
            "barrier": "Barriere",
            "building": "Gebäude",
            "boundary": "Grenze",
            "craft": "Handwerk",
            "emergency": "Notfalleinrichtung",
            "highway": "Weg",
            "historic": "Historisch",
            "house": "Gebäude",
            "landuse": "Landnutzung",
            "leisure": "Freizeit",
            "man_made": "Kunstbauten",
            "natural": "Natur",
            "office": "Dienststelle",
            "power": "Energieversorgung",
            "railway": "Eisenbahn",
            "shop": "Geschäft",
            "tourism": "Tourismus",
            "vending": "Automaten",
            "waterway": "Wasserlauf"
        }
    };

    var pg = Gbd.plugin('search_nominatim');

    pg.on('searchBoxChange', function (evt) {

        var val = evt.value,
            params = {
                query: val,
                viewbox: Gbd.map().maxExtent.toString(),
                crs: Gbd.option('project.authid')
            };

        pg.http('search', params).then(function (res) {
            Gbd.send('searchBoxUpdate', {
                results: res.map(function (r) {
                    r.value = val;
                    r.source = 'search_nominatim';
                    r.section = (STRINGS.categoryNames[r.category] || r.category) + ' (OSM)';
                    return r;
                })
            });
        })
    });

    pg.on('searchBoxSelect', function (evt) {
        if (evt.item.source !== 'search_nominatim') {
            return;
        }
        Gbd.send('setMarker', {wkt: evt.item.wkt});
    });

})();



