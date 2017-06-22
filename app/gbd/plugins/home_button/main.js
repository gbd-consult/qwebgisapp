///

(function () {

    var STRINGS = {
        tooltip: 'Zur Startseite',
    };

    var pg = Gbd.plugin('home_button');

    pg.on('afterMapInit', function (event) {

        var toolbar = Ext.getCmp('myTopToolbar');

        toolbar.insert(0, {
            xtype: 'tbseparator'
        });

        toolbar.insert(0, new Ext.Action({
            icon: pg.assetURL('icon.png'),
            id: 'homeButton',
            tooltip: STRINGS.tooltip,
            tooltipType: 'qtip',
            scale: 'medium',
            pressed: false,
            enableToggle: false,
            allowDepress: false
        }));

        Ext.getCmp('homeButton').on('click', function () {
            window.location.href = Gbd.option('home_button.url', '/');
        });
    });


})();