#!/usr/bin/env python

import sys, os

app_root = os.path.abspath(
        os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                '..',
                '..'
        )
)

sys.path.insert(1, app_root)

from gbd.core import config, setup

try:
    force = sys.argv[2] == 'force'
except IndexError:
    force = False

config.load(os.path.abspath(sys.argv[1]))
setup.main({
    'force': force
})
