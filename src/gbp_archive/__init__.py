"""gbp-archive: dump and restore builds in Gentoo Build Publisher"""

import importlib.metadata

__version__ = importlib.metadata.version("gbp-archive")

# Plugin definition
plugin = {
    "name": "gbp-archive",
    "version": __version__,
    "description": "Dump and restore builds in Gentoo Build Publisher",
}
