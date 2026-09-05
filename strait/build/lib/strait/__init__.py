"""strait — satellite vessel detection & port activity monitoring.

Detect vessels from Sentinel-1 SAR imagery. Measure port activity
from space. Any port, any time, no ground infrastructure needed.

Inspired by atlite (PyPSA): the Cutout abstraction makes a complex
satellite-data pipeline usable in 5 lines of code.

Use cases:
- Port activity nowcasting (satellite → economic indicator)
- Anchorage congestion monitoring (are anchorages full?)
- Dark vessel detection (SAR detections without AIS match)
- Bunkering activity estimation (anchored tanker counts)
- Research: vessel presence time series for econometrics
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
