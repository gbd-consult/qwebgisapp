<%def name="require_granted()">
    % if osname == 'suse':
        # apache 2.2
        Order allow,deny
        Allow from all
    % else:
        # apache 2.4
        Require all granted
    % endif
</%def>

<%def name="require_denied()">
    % if osname == 'suse':
        # apache 2.2
        Order allow,deny
        Deny from all
    % else:
        # apache 2.4
        Require all denied
    % endif
</%def>

<%def name="auth()">
    % if basic_auth:
        AuthType Basic
        AuthName "Zugriff verweigert - Bitte User und Passwort eingeben"
        AuthUserFile ${htpasswd_path}

        % if osname == 'suse':
           Require valid-user
        % else:
            <RequireAny>
               Require ip 127.0.0.1
               Require valid-user
            </RequireAny>
        % endif

    % else:
        ${require_granted()}
    % endif
</%def>

<%def name="qgis_server()">
    % if osname == 'suse':
        ScriptAlias /cgi-bin/ /srv/www/cgi-bin/
        <Directory "/srv/www/cgi-bin/">
    % else:
        ScriptAlias /cgi-bin/ /usr/lib/cgi-bin/
        <Directory "/usr/lib/cgi-bin/">
    % endif

        AllowOverride None
        Options +ExecCGI -MultiViews -SymLinksIfOwnerMatch
        ${require_granted()}
        <Files "*.fcgi">
            SetHandler fcgid-script
        </Files>
    </Directory>

    FcgidMaxRequestLen 8000000
    FcgidIOTimeout 120

    FcgidInitialEnv QGIS_SERVER_LOG_FILE ${log_dir}/mapserv.log
    FcgidInitialEnv QGIS_SERVER_LOG_LEVEL 0

    FcgidInitialEnv HOME ${home_dir}

    % if xvfb_display > 0:
        FcgidInitialEnv DISPLAY ":${xvfb_display}"
    % endif

    FcgidInitialEnv GBD_CONFIG_PATH ${config_path}
    FcgidInitialEnv PYTHONPATH ${python_path}
</%def>

% if is_https:
    # we need another http server for internal requests
    <VirtualHost *:80>
        ServerName ${loopback_host}
        ${qgis_server()}
    </VirtualHost>
% endif

<VirtualHost *:${server_port}>
    ServerAdmin webmaster@localhost
    ServerName ${server_name}

    % if not https:
        ServerAlias ${loopback_host}
    % endif

    DocumentRoot ${app_root}/www

    <Directory />
        Options FollowSymLinks
        AllowOverride None
        ${require_denied()}
    </Directory>

    <Directory ${app_root}/www>
        DirectoryIndex index.fcgi
        Options -Indexes +FollowSymLinks -MultiViews +ExecCGI
        AllowOverride All

        ${auth()}

        <Files "*.fcgi">
            SetHandler fcgid-script
        </Files>

        RewriteEngine On

        # make QWC assets work from root
        RewriteRule ^(gis_icons|img|help_).* ${qwc_root}/$0 [L]

        RewriteCond %{REQUEST_FILENAME} !-d
        RewriteCond %{REQUEST_FILENAME} !-f

        RewriteRule . /index.fcgi [L,QSA]

    </Directory>

    % for alias, dir in aliases:
        Alias "${alias}" "${dir}"
        <Directory ${dir}>
            ${require_denied()}
            <FilesMatch "^[^_.].*\.(${media_types})$">
                ${auth()}
            </FilesMatch>
        </Directory>
    % endfor

    ${qgis_server()}

    ErrorLog  ${log_dir}/apache-error.log
    CustomLog ${log_dir}/apache-access.log combined
    LogLevel debug

    SetEnvIf Authorization .+ HTTP_AUTHORIZATION=$0

    ${extra_config}

</VirtualHost>
