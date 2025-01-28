import sys
import math
import random
import time
import asyncio  # For potential async concurrency
import numpy as np

# PyQt6 for GUI
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFormLayout, QLineEdit, QPushButton,
    QLabel, QHBoxLayout, QVBoxLayout, QMessageBox, QCheckBox, QSpinBox, QComboBox
)
from PyQt6.QtCore import QTimer, Qt

# Matplotlib for visualization
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.patches import Circle, Rectangle

###############################################################################
# ENVIRONMENT
###############################################################################
class SimulationEnvironment:
    """
    Manages the environment where the agents (humans/drones) move.
    It can handle:
        - Dimensions
        - Obstacles
        - Terrain mapping (different speeds)
        - Trash positions
        - Bin location(s)
        - Future expansions: dynamic trash, weather, etc.
    """
    def __init__(self, length=25, width=25):
        self.length = length
        self.width = width

        # Example: store obstacles or restricted zones
        # For more sophisticated obstacles, you'd keep polygons or grids
        self.obstacles = []

        # Terrain can be mapped as a function or a 2D array
        # E.g., terrain_speed_factor[x][y]
        self.terrain_speed_factor = 1.0  # default no slowdown

        # Bin positions (you can have multiple bins in advanced scenarios)
        self.bin_position = (0, 0)

        # List of trash positions
        self.trash_positions = []

    def generate_random_trash(self, num_trash):
        """
        Randomly scatter trash in the area (ignoring obstacles).
        """
        self.trash_positions = [
            (random.uniform(0, self.length), random.uniform(0, self.width))
            for _ in range(num_trash)
        ]

    def set_bin_position(self, position):
        self.bin_position = position

    def is_inside_obstacle(self, x, y):
        """
        Check if (x, y) is within any obstacle region.
        For now, do not allow trash or agents to be placed here.
        """
        # Placeholder for obstacle logic
        return False

###############################################################################
# ROUTING MANAGER
###############################################################################
class RoutingManager:
    """
    Provides different routing algorithms. Users can select:
        - Nearest Neighbor
        - TSP (via OR-Tools or custom code)
        - CVRP
        - Genetic / Dynamic Programming
    """
    def __init__(self):
        pass

    def nearest_neighbor(self, start, points):
        """
        A simple nearest neighbor route.
        """
        if not points:
            return [start]

        path = [start]
        remaining = points.copy()
        current = start
        while remaining:
            nearest = min(remaining, key=lambda p: self.distance(current, p))
            path.append(nearest)
            remaining.remove(nearest)
            current = nearest
        return path

    def capacity_split_path(self, start, points, capacity):
        """
        Simple capacity-based route that picks up trash in batches.
        capacity=0 => unlimited.
        """
        if capacity < 1:
            # treat as unlimited
            base_path = self.nearest_neighbor(start, points)
            if len(base_path) > 0 and base_path[-1] != start:
                base_path.append(start)
            return base_path

        # limited capacity
        remaining = points.copy()
        full_path = [start]
        current = start
        while remaining:
            # pick up to capacity pieces
            chunk = []
            for _ in range(min(capacity, len(remaining))):
                nearest = min(remaining, key=lambda p: self.distance(current, p))
                chunk.append(nearest)
                remaining.remove(nearest)
                current = nearest

            full_path.extend(chunk)
            # Return to start (bin)
            full_path.append(start)
            current = start
        return full_path

    # Example TSP approach using OR-Tools (sketch)
    # def or_tools_tsp(self, start, points):
    #     from ortools.constraint_solver import pywrapcp, routing_enums
    #     # Implementation here...
    #     # return path

    # Example CVRP approach using OR-Tools (sketch)
    # def or_tools_cvrp(self, start, points, capacity):
    #     # Implementation here...
    #     # return path

    @staticmethod
    def distance(p1, p2):
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

