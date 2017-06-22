(function () {

    var pg = Gbd.plugin('select_tools');

    pg._layer = null;
    pg._mode = 'point';
    pg._propNames = {};
    pg._wfsMaxCount = 2000;

    pg.selectionComplete = function (geometry) {
        Gbd.WFS.request(geometry, false, pg._wfsMaxCount).then(function (features) {
            features.forEach(function(f) {
                f.layerName = Gbd.WFS.layerName(f.fid);
                Gbd.WFS.renameAttributes(f, f.layerName);
            });
            Gbd.send('selectFeatures', {features: features});
        }).catch(function(err) {
            // just don't select anything


        })
    };

    pg.removeLayer = function () {
        if (pg._layer) {
            try {
                Gbd.map().removeLayer(pg._layer);
            } catch (e) {
                // @TODO
                // layer might not be attached yet
            }
        }
        pg._layer = null;
    };

    pg.removeControl = function () {
        if (pg._control) {
            pg._control.deactivate();
            Gbd.map().removeControl(pg._control);
        }
        pg._control = null;
    };

    pg.layer = function () {
        if (pg._layer)
            return pg._layer;
        pg._layer = new OpenLayers.Layer.Vector('selectToolLayer', {
            styleMap: new OpenLayers.StyleMap({
                'default': {
                    strokeColor: "#000099",
                    strokeOpacity: 1,
                    strokeWidth: 1,
                    strokeDashstyle: "dot",
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

        pg._layer.events.register('featureadded', pg._layer, function () {
            var layer = pg._layer;
            //layer.removeFeatures(layer.features.slice(0, -1));
            var geom = layer.features[0].geometry;
            pg.clearLayer();
            pg.selectionComplete(geom);
        });

        return pg._layer;
    };

    pg.clearLayer = function () {
        if (pg._layer)
            pg._layer.removeAllFeatures();

    };

    pg.control = function (mode) {
        if (pg._control)
            return pg._control;

        var la = this.layer();

        switch (mode) {
            case 'point':
                return pg._control = new OpenLayers.Control.DrawFeature(la, OpenLayers.Handler.Point);
            case 'line':
                return pg._control = new OpenLayers.Control.DrawFeature(la, OpenLayers.Handler.Path);
            case 'polygon':
                return pg._control = new OpenLayers.Control.DrawFeature(la, OpenLayers.Handler.Polygon);
            case 'rectangle':
                return pg._control = new OpenLayers.Control.DrawFeature(la, OpenLayers.Handler.RegularPolygon,
                    {
                        handlerOptions: {sides: 4, irregular: true},
                    });
            case 'circle':
                return pg._control = new OpenLayers.Control.DrawFeature(la, OpenLayers.Handler.RegularPolygon,
                    {
                        handlerOptions: {sides: 150},
                    });
        }
    };

    pg.initEvents = function () {
        Ext.getCmp('selectionSelectToolMenu').on('click', function (menu, item) {
            Ext.getCmp('selectionSelectTool').setIcon(item.icon);
            pg._mode = item.mode;
            Ext.getCmp('selectionSelectTool').toggle(true);
            pg.removeControl();
            Gbd.map().addControl(pg.control(pg._mode));
            pg.control().activate();
        });


        Ext.getCmp('selectionSelectTool').on('toggle', function (btn) {

            pg.removeControl();

            if (!btn.pressed) {
                pg.removeLayer();
                return;
            }

            pg.removeLayer();
            Gbd.map().addLayer(pg.layer());

            pg.removeControl();
            Gbd.map().addControl(pg.control(pg._mode));
            pg.control().activate();

        });

        Ext.getCmp('selectionDeselectTool').on('click', function (btn) {
            Gbd.send('deselectAll');
        });

        Ext.getCmp('selectionZoomTool').on('click', function (btn) {
            Gbd.send('zoomToSelection');
        });

        Ext.getCmp('selectionInfoTool').on('click', function (btn) {
            Gbd.send('showSelectionInfo');
        });

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

    var ui = {
        "items": [
            {
                "xtype": "tbseparator"
            },
            {
                "xtype": "button",
                "tooltip": "Auswählen",
                "enableToggle": true,
                "icon": "icons/mActionSelectPoint.png",
                "allowDepress": true,
                "tooltipType": "qtip",
                "iconCls": "",
                "toggleGroup": "mapTools",
                "id": "selectionSelectTool",
                "scale": "medium"
            },
            {
                "xtype": "button",
                "menu": {
                    "id": "selectionSelectToolMenu",
                    "items": [
                        {
                            "id": "selectionSelectToolPoint",
                            "text": "Objekte über Einzelklick wählen",
                            "mode": "point",
                            "icon": "icons/mActionSelectPoint.png"
                        },
                        {
                            "id": "selectionSelectToolPolygon",
                            "text": "Objekte über Polygon wählen",
                            "mode": "polygon",
                            "icon": "icons/mActionSelectPolygon.png"
                        },
                        {
                            "id": "selectionSelectToolRectangle",
                            "text": "Objekte über Rechteck wählen",
                            "mode": "rectangle",
                            "icon": "icons/mActionSelectRectangle.png"
                        }
                    ]
                }
            },
            {
                "xtype": "button",
                "tooltip": "Zur Auswahl hinzoomen",
                "enableToggle": false,
                "icon": "icons/mActionZoomToSelected.png",
                "allowDepress": false,
                "tooltipType": "qtip",
                "iconCls": "",
                "id": "selectionZoomTool",
                "scale": "medium"
            },
            {
                "xtype": "button",
                "tooltip": "Infos anzeigen",
                "enableToggle": false,
                "icon": "icons/sub_selection.png",
                "allowDepress": false,
                "tooltipType": "qtip",
                "iconCls": "",
                "id": "selectionInfoTool",
                "scale": "medium"
            },
            {
                "xtype": "button",
                "tooltip": "Auswahl entfernen",
                "enableToggle": false,
                "icon": "icons/mActionDeselectAll.png",
                "allowDepress": false,
                "tooltipType": "qtip",
                "iconCls": "",
                "id": "selectionDeselectTool",
                "scale": "medium"
            }
        ]
    };


    pg.on('toolbarLoad', function (event) {
        var toolbar = Ext.getCmp('myTopToolbar');
        resolveAssetPaths(ui);
        ui.items.forEach(function (item) {
            toolbar.add(item);
        });
        pg.initEvents();
    });


})();
