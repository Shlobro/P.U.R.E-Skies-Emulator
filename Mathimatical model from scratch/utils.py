# utils.py
import math


def distance(from_x: float, from_y: float, to_x: float, to_y: float) -> float:
    """Calculates the Euclidean distance between two points (from_x, from_y) and (to_x, to_y)."""
    return math.sqrt((to_x - from_x) ** 2 + (to_y - from_y) ** 2)


def time_to_travel(distance: float, speed: float) -> float:
    return distance / speed