###############################################################################
# AGENT CLASSES
###############################################################################
class Agent:
    """
    Base class for any agent (human, drone).
    Handles:
        - Current position
        - Speed, acceleration, max speed
        - Movement logic
        - Pickup/delivery capacity
        - Route
    """
    def __init__(self,
                 environment: SimulationEnvironment,
                 route=None,
                 speed=1.0,
                 acceleration=0.0,
                 max_speed=2.0,
                 pickup_time=2.0,
                 capacity=0):
        self.env = environment
        self.route = route if route else []
        self.position_index = 0
        self.current_position = self.route[0] if self.route else environment.bin_position

        # Movement parameters
        self.speed = speed             # current speed
        self.acceleration = acceleration
        self.max_speed = max_speed

        # Time spent picking up
        self.pickup_time = pickup_time
        self.pickup_timer = 0.0

        # Stats
        self.distance_traveled = 0.0
        self.total_time = 0.0

        # Capacity: how many items can be carried (0 => unlimited)
        self.capacity = capacity

        # For collecting trash
        self.collected_positions = set()

    def update(self, dt):
        """
        Update the agent's state for this time step.
        - If picking up, decrement timer
        - Else move along route with acceleration
        """
        if self.pickup_timer > 0:
            self.pickup_timer -= dt
            if self.pickup_timer < 0:
                self.pickup_timer = 0.0
        else:
            self.move_along_route(dt)
        self.total_time += dt

    def move_along_route(self, dt):
        """
        Move to the next point in the route, subject to acceleration and max speed.
        """
        if self.position_index >= len(self.route) - 1:
            return  # finished route

        next_pos = self.route[self.position_index + 1]
        dist = self.distance(self.current_position, next_pos)

        # Increase speed with acceleration (simple model)
        if self.acceleration != 0:
            self.speed += self.acceleration * dt
            self.speed = min(self.speed, self.max_speed)

        # Distance we can travel this frame
        step_dist = self.speed * dt

        if step_dist >= dist:
            # We arrive at the next waypoint
            self.current_position = next_pos
            self.distance_traveled += dist
            self.position_index += 1

            # If it's a trash location, pick it up
            if next_pos in self.env.trash_positions:
                self.env.trash_positions.remove(next_pos)
                self.collected_positions.add(next_pos)
                self.pickup_timer = self.pickup_time

        else:
            # Move partially toward next_pos
            ratio = step_dist / dist
            nx = self.current_position[0] + ratio*(next_pos[0] - self.current_position[0])
            ny = self.current_position[1] + ratio*(next_pos[1] - self.current_position[1])
            self.current_position = (nx, ny)
            self.distance_traveled += step_dist

    @staticmethod
    def distance(p1, p2):
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

class HumanAgent(Agent):
    """
    Human-specific logic:
      - Possibly has fatigue (reducing max speed over time).
      - Has a typical walking speed, etc.
    """
    def __init__(self, environment, route=None, speed=1.4, pickup_time=2.0, capacity=20):
        super().__init__(
            environment,
            route=route,
            speed=speed,
            acceleration=0.0,
            max_speed=2.0,
            pickup_time=pickup_time,
            capacity=capacity
        )
        self.fatigue_factor = 0.0005  # example: lose 0.5% speed per second (tweak as needed)

    def update(self, dt):
        # Simple fatigue model: reduce speed slightly each update
        if self.speed > 0:
            self.speed -= self.speed * self.fatigue_factor * dt
        if self.speed < 0.1:
            self.speed = 0.1  # floor speed

        super().update(dt)

class DroneAgent(Agent):
    """
    Drone-specific logic:
      - Has acceleration, deceleration
      - Possibly limited battery or energy consumption model
      - Higher speed
    """
    def __init__(self,
                 environment,
                 route=None,
                 speed=0.0,
                 acceleration=2.0,
                 max_speed=16.0,
                 pickup_time=4.0,
                 capacity=1):
        super().__init__(
            environment,
            route=route,
            speed=speed,
            acceleration=acceleration,
            max_speed=max_speed,
            pickup_time=pickup_time,
            capacity=capacity
        )
        self.energy_consumed = 0.0
        self.energy_rate = 1.0  # dummy rate

    def update(self, dt):
        # Example energy consumption: consumption = speed * rate
        self.energy_consumed += self.speed * self.energy_rate * dt
        super().update(dt)

