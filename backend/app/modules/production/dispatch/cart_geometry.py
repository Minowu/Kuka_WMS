"""Geometry helpers for cart / location selection."""

import math

from app.modules.warehouse.location_map.location_model import Location


def calculate_distance(loc1: Location, loc2: Location) -> float:
    """2D Euclidean distance between two map nodes."""
    x1 = loc1.map_x or 0
    y1 = loc1.map_y or 0
    x2 = loc2.map_x or 0
    y2 = loc2.map_y or 0
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)
