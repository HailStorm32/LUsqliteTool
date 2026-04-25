# Vendored Helpers

This folder holds small third-party code copies that are kept in-repo on
purpose.

## `swf/`

`swf/` is a trimmed and patched subset of `pyswf` used by the Minifig face
editor to render static preview images from LEGO Universe `.gfx` files.

It is vendored instead of imported as a normal dependency because:

- the upstream `pyswf` install path pulled in build-time dependencies that did
  not install cleanly in this environment,
- the upstream code still required Python 3 compatibility fixes, and
- the app only needs a narrow local rendering path for preview generation.

Keep changes here focused on the face-preview use case.
