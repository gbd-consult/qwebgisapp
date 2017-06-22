// ZMF plugin

(function () {

    var pg = Gbd.plugin('zmf');

    var STRINGS = {
        loading: 'WFS wird geladen...',
        error: 'Fehler!',
        httpError: 'Es ist ein Serverfehler aufgetreten',
        overflowError: 'Zu viele Ergebnisse, bitte die Suche weiter einschränken'
    };

    var CIRCLE_SIDES = 80;
    var MAX_WFS_COUNT = 500;

//////////////////////////////////////////////////////////////////////////////////
////////////// Create Layer and Event handling for ZMF Layer /////////////////////

    function initZMFLayer() {
        var renderer = OpenLayers.Util.getParameters(window.location.href).renderer;
        renderer = (renderer) ? [renderer] : OpenLayers.Layer.Vector.prototype.renderers;

        var zmf_styleMap = new OpenLayers.StyleMap({
            'default': {
                strokeColor: "#DBA400",
                strokeOpacity: 1,
                strokeWidth: 1,
                fillColor: "#DBA400",
                fillOpacity: 0.3,
                pointRadius: 5,
                // pointerEvents: "visiblePainted",// label with \n linebreaks
                label: "${labelInfos}",
                fontColor: "#333333",
                fontSize: "12px",
                fontFamily: "helvetica, sans-serif",
                fontWeight: "normal",
                labelOutlineColor: "white",
                labelOutlineWidth: 3
                //labelAlign: "${align}",//labelXOffset: "${xOffset}",//labelYOffset: "${yOffset}",
            }
        });
        var zmfHighlightStyleMap = new OpenLayers.StyleMap({
            'default': {
                strokeColor: "yellow",
                strokeOpacity: 1,
                strokeWidth: 2,
                fillColor: "#DBA400",
                fillOpacity: 0,
                pointRadius: 5,
                label: "${label}",
                fontColor: "#333333",
                fontSize: "12px",
                fontFamily: "helvetica, sans-serif",
                fontWeight: "normal",
                labelOutlineColor: "white",
                labelOutlineWidth: 3
            }
        });

        pg.zmfLayer = new OpenLayers.Layer.Vector("ZMF Layer", {styleMap: zmf_styleMap, renderers: renderer});
        var zmfHighlightLayer = new OpenLayers.Layer.Vector("ZMF highlight Layer", {
            styleMap: zmfHighlightStyleMap,
            renderers: renderer
        });
        //var zmf_radiusLayer = new OpenLayers.Layer.Vector("ZMF Radius Layer");
        //var zmf_labelLayer = new OpenLayers.Layer.Vector("ZMF Label Layer");

        geoExtMap.map.addLayers([zmfHighlightLayer, pg.zmfLayer]);

        // callback functions for measurements while drawing
        pg.zmfDrawCallbacks = {
            line: {
                "point": function (vertex, feature) {
                    var length = feature.getLength();
                    var fixedlength = length.toFixed(2) + ' m';
                    if (length > 999) {
                        fixedlength = (length / 1000).toFixed(3) + ' km';
                    }
                    var htmlContent = 'Länge: ' + fixedlength;
                    Ext.getCmp('zmfMeasurementInfo' + zmfFeatureID.substr(4)).update(htmlContent);
                }
            },
            polygon: {
                "point": function (vertex, feature) {
                    var length = feature.getLength();
                    var area = feature.getArea();
                    var fixedArea = area.toFixed(2) + ' m²';
                    var fixedLength = length.toFixed(2) + ' m';
                    if (area > 999999) {
                        fixedArea = (area / 1000000).toFixed(3) + ' km²';
                    }
                    if (length > 999) {
                        fixedLength = (length / 1000).toFixed(3) + ' km';
                    }
                    var htmlContent = 'Umfang: ' + fixedLength + '<br>Fläche: ' + fixedArea;
                    Ext.getCmp('zmfMeasurementInfo' + zmfFeatureID.substr(4)).update(htmlContent);
                }
            },
            box: {
                "move": function (e) {
                    var linearRing = new OpenLayers.Geometry.LinearRing(e.components[0].components);
                    var geometry = new OpenLayers.Geometry.Polygon([linearRing]);
                    var polygonFeature = new OpenLayers.Feature.Vector(geometry, null);
                    f = polygonFeature;
                    var bounds = f.geometry.getBounds();
                    // make points from bbox-corners: tl = topleft
                    var p_tl = new OpenLayers.Geometry.Point(bounds.left, bounds.top);
                    var p_tr = new OpenLayers.Geometry.Point(bounds.right, bounds.top);
                    var p_bl = new OpenLayers.Geometry.Point(bounds.left, bounds.bottom);
                    //var p_br = new OpenLayers.Geometry.Point(bounds.right,bounds.bottom);

                    var minX = f.geometry.getBounds().left;
                    var minY = f.geometry.getBounds().bottom;
                    var maxX = f.geometry.getBounds().right;
                    var maxY = f.geometry.getBounds().top;
                    //calculate the center coordinates
                    var startX = (minX + maxX) / 2;
                    var startY = (minY + maxY) / 2;

                    var width = p_tl.distanceTo(p_tr);
                    var height = p_tl.distanceTo(p_bl);
                    var area = polygonFeature.geometry.getArea();
                    var circumference = f.geometry.getLength();
                    var fixedWidth = width.toFixed(2) + ' m';
                    if (width > 999) {
                        fixedWidth = (width / 1000).toFixed(3) + ' km';
                    }
                    var fixedHeight = height.toFixed(2) + ' m';
                    if (height > 999) {
                        fixedHeight = (height / 1000).toFixed(3) + ' km';
                    }
                    var fixedCircumference = circumference.toFixed(2) + ' m';
                    if (circumference > 999) {
                        fixedCircumference = (circumference / 1000).toFixed(3) + ' km';
                    }
                    var fixedArea = area.toFixed(2) + ' m²';
                    if (area > 999999) {
                        fixedArea = (area / 1000000).toFixed(3) + ' km²';
                    }
                    var htmlContent = 'Breite: ' + fixedWidth + ' - Höhe: ' + fixedHeight + '<br>Umfang: ' + fixedCircumference + '<br>Fläche: ' + fixedArea;
                    Ext.getCmp('zmfMeasurementInfo' + zmfFeatureID.substr(4)).update(htmlContent);
                }

            },
            circle: {
                "move": function (e) {
                    var linearRing = new OpenLayers.Geometry.LinearRing(e.components[0].components);
                    var geometry = new OpenLayers.Geometry.Polygon([linearRing]);
                    var polygonFeature = new OpenLayers.Feature.Vector(geometry, null);
                    var polybounds = polygonFeature.geometry.getBounds();
                    var minX = polybounds.left;
                    var minY = polybounds.bottom;
                    var maxX = polybounds.right;
                    var maxY = polybounds.top;

                    //calculate the center coordinates
                    var startX = (minX + maxX) / 2;
                    var startY = (minY + maxY) / 2;
                    //make two points at center and at the edge
                    var startPoint = new OpenLayers.Geometry.Point(startX, startY);
                    var endPoint = new OpenLayers.Geometry.Point(maxX, startY);
                    var radius = new OpenLayers.Geometry.LineString([startPoint, endPoint]);
                    //var len = Math.round(radius.getLength()).toString();
                    var radiuslength = Math.round(radius.getLength());
                    var area = radiuslength * radiuslength * Math.PI;
                    var circumference = (2 * radiuslength * Math.PI);
                    var fixedRadius = radiuslength.toFixed(2) + ' m';
                    if (radiuslength > 999) {
                        fixedRadius = (radiuslength / 1000).toFixed(3) + ' km';
                    }
                    var fixedCircumference = circumference.toFixed(3) + ' m';
                    if (circumference > 999) {
                        fixedCircumference = (circumference / 1000).toFixed(3) + ' km';
                    }
                    var fixedArea = area.toFixed(2) + ' m²';
                    if (area > 999999) {
                        fixedArea = (area / 1000000).toFixed(3) + ' km²';
                    }
                    var htmlContent = 'Radius: ' + fixedRadius + '<br>Umfang: ' + fixedCircumference + '<br>Fläche: ' + fixedArea;
                    Ext.getCmp('zmfMeasurementInfo' + zmfFeatureID.substr(4)).update(htmlContent);
                }
            }
        }

        // Controls for different Geometry Types within pg.zmfLayer
        pg.zmfDrawControls = {
            point: new OpenLayers.Control.DrawFeature(pg.zmfLayer,
                OpenLayers.Handler.Point),
            line: new OpenLayers.Control.DrawFeature(pg.zmfLayer,
                OpenLayers.Handler.Path, {
                    callbacks: pg.zmfDrawCallbacks.line
                }),
            polygon: new OpenLayers.Control.DrawFeature(pg.zmfLayer,
                OpenLayers.Handler.Polygon, {
                    callbacks: pg.zmfDrawCallbacks.polygon
                }),
            box: new OpenLayers.Control.DrawFeature(pg.zmfLayer,
                OpenLayers.Handler.RegularPolygon, {
                    handlerOptions: {sides: 4, irregular: true}, callbacks: pg.zmfDrawCallbacks.box
                }),
            circle: new OpenLayers.Control.DrawFeature(pg.zmfLayer,
                OpenLayers.Handler.RegularPolygon, {
                    handlerOptions: {sides: CIRCLE_SIDES}, callbacks: pg.zmfDrawCallbacks.circle
                })
        };

        // What happens when new feature is added:
        pg.zmfLayer.events.register('featureadded', pg.zmfLayer, onAddedNewFeature);

        function onAddedNewFeature(ev) {
            var geomType = null;

            for (var f = 0; f < pg.zmfLayer.features.length; f++) {
                if (pg.zmfLayer.features[f].attributes.fIdentifier == zmfFeatureID) {
                    geomType = pg.zmfLayer.features[f].attributes.geomType;
                    pg.zmfLayer.removeFeatures(pg.zmfLayer.features[f]);
                    break;
                }
            }

            geomType = geomType || zmfGeomType;

            var labelInfotext = '';
            ev.feature.attributes = {fIdentifier: zmfFeatureID, labelInfos: labelInfotext, geomType: geomType};

            var delimiter = '\n\n';

            if (geomType == 'point') {
                var easting = (ev.feature.geometry.x).toFixed(2);
                var northing = (ev.feature.geometry.y).toFixed(2);
                var labelInfotext = '';
                if (Ext.getCmp("cb_measurements_" + zmfFeatureID.substr(4)).checked == true) {
                    labelInfotext += 'Ostwert: ' + easting + '\n' + 'Nordwert: ' + northing;
                }
                else {
                }
                if (Ext.getCmp("cb_notes_" + zmfFeatureID.substr(4)).checked == true) {
                    labelInfotext += delimiter + Ext.getCmp("notes_" + zmfFeatureID.substr(4)).getValue();
                }
                else {
                }
                ev.feature.attributes.labelInfos = Gbd.trim(labelInfotext);
                Ext.getCmp('easting_' + ev.feature.attributes.fIdentifier.substr(4)).setValue(easting);
                Ext.getCmp('northing_' + ev.feature.attributes.fIdentifier.substr(4)).setValue(northing);
                this.redraw(true);
            }
            else if (geomType == 'line') {
                var labelInfotext = '';
                // check the checkboxes for labeling of layer
                if (Ext.getCmp("cb_measurements_" + zmfFeatureID.substr(4)).checked == true) {
                    labelInfotext += Ext.getCmp('zmfMeasurementInfo' + zmfFeatureID.substr(4)).getEl().dom.innerHTML;
                }
                if (Ext.getCmp("cb_notes_" + zmfFeatureID.substr(4)).checked == true) {
                    labelInfotext += delimiter + Ext.getCmp("notes_" + zmfFeatureID.substr(4)).getValue();
                }
                ev.feature.attributes.labelInfos = Gbd.trim(labelInfotext);
                this.redraw(true);
            }
            else if (geomType == 'polygon') {
                var labelInfotext = '';
                // check the checkboxes for labeling of layer
                if (Ext.getCmp("cb_measurements_" + zmfFeatureID.substr(4)).checked == true) {
                    labelizedHtmlText = Ext.getCmp('zmfMeasurementInfo' + zmfFeatureID.substr(4)).getEl().dom.innerHTML
                    labelizedHtmlText = labelizedHtmlText.replace("<br>", "\n");
                    labelInfotext += labelizedHtmlText;
                }
                if (Ext.getCmp("cb_notes_" + zmfFeatureID.substr(4)).checked == true) {
                    labelInfotext += delimiter + Ext.getCmp("notes_" + zmfFeatureID.substr(4)).getValue();
                }
                ev.feature.attributes.labelInfos = Gbd.trim(labelInfotext);
                this.redraw(true);
            }
            else if (geomType == 'box') {
                f = ev.feature;
                //calculate all necessary measures
                var easting = f.geometry.x;
                var northing = f.geometry.y;
                var bounds = f.geometry.getBounds();
                // make points from bbox-corners: tl = topleft
                var p_tl = new OpenLayers.Geometry.Point(bounds.left, bounds.top);
                var p_tr = new OpenLayers.Geometry.Point(bounds.right, bounds.top);
                var p_bl = new OpenLayers.Geometry.Point(bounds.left, bounds.bottom);
                var p_br = new OpenLayers.Geometry.Point(bounds.right, bounds.bottom);

                var minX = f.geometry.getBounds().left;
                var minY = f.geometry.getBounds().bottom;
                var maxX = f.geometry.getBounds().right;
                var maxY = f.geometry.getBounds().top;
                //calculate the center coordinates
                var startX = (minX + maxX) / 2;
                var startY = (minY + maxY) / 2;

                var width = p_tl.distanceTo(p_tr);
                var height = p_tl.distanceTo(p_bl);
                var area = f.geometry.getArea();
                var circumference = f.geometry.getLength();
                var fixedWidth = width.toFixed(2) + ' m';
                if (width > 999) {
                    fixedWidth = (width / 1000).toFixed(3) + ' km';
                }
                var fixedHeight = height.toFixed(2) + ' m';
                if (height > 999) {
                    fixedHeight = (height / 1000).toFixed(3) + ' km';
                }
                var fixedCircumference = circumference.toFixed(2) + ' m';
                if (circumference > 999) {
                    fixedCircumference = (circumference / 1000).toFixed(3) + ' km';
                }
                var fixedArea = area.toFixed(2) + ' m²';
                if (area > 999999) {
                    fixedArea = (area / 1000000).toFixed(3) + ' km²';
                }

                var labelInfotext = '';
                if (Ext.getCmp("cb_measurements_" + zmfFeatureID.substr(4)).checked == true) {
                    labelInfotext += 'Breite: ' + fixedWidth + '\n' + 'Höhe: ' + fixedHeight + '\n' + 'Umfang: ' + fixedCircumference + '\n' + 'Fläche: ' + fixedArea;
                }
                else {
                }
                if (Ext.getCmp("cb_notes_" + zmfFeatureID.substr(4)).checked == true) {
                    labelInfotext += delimiter + Ext.getCmp("notes_" + zmfFeatureID.substr(4)).getValue();
                }
                else {
                }
                ev.feature.attributes.labelInfos = Gbd.trim(labelInfotext);
                Ext.getCmp('easting_' + ev.feature.attributes.fIdentifier.substr(4)).setValue(minX);
                Ext.getCmp('northing_' + ev.feature.attributes.fIdentifier.substr(4)).setValue(maxY);
                Ext.getCmp('height_' + ev.feature.attributes.fIdentifier.substr(4)).setValue(p_tl.distanceTo(p_bl));
                Ext.getCmp('width_' + ev.feature.attributes.fIdentifier.substr(4)).setValue(p_tl.distanceTo(p_tr));
                var htmlContent = 'Breite: ' + fixedWidth + ' - Höhe: ' + fixedHeight + '<br>Umfang: ' + fixedCircumference + '<br>Fläche: ' + fixedArea;
                Ext.getCmp('zmfMeasurementInfo' + zmfFeatureID.substr(4)).update(htmlContent);
                this.redraw(true);
            }
            else if (geomType == 'circle') {
                var f = ev.feature;
                //calculate the min/max coordinates of the circle
                var minX = f.geometry.getBounds().left;
                var minY = f.geometry.getBounds().bottom;
                var maxX = f.geometry.getBounds().right;
                var maxY = f.geometry.getBounds().top;
                //calculate the center coordinates
                var startX = (minX + maxX) / 2;
                var startY = (minY + maxY) / 2;
                //make two points at center and at the edge
                var startPoint = new OpenLayers.Geometry.Point(startX, startY);
                var endPoint = new OpenLayers.Geometry.Point(maxX, startY);
                // create line from center to border
                var radiusline = new OpenLayers.Geometry.LineString([startPoint, endPoint]);

                //calculate length. WARNING! The EPSG:900913 lengths are meaningless except around the equator. Either use a local coordinate system like UTM, or geodesic calculations.
                // GBD WARNING: since the geometry is no perfect circle but consists of line-segments the calculations are only approximations. Values above 5000 m Radius lead to wrong results
                var radius = Math.ceil(radiusline.getLength());
                var circumference = (2 * radius * Math.PI);
                var area = (radius * radius * Math.PI);
                // calc and set measurement units
                var fixedRadius = radius.toFixed(2) + ' m';
                if (radius > 999) {
                    fixedRadius = (radius / 1000).toFixed(3) + ' km';
                }
                var fixedCircumference = circumference.toFixed(3) + ' m';
                if (circumference > 999) {
                    fixedCircumference = (circumference / 1000).toFixed(3) + ' km';
                }
                var fixedArea = area.toFixed(2) + ' m²';
                if (area > 999999) {
                    fixedArea = (area / 1000000).toFixed(3) + ' km²';
                }

                var labelInfotext = '';
                if (Ext.getCmp("cb_measurements_" + zmfFeatureID.substr(4)).checked == true) {
                    labelInfotext += 'Radius: ' + fixedRadius + '\nUmfang: ' + fixedCircumference + '\nFläche: ' + fixedArea;
                }
                if (Ext.getCmp("cb_notes_" + zmfFeatureID.substr(4)).checked == true) {
                    labelInfotext += delimiter + Ext.getCmp("notes_" + zmfFeatureID.substr(4)).getValue();
                }
                ev.feature.attributes.labelInfos = Gbd.trim(labelInfotext);
                Ext.getCmp('easting_' + ev.feature.attributes.fIdentifier.substr(4)).setValue(startPoint.x);
                Ext.getCmp('northing_' + ev.feature.attributes.fIdentifier.substr(4)).setValue(startPoint.y);
                Ext.getCmp('radius_' + ev.feature.attributes.fIdentifier.substr(4)).setValue(Math.round(startPoint.distanceTo(endPoint)));
                var htmlContent = 'Radius: ' + fixedRadius + '<br>Umfang: ' + fixedCircumference + '<br>Fläche: ' + fixedArea;
                Ext.getCmp('zmfMeasurementInfo' + zmfFeatureID.substr(4)).update(htmlContent);
                this.redraw(true);
            }
        }

        //Function for removal of identical features => only one feature per tab!
        var removeIdenticalFeature = function (layer) {
            for (var f = 0; f < layer.features.length; f++) {
                if (layer.features[f].attributes.fIdentifier == zmfFeatureID) {
                    layer.removeFeatures(layer.features[f]);
                    break;
                }
            }
        }

        for (var key in pg.zmfDrawControls) {
            geoExtMap.map.addControl(pg.zmfDrawControls[key]);
        }

        //document.getElementById('noneToggle').checked = true;
        var zmfFeatureID = '';
        var zmfGeomType = '';

        pg.zmfToggleControl = function (type, tab_id) {
            //Tab_ID = tab_id.substr(4);
            zmfGeomType = type;
            for (key in pg.zmfDrawControls) {
                var control = pg.zmfDrawControls[key];
                if (type == key) {
                    zmfFeatureID = tab_id;
                    control.activate();
                } else {
                    control.deactivate();
                }
            }
        }
    }


//////////////////////////////////////////////////////////////////////////////////
////////////// Create Items and Event handling ZMF-Tool-Tabs /////////////////////

    var wfsQueryTabIndex = 0;

    function addZMFTab(btn) {

        ++wfsQueryTabIndex;
        var tabIdentifier = wfsQueryTabIndex;
        var geometryType = btn.id.substr(9);

        var item_coordPair = {
            xtype: 'compositefield',
            fieldLabel: 'Ostwert, Nordwert',
            cls: 'arrrgh',
            msgTarget: 'side',
            anchor: '0',
            hideMode: 'display',
            defaults: {flex: 1, width: '45%'},
            items: [{
                xtype: 'numberfield',
                labelAlign: 'top',
                emptyText: '1234',
                id: "easting_" + tabIdentifier,
                name: 'last'
            }, {
                xtype: 'numberfield',
                labelAlign: 'top',
                emptyText: '1234',
                id: "northing_" + tabIdentifier,
                name: ''
            }
            ]
        };

        var item_length = {
            xtype: 'numberfield',
            readOnly: true,
            labelAlign: 'left',
            fieldLabel: 'Länge (in m)',
            emptyText: '',
            id: "length_" + tabIdentifier,
            name: ''
        };

        var item_radius = {
            xtype: 'numberfield',
            labelAlign: 'left',
            fieldLabel: 'Radius (in m)',
            emptyText: '',
            width: '95%',
            id: "radius_" + tabIdentifier,
            name: ''
        };

        var item_linebreak = {
            xtype: 'box',
            autoEl: {tag: 'hr'},
            width: '95%'
        };

        var item_widthHeight = {
            xtype: 'compositefield',
            fieldLabel: 'Breite (in m) x Höhe (in m)',
            msgTarget: 'side',
            anchor: '0',
            hideMode: 'display',
            defaults: {flex: 1, xtype: 'numberfield', width: '45%'},
            items: [{
                fieldLabel: 'Breite (m)',
                emptyText: 'Breite',
                id: "width_" + tabIdentifier,
                name: ''
            }, {
                fieldLabel: 'Höhe (m)',
                emptyText: 'Höhe',
                id: "height_" + tabIdentifier,
                name: ''
            }]
        };

        var item_geomButton = {
            xtype: 'button',
            height: '1.5em',
            //width: '120px',
            text: 'Aktualisieren',
            id: 'dogeomUpdate' + tabIdentifier,
            tooltip: 'Objekt aktualisieren',
            enableToggle: false,
            allowDepress: false,
            flex: 0.1,
            listeners: {
                click: function () {
                    refresh_zmf_layer(geometryType, 'tab_' + tabIdentifier);
                }
            }
        };

        var item_measurementBox = new Ext.form.FieldSet({
            title: 'Maße',
            height: 80,
            style: {
                'font-family': 'arial',
                'font-size': '12px',
            },
            items: [{
                xtype: 'box',
                html: 'Bitte Objekt zeichnen!',
                id: 'zmfMeasurementInfo' + tabIdentifier,
            }]
        })

        var item_mapNotes = [{
            xtype: 'compositefield',
            hideLabel: true,
            anchor: '0',
            hideMode: 'display',
            defaults: {flex: 1, width: '45%'},
            items: [{
                id: "cb_measurements_" + tabIdentifier,
                xtype: 'checkbox',
                name: 'name',
                labelSeparator: '',
                hideLabel: true,
                boxLabel: 'Maße in Karte',
                listeners: {
                    check: function (field) {
                        refresh_zmf_layer(geometryType, 'tab_' + tabIdentifier);
                        //refresh_zmf_layer(geometryType, tabIdentifier);
                        /*console.log('change:' + field.id);*/
                    }
                }
            }, {
                id: "cb_notes_" + tabIdentifier,
                xtype: 'checkbox',
                name: 'name',
                labelSeparator: '',
                hideLabel: true,
                boxLabel: 'Bemerkung in Karte',
                listeners: {
                    check: function (field) {
                        /*console.log('change:' + field.id);*/
                        refresh_zmf_layer(geometryType, 'tab_' + tabIdentifier);
                    }
                }
            }]
        }, {
            xtype: 'textarea',
            grow: true,
            hideLabel: true,
            name: 'message',
            width: '95%',
            emptyText: 'Hier Bemerkungen für Objekt eintragen',
            id: "notes_" + tabIdentifier
        }];

        var item_wfsButton = {
            xtype: 'button',
            height: '1.5em',
            //width: '120px',
            text: 'WFS abfragen',
            id: 'doWfsQuery' + tabIdentifier,
            tooltip: 'WFS mit Geometrie abfragen',
            enableToggle: false,
            allowDepress: false,
            flex: 0.1,
            listeners: {
                click: function () {
                    getWfsFeatureList(geometryType, 'tab_' + tabIdentifier);
                }
            }
        };

        var formItems = [];
        var iconString = '';
        switch (geometryType) {
            case 'point':
                formItems.push(item_coordPair, item_mapNotes, item_geomButton, item_linebreak, item_wfsButton);
                iconString = 'mActionSelectPoint';
                break;
            case 'line':
                formItems.push(/*item_length,*/item_measurementBox, item_mapNotes, item_geomButton, item_linebreak, item_wfsButton);
                iconString = 'mActionSelectLine';
                break;
            case 'circle':
                formItems.push(item_coordPair, item_radius, item_measurementBox, item_mapNotes, item_geomButton, item_linebreak, item_wfsButton);
                iconString = 'mActionSelectRadius';
                break;
            case 'box':
                formItems.push(item_coordPair, item_widthHeight, item_measurementBox, item_mapNotes, item_geomButton, item_linebreak, item_wfsButton);
                iconString = 'mActionSelectRectangle';
                break;
            case 'polygon':
                formItems.push(item_measurementBox, item_mapNotes, item_geomButton, item_linebreak, item_wfsButton);
                iconString = 'mActionSelectPolygon';
                break;
        }

        var tab_form = new Ext.FormPanel({
            labelWidth: 60, // label settings here cascade unless overridden
            //url:'save-form.php',
            //frame:true,
            //title: 'Simple Form',
            bodyStyle: 'background-color:#f1f1f1;',
            labelAlign: 'top',
            border: false,
            height: '100%',
            width: '100%',
            id: 'form_' + tabIdentifier,
            bodyStyle: 'padding:5px 5px 5px 5px',
            defaults: {width: '98%',},
            items: [formItems]
        });

        var zmfQueryResponseData = [];
        //Ext.MessageBox.alert(geometryType);
        var reader = new Ext.data.ArrayReader({}, [
            {name: 'layername'},
            {name: 'label'},
            {name: 'bounds'},
            {name: 'alldata'}
        ]);

        var zmfStore = new Ext.data.GroupingStore({
            reader: reader,
            data: zmfQueryResponseData,
            sortInfo: {field: 'layername', direction: "ASC"},
            groupField: 'layername'
        });

        var zmfResultGrid = new Ext.grid.GridPanel({
            id: 'zmfResultGrid' + tabIdentifier,
            width: '98%',
            height: 200,
            store: zmfStore,
            columns: [
                {header: "Aktionen", text: "ID", width: '30%', dataIndex: 'fid'},
                {header: "Objektname", text: "Objektname", width: '70%', dataIndex: 'label'},
            ],
            view: new Ext.grid.GroupingView({
                forceFit: true,
                groupTextTpl: '{text} ({[values.rs.length]} {[values.rs.length > 1 ? "Objekte" : "Objekt"]})'
            })
        });

        var zmfLoadIndicator = new Ext.Panel({
            frame: true,
            width: '98%',
            id: "zmfLoadIndicator",
            html: STRINGS.loading,
            hidden: true,
            bodyStyle: {
                "font-weight": "bold",
                padding: "5px 5px 5px 20px",
                background: "url('" + pg.assetURL('icons/loading.gif') + "') no-repeat left center"
            }
        });


        var imgUrl = pg.assetURL('icons/' + iconString + '.png');
        Ext.getCmp('zmfTabs').add({
            title: '<img src="' + imgUrl + '"> ' + (wfsQueryTabIndex),
            //label used for type-detection of active panel
            label: geometryType,
            //id: 'tab_'+geometryType+tabIdentifier,
            id: 'tab_' + tabIdentifier,
            height: '100%',
            //iconCls: 'tabs',
            //html: html,
            items: [tab_form, zmfResultGrid, zmfLoadIndicator],
            closable: true
            /*,	listeners:{close: function() {alert('Closed')}}
             listeners:{
             close: function() {
             alert('Closed '+geometryType+'_tab_'+tabIdentifier);
             //'zmf_'+geometryType+'Layer'.removeFeatures('zmf_'+geometryType+'Layer'.features[tabIdentifier]);
             }
             }*/
        }).show();
    }

    // Function for refreshing the tabs in ZMF-Tool = update geometry + update tab

    function refresh_zmf_layer(geometryType, tabID) {
        // detect correct layer by name
        var matchingLayer = geoExtMap.map.getLayersByName("ZMF Layer");
        // detect correct feature to update/replace
        for (var f = 0; f < matchingLayer[0].features.length; f++) {
            if (matchingLayer[0].features[f].attributes.fIdentifier == tabID) {
                // replace/move feature by new feature
                if (geometryType == 'point') {
                    // get values from gui, create and add new Point
                    var easting = Ext.getCmp('easting_' + tabID.substr(4)).getValue();
                    var northing = Ext.getCmp('northing_' + tabID.substr(4)).getValue();
                    var newPoint = new OpenLayers.Geometry.Point(easting, northing);
                    var newPoint_feature = new OpenLayers.Feature.Vector(newPoint);
                    matchingLayer[0].addFeatures(newPoint_feature);
                }
                else if (geometryType == 'circle') {
                    // get values from gui, create and add new Circle
                    var easting = Ext.getCmp('easting_' + tabID.substr(4)).getValue();
                    var northing = Ext.getCmp('northing_' + tabID.substr(4)).getValue();
                    var radius = Ext.getCmp('radius_' + tabID.substr(4)).getValue();
                    //create circle (regularpoly with 100 segments) and pass to layer
                    var center = new OpenLayers.Geometry.Point(easting, northing);
                    var newCircle = OpenLayers.Geometry.Polygon.createRegularPolygon(center, radius, CIRCLE_SIDES, 0);
                    var newCircle_feature = new OpenLayers.Feature.Vector(newCircle);
                    matchingLayer[0].addFeatures(newCircle_feature);
                }
                else if (geometryType == 'box') {
                    // get values from gui
                    var minx = Ext.getCmp('easting_' + tabID.substr(4)).getValue();
                    var maxy = Ext.getCmp('northing_' + tabID.substr(4)).getValue();
                    var height = Ext.getCmp('height_' + tabID.substr(4)).getValue();
                    var width = Ext.getCmp('width_' + tabID.substr(4)).getValue();
                    var maxx = minx + width;
                    var miny = maxy - height;
                    //GBD FIXME!! - die berechnung hier ist noch nicht perfekt!
                    /*for (var w = width-30; w <= width; w++){
                     var newx = new OpenLayers.Geometry.Point(minx+w,maxy);
                     //p_ul.distanceTo(newx);
                     //console.log('w: '+w+', distance: '+p_ul.distanceTo(newx));
                     p_ur = newx
                     }*/
                    // make points for corners from min and max values
                    var p_ul = new OpenLayers.Geometry.Point(minx, maxy);
                    var p_ur = new OpenLayers.Geometry.Point(maxx, maxy);
                    var p_br = new OpenLayers.Geometry.Point(maxx, miny);
                    var p_bl = new OpenLayers.Geometry.Point(minx, miny);
                    var p_ul_close = p_ul;
                    var pnt = [];
                    pnt.push(p_ul, p_ur, p_br, p_bl, p_ul_close);

                    // create and add new Box
                    var lR = new OpenLayers.Geometry.LinearRing(pnt);
                    var polygon = new OpenLayers.Geometry.Polygon([lR]);
                    var newRectangle_feature = new OpenLayers.Feature.Vector(polygon);
                    matchingLayer[0].addFeatures(newRectangle_feature);
                }
                else if (geometryType == 'polygon') {
                    // GBD muss nochmal verbessert werden - nur eine Aktualisierung möglich
                    var oldfeature = matchingLayer[0].features[f];
                    var pnt = oldfeature.geometry.components[0]['components'];
                    var lR = new OpenLayers.Geometry.LinearRing(pnt);
                    var polygon = new OpenLayers.Geometry.Polygon([lR]);
                    var newPolygon_feature = new OpenLayers.Feature.Vector(polygon);
                    matchingLayer[0].addFeatures(newPolygon_feature);
                    //matchingLayer[0].removeFeatures(matchingLayer[0].features[f]);
                }
                else if (geometryType == 'line') {
                    var oldfeature = matchingLayer[0].features[f];
                    var pnt = new OpenLayers.Geometry.LineString(oldfeature.geometry.components);
                    var newLine_feature = new OpenLayers.Feature.Vector(pnt);
                    matchingLayer[0].addFeatures(newLine_feature);
                    //matchingLayer[0].removeFeatures(matchingLayer[0].features[f]);
                }
                break;
            }
        }
    }

    function deleteZmfTabFeature(geometryType, tabID) {
        var matchingLayer = geoExtMap.map.getLayersByName("ZMF Layer");
        for (var f = 0; f < matchingLayer[0].features.length; f++) {
            if (matchingLayer[0].features[f].attributes.fIdentifier == tabID) {
                matchingLayer[0].removeFeatures(matchingLayer[0].features[f]);
                pg.zmfToggleControl('no control');
                break;
            }
        }
    }

    // Ask for all queryable features intersecting current feature in ZMF-Tab and create list from response
    function getWfsFeatureList(geometryType, tabID) {
        var matchingLayer = geoExtMap.map.getLayersByName("ZMF Layer");
        // detect correct feature to update/replace
        for (var f = 0; f < matchingLayer[0].features.length; f++) {
            if (matchingLayer[0].features[f].attributes.fIdentifier == tabID) {
                // replace/move feature by new feature
                myfeature = matchingLayer[0].features[f];
            }
        }

        function myhandler(features) {
            var zmfQueryResponseData = [];
            var fWfsModel = new Ext.grid.ColumnModel([
                {
                    header: "Aktionen",
                    xtype: 'actioncolumn',
                    width: 60,
                    padding: 0,
                    margin: 0,
                    items: [{	// button for zoom to feature
                        icon: pg.assetURL('icons/mActionZoomToLayer.png'),
                        tooltip: 'Zoom auf Object',
                        handler: function (grid, rowIndex) {
                            var rec = grid.getStore().getAt(rowIndex);
                            var bounds = rec.get('bounds');
                            geoExtMap.map.zoomToExtent(bounds);
                            // add a tenth of scale, so there is a little space from features to map-bounds
                            var scale = geoExtMap.map.getScale() * 1.1;
                            if (scale < 500) {
                                scale = 500;
                            }
                            if (rec.get("selected") === false) {
                                rec.set("selected", true);
                            }
                            geoExtMap.map.zoomToScale(scale);
                            //Feature-definition with WKT-Geometry and attributes for labeling

                        }
                    }, {   	// button for creation attribute-table
                        icon: pg.assetURL('icons/mActionOpenTable.png'),
                        tooltip: 'Datenblatt öffnen',
                        handler: function (grid, rowIndex) {
                            var rec = grid.getStore().getAt(rowIndex);
                            // table for atttributes
                            var theTable = '<table><tbody>';
                            var theAttributeData = rec.json[3].data;
                            var tr_index = 1;
                            Object.keys(theAttributeData).forEach(function (key) {
                                var val = theAttributeData[key];
                                if (val == null) {
                                    val = '-';
                                }
                                function oddOrEven(x) {
                                    return ( x & 1 ) ? "#fff" : "#f1f1f1";
                                }

                                if (key != 'boundedBy' && key != 'geometry') {
                                    theTable += '<tr style="background-color: ' + oddOrEven(tr_index) + '"><td>' + key + '</td><td>' + val + '</td></tr>';
                                }
                                tr_index++;
                            });
                            theTable += '</tbody></table>';
                            // window for table
                            var theWin = new Ext.Window({
                                //cls: 'wfsInfoTable',
                                autoHeight: true,
                                width: 300,
                                closeAction: 'destroy',
                                title: 'Objekt: ' + rec.json[1] + ' aus Layer: ' + rec.json[0],
                                items: [{xtype: 'panel', html: theTable}]
                            }).show();
                        }
                    }, {   	// button for chighlighting feature
                        icon: pg.assetURL('icons/mActionSelect.png'),
                        tooltip: 'selektieren',
                        handler: function (grid, rowIndex) {
                            //Gbd.send('selectFeatures', {features: fs});
                            var rec = grid.getStore().getAt(rowIndex);
                            var hlayer = geoExtMap.map.getLayersByName("ZMF highlight Layer");
                            hlayer[0].removeAllFeatures();
                            hlayer[0].addFeatures(rec.json[3]);
                        }
                    }

                    ]
                },
                {header: "Objektname", text: "Objektname", width: '60%', dataIndex: 'label'},
                {header: "Layer", text: "ID", width: '1%', dataIndex: 'layername', hidden: true}
            ]);

            if (features) {
                for (var i = 0; i < features.length; i++) {
                    var wfsfeature = features[i];
                    var wfsLayername = Gbd.WFS.layerName(wfsfeature.fid);
                    Gbd.WFS.renameAttributes(wfsfeature, wfsLayername);

                    var displayField = 'name';
                    try {
                        displayField = wmsLoader.layerProperties[wfsLayername].displayField;
                    } catch (e) {
                    }

                    var label = wfsfeature.data[displayField] || '';
                    wfsfeature.attributes.label = label;
                    wfsfeature.data.label = label;
                    zmfQueryResponseData.push([wfsLayername, label, wfsfeature.bounds, wfsfeature]);
                }
            }

            var reader = new Ext.data.ArrayReader({}, [
                {name: 'layername'},
                {name: 'label'},
                {name: 'bounds'},
                {name: 'feature'}
            ]);

            var zmfStore = new Ext.data.GroupingStore({
                reader: reader,
                data: zmfQueryResponseData,
                sortInfo: {field: 'layername', direction: "ASC"},
                groupField: 'layername'
            });

            //update result grid
            zmfStore.loadData(zmfQueryResponseData);
            Ext.getCmp('zmfResultGrid' + tabID.substr(4)).reconfigure(zmfStore, fWfsModel);
        }

        Ext.getCmp('zmfLoadIndicator').setVisible(true);

        Gbd.WFS.request(myfeature.geometry, true, MAX_WFS_COUNT)
            .then(myhandler)
            .then(function() {
                Ext.getCmp('zmfLoadIndicator').setVisible(false);
            })
            .catch(function (e) {
                Ext.getCmp('zmfLoadIndicator').setVisible(false);
                if (e.httpError) {
                    Ext.MessageBox.alert(STRINGS.error, STRINGS.httpError);
                }
                if (e.overflowError) {
                    Ext.MessageBox.alert(STRINGS.error, STRINGS.overflowError);
                }
            });

    }

    var myWFSQueryToolbar = function () {
        return {
            xtype: 'toolbar',
            id: 'myWFSQueryToolbar',
            "region": "north",

            defaults: {xtype: 'button', scale: 'medium', tooltipType: 'qtip', handler: addZMFTab},
            items: [{
                icon: pg.assetURL('icons/mActionSelectPoint.png'),
                tooltip: "Punkt hinzufügen",
                id: 'btn_draw_point'
            }, {
                xtype: 'tbseparator'
            }, {
                icon: pg.assetURL('icons/mActionSelectLine.png'),
                tooltip: "Linie hinzufügen",
                id: 'btn_draw_line'
            }, {
                xtype: 'tbseparator'
            }, {
                icon: pg.assetURL('icons/mActionSelectRadius.png'),
                tooltip: "Kreis hinzufügen",
                id: 'btn_draw_circle'
            }, {
                xtype: 'tbseparator'
            }, {
                icon: pg.assetURL('icons/mActionSelectRectangle.png'),
                tooltip: "Rechteck hinzufügen",
                id: 'btn_draw_box'
            }, {
                xtype: 'tbseparator'
            }, {
                icon: pg.assetURL('icons/mActionSelectPolygon.png'),
                tooltip: "Polygon hinzufügen",
                id: 'btn_draw_polygon'
            }
            ]
        }
    };
    var zmfTabs = function () {
        return new Ext.TabPanel({
            //renderTo:'RightPanel',
            id: 'zmfTabs',
            resizeTabs: true, // turn on tab resizing
            minTabWidth: 60,
            tabWidth: 50,
            enableTabScroll: true,
            width: '100%',
            "region": "center",

            defaults: {
                autoScroll: true,
                closable: true,
                width: '100%',
                padding: '5px',
                listeners: {
                    activate: function (tab, eOpts) {
                        pg.zmfToggleControl(tab.label, tab.id);
                    },
                    close: function (tab, eOpts) {
                        deleteZmfTabFeature(tab.label, tab.id);
                    }
                }
            },
            //plugins: new Ext.ux.TabCloseMenu(),
            //activeTab: 0,
            items: []
        })
    };


    ////

    function initInterface() {
        Ext.getCmp('zmfTool').on('toggle', function (btn, toPress) {
            if (toPress) {
                Ext.getCmp('RightPanel').doLayout(0, 1);
                Ext.getCmp('RightPanel').expand();
                Ext.getCmp('ZMFPanel').expand();
                Ext.getCmp('RightPanel').doLayout(0, 1);
            } else {
                pg.zmfToggleControl('noControl');
                Ext.getCmp('ZMFPanel').collapse();
                var hlayer = geoExtMap.map.getLayersByName("ZMF highlight Layer");
                if (hlayer)
                    hlayer[0].removeAllFeatures();
            }
        });

        Gbd.initRightPanel();

        Ext.getCmp('rightCollapsiblePanels').add({
            "xtype": "panel",
            "title": "Zeichnen, Messen, Finden",
            "id": "ZMFPanel",
            "hidden": false,
            "width": '100%',
            "layout": "border",
            "collapsed": true,
            frame: false,
            items: []
        });

        Ext.getCmp('ZMFPanel').add(myWFSQueryToolbar(), zmfTabs());
        Ext.getCmp('RightPanel').doLayout(0, 1);
    }


    pg.on('toolbarLoad', function (event) {

        var toolbar = Ext.getCmp('myTopToolbar');

        var btn = new Ext.Button({
            icon: pg.assetURL('icons/mActionZMF.png'),
            id: 'zmfTool',
            tooltip: 'Zeichnen, Messen, Finden',
            tooltipType: 'qtip',
            scale: 'medium',
            toggleGroup: 'mapTools',
            hidden: true,
            enableToggle: true,
            allowDepress: true,
            visible: false
        });

        //toolbar.add({
        //    xtype: 'tbseparator'
        //});

        toolbar.add(btn);

        pg.http('check_enabled', {nocache: Math.random()}).then(function (res) {
            if (res.enabled) {
                btn.setVisible(true);
                initInterface();
            } else {
                toolbar.remove(btn);
            }
        });


    });

    pg.on('afterMapInit', function (event) {
        pg.http('check_enabled', {nocache: Math.random()}).then(function (res) {
            if (res.enabled)
                initZMFLayer();
        });
    });

    pg.on('enumPrintableFeatures', function (event) {
        if (pg.zmfLayer) {
            pg.zmfLayer.features.forEach(function (f) {
                event.features.push({
                    plugin: pg.name,
                    label: f.attributes.labelInfos || '',
                    wkt: f.geometry.toString()
                });
            });
        }
    })


})();
