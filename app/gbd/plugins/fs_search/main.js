(function () {

    var pg = Gbd.plugin('fs_search');

    var STRINGS = {
        errorTitle: 'Fehler',
        errorText: 'Das Flurstück konnte nicht gefunden werden',
        layerName: 'Flurstücke',
        status: {
            'x': 'X',
            'y': 'Y',
            'area': 'Fläche',
            'length': 'Länge',
            'width': 'Breite',
            'height': 'Höhe',
        }
    };

    var localData = {
        fs: [],
        strassenAll: [],
        strassen: {},
        gemarkung: []
    };

    function highlightFs(fs) {
        Gbd.send('setMarker', {wkt: fs.wkt_geometry});
    }

    function handleQueryStringRequest() {
        var keys = [
            'gemarkungsnummer',
            'flurnummer',
            'zaehler',
            'nenner',
            'flurstuecksfolge'
        ];

        var qs = OpenLayers.Util.getParameters(),
            params = {};

        keys.forEach(function (k) {
            if (k in qs) {
                params[k] = qs[k];
            }
        });

        if (Object.keys(params).length === 0) {
            return;
        }

        pg.http('details', params).then(function (fs) {
            if (!fs) {
                Ext.Msg.alert(
                    STRINGS.errorTitle,
                    STRINGS.errorText
                );
                return;
            }
            highlightFs(fs);
        });

    }

    // http://forums.ext.net/showthread.php?25070-CLOSED-CompositeField-and-BasicForm-getFieldValues
    function getFieldValues(form, dirtyOnly, keyField) {
        var o = {},
            n,
            key,
            val,
            addField = function (f) {
                if (dirtyOnly !== true || f.isDirty()) {
                    n = keyField ? f[keyField] : f.getName();
                    key = o[n];
                    val = f.getValue();

                    if (Ext.isDefined(key)) {
                        if (Ext.isArray(key)) {
                            o[n].push(val);
                        } else {
                            o[n] = [key, val];
                        }
                    } else {
                        o[n] = val;
                    }
                }
            };

        form.items.each(function (f) {
            if (f.isComposite && f.eachItem && f.getValue === Ext.form.Field.prototype.getValue) {
                f.eachItem(function (cf) {
                    addField(cf);
                });
            } else {
                addField(f);
            }
        });
        return o;
    }

    function shortDescription(fs) {
        var s = '';

        if (fs.flurnummer) {
            s += fs.flurnummer + '-';
        }

        if (fs.zaehler) {
            s += fs.zaehler;
        }

        if (fs.nenner) {
            s += '/' + fs.nenner;
        }

        return s;
    }

    function makeSearchRequest(params, zoomToResult) {
        pg.http('find', params).then(function (res) {
            localData.fs = res;

            Ext.getCmp('fsSearchResultsPanel').store.loadData(res.map(function (fs) {
                return [fs.gml_id, shortDescription(fs), fs.gemarkung];
            }));

            Gbd.send('setMarker', {
                wkt: res.map(function (r) {
                    return r.wkt_geometry
                }),
                'static': !zoomToResult
            });

            Ext.getCmp('fsSearchResultText').setText(res.length + ' von ' + localData.count);
        });

    }

    function doSubmit() {
        var params = getFieldValues(Ext.getCmp('fsSearchForm').getForm());
        makeSearchRequest(params, true);
    }

    function disableStrasse(disabled) {
        Ext.getCmp('fsSearchStrasseCombo').setDisabled(disabled);
        Ext.getCmp('fsSearchStrasseNr').setDisabled(disabled);
    }

    function doInit() {
        Ext.getCmp('fsSearchForm').getForm().reset();
        Ext.getCmp('fsSearchStrasseCombo').store.loadData([[]]);
        Ext.getCmp('fsSearchResultsPanel').store.loadData([]);
        Ext.getCmp('fsSearchResultText').setText('');
        updateStrassen(0);
    }

    function doReset() {
        doInit();
        Gbd.send('clearMarker');
        Gbd.send('hideFsDetails');
        spatialSearch.reset();
    }

    function resolveAssetPaths(obj) {
        Object.keys(obj).forEach(function (k) {
            var v = obj[k];
            if (k === 'icon' && typeof v === 'string') {
                obj[k] = pg.assetURL(v);
                return;
            }
            if (typeof v === 'object') {
                resolveAssetPaths(v);
            }
        });
    }

    function updateStrassen(gemarkungsnummer) {
        var ct = Ext.getCmp('fsSearchStrasseCombo');

        ct.clearValue();
        gemarkungsnummer = Number(gemarkungsnummer);

        ct.store.loadData(localData.strassenAll.filter(function(s) {
            return !gemarkungsnummer || s[1].indexOf(gemarkungsnummer) >= 0;
        }).map(function(s) {
            return [s[0]];
        }));
    }

    function loadStrassen(gemarkungsnummer) {
        if (gemarkungsnummer in localData.strassen) {
            return Promise.resolve(localData.strassen[gemarkungsnummer]);
        }
        return pg.http('strassen', {gemarkungsnummer: gemarkungsnummer}).then(function (res) {
            return localData.strassen[gemarkungsnummer] = res;
        });
    }

    function gemarkungSelected(gemarkungsnummer) {
        updateStrassen(gemarkungsnummer);
    }

    function selectFeatures(flist) {
        flist = flist.map(function(f) {
            return {
                geometry: f.wkt_geometry,
                layerName: STRINGS.layerName,
                attributes: f
            }
        });
        Gbd.send('selectFeatures', {features: flist});
    }

    pg.on('featuresSelected', function(e) {
        var gmlIds = e.features.map(function(f) {
            return f.attributes.gml_id;
        }).filter(Boolean);

        var rows = [];
        localData.fs.forEach(function(f, n) {
            if(gmlIds.indexOf(f.gml_id) >= 0) {
                rows.push(n);
            }
        });

        try {
            var sm = Ext.getCmp('fsSearchResultsPanel').getSelectionModel();
            sm.selectRows(rows);
        } catch(e) {

        }
    });

    function initUI(with_owner) {

        pg.http('ui.json').then(function (res) {

            resolveAssetPaths(res);

            Ext.getCmp('collapsiblePanels').insert(1, res);
            Ext.getCmp('LeftPanel').doLayout();

            Ext.getCmp('fsSearchResultsPanel').store = new Ext.data.ArrayStore({
                fields: ['', 'kennzeichen', 'gemarkung']
            });

            Ext.getCmp('fsSearchStrasseCombo').store = new Ext.data.ArrayStore({
                fields: ['name']
            });

            Ext.getCmp('fsSearchGemarkungCombo').store = new Ext.data.ArrayStore({
                fields: ['id', 'name']
            });

            Ext.getCmp('fsSearchResultsPanel').on('cellclick', function (grid, rowIndex, columnIndex, e) {
                var fs = localData.fs[rowIndex];

                if (columnIndex === 0) {
                    selectFeatures([fs]);
                } else {
                    highlightFs(fs);
                    Gbd.send('showFsDetails', {gml_id: fs.gml_id});
                }
            });

        }).then(function (res) {

            if (!with_owner) {
                Ext.getCmp('fsSearchNachname').hide();
                Ext.getCmp('fsSearchVorname').hide();
                Ext.getCmp('fsSearchFormPanel').setHeight(310);
            }

        }).then(function () {

            return pg.http('gemarkungen')

        }).then(function (res) {
            localData.gemarkung = {
                list: res,
                name: {}
            };

            res.forEach(function (r) {
                localData.gemarkung.name[r[0]] = r[1];
            });

            var gc = Ext.getCmp('fsSearchGemarkungCombo');

            gc.valueField = 'id';
            gc.displayField = 'name';

            gc.store.loadData(res);

            gc.on('select', function (gc, rec, index) {
                gemarkungSelected(localData.gemarkung.list[index][0]);
            });

            gc.on('change', function (gc, val) {
                gemarkungSelected(val);
            });

            var sc = Ext.getCmp('fsSearchStrasseCombo');

            sc.valueField = 'name';
            sc.displayField = 'name';

        }).then(function() {

            return pg.http('strasse_all')

        }).then(function(res) {

            localData.strassenAll = res.sort(function(a, b) {
                return a[0].localeCompare(b[0]);
            });

        }).then(function () {

            Ext.getCmp('fsSearchSearchButton').on('click', doSubmit);
            Ext.getCmp('fsSearchResetButton').on('click', doReset);

            Ext.getCmp('fsSearchSelectAllButton').on('click', function () {
                selectFeatures(localData.fs);
            });

            Ext.getCmp('fsSearchForm').items.each(function (f) {
                f.on('specialkey', function (f, evt) {
                    if (evt.getKey() === 13) {
                        doSubmit();
                    }
                    if (evt.getKey() === 27) {
                        doReset();
                    }
                });
            });

            Ext.getCmp('fsSearchDrawTools').items.each(function (f) {
                f.on('click', function (btn) {
                    spatialSearch.click(btn)
                });
            });


        }).then(function () {

            Ext.getCmp('LeftPanel').doLayout();

            if (Gbd.option('fs_search.expand'))
                Ext.getCmp('fsSearchPanel').expand();

        }).then(function () {

            return pg.http('count')

        }).then(function (res) {

            localData.count = res['count'];

        }).then(doInit);
    }

    ////

    var spatialSearch = {};

    spatialSearch.removeLayer = function () {
        if (this._layer) {
            try {
                Gbd.map().removeLayer(this._layer);
            } catch (e) {
                // @TODO
                // layer might not be attached yet
            }
        }
        this._layer = null;
        spatialSearch.showStatus({});
    };

    spatialSearch.removeControl = function () {
        if (this._control) {
            this._control.deactivate();
            Gbd.map().removeControl(this._control);
        }
        this._control = null;
    };

    spatialSearch.layer = function () {
        if (this._layer)
            return this._layer;
        this._layer = new OpenLayers.Layer.Vector('fsSearchSpatialLayer', {
            styleMap: new OpenLayers.StyleMap({
                'default': {
                    strokeColor: "#000099",
                    strokeOpacity: 1,
                    strokeWidth: 3,
                    strokeDashstyle: "longdash",
                    fillColor: "#000099",
                    fillOpacity: 0.1,
                    pointRadius: 3,
                    pointerEvents: "visiblePainted",
                    cursor: "move",
                    fontColor: "#333333",
                    fontSize: "12px",
                    fontFamily: "helvetica, sans-serif",
                    fontWeight: "normal",
                    label: '',
                }
            })
        });

        this._layer.events.register('featureadded', this._layer, function () {
            var layer = spatialSearch._layer;
            layer.removeFeatures(layer.features.slice(0, -1));
            makeSearchRequest({
                bounds: layer.features[0].geometry.toString()
            })
        });

        return this._layer;
    };

    spatialSearch.clearLayer = function () {
        if (this._layer)
            this._layer.removeAllFeatures();

    };

    spatialSearch.showStatus = function(status) {
        var html = '';

        Object.keys(status).forEach(function(k) {
            var v = status[k],
                unit = '';

            if(!v)
                return;

            if(k == 'area') {
                unit = 'm²';
                if(v >= 1e5) {
                    v /= 1e6;
                    unit = 'km²';
                }
            }

            if(k == 'length' || k == 'width' || k == 'height') {
                unit = 'm';
                if(v >= 500) {
                    v /= 1000;
                    unit = 'km';
                }
            }

            html += '<b>' + STRINGS.status[k] + '</b>:&nbsp;' + v.toFixed(2) + unit + '. ';
        });

        Ext.getCmp('fsSearchSpatialInfo').update('<div style="padding-top: 5px; font-size: 10px">' + html + '</div>');

    };

    spatialSearch.updateStatus = function(feature) {
        spatialSearch.showStatus(spatialSearch.status(feature));
    };

    spatialSearch.status = function(feature) {
        var status = {};

        try {
            status.x = feature.geometry.x;
            status.y = feature.geometry.y;
        } catch (e) {
        }

        try {
            status.length = feature.getLength();
        } catch(e) {
        }

        try {
            status.area = feature.getArea();
        } catch(e) {
        }

        try {
            var b = feature.getBounds();
            status.width = b.right - b.left;
            status.height = b.top - b.bottom;
        } catch(e) {
        }
        return status;
    }

    spatialSearch.control = function (id) {
        if (this._control)
            return this._control;
        switch (id) {
            case 'fsSearchDrawPoint':
                return this._control = new OpenLayers.Control.DrawFeature(
                    this.layer(),
                    OpenLayers.Handler.Point,
                    {
                        callbacks: {
                            create: function(_, feature) {
                                spatialSearch.updateStatus(feature);
                            }
                        }
                    });
            case 'fsSearchDrawLine':
                return this._control = new OpenLayers.Control.DrawFeature(
                    this.layer(),
                    OpenLayers.Handler.Path,
                    {
                        callbacks: {
                            point: function (_, feature) {
                                spatialSearch.updateStatus(feature);
                            }
                        }
                    });
            case 'fsSearchDrawPolygon':
                return this._control = new OpenLayers.Control.DrawFeature(
                    this.layer(),
                    OpenLayers.Handler.Polygon,
                    {
                        callbacks: {
                            point: function (_, feature) {
                                spatialSearch.updateStatus(feature);
                            }
                        }
                    });
            case 'fsSearchDrawBox':
                return this._control = new OpenLayers.Control.DrawFeature(
                    this.layer(),
                    OpenLayers.Handler.RegularPolygon,
                    {
                        handlerOptions: {sides: 4, irregular: true},
                        callbacks: {
                            move: function (feature) {
                                spatialSearch.updateStatus(feature);
                            }
                        }
                    });
            case 'fsSearchDrawCircle':
                return this._control = new OpenLayers.Control.DrawFeature(
                    this.layer(),
                    OpenLayers.Handler.RegularPolygon,
                    {
                        handlerOptions: {sides: 150},
                        callbacks: {
                            move: function (feature) {
                                spatialSearch.updateStatus(feature);
                            }
                        }
                    });
            case 'fsSearchDrawDrag':
                this._control = new OpenLayers.Control.DragFeature(
                    this.layer(),
                    {
                        multiple: false,
                        clickout: true,
                    });
                this._control.onComplete = function () {
                    makeSearchRequest({
                        bounds: spatialSearch.layer().features[0].geometry.toString()
                    })
                }
                return this._control;

        }
    };

    spatialSearch.click = function (btn) {

        this.removeControl();

        if (!btn.pressed) {
            this.removeLayer();
            return;
        }

        if (btn.id !== 'fsSearchDrawDrag') {
            this.removeLayer();
            Gbd.map().addLayer(this.layer());
        }

        this.removeControl();
        Gbd.map().addControl(this.control(btn.id));
        this.control().activate();
    };

    spatialSearch.reset = function() {
        this.removeControl();
        this.removeLayer();
        Ext.getCmp('fsSearchDrawTools').items.each(function (f) {
            f.toggle(false);
        });
    };


    //

    pg.on('toolbarLoad', function (event) {
        pg.http('check_enabled', {nocache: Math.random()})
            .then(function(res) {
                if(res.enabled) {
                    initUI(res.enabled_owner);
                }
            });
    });

    pg.on('afterMapInit', function (event) {
        pg.http('check_enabled', {nocache: Math.random()})
            .then(function(res) {
                if(res.enabled) {
                    handleQueryStringRequest();
                }
            });

    });


})();