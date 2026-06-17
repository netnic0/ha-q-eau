"""Public exports for the ha_q_eau.api sub-package."""

from .client import HubEauClient
from .exceptions import HubEauApiError, HubEauError, HubEauNoDataError
from .models import CommuneInfo, ParameterReading, WaterQualityData, WaterQualityReading

__all__ = [
    "HubEauClient",
    "HubEauApiError",
    "HubEauError",
    "HubEauNoDataError",
    "CommuneInfo",
    "ParameterReading",
    "WaterQualityData",
    "WaterQualityReading",
]
