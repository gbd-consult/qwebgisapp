(function () {

    var pg = Gbd.plugin('marker');

    pg.layer = null;
    pg.css = null;

    pg.on('setMarker', function (event) {
        /*
         options:
         wkt - geometry
         label - label for the marker
         hidden - don't show (only zoom)
         nozoom - no zoom
         padding - zoom padding
         */
        pg.setMarker(event);
    });

    pg.on('clearMarker', function () {
        pg.clear();
    });

    pg.on('enumPrintableFeatures', function (event) {
        if (pg.layer) {
            pg.layer.features.forEach(function (f) {
                event.features.push({
                    plugin: pg.name,
                    //label: f.attributes.labelInfos || '',
                    wkt: f.geometry.toString()
                });
            });
        }
    })


    pg.clear = function () {
        if (pg.layer) {
            try {
                Gbd.map().removeLayer(pg.layer);
            } catch (e) {
            }
        }
        pg.layer = null;
    };

    pg.loadCSS = function () {
        if (pg.css) {
            return Promise.resolve(pg.css);
        }
        return pg.http('css.json').then(function (css) {
            pg.css = css;

            var color = Gbd.option('marker.color');
            if (color) {
                pg.css.strokeColor = pg.css.fillColor = color;
            }

            return pg.css;
        });
    };

    pg.mouseHandler = function () {
        pg.clear();
        Gbd.map().events.unregister('click', null, pg.mouseHandler);
    };

    pg.initLayer = function (css) {

        var styleMap = new OpenLayers.StyleMap({
            'default': new OpenLayers.Style(css)
        });

        var layer = new OpenLayers.Layer.Vector('_gbd_marker', {styleMap: styleMap});
        Gbd.map().events.register('click', null, pg.mouseHandler);

        return layer;
    };

    pg.getLayer = function () {
        pg.clear();
        return pg.loadCSS().then(function (css) {
            pg.layer = pg.initLayer(css);
            Gbd.map().addLayer(pg.layer);
            return pg.layer;
        });
    };

    pg.setMarker = function (options) {

        pg.clear();

        if (!options.wkt || !options.wkt.length) {
            return;
        }

        var features = Gbd.readWKT(options.wkt);

        if (!features) {
            return;
        }

        features.forEach(function (f) {
            f.attributes.label = options.label || '';
        });

        if (!options.nozoom) {
            Gbd.zoomTo(Gbd.bounds(features), options.padding);
        }

        if (!options.hidden) {
            pg.getLayer().then(function (layer) {
                layer.addFeatures(features);
            });
        }
    };


})();