(function () {

    var pg = Gbd.plugin('infobox');

    pg.content = null;

    pg.on('showInfoBox', function (event) {
        pg.content = event;
        pg.initInfoBox();
        Ext.getCmp('RightPanel').doLayout(0, 1);
        Ext.getCmp('InfoBox').body.update(pg.content.html);
        Ext.getCmp('RightPanel').expand();
        Ext.getCmp('RightPanel').doLayout(0, 1);
        Ext.getCmp('InfoBoxPanel').expand();
    });

    pg.on('hideInfoBox', function (event) {
        if (!Ext.getCmp('InfoBox'))
            return;
        if(pg.content && pg.content.type === event.type) {
            pg.content = null;
            Ext.getCmp('InfoBox').body.update('');
            Ext.getCmp('InfoBoxPanel').collapse();
        }
    });

    pg.initInfoBox = function () {
        if (Ext.getCmp('InfoBox'))
            return;

        Gbd.initRightPanel();

        Ext.getCmp('rightCollapsiblePanels').add({
            "xtype": "panel",
            "title": "Objekt-Info",
            "id": "InfoBoxPanel",
            "hidden": false,
            "width": '100%',
            "layout": "border",
            frame: false,
            items: [
                {
                    id: "InfoBox",
                    "xtype": "panel",
                    "region": "center",
                    autoScroll: true,
                    width: '100%',
                    frame: false,
                    layout: 'fit'

                }
            ],
            fbar: {
                items: [
                    {
                        xtype: 'button',
                        id: 'InfoBoxPrintButton',
                        scale: 'medium',
                        icon: 'gis_icons/mActionFilePrint.png',
                        tooltipType: 'qtip',
                        tooltip: "Datenblatt drucken",
                    }
                ]

            }
        });

        Ext.getCmp('InfoBoxPrintButton').on('click', function () {
            Gbd.send('printInfoBox', pg.content);
        });

    }


})();