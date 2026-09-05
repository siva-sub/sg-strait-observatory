"""Built-in zone definitions for major ports and anchorages."""
from typing import Dict, Tuple


class Zones:
    """Zone definitions for vessel aggregation.

    Each zone is a bounding box: (lon_min, lat_min, lon_max, lat_max)
    """

    @staticmethod
    def singapore_strait() -> Dict[str, Tuple[float, float, float, float]]:
        """Singapore Strait zones (from the observatory project, AIS-validated)."""
        return {
            "port_core": (103.68, 1.20, 104.02, 1.34),
            "eastern_opl": (104.00, 1.24, 104.35, 1.40),  # tanker anchorage (77% tankers)
            "western_opl": (103.58, 1.10, 103.78, 1.32),
        }

    @staticmethod
    def rotterdam() -> Dict[str, Tuple[float, float, float, float]]:
        """Rotterdam approach zones."""
        return {
            "maasvlakte": (3.90, 51.90, 4.20, 52.10),
            "europoort": (4.10, 51.90, 4.40, 52.05),
        }

    @staticmethod
    def custom(zones: Dict[str, Tuple[float, float, float, float]]) -> Dict:
        """Define your own zones.

        Example:
            zones = Zones.custom({
                "my_anchorage": (104.0, 1.24, 104.35, 1.40),
                "port": (103.68, 1.20, 104.02, 1.34),
            })
        """
        return zones
