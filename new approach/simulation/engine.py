import time
import logging


class SimulationEngine:
    def __init__(self, environment, agents, route_planner, visualization=None, time_step=0.1):
        """
        :param environment: Environment object containing terrain, obstacles, bins, etc.
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

        # Basic logger setup
        self.logger = logging.getLogger("SimulationEngine")
        if not self.logger.handlers:
            self.logger.setLevel(logging.DEBUG)
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            self.logger.addHandler(console_handler)

    def run(self, max_time=1000):
        """
        Runs the simulation for a maximum of `max_time` seconds (or until tasks are complete).
        """
        # Initialize routes
        for agent in self.agents:
            route = self.route_planner.get_route_for_agent(agent, self.environment)
            agent.assign_route(route)

        while self.current_time < max_time and not self.all_tasks_completed():
            self.update_agents()
            self.current_time += self.time_step

            # Record state
            self.logs.append(self.record_state())

            # Visualization update
            if self.visualization:
                self.visualization.update(self.environment, self.agents, self.current_time)

        # Finalize visualization
        if self.visualization:
            self.visualization.finalize()

    def update_agents(self):
        """
        Update each agent's position according to its physics and route.
        """
        for agent in self.agents:
            old_load = agent.current_load
            old_position = agent.position
            agent.update(self.time_step, self.environment)

            # Simple debug: check if the agent dropped off trash
            if old_load > agent.current_load and agent.current_load == 0:
                self.logger.debug(f"{agent.name} dropped trash at bin {agent.position}")

    def all_tasks_completed(self):
        """
        Placeholder for checking if all trash collection tasks are complete.
        For now, we'll say tasks are complete if all agents are 'done' with their routes.
        """
        return all(agent.is_done() for agent in self.agents)

    def record_state(self):
        """
        Return a snapshot of the current state for logging or analysis.
        """
        state_info = {
            'time': self.current_time,
            'agents': [agent.get_state() for agent in self.agents]
        }
        return state_info