###############################################################################
# VISUALIZATION
###############################################################################
class SimulationVisualizer(FigureCanvasQTAgg):
    """
    Uses matplotlib to draw:
        - Agents (humans, drones)
        - Trash
        - Bins
        - Possibly obstacles or terrain differences
    """
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(10, 5))
        super().__init__(self.fig)
        self.setParent(parent)

        # Two subplots: left for human, right for drone
        self.ax_human, self.ax_drone = self.fig.subplots(1, 2)
        self.ax_human.set_aspect('equal', adjustable='box')
        self.ax_drone.set_aspect('equal', adjustable='box')

        # Some state references
        self.agents = []
        self.env = None

        # For real-time updates
        self.timer = QTimer()
        self.timer.setInterval(50)  # ~20 FPS
        self.timer.timeout.connect(self.update_frame)
        self.last_time = None

        # Patches
        self.human_patches = []
        self.drone_patches = []
        self.trash_scat_human = None
        self.trash_scat_drone = None
        self.bin_patch_human = None
        self.bin_patch_drone = None

        # Stats text
        self.human_info_text = None
        self.drone_info_text = None

    def setup_environment(self, env: SimulationEnvironment):
        self.env = env
        # Clear axes
        self.ax_human.clear()
        self.ax_drone.clear()

        # Titles
        self.ax_human.set_title("Human Cleaning")
        self.ax_drone.set_title("Drone Cleaning")

        self.ax_human.set_xlim(0, env.length)
        self.ax_human.set_ylim(0, env.width)
        self.ax_drone.set_xlim(0, env.length)
        self.ax_drone.set_ylim(0, env.width)

        # Bin patch
        bin_size = 0.04 * max(env.length, env.width)
        bx, by = env.bin_position
        self.bin_patch_human = Rectangle(
            (bx - bin_size/2, by - bin_size/2), bin_size, bin_size, color='brown'
        )
        self.bin_patch_drone = Rectangle(
            (bx - bin_size/2, by - bin_size/2), bin_size, bin_size, color='brown'
        )
        self.ax_human.add_patch(self.bin_patch_human)
        self.ax_drone.add_patch(self.bin_patch_drone)

        # Trash scatter
        hx = [p[0] for p in env.trash_positions]
        hy = [p[1] for p in env.trash_positions]
        self.trash_scat_human = self.ax_human.scatter(hx, hy, c='red')
        self.trash_scat_drone = self.ax_drone.scatter(hx, hy, c='red')

        # Info text
        self.human_info_text = self.ax_human.text(
            0.01, 1.01, "",
            transform=self.ax_human.transAxes,
            fontsize=10, color="blue"
        )
        self.drone_info_text = self.ax_drone.text(
            0.01, 1.01, "",
            transform=self.ax_drone.transAxes,
            fontsize=10, color="green"
        )

        self.draw()

    def add_agents(self, human_agents, drone_agents):
        """
        Add references to the agents we want to visualize.
        """
        self.agents = list(human_agents) + list(drone_agents)

        # For each human agent, add a circle patch in ax_human
        for i, agent in enumerate(human_agents):
            patch = Circle(agent.current_position, radius=0.3, color='blue')
            self.ax_human.add_patch(patch)
            self.human_patches.append(patch)

        # For each drone agent, add a circle patch in ax_drone
        for i, agent in enumerate(drone_agents):
            patch = Circle(agent.current_position, radius=0.3, color='green')
            self.ax_drone.add_patch(patch)
            self.drone_patches.append(patch)

        self.draw()

    def start(self):
        self.last_time = time.time()
        self.timer.start()

    def stop(self):
        self.timer.stop()

    def update_frame(self):
        current_time = time.time()
        dt = current_time - self.last_time if self.last_time else 0
        self.last_time = current_time

        # Update all agents
        for agent in self.agents:
            agent.update(dt)

        # Update circle positions
        for hp in self.human_patches:
            # Find which agent it belongs to
            # (Here we rely on the matching index in the agent list)
            idx = self.human_patches.index(hp)
            agent = [a for a in self.agents if isinstance(a, HumanAgent)][idx]
            hp.center = agent.current_position

        for dp in self.drone_patches:
            idx = self.drone_patches.index(dp)
            agent = [a for a in self.agents if isinstance(a, DroneAgent)][idx]
            dp.center = agent.current_position

        # Update trash scatters if any trash was picked
        # (Here, we can just re-draw them from the environment)
        if self.env:
            hx = [p[0] for p in self.env.trash_positions]
            hy = [p[1] for p in self.env.trash_positions]
            self.trash_scat_human.set_offsets(np.c_[hx, hy])
            self.trash_scat_drone.set_offsets(np.c_[hx, hy])

        # Update info text
        # For simplicity, assume one human agent and one drone agent
        human_agents = [a for a in self.agents if isinstance(a, HumanAgent)]
        drone_agents = [a for a in self.agents if isinstance(a, DroneAgent)]

        if human_agents:
            h = human_agents[0]  # just the first human for display
            collected = len(h.collected_positions)
            total_trash = len(h.collected_positions) + len(self.env.trash_positions)
            self.human_info_text.set_text(
                f"Time: {h.total_time:.2f}s\n"
                f"Distance: {h.distance_traveled:.2f}m\n"
                f"Collected: {collected}/{total_trash}"
            )

        if drone_agents:
            d = drone_agents[0]  # first drone
            collected = len(d.collected_positions)
            total_trash = len(d.collected_positions) + len(self.env.trash_positions)
            self.drone_info_text.set_text(
                f"Time: {d.total_time:.2f}s\n"
                f"Distance: {d.distance_traveled:.2f}m\n"
                f"Collected: {collected}/{total_trash}"
            )

        self.draw()

        # Check if all routes are done
        done = all(a.position_index >= len(a.route) - 1 for a in self.agents)
        # (You might also check if all trash is collected)
        if done:
            self.stop()
            self.print_summary()

    def print_summary(self):
        """
        Print or store final simulation results.
        """
        print("\n=== Simulation Complete ===")
        for i, agent in enumerate(self.agents):
            if isinstance(agent, HumanAgent):
                print(f"Human {i} -> Time: {agent.total_time:.2f}, Distance: {agent.distance_traveled:.2f}")
            else:
                print(f"Drone {i} -> Time: {agent.total_time:.2f}, Distance: {agent.distance_traveled:.2f}")

