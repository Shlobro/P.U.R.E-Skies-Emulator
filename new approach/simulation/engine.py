import time


class SimulationEngine:
    def __init__(self, environment, agents, route_planner, visualization=None, time_step=0.1):
        """
        :param environment: Environment object containing terrain, obstacles, etc.
        :param agents: List of Agent objects (humans, drones).
        :param route_planner: A routing object providing paths for agents.
        :param visualization: Visualization object for real-time rendering.
        :param time_step: Simulation step in seconds.
        """
        self.environment = environment
        self.agents = agents
        self.route_planner = route_planner
        self.visualization = visualization
        self.time_step = time_step
        self.current_time = 0.0
        self.logs = []

    def run(self, max_time=1000):
        """
        Runs the simulation for a maximum of `max_time` seconds (or until tasks are complete).
        """
        # Initialize routes (if needed)
        for agent in self.agents:
            agent.assign_route(self.route_planner.get_route_for_agent(agent, self.environment))

        while self.current_time < max_time and not self.all_tasks_completed():
            self.update_agents()
            self.current_time += self.time_step

            # Logging
            self.logs.append(self.record_state())

            # Visualization update
            if self.visualization:
                self.visualization.update(self.environment, self.agents, self.current_time)

            # Sleep or pass for real-time feel (optional)
            # time.sleep(self.time_step)

        # Simulation ended
        if self.visualization:
            self.visualization.finalize()

    def update_agents(self):
        """
        Update each agent's position according to physics and their assigned route.
        """
        for agent in self.agents:
            agent.update(self.time_step, self.environment)

    def all_tasks_completed(self):
        """
        Placeholder for checking if all trash collection tasks are complete.
        """
        return all(agent.is_done() for agent in self.agents)

    def record_state(self):
        """
        Return a snapshot of the current state for logging.
        """
        state_info = {
            'time': self.current_time,
            'agents': [agent.get_state() for agent in self.agents]
        }
        return state_info
