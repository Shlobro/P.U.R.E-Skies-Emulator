import networkx as nx

class Environment:
    def __init__(self):
        """
        Holds a representation of the environment, like:
          - a graph for routing
          - obstacle data
          - terrain types
        """
        self.graph = nx.Graph()
        self.obstacles = []
        self.terrain_speeds = {'default': 1.0, 'grass': 0.8, 'pavement': 1.2}
        # Example: nodes, edges, positions can be loaded or generated

    def add_obstacle(self, obstacle):
        """
        Add obstacle to the environment (could be a rectangle, circle, etc.).
        """
        self.obstacles.append(obstacle)

    def is_path_blocked(self, start, end):
        """
        Check if a path is blocked. This is a placeholder for collision checks.
        """
        # Implement collision logic or restricted zone logic
        return False

    def get_speed_modifier(self, terrain_type):
        """
        Return speed modifier based on the terrain type.
        """
        return self.terrain_speeds.get(terrain_type, self.terrain_speeds['default'])
