/// Common QWC GUI tools

(function () {

    var pg = Gbd.plugin('gui');

    pg.remove = function(id) {
        var ct = Ext.getCmp(id);
        if(ct) {
            ct.ownerCt.remove(ct);
        }
    };

    pg.hide = function(id) {
        var ct = Ext.getCmp(id);
        if(ct) {
            ct.hide();
        }
    };

    pg.expand = function(id) {
        var ct = Ext.getCmp(id);
        if(ct) {
            ct.expand(false);
        }
    };

    pg.collapse = function(id) {
        var ct = Ext.getCmp(id);
        if(ct) {
            ct.collapse(false);
        }
    };

    function opt(name) {
        return Gbd.option('gui.' + name, '').split(/\s*,\s*/);
    }

    pg.on('postLoading', function (event) {
        opt('hide').forEach(pg.hide);
        opt('expand').forEach(pg.expand);
        opt('collapse').forEach(pg.collapse);
    });




})();
