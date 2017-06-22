/// Adjust the initial map based on query string parameters:  x, y, zoom

(function () {

    var pg = Gbd.plugin('xy');

    pg.on('afterMapInit', function (event) {

        var qs = OpenLayers.Util.getParameters(window.location.href, {splitArgs: false}),
            x, y,
            wkt,
            map = Gbd.map();

        if (qs.wkt) {
            wkt = qs.wkt;
        } else {
            if (qs.xy) {
                var p = qs.xy.split(/[^\d.]/);
                x = parseFloat(p[0]);
                y = parseFloat(p[1]);
            } else {
                x = parseFloat(qs.x);
                y = parseFloat(qs.y);

            }
            if (!isNaN(x) && !isNaN(y)) {
                wkt = Gbd.format('POINT(${0} ${1})', x, y);
            }
        }

        if (wkt) {
            Gbd.send('setMarker', {wkt: wkt});
        }

        if (qs.zoom && map.isValidZoomLevel(qs.zoom)) {
            map.zoomTo(qs.zoom)
        }

        if (qs.scale) {
            map.zoomToScale(qs.scale)
        }
    });

})();