###############################################################################
# MAIN WINDOW (GUI)
###############################################################################
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cleaning Simulation (Modular)")

        # Main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout()
        self.central_widget.setLayout(self.main_layout)

        # Form layout (left side)
        self.form_layout = QFormLayout()

        # Inputs
        self.length_edit = QLineEdit("25")
        self.width_edit = QLineEdit("25")
        self.trash_edit = QLineEdit("20")

        self.human_speed_edit = QLineEdit("1.4")
        self.drone_speed_edit = QLineEdit("16.0")

        self.human_pickup_edit = QLineEdit("2.0")
        self.drone_pickup_edit = QLineEdit("4.0")

        self.human_capacity_edit = QLineEdit("20")
        self.drone_capacity_edit = QLineEdit("1")

        self.multiple_drones_checkbox = QCheckBox("Use Multiple Drones?")
        self.drones_spin = QSpinBox()
        self.drones_spin.setValue(2)
        self.drones_spin.setMinimum(1)
        self.drones_spin.setEnabled(False)

        self.bin_position_combo = QComboBox()
        self.bin_position_combo.addItems([
            "Bottom-Left",
            "Top-Left",
            "Bottom-Right",
            "Top-Right",
            "Center"
        ])

        self.routing_combo = QComboBox()
        self.routing_combo.addItems([
            "Nearest Neighbor",
            "Capacity-based",
            # "OR-Tools TSP",    # uncomment if you implement it
            # "OR-Tools CVRP",   # likewise
        ])

        # Buttons
        self.start_button = QPushButton("Start Simulation")
        self.reset_button = QPushButton("Reset")

        # Connect signals
        self.multiple_drones_checkbox.stateChanged.connect(self.on_multiple_drones_checked)
        self.start_button.clicked.connect(self.start_simulation)
        self.reset_button.clicked.connect(self.reset_parameters)

        # Populate the form
        self.form_layout.addRow("Area Length (m):", self.length_edit)
        self.form_layout.addRow("Area Width (m):", self.width_edit)
        self.form_layout.addRow("Number of Trash:", self.trash_edit)

        self.form_layout.addRow("Human Speed:", self.human_speed_edit)
        self.form_layout.addRow("Drone Speed:", self.drone_speed_edit)

        self.form_layout.addRow("Human Pickup Time:", self.human_pickup_edit)
        self.form_layout.addRow("Drone Pickup Time:", self.drone_pickup_edit)

        self.form_layout.addRow("Human Capacity (0=unlimited):", self.human_capacity_edit)
        self.form_layout.addRow("Drone Capacity (0=unlimited):", self.drone_capacity_edit)

        self.form_layout.addRow(self.multiple_drones_checkbox, self.drones_spin)

        self.form_layout.addRow("Bin Position:", self.bin_position_combo)
        self.form_layout.addRow("Routing Algorithm:", self.routing_combo)

        self.form_layout.addRow(self.start_button, self.reset_button)

        # Add form layout to main
        self.main_layout.addLayout(self.form_layout)

        # Visualization Canvas
        self.sim_canvas = SimulationVisualizer()
        self.main_layout.addWidget(self.sim_canvas)

        # Data
        self.env = SimulationEnvironment()
        self.routing_mgr = RoutingManager()

    def on_multiple_drones_checked(self, state):
        if state == Qt.CheckState.Checked.value:
            self.drones_spin.setEnabled(True)
        else:
            self.drones_spin.setEnabled(False)

    def start_simulation(self):
        try:
            length = float(self.length_edit.text())
            width = float(self.width_edit.text())
            num_trash = int(self.trash_edit.text())

            human_speed = float(self.human_speed_edit.text())
            drone_speed = float(self.drone_speed_edit.text())

            human_pickup = float(self.human_pickup_edit.text())
            drone_pickup = float(self.drone_pickup_edit.text())

            human_capacity = int(self.human_capacity_edit.text())
            drone_capacity = int(self.drone_capacity_edit.text())

            # Validation
            if (length <= 0 or width <= 0 or num_trash < 0 or
                human_speed <= 0 or drone_speed <= 0 or
                human_pickup < 0 or drone_pickup < 0 or
                human_capacity < 0 or drone_capacity < 0):
                QMessageBox.warning(self, "Invalid Input",
                                    "Please enter valid positive values.\nUse 0 only for unlimited capacity.")
                return

            # Set up environment
            self.env.length = length
            self.env.width = width
            self.env.generate_random_trash(num_trash)

            # Bin position
            bin_choice = self.bin_position_combo.currentText()
            bin_pos = self.get_bin_position(bin_choice, length, width)
            self.env.set_bin_position(bin_pos)

            # Decide which routing to use
            route_selection = self.routing_combo.currentText()

            # Single or multiple drones
            multiple_drones = self.multiple_drones_checkbox.isChecked()
            n_drones = self.drones_spin.value() if multiple_drones else 1

            # Build agent routes
            # 1. Human
            if route_selection == "Nearest Neighbor":
                human_route = self.routing_mgr.nearest_neighbor(bin_pos, self.env.trash_positions)
                if human_route[-1] != bin_pos:
                    human_route.append(bin_pos)
            elif route_selection == "Capacity-based":
                human_route = self.routing_mgr.capacity_split_path(bin_pos, self.env.trash_positions, human_capacity)
            else:
                # fallback
                human_route = [bin_pos]

            human_agent = HumanAgent(
                self.env,
                route=human_route,
                speed=human_speed,
                pickup_time=human_pickup,
                capacity=human_capacity
            )

            # 2. Drones
            # For simplicity, we'll assign all trash to each drone with same route or
            # do naive splitting. Here we do naive splitting:
            if route_selection == "Nearest Neighbor":
                # single route for all trash, then replicate for each drone? (not ideal)
                # or we can do a naive round-robin split
                all_points = self.env.trash_positions.copy()
                # We'll rebuild trash sets for each drone so they each do partial tasks.
                splitted = self.split_trash_among_drones(all_points, n_drones, bin_pos)
                drone_agents = []
                for i in range(n_drones):
                    route = self.routing_mgr.nearest_neighbor(bin_pos, splitted[i])
                    if route[-1] != bin_pos:
                        route.append(bin_pos)
                    drone = DroneAgent(
                        self.env,
                        route=route,
                        speed=0.0,            # start from 0, accelerate
                        acceleration=2.0,
                        max_speed=drone_speed,
                        pickup_time=drone_pickup,
                        capacity=drone_capacity
                    )
                    drone_agents.append(drone)

            elif route_selection == "Capacity-based":
                # same capacity-based route for each drone with partial trash
                all_points = self.env.trash_positions.copy()
                splitted = self.split_trash_among_drones(all_points, n_drones, bin_pos)
                drone_agents = []
                for i in range(n_drones):
                    route = self.routing_mgr.capacity_split_path(bin_pos, splitted[i], drone_capacity)
                    drone = DroneAgent(
                        self.env,
                        route=route,
                        speed=0.0,            # start from 0, accelerate
                        acceleration=2.0,
                        max_speed=drone_speed,
                        pickup_time=drone_pickup,
                        capacity=drone_capacity
                    )
                    drone_agents.append(drone)
            else:
                drone_agents = []

            # Reset the visualization
            self.sim_canvas.stop()
            self.sim_canvas.setup_environment(self.env)
            self.sim_canvas.add_agents([human_agent], drone_agents)
            self.sim_canvas.start()

        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please check your input fields.")

    def reset_parameters(self):
        self.sim_canvas.stop()
        # Restore defaults
        self.length_edit.setText("25")
        self.width_edit.setText("25")
        self.trash_edit.setText("20")
        self.human_speed_edit.setText("1.4")
        self.drone_speed_edit.setText("16.0")
        self.human_pickup_edit.setText("2.0")
        self.drone_pickup_edit.setText("4.0")
        self.human_capacity_edit.setText("20")
        self.drone_capacity_edit.setText("1")
        self.multiple_drones_checkbox.setChecked(False)
        self.drones_spin.setValue(2)
        self.drones_spin.setEnabled(False)
        self.bin_position_combo.setCurrentIndex(0)
        self.routing_combo.setCurrentIndex(0)

        # Clear environment and canvas
        self.env = SimulationEnvironment()
        self.sim_canvas.setup_environment(self.env)

    def split_trash_among_drones(self, trash_points, num_drones, start):
        """
        Simple method: sort by distance to 'start' and round-robin.
        """
        sorted_pts = sorted(trash_points, key=lambda p: math.hypot(p[0]-start[0], p[1]-start[1]))
        assignments = [[] for _ in range(num_drones)]
        idx = 0
        for pt in sorted_pts:
            assignments[idx].append(pt)
            idx = (idx + 1) % num_drones
        return assignments

    def get_bin_position(self, selection, length, width):
        if selection == "Bottom-Left":
            return (0, 0)
        elif selection == "Top-Left":
            return (0, width)
        elif selection == "Bottom-Right":
            return (length, 0)
        elif selection == "Top-Right":
            return (length, width)
        elif selection == "Center":
            return (length/2, width/2)
        else:
            return (0, 0)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(1300, 600)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
