<style>
.gbd_auth {
    font: 11px Tahoma,sans-serif;
}
.gbd_auth.absolute {
    position: absolute;
    top: 5px;
    right: 15px;
    z-index: 9999;
}
.gbd_auth.static {
    margin: auto;
    width: 300px;
}
.gbd_auth_login {
    position: absolute;
    top: 20px;
    right: 0px;
    width: 150px;
    background: #ececec;
    border: 1px solid silver;
    padding: 10px;
    box-shadow: 4px 4px 4px #aaa;
}
.gbd_auth_login.hidden {
    display: none;
}
.gbd_auth label {
    display: block;
    margin: 5px 0;
}
.gbd_auth label span {
    display: block;
    font-weight: bold;
    margin: 5px 0;
}
.gbd_auth label input {
    display: block;
    width: 100%;
    margin: 5px 0;
}
.gbd_auth_name {
    display:inline;
    padding: 0 10px;
}
.gbd_auth_logout {
    display: inline;
}
.gbd_auth_logout form {
    display: inline;
}
.gbd_auth_logout button {
    border: none;
    background: transparent;
    padding: 0;
    border-bottom: 1px dotted black;

}
.gbd_auth_link {
    cursor: pointer;
    border-bottom: 1px dotted black;
}
.gbd_auth_link:hover {
    color: blue;
}
.gbd_auth_login button {
    cursor: pointer;
    border: 1px solid #bbbbbb;
    background: linear-gradient(to bottom, #ffffff 0%,#e7e7e7 100%);
    padding: 4px;
    border-radius: 5px;
}
</style>

<script>
function gbdAuthToggleForm() {
    var f = document.getElementsByClassName('gbd_auth_login')[0],
        c = String(f.className);
    if (c.match(/hidden/))
        f.className = c.replace(/\s+hidden/, '');
    else
        f.className = c + ' hidden';
}
</script>

% if status == 'logged_in':
    <div class="gbd_auth absolute">
        <div class="gbd_auth_name">${request.user.name}</div>
        <div class="gbd_auth_logout">
            <form method="post">
                <input type="hidden" name="gbd_logout" value="1">
                <button type='submit'>Ausloggen</button>
            </form>
        </div>
    </div>
% endif

% if status == 'not_logged_in':
    <div class="gbd_auth absolute">
        <div class="gbd_auth_link" onclick="gbdAuthToggleForm()">Einloggen</div>
        <div class="gbd_auth_login hidden">
            <form method="post">
                <input type="hidden" name="gbd_login" value="1">
                <label>
                    <span>Benutzername</span>
                    <input type="text" name="login">
                </label>
                <label>
                    <span>Passwort</span>
                    <input type="password" name="password">
                </label>
                <button type='submit'>Ok</button>
            </form>
        </div>
    </div>
% endif

% if status == 'login_failed':
    <div class="gbd_auth static">
        <h3>Anmeldung fehlgeschlagen</h3>
        <form method="post">
            <input type="hidden" name="gbd_login" value="1">
            <label>
                <span>Benutzername</span>
                <input type="text" name="login">
            </label>
            <label>
                <span>Passwort</span>
                <input type="password" name="password">
            </label>
            <button type='submit'>Ok</button>
        </form>
    </div>
% endif

