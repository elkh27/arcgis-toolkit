"""Sign in to ArcGIS Online or ArcGIS Location Platform."""
import os
from getpass import getpass

DEFAULT_PORTAL = "https://www.arcgis.com"


def connect(portal_url: str = DEFAULT_PORTAL):
    """Sign in with ARCGIS_USERNAME / ARCGIS_PASSWORD, or prompt for them."""
    # Imported lazily so the rest of the package (and the tests) never need a live connection
    from arcgis.gis import GIS

    username = os.getenv("ARCGIS_USERNAME") or input("Username: ")
    password = os.getenv("ARCGIS_PASSWORD") or getpass("Password: ")
    return GIS(portal_url, username, password)