<!DOCTYPE HTML>
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
    <meta http-equiv="X-UA-Compatible" content="IE=edge"/>

    % if dev_mode:
        <script type="text/javascript" src="/gbd/www/msie.js?_rnd=${rand}"></script>
        <script type="text/javascript" src="/gbd/www/main.js?_rnd=${rand}"></script>
    % else:
        <script type="text/javascript" src="/gbd/www/msie.js"></script>
        <script type="text/javascript" src="/gbd/www/main.js"></script>
    % endif

    <script type="text/javascript">
        Gbd.init(0, ${js_options});
    </script>

    % for url in plugins_js:
        <script type="text/javascript" src="${url}"></script>
    % endfor

    <script type="text/javascript">
        Gbd.init(1);
    </script>

    <link rel="stylesheet" type="text/css" href="${qwc_root}/libs/ext/resources/css/ext-all-notheme.css"/>
    <link rel="stylesheet" type="text/css" href="${qwc_root}/libs/ext/resources/css/xtheme-gray.css"/>
    <link rel="stylesheet" type="text/css" href="${qwc_root}/libs/ext/ux/css/ux-all.css"/>
    <link rel="stylesheet" type="text/css" href="${qwc_root}/css/TriStateTreeAndCheckbox.css"/>
    <link rel="stylesheet" type="text/css" href="${qwc_root}/css/ThemeSwitcherDataView.css"/>
    <link rel="stylesheet" type="text/css" href="${qwc_root}/css/popup.css"/>
    <link rel="stylesheet" type="text/css" href="${qwc_root}/css/layerOrderTab.css"/>

    <!-- <script src="https://maps.googleapis.com/maps/api/js?v=3&sensor=false"></script> -->

    % if dev_mode:
        <script type="text/javascript" src="${qwc_root}/libs/ext/adapter/ext/ext-base-debug.js"></script>
        <script type="text/javascript" src="${qwc_root}/libs/ext/ext-all-debug-w-comments.js"></script>
    % else:
        <script type="text/javascript" src="${qwc_root}/libs/ext/adapter/ext/ext-base.js"></script>
        <script type="text/javascript" src="${qwc_root}/libs/ext/ext-all.js"></script>
    % endif

    <script type="text/javascript" src="${qwc_root}/libs/ext/ux/ux-all.js"></script>
    <script type="text/javascript" src="${qwc_root}/libs/proj4js/proj4js-compressed.js"></script>

    % if dev_mode:
        <script type="text/javascript" src="/open_layers_full/lib/OpenLayers.js"></script>
        <script type="text/javascript" src="/GeoExt/lib/GeoExt.js"></script>
    % else:
        <script type="text/javascript" src="${qwc_root}/libs/openlayers/OpenLayers.js"></script>
        <script type="text/javascript" src="${qwc_root}/libs/geoext/script/GeoExt.js"></script>
    % endif

    <script>
        OpenLayers.IMAGE_RELOAD_ATTEMPTS = 5;
        OpenLayers.Util.alphaHackNeeded = false;
    </script>

    <script type="text/javascript">
        ${global_options}
    </script>

    % for url in user_js:
        <script type="text/javascript" src="${url}"></script>
    % endfor

    % for c in qwc_components:
        <script type="text/javascript" src="${qwc_root}/js/${c}.js"></script>
    % endfor

    <style type="text/css">
        <!--
        #dpiDetection {
            height: 1in;
            left: -100%;
            position: absolute;
            top: -100%;
            width: 1in;
        }

        #panel_header_title {
            float: left;
            font-size: 24px;
        }

        #panel_header_link {
            float: left;
        }

        #panel_header_terms_of_use {
            float: right;
            font-weight: normal;
        }

        #panel_header_lang_switcher {
            float: right;
            font-weight: normal;
        }

        p.DXFExportDisclaimer {
            margin-bottom: 0.75em;
        }

        h4.DXFExportDisclaimer {
            margin-bottom: 1em;
        }

        .DXFExportCurrentAreaLabel {
            color: red;
        }

        -->
    </style>

    <link rel="stylesheet" type="text/css" href="/gbd/www/main.css"/>

    % for url in plugins_css:
        <link rel="stylesheet" type="text/css" href="${url}"/>
    % endfor

    % for url in user_css:
        <link rel="stylesheet" type="text/css" href="${url}"/>
    % endfor

    <script type="text/javascript">
        Gbd.init(9);
    </script>


</head>
<body>
<!-- this empty div is used for dpi-detection - do not remove it -->
<div id="dpiDetection"></div>
${login_block}
</body>
</html>
