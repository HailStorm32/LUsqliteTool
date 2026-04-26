#
# Vendored from PySWF: https://github.com/timknip/pyswf
# Original author: Tim Knip
# License: MIT
#
"""Vendored SWF parser adapted from PySWF for local minifig preview rendering."""

from __future__ import annotations

import builtins
from functools import reduce as _reduce

__version__ = "1.5.4"
__upstream_repo__ = "https://github.com/timknip/pyswf"
__upstream_ref__ = "3740cc80d7650156831e728ea0d408819e5671eb"

# The original PySWF code targets Python 2. Expose a few Python 2 builtins so
# the vendored modules can stay close to upstream while we only patch the
# runtime-sensitive paths we actually use for minifig face previews.
if not hasattr(builtins, "xrange"):
    builtins.xrange = range
if not hasattr(builtins, "unichr"):
    builtins.unichr = chr
if not hasattr(builtins, "reduce"):
    builtins.reduce = _reduce
