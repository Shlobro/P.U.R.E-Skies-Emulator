import math


class RoutePlanner:
    def __init__(self, algorithm='nearest_neighbor'):
        self.algorithm = algorithm

        # For demonstration, we'll store some "trash points" here directly.
        # In a real system, these might come from the environment or a config.
        self.trash_points = [
            (100, 50),
            (120, 80),
            (200, 100),
            (250, 150)
        ]

    def get_route_for_agent(self, agent, environment):
        """
        Compute a route for the agent based on the chosen algorithm.
        """
        if self.algorithm == 'nearest_neighbor':
            return self._nearest_neighbor_route(agent, environment)
        elif self.algorithm == 'tsp':
            return self._tsp_route(agent, environment)
        else:
            return []

    def _nearest_neighbor_route(self, agent, environment):
        """
        A simplistic nearest-neighbor approach that also checks agent capacity.
        If the agent reaches capacity, we insert a detour to the nearest bin.
        """
        route = []
        # Copy the trash list so we don't modify the master list
        remaining_trash = list(self.trash_points)

        current_pos = agent.position

        # Reset agent load for new route (just in case)
        agent.current_load = 0

        while remaining_trash:
            # 1. Find the nearest trash point
            nearest_index = None
            nearest_dist = float('inf')
            for i, tpos in enumerate(remaining_trash):
                dist = (tpos[0] - current_pos[0]) ** 2 + (tpos[1] - current_pos[1]) ** 2
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_index = i

            if nearest_index is None:
                break

            # 2. Append that trash point to the route
            next_trash = remaining_trash.pop(nearest_index)
            route.append(next_trash)
            current_pos = next_trash

            # 3. "Pick up" the trash (increment load)
            agent.current_load += 1

            # 4. Check if agent is at or above capacity
            if agent.needs_to_empty():
                bin_pos = environment.get_closest_bin(current_pos[0], current_pos[1])
                if bin_pos:
                    # Detour to bin
                    route.append(bin_pos)
                    current_pos = bin_pos
                # Empty the load
                agent.current_load = 0

        return route

    def _tsp_route(self, agent, environment):
        """
        Placeholder for more advanced TSP logic (e.g., using OR-Tools).
        """
        return []
