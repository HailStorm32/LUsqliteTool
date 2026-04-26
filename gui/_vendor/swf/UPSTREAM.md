# Vendored PySWF Provenance

This folder vendors a patched subset of [`timknip/pyswf`](https://github.com/timknip/pyswf).

## Upstream reference

- Repo: `https://github.com/timknip/pyswf`
- Branch compared: `master`
- Commit compared on 2026-04-25:
  `3740cc80d7650156831e728ea0d408819e5671eb`
- Package version exposed by upstream `swf/__init__.py`: `1.5.4`

## Important note

This subtree is intentionally **not** a byte-for-byte copy of upstream.

The goal here is a stable local `.gfx` preview path for the face editor, not a
general-purpose SWF package mirror. Some differences are deliberate compatibility
fixes for Python 3 and for this app's vendored package layout.

## Known local differences

- All files include local attribution headers.
- [`__init__.py`](/D:/Projects/LUsqliteTool/gui/_vendor/swf/__init__.py) adds a
  small Python 2 builtin shim layer used by the vendored modules.
- [`stream.py`](/D:/Projects/LUsqliteTool/gui/_vendor/swf/stream.py),
  [`tag.py`](/D:/Projects/LUsqliteTool/gui/_vendor/swf/tag.py), and
  [`utils.py`](/D:/Projects/LUsqliteTool/gui/_vendor/swf/utils.py) keep
  Python 3 byte and `BytesIO` fixes that the current app relies on.
- The vendored code uses package-relative imports under `gui._vendor.swf`
  instead of assuming installation as top-level `swf`.

## Why not blindly mirror upstream `master`

During comparison, upstream `master` still contained changes that are not safe
to adopt verbatim for this repo, including at least one obvious regression in
`filters.py` with undefined names (`matrixX`, `matrixY`, `id`) inside paths that
should be instance-local.

If this subtree needs another sync in the future, compare against the commit
above first and preserve the local compatibility patches unless they are being
replaced deliberately.
