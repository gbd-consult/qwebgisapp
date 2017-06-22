///

(function () {

    var pg = Gbd.plugin('copyright_label');


    pg.on('afterMapInit', function (event) {
        pg.http('label').then(function (lab) {
            if (!lab)
                return;

            var div = document.createElement('div');
            div.id = 'copyright_label';
            for (var p in lab.style) {
                div.style[p] = lab.style[p];
            }
            div.innerHTML = lab.html;

            var panel = document.getElementById('geoExtMapPanel');
            if (panel)
                panel.appendChild(div);
        });
    });

})();