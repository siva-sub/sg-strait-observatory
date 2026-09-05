"""strait — satellite vessel detection & port activity monitoring.

A Python package for detecting vessels from Sentinel-1 SAR imagery and
measuring port activity from satellite data.

Inspired by atlite (PyPSA): the Cutout abstraction turns a specific
data pipeline into a reusable tool for any maritime region.
"""

__version__ = "0.1.0"
__author__ = "Sivasubramanian S."

from .cutout import Cutout
from .zones import Zones
from .detect import detect_vessels, TRIMMED_CFAR, CLASSIC_CFAR
from .aggregate import aggregate
from .validate import AISMatch

__all__ = [
    "Cutout",
    "Zones",
    "detect_vessels",
    "aggregate",
    "AISMatch",
    "TRIMMED_CFAR",
    "CLASSIC_CFAR",
    "__version__",
]
