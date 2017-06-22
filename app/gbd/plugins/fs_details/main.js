(function () {

    var pg = Gbd.plugin('fs_details');

    pg.on('showFsDetails', function (event) {
        var gml_id = event.gml_id;
        pg.http('infobox', {gml_id: gml_id}).then(function (r) {
            if (r) {
                Gbd.send('showInfoBox', {
                    type: 'fs_details',
                    gml_id: gml_id,
                    html: r.html
                });
            }
        });
    });

    pg.on('hideFsDetails', function (event) {
        Gbd.send('hideInfoBox', {
            type: 'fs_details',
        });
    });

    pg.on('printInfoBox', function (event) {
        if (event.type !== 'fs_details') {
            return;
        }

        var params = {
            plugin: pg.name,
            cmd: 'print',
            gml_id: event.gml_id
        };

        Gbd.send('doPrint', {params: params});
    });


})();