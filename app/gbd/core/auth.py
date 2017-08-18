"""Authorization related utils."""

import time, datetime
from gbd.core import db, config, log, util, session, debug
from gbd.core.util import inline_format as _f


class User(object):
    def __init__(self, udata):
        self.login = udata['login']
        self.roles = set(udata['roles'])
        self.name = udata.get('name', self.login)

        self.permissions = set()
        for key in config.keys('auth.role'):
            p = config.get_list(key)
            if p[0] in self.roles:
                self.permissions.update(p[1:])

    def is_guest(self):
        return 'guest' in self.roles

    def can(self, perm):
        return perm in self.permissions

    def can_open(self, project_path):
        for key in config.keys('auth.project'):
            p = config.get_list(key)
            if p[0] == project_path:
                return any(role in self.roles for role in p[1:])
        return True


def ldap_login(login, password):
    """Given a login and password, return a tuple (user record or None, error or None)."""

    def _utf8(s):
        if isinstance(s, str):
            s = s.decode('utf8')
        return unicode(s).encode('utf8')

    import ldap, urlparse

    url = config.get('ldap.url')
    p = urlparse.urlparse(url)

    server = 'ldap://' + p.netloc
    base = p.path.strip('/')
    prop = p.query

    # suffix = config.get('ldap.suffix', '')

    ld = ldap.initialize(server)
    if config.get('ldap.type') == 'AD':
        # see https://www.python-ldap.org/faq.html#usage
        ld.set_option(ldap.OPT_REFERRALS, 0)

    if config.get('ldap.admin_user'):
        ld.simple_bind_s(
                _utf8(config.get('ldap.admin_user')),
                _utf8(config.get('ldap.admin_password')))

    ls = ld.search_s(base, ldap.SCOPE_SUBTREE, _utf8(prop) + '=' + _utf8(login))
    if not ls:
        return None, _f('not found: {prop}={login}')

    # search returns a list of tuples (cn, data)
    # some installs also return entries with cn=None, skip them
    user_cn = None
    for cn, data in ls:
        if cn:
            user_cn = cn
            break

    if not user_cn:
        return None, _f('not found: {prop}={login}, zero cn returned')

    log.debug('found user', prop, login, user_cn)

    # find role mappings for the user
    udata = {'login': login, 'roles': [], 'name': login}
    for key in config.keys('ldap.login'):
        role, ldap_filter = config.get_list(key, 1)
        ls = ld.search_s(base, ldap.SCOPE_SUBTREE, _utf8(ldap_filter))
        for cn, data in ls:
            if cn == user_cn:
                log.debug('found role', role, ldap_filter)
                udata['roles'].append(role)
                try:
                    udata['name'] = data['cn'][0]
                except:
                    pass

    if not udata['roles']:
        return None, _f('no roles for {login}')

    try:
        ld.simple_bind_s(_utf8(user_cn), _utf8(password))
    except ldap.INVALID_CREDENTIALS:
        return None, 'wrong password'

    return udata, None


def login(login, password):
    """Try to log a user in and return a user record or None."""

    method = config.get('auth.method')
    udata, error = None, None

    if method == 'ldap':
        udata, error = ldap_login(login, password)
    else:
        error = 'invalid auth method'

    if error:
        log.error(_f('AUTH ERROR ({method}) login={login} error={error}'))
        return None

    return udata


def enabled():
    return config.get('auth.method') is not None


def guest():
    return User({'login': None, 'roles': ['guest']})


def check_web_auth(request, response):
    """Check web authorization for a web user (login/session) and return a status string."""

    # since we don't check map requests, let's this be long
    session_lifetime = 3600 * 4

    def init_sm():
        return session.SessionService(
                session.DiskSessionStore(storeDir=config.get('paths.temp') + '/sess'),
                request.environ,
                cookieName='sid',
                cookieAttributes={'httponly': True}
        )

    def close_sm():
        sm.addCookie(response.headers)
        sm.close()

    def debug_log(comment):
        # log.debug('r=', request.environ.get('QUERY_STRING'), request.environ.get('HTTP_COOKIE'))
        if sm._session:
            log.debug(_f(
                    '{0} {1} ({2}): {3}',
                    sm._session.identifier,
                    datetime.datetime.fromtimestamp(sm._session.creationTime),
                    int(time.time() - sm._session.get('time', 0)),
                    comment
            ))
        else:
            log.debug(comment)

    request.user = guest()
    sm = init_sm()

    if request.method == 'POST' and 'gbd_login' in request.body:
        if sm.hasSession:
            debug_log('active in login')
            sm.session.invalidate()
            close_sm()
            sm = init_sm()

        udata = login(
                request.body.get('login', ''),
                request.body.get('password', ''))

        if udata:
            request.user = User(udata)
            sm.session['user'] = request.user
            sm.session['time'] = time.time()
            debug_log('new')
            close_sm()
            return 'login_success'
        else:
            close_sm()
            return 'login_failure'

    if not sm.hasSession:
        debug_log('no session')
        close_sm()
        return 'not_logged_in'

    if request.method == 'POST' and 'gbd_logout' in request.body:
        debug_log('logout')
        sm.session.invalidate()
        close_sm()
        return 'logout_success'

    if sm.hasSessionExpired:
        debug_log('expired(1)')
        sm.session.invalidate()
        close_sm()
        return 'not_logged_in'

    if 'user' not in sm.session or 'time' not in sm.session:
        debug_log('no keys')
        sm.session.invalidate()
        close_sm()
        return 'not_logged_in'

    if time.time() - sm.session['time'] > session_lifetime:
        debug_log('expired(2)')
        sm.session.invalidate()
        close_sm()
        return 'not_logged_in'

    debug_log('ok')
    request.user = sm.session['user']
    sm.session['time'] = time.time()
    close_sm()
    return 'logged_in'
