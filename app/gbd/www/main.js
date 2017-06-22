/// Define the global GBD plugin support object

;(function (window) {

    var STRINGS = {
        WFS: {
            loading: 'WFS wird geladen',
            errorTitle: 'Fehler',
            errorMessage: 'Beim Laden ist ein Fehler aufgetreten'
        }
    };


    var Gbd = {
        plugins: {},
        options: {}
    };

    Gbd.Plugin = {};

    Gbd.Plugin.assetURL = function (path) {
        return '/gbd/plugins/' + this.name + '/' + path;
    };

    Gbd.Plugin.requestURL = function (params) {
        var qs = ['plugin=' + this.name];

        Object.keys(params || {}).forEach(function (k) {
            qs.push(k + '=' + encodeURIComponent(params[k]));
        });

        return '/?' + qs.join('&');
    };


    Gbd.Plugin.on = function (eventName, fn) {
        this['_on_' + eventName] = fn;
    };

    Gbd.Plugin.http = function (cmd, params, data) {

        var url = '/',
            params = params || {};

        if (cmd) {
            if (cmd.indexOf('.') > 0) {
                url = this.assetURL(cmd);
            } else if (!('cmd' in params)) {
                params.cmd = cmd;
            }
        }

        if (!('plugin' in params)) {
            params.plugin = this.name;
        }

        if (!('map' in params)) {
            params.map = Gbd.activeMapPath();
        }

        return new Promise(function (resolve, reject) {
            var p = {
                url: url,
                params: params,
                callback: function (xhr) {

                    if (xhr.status != 200) {
                        return reject(xhr.status);
                    }

                    var text = xhr.responseText,
                        js = null;

                    try {
                        js = JSON.parse(text.replace(/^\s*\/\/.*/gm, ''));
                    } catch (e) {
                        console.log('JSON ERROR', e, url, text);
                        return reject(500);
                    }
                    resolve(js);
                }
            };

            var method = 'GET';

            if (data) {
                p.headers = {
                    'content-type': 'application/json',
                };
                p.data = JSON.stringify(data);
                method = 'POST';
            }

            OpenLayers.Request[method](p);
        });
    };

    Gbd.Plugin.handleEvent = function (evt, args) {
        var h = this['_on_' + evt];
        if (typeof h === 'function') {
            var done = !!h.call(this, args);
            //console.log('handle', evt, this.name, done);
            return done;
        }
    }


    Gbd.plugin = function (name, parent) {
        parent = parent || Gbd.Plugin;

        if (typeof parent === 'string') {
            parent = Gbd.plugins[parent];
        }

        var p = Object.create(parent);
        p.name = name;
        p.parent = parent;

        Gbd.plugins[name] = p;

        return p;
    };

    Gbd.send = function (evt, args) {
        var done = false;

        //console.log('send', evt, args);

        Object.keys(Gbd.plugins).reverse().forEach(function (k) {
            if (!done) {
                done = Gbd.plugins[k].handleEvent(evt, args);
            }
        });

        return done;
    };

    Gbd.format = function (str) {
        var args = [].slice.call(arguments, 1);

        return str.replace(/\${(.*?)}/g, function ($0, ref) {

            var obj = args[0],
                m = ref.match(/^(\d+)/);

            if (m) {
                obj = args[m[1]];
                ref = ref.substr(m[0].length);
            }

            while (ref) {
                m = ref.match(/^\.?(\w+)/) || ref.match(/^\[(.+?)\]/);
                if (m) {
                    obj = obj[m[1]];
                    ref = ref.substr(m[0].length);
                } else {
                    return $0;
                }
            }

            return obj;

        });
    };

    Gbd.escapeHTML = function (str) {
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }

    Gbd.def = function (base, ctr) {
        if (arguments.length === 1) {
            ctr = base;
            base = {};
        }
        ctr.prototype = Object.create(base.prototype || {});
        ctr.prototype.constructor = ctr;
        return ctr;
    };


    // returns the main Map object

    Gbd.map = function () {
        return geoExtMap.map;
    };


    function setQWCEvents() {
        window.customInit = function () {
            Gbd.send('init');
        };

        window.customBeforeMapInit = function () {
            Gbd.send('beforeMapInit');
        };

        window.customAfterMapInit = function () {

            // monkey patch "Cannot read property 'maxExtent' of null"
            Gbd.map().tileManager.drawTilesFromQueue = function (map) {
                var tileQueue = this.tileQueue[map.id];
                var limit = this.tilesPerFrame;
                var animating = map.zoomTween && map.zoomTween.playing;
                while (!animating && tileQueue.length && limit) {
                    var tile = tileQueue.shift();
                    if (!tile || !tile.layer) {
                        continue;
                    }
                    tile.draw(true);
                    --limit;
                }

            };
            Gbd.send('afterMapInit');

            var lastSize = {w: 0, h: 0, c: 1};

            // remove webgis resize listener

            Ext.getCmp('MapPanel').events.resize = true;

            Ext.getCmp('MapPanel').addListener('resize', function (panel, w, h) {
                // force refresh
                Ext.getCmp('geoExtMapPanel').setSize(panel.getInnerWidth(), panel.getInnerHeight());
                Ext.getCmp('geoExtMapPanel').map.moveByPx(lastSize.c, 0);
                var center = Ext.getCmp('geoExtMapPanel').map.getCenter();
                Ext.getCmp('geoExtMapPanel').map.setCenter(center);
                lastSize.c = -lastSize.c;
                lastSize.w = w;
                lastSize.h = h;
            });

            Ext.getCmp('GisBrowserPanel').doLayout(false, true);
            Gbd.send('initComplete');
        };

        window.customAfterGetMapUrls = function () {
            Gbd.send('afterGetMapUrls');
        };

        window.customPostLoading = function () {
            Gbd.send('postLoading');
            Gbd.initRightPanel();
        };

        window.customBeforePrint = function (provider, map, pages, options) {
            Gbd.send('beforePrint', {
                provider: provider,
                map: map,
                pages: pages,
                options: options
            });
        };

        window.customAfterPrint = function () {
            Gbd.send('afterPrint');
        };

        window.customToolbarLoad = function () {
            Gbd.send('toolbarLoad');
        };

        window.customMapToolbarHandler = function (btn, evt) {
            Gbd.send({name: 'toolbarEvent', button: btn, originalEvent: evt});
        };

        window.customActionLayerTreeCheck = function (n) {
            Gbd.send({name: 'layerTreeCheck', node: n});
        };

        window.customActionOnZoomEvent = function () {
            Gbd.send('zoom');
        };

        window.customActionOnMoveEvent = function () {
            Gbd.send('move');
        };

        window.customButtons = [];
    }

    Gbd.init = function (stage, options) {
        // stage 0 - first load
        // stage 1 - plugins loaded
        // stage 9 - everything is loaded

        Object.assign(Gbd.options, options || {});

        switch (stage) {
            case 0:
                setQWCEvents();
                // some QWC globals we don't use
                window.gis_projects = null;

                break;
            case 9:
                // disable the waiting msg for a tiled map
                if (!LayerOptions.singleTile) {
                    window.displayLoadMask = function () {
                    };
                }
                break;
        }
    };

    Gbd.readWKT = function (wkt) {
        var reader = new OpenLayers.Format.WKT(),
            features;

        if (Array.isArray(wkt)) {
            features = wkt.map(function (w) {
                return reader.read(w)
            });
        } else {
            features = reader.read(wkt);
        }

        if (features && !Array.isArray(features))
            return [features];

        return features;

    };

    Gbd.bounds = function (features) {
        if (!Array.isArray(features)) {
            features = [features];
        }

        var bs = features[0].geometry.getBounds();
        features.slice(1).forEach(function (f) {
            bs.extend(f.geometry.getBounds());
        });
        return bs;
    };

    Gbd.zoomTo = function (bounds, padding) {
        var padBounds = bounds;

        if (typeof padding === 'undefined')
            padding = 100;

        if (padding) {
            padBounds = new OpenLayers.Bounds(
                bounds.left - padding,
                bounds.bottom - padding,
                bounds.right + padding,
                bounds.top + padding);
        }

        var maxExtent = Gbd.map().getMaxExtent();

        if (maxExtent.containsBounds(padBounds)) {
            return Gbd.map().zoomToExtent(padBounds, true);
        }

        if (maxExtent.containsBounds(bounds)) {
            return Gbd.map().zoomToExtent(bounds, true);
        }

        Gbd.map().zoomToMaxExtent();
    };

    Gbd.initRightPanel = function () {

        if (Ext.getCmp('rightCollapsiblePanels')) {
            return;
        }

        Ext.getCmp('RightPanel').setLayout(new Ext.Container.LAYOUTS.vbox());
        Ext.getCmp('RightPanel').setTitle('Extras');
        Ext.getCmp('RightPanel').setWidth(300);
        Ext.getCmp('RightPanel').show();

        Ext.getCmp('RightPanel').add({
            xtype: 'panel',
            layout: 'accordion',
            border: false,
            frame: false,
            id: 'rightCollapsiblePanels',
            flex: 1,
            width: '100%',
            layoutConfig: {
                titleCollapse: true,
                animate: true,
                activeOnTop: false
            },
        });

        Ext.getCmp('RightPanel').addListener('resize', function (panel, width) {
            panel.items.each(function (item) {
                item.setWidth(width);
            });
            panel.doLayout();
        });


    };

    Gbd.option = function (name, def) {
        return (name in Gbd.options) ? Gbd.options[name] : def;
    };

    Gbd.queryString = function (key) {
        var qs = OpenLayers.Util.getParameters();
        return qs[key];
    };

    Gbd.trim = function (s) {
        return String(s || '').replace(/^\s+|\s+$/g, '');
    };

    Gbd.activeMapPath = function () {
        try {
            // global in WegGisInit.js
            var m = window.thematicLayer.url.match(/map=([^&]+)/);
            if (m)
                return m[1];
        } catch (e) {
        }
        return Gbd.queryString('map');
    };

    Gbd.activeMapLayers = function () {
        try {
            // global in WegGisInit.js
            return window.thematicLayer.params.LAYERS.split(',');
        } catch (e) {
            return [];
        }
    };

    Gbd.WFS = {
        names: {}
    };

    Gbd.WFS.layerName = function (id) {
        var s = String(id).split('.');
        return Gbd.WFS.names[s[0]];
    };

    Gbd.WFS.canQueryLayer = function (treeNode) {
        return treeNode.isLeaf() && treeNode.attributes.checked && !treeNode.isOutsideScale;
    };

    Gbd.WFS.listLayers = function (all) {
        var names = [],
            loader = window.wmsLoader,
            root = all ?
                window.layerTree.root.firstChild :
                window.layerTree.getSelectionModel().getSelectedNode();

        root.cascade(function (node) {
            if (Gbd.WFS.canQueryLayer(node)) {
                var props = loader.layerProperties[loader.layerTitleNameMapping[node.text]];
                if (!props.wmtsLayer) {
                    // in WFS names, replace space with _
                    // see qgswfsprojectparser.featureTypeList
                    var name = props.title || props.name;
                    if (name) {
                        var wfsName = name.replace(/\s/g, '_');
                        names.push(wfsName);
                        Gbd.WFS.names[wfsName] = name;
                    }
                }
            }
        });

        var order = loader.projectSettings.capability.layerDrawingOrder || [];

        names.sort(function (a, b) {
            return order.indexOf(a) - order.indexOf(b);
        });

        return names;
    };

    Gbd.WFS.renameAttributes = function (feature, layerName) {
        wmsLoader.layerProperties[layerName].attributes.forEach(function (attr) {
            if (attr.alias && (attr.name in feature.data)) {
                feature.data[attr.alias] = feature.data[attr.name];
                feature.attributes[attr.alias] = feature.attributes[attr.name];
                delete feature.data[attr.name];
                delete feature.attributes[attr.name];
            }
        });
    };

    Gbd.WFS.queryLayer = function (geometry, layer, maxCount) {
        var url = window.serverAndCGI,
            data = {
                map: Gbd.option('project.map'),
                service: 'WFS',
                version: '1.0.0',
                request: 'GetFeature',
                typename: layer,
                bbox: geometry.bounds.toBBOX(),
                count: maxCount + 1,
                maxFeatures: maxCount + 1
            };

        Gbd.loadMask(STRINGS.WFS.loading);
        //console.time('WFS.load ' + layer);

        return new Promise(function (resolve, reject) {
            OpenLayers.Request.POST({
                url: url,
                data: OpenLayers.Util.getParameterString(data),
                headers: {
                    'content-type': 'application/x-www-form-urlencoded'
                },
                callback: function (xhr) {
                    //console.timeEnd('WFS.load ' + layer);

                    Gbd.loadMask();
                    if (xhr.status != 200) {
                        Ext.MessageBox.alert(
                            STRINGS.WFS.errorTitle,
                            STRINGS.WFS.errorMessage
                        );
                        return reject({httpError: xhr.status});
                    }

                    var xml = xhr.responseText,
                        cnt = (xml.match(/<gml:featureMember/g) || '').length;

                    if (cnt > maxCount) {
                        return reject({overflowError: true})
                    }

                    if (cnt === 0) {
                        return resolve([]);
                    }

                    //console.time('WFS.parse ' + layer);
                    var gmlParser = new OpenLayers.Format.GML();
                    gmlParser.extractAttributes = true;
                    var features = gmlParser.read(xml);
                    //console.timeEnd('WFS.parse ' + layer);
                    //console.log('WFS.count ' + layer, features.length);

                    //console.time('WFS.filter ' + layer);
                    features = features.filter(function (f) {
                        return f.geometry.intersects(geometry);
                    });
                    //console.timeEnd('WFS.filter ' + layer);

                    resolve(features);
                }
            });
        });
    };

    Gbd.WFS.request = function (geometry, allLayers, maxCount) {

        var layers = Gbd.WFS.listLayers(allLayers);

        return Promise.all(layers.map(function (layer) {
            return Gbd.WFS.queryLayer(geometry, layer, maxCount);
        })).then(function (ls) {
            return [].concat.apply([], ls);
        });
    };


    var maskObject = null, maskTimer = 0;

    Gbd.loadMask = function (text) {
        clearTimeout(maskTimer);

        if (maskObject) {
            maskObject.hide();
        }
        maskObject = null;

        if (!text) {
            return;
        }

        maskTimer = setTimeout(function () {
            if (maskObject) {
                return;
            }
            maskObject = new Ext.LoadMask(Ext.getCmp('MapPanel').body, {msg: text});
            maskObject.show();
        }, 2000);

    };

    RegExp.escape = function (s) {
        return s.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
    };

    window.Gbd = Gbd;


})(window);
