"""Interface for Objektbereich:Tatsaechliche Nutzung"""

import json

from gbd.core import db
from gbd.core.util import inline_format as _f
from . import index


def get_all():
    return db.select(_f('SELECT * FROM {index.main_index}'))


def install(options):
    index.check(options.get('force'))
