(function () {

    var pg = Gbd.plugin('selection');

    pg.layer = null;
    pg.selection = {};

    function styleMap() {
        var style = new OpenLayers.Style(),
        /*
         label: "${_label}",
         fontColor: "#333333",
         fontSize: "12px",
         fontFamily: "helvetica, sans-serif",
         fontWeight: "normal",
         labelOutlineColor: "white",
         labelOutlineWidth: 3
         */
            pointRule = new OpenLayers.Rule({
                filter: new OpenLayers.Filter({
                    evaluate: function (f) {
                        return !!(f._geomClass || '').match(/Point/);
                    }
                }),
                symbolizer: {
                    strokeWidth: 0,
                    fillColor: "#FFFF00",
                    fillOpacity: 1,
                    pointRadius: 5,
                    pointerEvents: "visiblePainted"
                }
            }),
            polyRule = new OpenLayers.Rule({
                filter: new OpenLayers.Filter({
                    evaluate: function (f) {
                        return !(f._geomClass || '').match(/Point/);
                    }
                }),
                symbolizer: {
                    strokeColor: "#FFFF00",
                    strokeOpacity: 1,
                    strokeWidth: 2,
                    strokeDashstyle: "dash",
                    fillOpacity: 0,
                    pointerEvents: "visiblePainted"
                }
            });

        style.addRules([pointRule, polyRule]);

        return new OpenLayers.StyleMap({
            'default': style
        });
    }

    function selectionLayer() {
        if (!pg.layer) {
            pg.layer = new OpenLayers.Layer.Vector('_gbd_selection', {styleMap: styleMap()});
            Gbd.map().addLayers([pg.layer]);
        }
        return pg.layer;
    }

    function removeLayer() {
        if (pg.layer) {
            Gbd.map().removeLayer(pg.layer);
            pg.layer = null;
        }
    }

    function featureUid(f) {
        if (f.attributes.gml_id) {
            return f.attributes.gml_id;
        }
        if (f.fid) {
            return f.fid;
        }
        if (f.attributes.ogc_fid) {
            return (f.layerName || '') + ':::' + f.attributes.ogc_fid;
        }
        return (f.layerName || '') + ':::' + String(f.geometry);
    }

    function selectFeatures(features) {
        var wkt = new OpenLayers.Format.WKT();

        features.forEach(function (f) {
            if (!f || !f.geometry) {
                return;
            }
            var p = {
                layerName: f.layerName,
                geometry: f.geometry,
                attributes: Object.assign({}, f.attributes)
            };

            if (typeof p.geometry == 'string') {
                p.geometry = wkt.read(p.geometry).geometry;
            }

            var displayField = '_label';
            try {
                displayField = window.wmsLoader.layerProperties[f.layerName].displayField;
            } catch (e) {
            }

            p.attributes._geomClass = p.geometry.CLASS_NAME;
            p.attributes._label = f.attributes[displayField] || '';
            p.uid = featureUid(p);

            if (p.uid in pg.selection) {
                delete pg.selection[p.uid];
            } else {
                pg.selection[p.uid] = p;
            }
        });

        removeLayer();

        var fs = Object.keys(pg.selection).map(function (k) {
            return pg.selection[k];
        });

        if (fs.length) {
            selectionLayer().addFeatures(fs);
        }

        Gbd.send('featuresSelected', {features: fs});
    }

    pg.on('selectFeatures', function (event) {
        selectFeatures(event.features);
        return true;
    });

    pg.on('deselectAll', function (event) {
        removeLayer();
        pg.selection = {};
        Gbd.send('featuresSelected', {features: []});
        return true;
    });

    pg.on('zoomToSelection', function (event) {
        var bounds = null;

        Object.keys(pg.selection).forEach(function (k) {
            var f = pg.selection[k];
            if (!bounds) {
                bounds = f.geometry.getBounds();
            } else {
                bounds.extend(f.geometry.getBounds());
            }
        });

        Gbd.map().zoomToExtent(bounds);

        var scale = Gbd.map().getScale() * 1.5;
        if (scale < 500) {
            scale = 500;
        }
        Gbd.map().zoomToScale(scale);
        return true;
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
    });

    pg.selectionInfoHtml = function () {
        var byLayer = {},
            html = '';

        Object.keys(pg.selection).forEach(function (k) {
            var p = pg.selection[k];
            if (!byLayer[p.layerName])
                byLayer[p.layerName] = [];
            byLayer[p.layerName].push(p);
        });

        Object.keys(byLayer).sort().forEach(function (layerName) {
            html += Gbd.format('<h1>${0}</h1>', layerName);

            var ps = byLayer[layerName],
                rec = Object.assign({}, ps[0].attributes);

            var ignore = ['_geomClass', '_label', 'geometry', 'boundedBy', 'wkt_geometry', 'wkb_geometry'];

            Gbd.option('selection.exclude_fields', '').split(',').forEach(function (f) {
                ignore.push(Gbd.trim(f));
            });

            ignore.forEach(function (k) {
                delete rec[k];
            });

            var keys = Object.keys(rec).sort();

            html += '<table class="border"><thead><tr>';
            keys.forEach(function (k) {
                html += Gbd.format('<td>${0}</td>', k);
            });
            html += '</tr></thead><tbody>';

            ps.forEach(function (p) {
                html += '<tr>';
                keys.forEach(function (k) {
                    var t = p.attributes[k] || '';

                    if (String(t).match(/^https?:/)) {
                        t = Gbd.format('<a href="${0}" target="_blank">${0}</a>', t);
                    }

                    html += Gbd.format('<td>${0}</td>', t);
                });
                html += '</tr>';
            });

            html += '</tbody></table>';
        });

        return html;
    };

    pg.on('showSelectionInfo', function (event) {
        if (Object.keys(pg.selection).length === 0)
            return '';
        Gbd.send('showInfoBox', {
            type: 'selection_info',
            html: pg.selectionInfoHtml()
        });
    });

    pg.on('printInfoBox', function (event) {
        if (event.type !== 'selection_info') {
            return;
        }

        var params = {
            plugin: pg.name,
            cmd: 'print'
        };

        Gbd.send('doPrint', {
            params: params,
            data: {html: pg.selectionInfoHtml()}
        });
    });


})();