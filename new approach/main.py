import pygame

from simulation.engine import SimulationEngine
from simulation.environment import Environment
from simulation.routing import RoutePlanner
from simulation.agents import HumanAgent, DroneAgent
from visualization.visualizer import PygameVisualizer
from results.analysis import analyze_logs

def main():
    # 1. Create the environment
    environment = Environment()

    # 2. Add bins (for trash drop-off)
    environment.add_bin(200, 200)
    environment.add_bin(400, 400)

    # 3. Add an obstacle (rectangle) to visualize it and store
    environment.add_obstacle(pygame.Rect(100, 100, 50, 50))

    # 4. Define the routing planner
    route_planner = RoutePlanner(algorithm='nearest_neighbor')

    # 5. Create agents with capacities
    human = HumanAgent(name="Human1", position=(50, 50), capacity=5)
    drone = DroneAgent(name="Drone1", position=(300, 300), capacity=3)

    agents = [human, drone]

    # 6. Create a Pygame visualization
    visualizer = PygameVisualizer(width=800, height=600)

    # 7. Initialize the simulation engine
    engine = SimulationEngine(environment, agents, route_planner, visualization=visualizer, time_step=0.1)

    # 8. Run the simulation
    engine.run(max_time=300)

    # 9. Analyze results (optional)
    analyze_logs(engine.logs)


if __name__ == "__main__":
    main()
