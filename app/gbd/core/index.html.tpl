${login_block}

<h1>Projekte</h1>
% for name, path in projects:
    <p><a href="?map=${path}">${name}</a></p>
% endfor
