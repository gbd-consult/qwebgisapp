(function () {

    var pg = Gbd.plugin('printer');

    var STRINGS = {
        pdfError: 'PDF kann nicht angezeigt werden. Klicken Sie <a href="${0}">hier</a> um die Datei zu öffnen',
        errorTitle: 'Fehler',
        errorText: 'Der Druckauftrag ist fehlgeschlagen.'
    };

    pg.on('afterMapInit', function() {
        if(!printWindow)
            return;
        printWindow.setWidth(printWindow.getWidth() + 160)
        var tb = Ext.getCmp('myPrintToolbar');
        tb.insert(10, {xtype: 'tbspacer', width:'4px'});
        tb.insert(11, {xtype: 'label', text: 'Titel:'});
        tb.insert(12, {xtype: 'tbspacer'});
        tb.insert(13, {xtype: 'textfield', id: 'printTitle'});
        tb.insert(14, {xtype: 'tbspacer'});
    });

    pg.on('doPrint', function (event) {
        pg.doPrint(event.params || {}, event.data || {})
    });

    pg.on('beforePrint', function (event) {
        event.provider.download = function (url) {
            var
                data = OpenLayers.Util.getParameters(url),
                params = {
                    plugin: pg.name,
                    cmd: 'print'
                };
            pg.doPrint(params, data)
        }
    });

    pg.doPrint = function (params, data) {
        params = params || {};
        data = data || {};

        if (!('map' in params)) {
            params.map = Gbd.activeMapPath();
        }

        if (!('map' in data)) {
            data['map'] = Gbd.activeMapPath();
        }

        if (!('layers' in data)) {
            data['layers'] = Gbd.activeMapLayers()
        }

        if (!('extra_features' in data)) {
            data['extra_features'] = [];
            Gbd.send('enumPrintableFeatures', {features: data['extra_features']})
        }

        if (!('map0:extent' in data)) {
            var ext = Gbd.map().getExtent();
            data['map0:extent'] = [ext.left, ext.top, ext.right, ext.bottom];
        }

        if (!('print_title' in data)) {
            try {
                var s = Gbd.trim(Ext.getCmp('printTitle').getValue());
                if (s) {
                    data['print_title'] = s;
                }
            } catch(e) {
            }
        }

        Ext.getBody().mask(printLoadingString[lang], 'x-mask-loading');

        OpenLayers.Request.POST({
            url: '/',
            headers: {
                'content-type': 'application/json',
            },
            params: params,
            data: JSON.stringify(data),
            callback: pg.printCallback
        });
    };

    pg.printCallback = function (xhr) {
        Ext.getBody().unmask();

        if (xhr.status === 200) {

            var js = JSON.parse(xhr.responseText),
                url = Gbd.format('/download/${0}.pdf', js.uid);

            var w = new Ext.Window({
                title: '',
                width: Ext.getBody().getWidth() - 100,
                height: Ext.getBody().getHeight() - 100,
                resizable: true,
                closable: true,
                constrain: true,
                constrainHeader: true,
                x: 50,
                y: 50,
                html: Gbd.format(
                    '<object data="${0}" type="application/pdf" width="100%" height="100%">'
                    + STRINGS.pdfError
                    + '</object>',
                    url)

            });

            w.show();

        } else {
            Ext.Msg.alert(
                STRINGS.errorTitle,
                STRINGS.errorText
            );
        }

    }


})();