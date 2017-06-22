/// Replace standard help button logic with an url

(function () {

    var pg = Gbd.plugin('help_button');

    pg.on('afterMapInit', function (event) {

        var helpButton = Ext.getCmp('ShowHelp');

        delete helpButton.handler;

        helpButton.on('click', function (btn, e) {
            window.open(Gbd.option('help_button.url', '/'));
        });
    });


})();