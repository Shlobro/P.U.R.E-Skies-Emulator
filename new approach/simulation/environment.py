import networkx as nx
import math


class Environment:
    def __init__(self):
        """
        Holds a representation of the environment, like:
          - a graph for routing
          - obstacle data
          - bin locations
          - terrain types
        """
        self.graph = nx.Graph()
        self.obstacles = []

        # NEW: Track bins for trash drop-off
        self.bins = []

        self.terrain_speeds = {'default': 1.0, 'grass': 0.8, 'pavement': 1.2}

    def add_bin(self, x, y):
        """
        Add a bin location where agents can drop off trash.
        """
        self.bins.append((x, y))

    def add_obstacle(self, obstacle):
        """
        Add an obstacle (for now, store a rectangle or polygon).
        We can expand collision logic later.
        """
        self.obstacles.append(obstacle)

    def get_closest_bin(self, x, y):
        """
        Return the closest bin to the (x, y) position.
        If no bins exist, return None.
        """
        if not self.bins:
            return None

        min_dist = float('inf')
        closest_bin = None
        for (bx, by) in self.bins:
            dist = math.sqrt((bx - x) ** 2 + (by - y) ** 2)
            if dist < min_dist:
                min_dist = dist
                closest_bin = (bx, by)
        return closest_bin

    def is_path_blocked(self, start, end):
        """
        Placeholder for checking if a path is blocked by an obstacle.
        Expand using collision checks, line intersections, etc.
        """
        return False

    def get_speed_modifier(self, terrain_type):
        """
        Return speed modifier based on the terrain type.
        """
        return self.terrain_speeds.get(terrain_type, self.terrain_speeds['default'])
