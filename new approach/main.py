from simulation.engine import SimulationEngine
from simulation.environment import Environment
from simulation.routing import RoutePlanner
from simulation.agents import HumanAgent, DroneAgent
from visualization.visualizer import PygameVisualizer
from results.analysis import analyze_logs

def main():
    # 1. Create the environment
    environment = Environment()
    # Example obstacle (rectangle): position (100,100), size 50x50
    environment.add_obstacle(pygame.Rect(100, 100, 50, 50))

    # 2. Define the routing planner
    route_planner = RoutePlanner(algorithm='nearest_neighbor')

    # 3. Create agents
    human = HumanAgent(name="Human1", position=(50,50))
    drone = DroneAgent(name="Drone1", position=(300,300))

    agents = [human, drone]

    # 4. Create visualization
    visualizer = PygameVisualizer(width=800, height=600)

    # 5. Initialize the simulation engine
    engine = SimulationEngine(environment, agents, route_planner, visualization=visualizer)

    # 6. Run the simulation
    engine.run(max_time=300)

    # 7. Analyze results
    analyze_logs(engine.logs)

if __name__ == "__main__":
    import pygame  # If you're using Pygame
    main()
