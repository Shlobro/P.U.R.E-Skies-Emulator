import numpy as np
import pygame
from dataclasses import dataclass
from typing import List, Tuple, Optional
from enum import Enum
from abc import ABC, abstractmethod
import asyncio
import heapq
from collections import defaultdict

# Physics constants
GRAVITY = 9.81  # m/s^2
AIR_RESISTANCE = 0.1
HUMAN_MAX_SPEED = 1.4  # m/s (average walking speed)
DRONE_MAX_SPEED = 5.0  # m/s
DRONE_MAX_ACCELERATION = 2.0  # m/s^2


class TerrainType(Enum):
    PAVEMENT = 1.0  # Speed multiplier
    GRASS = 0.7
    GRAVEL = 0.8


@dataclass
class Vector2D:
    x: float
    y: float

    def __add__(self, other):
        return Vector2D(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Vector2D(self.x - other.x, self.y - other.y)

    def magnitude(self):
        return np.sqrt(self.x ** 2 + self.y ** 2)

    def normalize(self):
        mag = self.magnitude()
        if mag == 0:
            return Vector2D(0, 0)
        return Vector2D(self.x / mag, self.y / mag)


class PhysicsObject:
    def __init__(self, position: Vector2D, mass: float):
        self.position = position
        self.velocity = Vector2D(0, 0)
        self.acceleration = Vector2D(0, 0)
        self.mass = mass

    def update(self, dt: float):
        # Update position and velocity using verlet integration
        self.velocity.x += self.acceleration.x * dt
        self.velocity.y += self.acceleration.y * dt
        self.position.x += self.velocity.x * dt
        self.position.y += self.velocity.y * dt

        # Apply air resistance
        speed = self.velocity.magnitude()
        if speed > 0:
            resistance = AIR_RESISTANCE * speed * speed
            direction = self.velocity.normalize()
            self.velocity.x -= direction.x * resistance * dt
            self.velocity.y -= direction.y * resistance * dt


class Agent(PhysicsObject, ABC):
    def __init__(self, position: Vector2D, mass: float, capacity: float):
        super().__init__(position, mass)
        self.capacity = capacity
        self.current_load = 0
        self.path = []
        self.stats = {
            'distance_traveled': 0,
            'items_collected': 0,
            'time_elapsed': 0
        }

    @abstractmethod
    def calculate_movement(self, target: Vector2D, dt: float):
        pass

    @abstractmethod
    def can_pickup(self, item_weight: float) -> bool:
        pass


class Human(Agent):
    def __init__(self, position: Vector2D):
        super().__init__(position, mass=70, capacity=20)
        self.fatigue = 0
        self.max_speed = HUMAN_MAX_SPEED

    def calculate_movement(self, target: Vector2D, dt: float):
        direction = target - self.position
        if direction.magnitude() > 0:
            # Apply fatigue effect
            current_max_speed = self.max_speed * (1 - self.fatigue)
            normalized_direction = direction.normalize()
            self.velocity.x = normalized_direction.x * current_max_speed
            self.velocity.y = normalized_direction.y * current_max_speed

        # Increase fatigue over time
        self.fatigue = min(0.5, self.fatigue + 0.001 * dt)

    def can_pickup(self, item_weight: float) -> bool:
        return self.current_load + item_weight <= self.capacity


class Drone(Agent):
    def __init__(self, position: Vector2D):
        super().__init__(position, mass=2, capacity=5)
        self.max_speed = DRONE_MAX_SPEED
        self.max_acceleration = DRONE_MAX_ACCELERATION
        self.battery_level = 100

    def calculate_movement(self, target: Vector2D, dt: float):
        direction = target - self.position
        if direction.magnitude() > 0:
            # Calculate desired velocity
            normalized_direction = direction.normalize()
            desired_velocity = Vector2D(
                normalized_direction.x * self.max_speed,
                normalized_direction.y * self.max_speed
            )

            # Calculate acceleration needed
            velocity_difference = desired_velocity - self.velocity
            self.acceleration.x = np.clip(velocity_difference.x, -self.max_acceleration, self.max_acceleration)
            self.acceleration.y = np.clip(velocity_difference.y, -self.max_acceleration, self.max_acceleration)

        # Decrease battery level based on movement
        self.battery_level -= 0.01 * self.velocity.magnitude() * dt

    def can_pickup(self, item_weight: float) -> bool:
        return self.current_load + item_weight <= self.capacity and self.battery_level > 10


class Environment:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.terrain = defaultdict(lambda: TerrainType.PAVEMENT)
        self.obstacles = []
        self.trash_items = []
        self.bins = []

    def add_obstacle(self, pos: Vector2D, size: Vector2D):
        self.obstacles.append((pos, size))

    def add_trash(self, pos: Vector2D, weight: float):
        self.trash_items.append((pos, weight))

    def add_bin(self, pos: Vector2D):
        self.bins.append(pos)

    def set_terrain(self, pos: Vector2D, terrain_type: TerrainType):
        self.terrain[(int(pos.x), int(pos.y))] = terrain_type


class Simulation:
    def __init__(self, environment: Environment):
        self.environment = environment
        self.agents = []
        self.time = 0
        self.running = False

    def add_agent(self, agent: Agent):
        self.agents.append(agent)

    async def run(self, duration: float):
        self.running = True
        dt = 0.016  # ~60 FPS

        while self.time < duration and self.running:
            for agent in self.agents:
                if agent.path:
                    target = agent.path[0]
                    agent.calculate_movement(target, dt)
                    agent.update(dt)

                    # Check if reached target
                    if (target - agent.position).magnitude() < 0.1:
                        agent.path.pop(0)

            self.time += dt
            await asyncio.sleep(dt)

    def stop(self):
        self.running = False


class Visualizer:
    def __init__(self, simulation: Simulation):
        pygame.init()
        self.simulation = simulation
        self.screen = pygame.display.set_mode((800, 600))
        self.clock = pygame.time.Clock()
        self.scale = 10  # pixels per meter

    def run(self):
        while self.simulation.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.simulation.stop()

            self.screen.fill((255, 255, 255))

            # Draw environment
            self._draw_environment()

            # Draw agents
            self._draw_agents()

            pygame.display.flip()
            self.clock.tick(60)

    def _draw_environment(self):
        # Draw terrain
        for pos, terrain_type in self.simulation.environment.terrain.items():
            color = {
                TerrainType.PAVEMENT: (200, 200, 200),
                TerrainType.GRASS: (100, 200, 100),
                TerrainType.GRAVEL: (150, 150, 150)
            }[terrain_type]
            pygame.draw.rect(self.screen, color,
                             (pos[0] * self.scale, pos[1] * self.scale,
                              self.scale, self.scale))

        # Draw obstacles
        for pos, size in self.simulation.environment.obstacles:
            pygame.draw.rect(self.screen, (100, 100, 100),
                             (pos.x * self.scale, pos.y * self.scale,
                              size.x * self.scale, size.y * self.scale))

        # Draw trash and bins
        for pos, _ in self.simulation.environment.trash_items:
            pygame.draw.circle(self.screen, (255, 0, 0),
                               (int(pos.x * self.scale), int(pos.y * self.scale)), 3)

        for pos in self.simulation.environment.bins:
            pygame.draw.rect(self.screen, (0, 255, 0),
                             (pos.x * self.scale - 5, pos.y * self.scale - 5, 10, 10))

    def _draw_agents(self):
        for agent in self.simulation.agents:
            color = (0, 0, 255) if isinstance(agent, Human) else (255, 165, 0)
            pygame.draw.circle(self.screen, color,
                               (int(agent.position.x * self.scale),
                                int(agent.position.y * self.scale)), 5)


# Example usage
async def main():
    # Create environment
    env = Environment(80, 60)

    # Add some terrain variations
    for x in range(20, 40):
        for y in range(15, 30):
            env.set_terrain(Vector2D(x, y), TerrainType.GRASS)

    # Add obstacles
    env.add_obstacle(Vector2D(30, 20), Vector2D(5, 2))

    # Add trash items
    env.add_trash(Vector2D(25, 25), 0.5)
    env.add_trash(Vector2D(35, 35), 1.0)

    # Add bins
    env.add_bin(Vector2D(40, 40))

    # Create simulation
    sim = Simulation(env)

    # Add agents
    human = Human(Vector2D(10, 10))
    drone = Drone(Vector2D(15, 15))

    # Set initial paths
    human.path = [Vector2D(25, 25), Vector2D(40, 40)]
    drone.path = [Vector2D(35, 35), Vector2D(40, 40)]

    sim.add_agent(human)
    sim.add_agent(drone)

    # Create visualizer
    vis = Visualizer(sim)

    # Run simulation and visualization
    await asyncio.gather(
        sim.run(60.0),  # Run for 60 seconds
        asyncio.to_thread(vis.run)
    )


if __name__ == "__main__":
    asyncio.run(main())