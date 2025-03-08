import random

def generate_trash_locations(width, height, num_trash):
    """
    Generate a list of trash locations (x, y) coordinates within the specified area.
    All coordinates are in meters.
    """
    return [(random.uniform(0, width), random.uniform(0, height)) for _ in range(num_trash)]
