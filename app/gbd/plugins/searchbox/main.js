/// Provides the generic search box

(function () {

    var pg = Gbd.plugin('searchbox');

    pg.state = {
        value: '',
        results: [],
        timer: 0
    };

    pg.delay = Gbd.options['searchbox.delay'] || 100;

    pg.showPopup = function () {
        pg.popup.show();
        pg.popup.doLayout();
        pg.popup.getEl().alignTo(pg.box.el, 'tr-br', [0, 1]);
    };

    pg.hidePopup = function () {
        pg.popup.hide();
    };

    pg.sort = function (items) {
        if(!pg.doSort)
            return items;
        return items.sort(function (a, b) {
            return a.section.localeCompare(b.section) ||
                a.text.localeCompare(b.text);
        });
    };

    pg.renderResults = function (value) {
        var html = '',
            re = new RegExp(RegExp.escape(value), 'i'),
            sections = {};

        pg.state.results.forEach(function(r, n) {
            if(!sections[r.section]) {
                sections[r.section] = [];
            }
            r.index = n;
            sections[r.section].push(r);
        });

        Object.keys(sections).sort().forEach(function(sec) {
            html += Gbd.format('<h2>${0}</h2>', sec);
            sections[sec].forEach(function(r) {
                html += Gbd.format('<p data-index="${0}">${1}</p>',
                    r.index, r.text.replace(re, '<u>$&</u>').replace(/\n/g, '<br>')
                );
            });
        });

        return '<div id="SearchBoxResults">' + html + '</div>';
    };

    pg.reset = function () {
        clearTimeout(pg.state.timer);
        pg.state.results = [];
    };

    pg.value = function () {
        return Gbd.trim(pg.box.getRawValue());
    };

    pg.doSearch = function () {
        var val = pg.value();
        if (val !== pg.state.value) {
            pg.state.value = val;
            pg.reset();
            if (val.length) {
                Gbd.send('searchBoxChange', {value: val});
            } else {
                pg.popup.update('');
            }
        }
    };

    pg.onKey = function (el, evt) {
        if (evt.button == 26) {
            return pg.hidePopup();
        }
        clearTimeout(pg.state.timer);
        pg.state.timer = setTimeout(pg.doSearch, pg.delay);
    };

    pg.onSelect = function (index) {
        pg.hidePopup();
        Gbd.send('searchBoxSelect', {item: pg.state.results[index]});
    };

    pg.on('searchBoxUpdate', function (event) {
        pg.showPopup();
        pg.state.results = pg.state.results.concat(event.results);
        pg.popup.update(pg.renderResults(pg.value()));
    });


    pg.on('toolbarLoad', function (event) {

        var toolbar = Ext.getCmp('myTopToolbar');

        toolbar.add({
            "xtype": "tbfill"
        });
        toolbar.add({
            "xtype": "textfield",
            "id": "searchBox",
            "enableKeyEvents": true,
            "selectOnFocus": true,
            "width": 200,
            "emptyText": "Suche"
        });
        toolbar.add({
            "xtype": "tbspacer",
            "width": 5
        });

        pg.popup = new Ext.Panel({
            floating: true,
            modal: false,
            width: 300,
            height: 350,
            renderTo: Ext.getBody(),
            listeners: {
                render: function (p) {
                    p.getEl().on('click', function (evt, el) {
                        while (el && el.tagName.toUpperCase() !== 'P') {
                            el = el.parentNode;
                        }
                        if(el && el.hasAttribute('data-index')) {
                            pg.onSelect(el.getAttribute('data-index'))
                        }
                        evt.stopPropagation();
                    });
                }
            }
        });

        toolbar.doLayout();

        pg.box = Ext.getCmp("searchBox");

        pg.box.on('keyup', pg.onKey);

        pg.box.getEl().on('click', function (evt) {
            if (pg.state.results.length) {
                pg.showPopup();
            }
        });

        Ext.getDoc().on('mousedown', function (evt, el) {
            var boxEl = pg.box.getEl().dom,
                popupEl = pg.popup.getEl().dom;

            while (el) {
                if (el === boxEl) {
                    return;
                }
                if (el === popupEl) {
                    return;
                }
                el = el.parentNode;
            }
            pg.hidePopup();
        });

        Ext.EventManager.onWindowResize(function () {
            pg.hidePopup();
        });


    });


})();
