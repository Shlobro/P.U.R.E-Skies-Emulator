#!/usr/bin/env python3
"""
Trash Collection Simulation:
A comprehensive simulation tool for comparing the efficiency and cost–effectiveness of using drones versus humans.
It features two modules:
  1. Business Analysis: Varies the time frame (in days, months, or years) to compute cumulative collection time and cost.
  2. Operational Simulation: A realistic agent–based simulation where drones and humans “move” in an environment.

Run this script to launch the PyQt6 GUI.
"""

import sys
import math
import random
import time
import numpy as np
import matplotlib.pyplot as plt

# PyQt6 imports
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QFormLayout, QLineEdit,
    QPushButton, QHBoxLayout, QVBoxLayout, QMessageBox, QCheckBox,
    QSpinBox, QComboBox, QSizePolicy
)
from PyQt6.QtCore import QTimer, Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle, Circle


###############################################################################
# Business Simulation Functions (Static Analysis)
###############################################################################
def get_inefficiency_factor(search_algorithm):
    """
    Returns an inefficiency factor based on the search algorithm string.
    Lower factor means a more efficient path plan.
    """
    algo = search_algorithm.lower()
    if "random" in algo:
        return 1.5
    elif "grid" in algo:
        return 1.0
    elif "ai" in algo:
        return 0.8
    else:
        return 1.2  # default


def compute_trip_distance(capacity, width, height, bin_location, ineff_factor, beta=0.75):
    """
    Estimate the trip distance (meters) for one trip to collect up to 'capacity' trash items.
    Uses a TSP–inspired scaling law.
    """
    area = width * height
    tsp_length = beta * np.sqrt(capacity * area)
    center = (width / 2.0, height / 2.0)
    d_center = np.sqrt((bin_location[0] - center[0]) ** 2 + (bin_location[1] - center[1]) ** 2)
    return ineff_factor * (tsp_length + d_center)


def compute_event_time(total_trash, capacity, num_agents, speed, width, height, bin_location, ineff_factor):
    """
    Compute the collection time (in hours) for one event.
    """
    trips_total = np.ceil(total_trash / capacity)
    trips_per_agent = np.ceil(trips_total / num_agents)
    trip_distance = compute_trip_distance(capacity, width, height, bin_location, ineff_factor)
    trip_time_seconds = trip_distance / speed  # seconds per trip
    return (trips_per_agent * trip_time_seconds) / 3600.0  # convert to hours


def compute_event_cost(total_time_hours, num_agents, hourly_cost):
    """Compute the operational cost (in dollars) for one event."""
    return total_time_hours * num_agents * hourly_cost


def breakeven_days(initial_drone_cost_total, human_event_cost, drone_event_cost, events_per_day=1):
    """
    Compute the number of days for the cumulative cost of drones (including initial cost)
    to become lower than human collection costs. Returns None if no breakeven exists.
    """
    cost_diff = human_event_cost - drone_event_cost
    if cost_diff <= 0:
        return None
    return initial_drone_cost_total / (cost_diff * events_per_day)


def run_business_simulation(params, flex_param_name, flex_range):
    """
    For each value in flex_range (which in this version is always 'time_frame'),
    update the simulation parameter and compute:
      - Total collection time (in hours) over the entire time frame
      - Total cost over the entire time frame
    (Assuming one collection event per day.)
    Returns a list of result dictionaries.
    """
    results = []
    ineff_factor = get_inefficiency_factor(params["search_algorithm"])
    # Compute per-event (single-day) values.
    drone_time_event = compute_event_time(
        total_trash=params["total_trash"],
        capacity=params["drone_capacity"],
        num_agents=params["num_drones"],
        speed=params["drone_speed"],
        width=params["width"],
        height=params["height"],
        bin_location=params["bin_location"],
        ineff_factor=ineff_factor
    )
    human_time_event = compute_event_time(
        total_trash=params["total_trash"],
        capacity=params["human_capacity"],
        num_agents=params["num_humans"],
        speed=params["human_speed"],
        width=params["width"],
        height=params["height"],
        bin_location=params["bin_location"],
        ineff_factor=ineff_factor
    )
    drone_cost_event = compute_event_cost(drone_time_event, params["num_drones"], params["hourly_drone_cost"])
    human_cost_event = compute_event_cost(human_time_event, params["num_humans"], params["hourly_human_cost"])

    # Since flex_param_name is always "time_frame", we scale by the number of days (events per day = 1).
    for val in flex_range:
        unit = params["time_frame_unit"]
        if unit.lower().startswith("day"):
            events = val  # val is in days
        elif unit.lower().startswith("month"):
            events = val * 30
        elif unit.lower().startswith("year"):
            events = val * 365
        else:
            events = val
        total_drone_time = drone_time_event * events
        total_human_time = human_time_event * events
        total_drone_cost = drone_cost_event * events + params["num_drones"] * params["initial_drone_cost"]
        total_human_cost = human_cost_event * events
        results.append({
            "time_frame": val,
            "drone_total_collection_time_hours": total_drone_time,
            "human_total_collection_time_hours": total_human_time,
            "drone_total_cost": total_drone_cost,
            "human_total_cost": total_human_cost
        })
    return results


###############################################################################
# Business Analysis Widget (Static Model)
###############################################################################
class BusinessAnalysisWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_params = {}  # to store parameters for later use in plotting
        self.init_ui()

    def init_ui(self):
        # Create layouts
        main_layout = QHBoxLayout(self)
        form_layout = QFormLayout()
        controls_layout = QVBoxLayout()

        # Input fields with defaults matching the Operational Simulator:
        self.drone_speed_edit = QLineEdit("16")  # m/s
        self.human_speed_edit = QLineEdit("1.4")  # m/s
        self.total_trash_edit = QLineEdit("20")
        self.width_edit = QLineEdit("25")  # m
        self.height_edit = QLineEdit("25")  # m
        self.drone_capacity_edit = QLineEdit("1")
        self.human_capacity_edit = QLineEdit("20")
        self.num_drones_edit = QLineEdit("1")
        self.num_humans_edit = QLineEdit("1")
        self.search_algo_edit = QLineEdit("Grid Search")
        self.bin_x_edit = QLineEdit("12.5")
        self.bin_y_edit = QLineEdit("12.5")
        self.hourly_drone_cost_edit = QLineEdit("20")
        self.hourly_human_cost_edit = QLineEdit("15")

        # Instead of a single time_frame value, we now provide a range for the time frame.
        self.time_frame_unit_combo = QComboBox()
        self.time_frame_unit_combo.addItems(["days", "months", "years"])
        self.time_frame_unit_combo.setCurrentText("days")
        self.time_frame_start_edit = QLineEdit("1")
        self.time_frame_stop_edit = QLineEdit("30")
        self.time_frame_step_edit = QLineEdit("1")
        self.initial_drone_cost_edit = QLineEdit("0")

        # Add form rows
        form_layout.addRow("Drone Speed (m/s):", self.drone_speed_edit)
        form_layout.addRow("Human Speed (m/s):", self.human_speed_edit)
        form_layout.addRow("Total Trash Items:", self.total_trash_edit)
        form_layout.addRow("Area Width (m):", self.width_edit)
        form_layout.addRow("Area Height (m):", self.height_edit)
        form_layout.addRow("Drone Capacity (items/trip):", self.drone_capacity_edit)
        form_layout.addRow("Human Capacity (items/trip):", self.human_capacity_edit)
        form_layout.addRow("Number of Drones:", self.num_drones_edit)
        form_layout.addRow("Number of Humans:", self.num_humans_edit)
        form_layout.addRow("Search Algorithm:", self.search_algo_edit)
        form_layout.addRow("Bin Location X (m):", self.bin_x_edit)
        form_layout.addRow("Bin Location Y (m):", self.bin_y_edit)
        form_layout.addRow("Hourly Drone Cost ($):", self.hourly_drone_cost_edit)
        form_layout.addRow("Hourly Human Cost ($):", self.hourly_human_cost_edit)
        form_layout.addRow("Initial Drone Cost ($):", self.initial_drone_cost_edit)
        form_layout.addRow("Time Frame Unit:", self.time_frame_unit_combo)
        form_layout.addRow("Time Frame Start:", self.time_frame_start_edit)
        form_layout.addRow("Time Frame Stop:", self.time_frame_stop_edit)
        form_layout.addRow("Time Frame Step:", self.time_frame_step_edit)

        # Run Analysis Button
        self.run_button = QPushButton("Run Analysis")
        self.run_button.clicked.connect(self.run_analysis)
        controls_layout.addLayout(form_layout)
        controls_layout.addWidget(self.run_button)
        controls_layout.addStretch()

        # Matplotlib canvas for plotting results
        self.figure = Figure(figsize=(6, 8))
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Add controls on left and plot on right
        main_layout.addLayout(controls_layout, 1)
        main_layout.addWidget(self.canvas, 2)

    def run_analysis(self):
        try:
            # Build simulation parameters dictionary (all per-event values)
            params = {
                "drone_speed": float(self.drone_speed_edit.text()),
                "human_speed": float(self.human_speed_edit.text()),
                "total_trash": int(self.total_trash_edit.text()),
                "width": float(self.width_edit.text()),
                "height": float(self.height_edit.text()),
                "drone_capacity": int(self.drone_capacity_edit.text()),
                "human_capacity": int(self.human_capacity_edit.text()),
                "num_drones": int(self.num_drones_edit.text()),
                "num_humans": int(self.num_humans_edit.text()),
                "search_algorithm": self.search_algo_edit.text(),
                "bin_location": (float(self.bin_x_edit.text()), float(self.bin_y_edit.text())),
                "hourly_drone_cost": float(self.hourly_drone_cost_edit.text()),
                "hourly_human_cost": float(self.hourly_human_cost_edit.text()),
                "time_frame_unit": self.time_frame_unit_combo.currentText(),
                "initial_drone_cost": float(self.initial_drone_cost_edit.text())
            }
            self.current_params = params  # save for plotting later

            # Always use "time_frame" as the flexible parameter.
            flex_param = "time_frame"
            start = float(self.time_frame_start_edit.text())
            stop = float(self.time_frame_stop_edit.text())
            step = float(self.time_frame_step_edit.text())
            flex_range = np.arange(start, stop + step / 2, step)

            # Run the simulation over the time frame range.
            results = run_business_simulation(params, flex_param, flex_range)
            self.plot_results(results)
        except Exception as e:
            QMessageBox.critical(self, "Input Error", f"An error occurred:\n{e}")

    def plot_results(self, results):
        # Clear the figure and set up two subplots.
        self.figure.clear()
        ax1 = self.figure.add_subplot(211)
        ax2 = self.figure.add_subplot(212, sharex=ax1)

        # Extract data from results.
        x_vals = [r["time_frame"] for r in results]
        drone_times = [r["drone_total_collection_time_hours"] for r in results]
        human_times = [r["human_total_collection_time_hours"] for r in results]
        drone_costs = [r["drone_total_cost"] for r in results]
        human_costs = [r["human_total_cost"] for r in results]

        # Plot cumulative collection time.
        ax1.plot(x_vals, drone_times, 'b-o', label="Drones")
        ax1.plot(x_vals, human_times, 'r-s', label="Humans")
        ax1.set_ylabel("Total Collection Time (hours)")
        ax1.set_title("Effect of Time Frame on Total Collection Time and Cost")
        ax1.legend()
        ax1.grid(True)

        # Plot cumulative cost.
        ax2.plot(x_vals, drone_costs, 'b-o', label="Drones")
        ax2.plot(x_vals, human_costs, 'r-s', label="Humans")
        unit = self.current_params["time_frame_unit"]
        ax2.set_xlabel(f"Time Frame ({unit})")
        ax2.set_ylabel("Total Cost ($)")
        ax2.legend()
        ax2.grid(True)

        self.canvas.draw()


###############################################################################
# Operational Simulation Classes (Dynamic, Agent-based Simulation)
###############################################################################
class SimulationEnvironment:
    """
    Represents the physical area for cleaning.
    """

    def __init__(self, length=25, width=25):
        self.length = length
        self.width = width
        self.obstacles = []  # future use
        self.bin_position = (0, 0)
        self.trash_positions = []

    def generate_random_trash(self, num_trash):
        self.trash_positions = [
            (random.uniform(0, self.length), random.uniform(0, self.width))
            for _ in range(num_trash)
        ]

    def set_bin_position(self, position):
        self.bin_position = position


class RoutingManager:
    """
    Provides simple routing algorithms.
    """

    def __init__(self):
        pass

    def nearest_neighbor(self, start, points):
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
        if path[-1] != start:
            path.append(start)
        return path

    def capacity_split_path(self, start, points, capacity):
        if capacity < 1:
            return self.nearest_neighbor(start, points)
        remaining = points.copy()
        full_path = [start]
        current = start
        while remaining:
            chunk = []
            for _ in range(min(capacity, len(remaining))):
                nearest = min(remaining, key=lambda p: self.distance(current, p))
                chunk.append(nearest)
                remaining.remove(nearest)
                current = nearest
            full_path.extend(chunk)
            full_path.append(start)
            current = start
        return full_path

    @staticmethod
    def distance(p1, p2):
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


class Agent:
    """
    Base class for an agent.
    """

    def __init__(self, environment: SimulationEnvironment, route=None,
                 speed=1.0, acceleration=0.0, max_speed=2.0, pickup_time=2.0, capacity=0):
        self.env = environment
        self.route = route if route else [environment.bin_position]
        self.position_index = 0
        self.current_position = self.route[0]
        self.speed = speed
        self.acceleration = acceleration
        self.max_speed = max_speed
        self.pickup_time = pickup_time
        self.pickup_timer = 0.0
        self.distance_traveled = 0.0
        self.total_time = 0.0
        self.capacity = capacity
        self.collected_positions = set()

    def update(self, dt):
        if self.pickup_timer > 0:
            self.pickup_timer -= dt
            if self.pickup_timer < 0:
                self.pickup_timer = 0.0
        else:
            self.move_along_route(dt)
        self.total_time += dt

    def move_along_route(self, dt):
        if self.position_index >= len(self.route) - 1:
            return
        next_pos = self.route[self.position_index + 1]
        dist = self.distance(self.current_position, next_pos)
        # Accelerate
        if self.acceleration:
            self.speed = min(self.speed + self.acceleration * dt, self.max_speed)
        step_dist = self.speed * dt
        if step_dist >= dist:
            self.current_position = next_pos
            self.distance_traveled += dist
            self.position_index += 1
            # If reached a trash position, "pick it up"
            if next_pos in self.env.trash_positions:
                self.env.trash_positions.remove(next_pos)
                self.collected_positions.add(next_pos)
                self.pickup_timer = self.pickup_time
        else:
            ratio = step_dist / dist
            nx = self.current_position[0] + ratio * (next_pos[0] - self.current_position[0])
            ny = self.current_position[1] + ratio * (next_pos[1] - self.current_position[1])
            self.current_position = (nx, ny)
            self.distance_traveled += step_dist

    @staticmethod
    def distance(p1, p2):
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


class HumanAgent(Agent):
    """
    Human agent with a simple fatigue model.
    """

    def __init__(self, environment, route=None, speed=1.4, pickup_time=2.0, capacity=20):
        super().__init__(environment, route, speed, acceleration=0.0, max_speed=2.0, pickup_time=pickup_time,
                         capacity=capacity)
        self.fatigue_factor = 0.0005

    def update(self, dt):
        if self.speed > 0:
            self.speed -= self.speed * self.fatigue_factor * dt
        if self.speed < 0.1:
            self.speed = 0.1
        super().update(dt)


class DroneAgent(Agent):
    """
    Drone agent with acceleration and energy consumption.
    """

    def __init__(self, environment, route=None, speed=0.0, acceleration=2.0, max_speed=16.0, pickup_time=4.0,
                 capacity=1):
        super().__init__(environment, route, speed, acceleration, max_speed, pickup_time, capacity)
        self.energy_consumed = 0.0
        self.energy_rate = 1.0

    def update(self, dt):
        self.energy_consumed += self.speed * self.energy_rate * dt
        super().update(dt)


class SimulationVisualizer(FigureCanvas):
    """
    Uses matplotlib to draw the simulation: agents, trash, and bin.
    """

    def __init__(self, parent=None):
        self.fig = Figure(figsize=(10, 5))
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax_human, self.ax_drone = self.fig.subplots(1, 2)
        self.ax_human.set_aspect('equal', adjustable='box')
        self.ax_drone.set_aspect('equal', adjustable='box')
        self.agents = []
        self.env = None
        self.timer = QTimer()
        self.timer.setInterval(50)  # ~20 FPS
        self.timer.timeout.connect(self.update_frame)
        self.last_time = None
        self.human_patches = []
        self.drone_patches = []
        self.trash_scat_human = None
        self.trash_scat_drone = None
        self.bin_patch_human = None
        self.bin_patch_drone = None
        self.human_info_text = None
        self.drone_info_text = None

    def setup_environment(self, env: SimulationEnvironment):
        self.env = env
        self.ax_human.clear()
        self.ax_drone.clear()
        self.ax_human.set_title("Human Cleaning")
        self.ax_drone.set_title("Drone Cleaning")
        self.ax_human.set_xlim(0, env.length)
        self.ax_human.set_ylim(0, env.width)
        self.ax_drone.set_xlim(0, env.length)
        self.ax_drone.set_ylim(0, env.width)
        # Bin marker
        bin_size = 0.04 * max(env.length, env.width)
        bx, by = env.bin_position
        self.bin_patch_human = Rectangle((bx - bin_size / 2, by - bin_size / 2), bin_size, bin_size, color='brown')
        self.bin_patch_drone = Rectangle((bx - bin_size / 2, by - bin_size / 2), bin_size, bin_size, color='brown')
        self.ax_human.add_patch(self.bin_patch_human)
        self.ax_drone.add_patch(self.bin_patch_drone)
        # Trash scatter
        hx = [p[0] for p in env.trash_positions]
        hy = [p[1] for p in env.trash_positions]
        self.trash_scat_human = self.ax_human.scatter(hx, hy, c='red')
        self.trash_scat_drone = self.ax_drone.scatter(hx, hy, c='red')
        self.human_info_text = self.ax_human.text(0.01, 1.01, "", transform=self.ax_human.transAxes, fontsize=10,
                                                  color="blue")
        self.drone_info_text = self.ax_drone.text(0.01, 1.01, "", transform=self.ax_drone.transAxes, fontsize=10,
                                                  color="green")
        self.draw()

    def add_agents(self, human_agents, drone_agents):
        self.agents = list(human_agents) + list(drone_agents)
        for agent in human_agents:
            patch = Circle(agent.current_position, radius=0.3, color='blue')
            self.ax_human.add_patch(patch)
            self.human_patches.append(patch)
        for agent in drone_agents:
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

        for agent in self.agents:
            agent.update(dt)

        # Update agent patches
        for idx, patch in enumerate(self.human_patches):
            human_agents = [a for a in self.agents if isinstance(a, HumanAgent)]
            if idx < len(human_agents):
                patch.center = human_agents[idx].current_position
        for idx, patch in enumerate(self.drone_patches):
            drone_agents = [a for a in self.agents if isinstance(a, DroneAgent)]
            if idx < len(drone_agents):
                patch.center = drone_agents[idx].current_position

        # Update trash
        if self.env:
            hx = [p[0] for p in self.env.trash_positions]
            hy = [p[1] for p in self.env.trash_positions]
            self.trash_scat_human.set_offsets(np.c_[hx, hy])
            self.trash_scat_drone.set_offsets(np.c_[hx, hy])

        # Update info text (showing first agent stats)
        human_agents = [a for a in self.agents if isinstance(a, HumanAgent)]
        drone_agents = [a for a in self.agents if isinstance(a, DroneAgent)]
        if human_agents:
            h = human_agents[0]
            collected = len(h.collected_positions)
            total = collected + len(self.env.trash_positions)
            self.human_info_text.set_text(
                f"Time: {h.total_time:.2f}s\nDistance: {h.distance_traveled:.2f}m\nCollected: {collected}/{total}")
        if drone_agents:
            d = drone_agents[0]
            collected = len(d.collected_positions)
            total = collected + len(self.env.trash_positions)
            self.drone_info_text.set_text(
                f"Time: {d.total_time:.2f}s\nDistance: {d.distance_traveled:.2f}m\nCollected: {collected}/{total}")

        self.draw()
        # Stop simulation if all agents are finished or trash is collected.
        done = all(a.position_index >= len(a.route) - 1 for a in self.agents) or len(self.env.trash_positions) == 0
        if done:
            self.stop()
            self.print_summary()

    def print_summary(self):
        print("\n=== Simulation Complete ===")
        for i, agent in enumerate(self.agents):
            kind = "Human" if isinstance(agent, HumanAgent) else "Drone"
            print(f"{kind} {i}: Time = {agent.total_time:.2f}s, Distance = {agent.distance_traveled:.2f}m")


class OperationalSimulationWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.env = SimulationEnvironment()
        self.routing_mgr = RoutingManager()
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        form_layout = QFormLayout()

        # Inputs with realistic defaults (matching the simulator)
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
        self.multiple_drones_checkbox.setChecked(False)
        self.drones_spin = QSpinBox()
        self.drones_spin.setValue(2)
        self.drones_spin.setMinimum(1)
        self.drones_spin.setEnabled(False)
        self.bin_position_combo = QComboBox()
        self.bin_position_combo.addItems(["Bottom-Left", "Top-Left", "Bottom-Right", "Top-Right", "Center"])
        self.routing_combo = QComboBox()
        self.routing_combo.addItems(["Nearest Neighbor", "Capacity-based"])

        self.start_button = QPushButton("Start Simulation")
        self.reset_button = QPushButton("Reset")

        # Connect signals
        self.multiple_drones_checkbox.stateChanged.connect(self.on_multiple_drones_checked)
        self.start_button.clicked.connect(self.start_simulation)
        self.reset_button.clicked.connect(self.reset_simulation)

        form_layout.addRow("Area Length (m):", self.length_edit)
        form_layout.addRow("Area Width (m):", self.width_edit)
        form_layout.addRow("Number of Trash Items:", self.trash_edit)
        form_layout.addRow("Human Speed (m/s):", self.human_speed_edit)
        form_layout.addRow("Drone Speed (m/s):", self.drone_speed_edit)
        form_layout.addRow("Human Pickup Time (s):", self.human_pickup_edit)
        form_layout.addRow("Drone Pickup Time (s):", self.drone_pickup_edit)
        form_layout.addRow("Human Capacity:", self.human_capacity_edit)
        form_layout.addRow("Drone Capacity:", self.drone_capacity_edit)
        form_layout.addRow(self.multiple_drones_checkbox, self.drones_spin)
        form_layout.addRow("Bin Position:", self.bin_position_combo)
        form_layout.addRow("Routing Algorithm:", self.routing_combo)
        form_layout.addRow(self.start_button, self.reset_button)

        controls_layout = QVBoxLayout()
        controls_layout.addLayout(form_layout)
        controls_layout.addStretch()

        # Visualization Canvas
        self.sim_canvas = SimulationVisualizer()
        main_layout.addLayout(controls_layout, 1)
        main_layout.addWidget(self.sim_canvas, 3)

    def on_multiple_drones_checked(self, state):
        self.drones_spin.setEnabled(state == Qt.CheckState.Checked.value)

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

            if length <= 0 or width <= 0 or num_trash < 0 or human_speed <= 0 or drone_speed <= 0:
                QMessageBox.warning(self, "Invalid Input", "Please enter positive values.")
                return

            # Setup environment
            self.env.length = length
            self.env.width = width
            self.env.generate_random_trash(num_trash)
            bin_choice = self.bin_position_combo.currentText()
            self.env.set_bin_position(self.get_bin_position(bin_choice, length, width))

            route_method = self.routing_combo.currentText()
            multiple_drones = self.multiple_drones_checkbox.isChecked()
            n_drones = self.drones_spin.value() if multiple_drones else 1

            # Human route using Nearest Neighbor
            human_route = self.routing_mgr.nearest_neighbor(self.env.bin_position, self.env.trash_positions)
            human_agent = HumanAgent(self.env, route=human_route, speed=human_speed, pickup_time=human_pickup,
                                     capacity=human_capacity)

            # Drone agents: split trash by a simple round-robin
            all_trash = self.env.trash_positions.copy()
            sorted_trash = sorted(all_trash, key=lambda p: math.hypot(p[0] - self.env.bin_position[0],
                                                                      p[1] - self.env.bin_position[1]))
            assignments = [[] for _ in range(n_drones)]
            for idx, pt in enumerate(sorted_trash):
                assignments[idx % n_drones].append(pt)
            drone_agents = []
            for i in range(n_drones):
                if route_method == "Nearest Neighbor":
                    route = self.routing_mgr.nearest_neighbor(self.env.bin_position, assignments[i])
                else:
                    route = self.routing_mgr.capacity_split_path(self.env.bin_position, assignments[i], drone_capacity)
                drone = DroneAgent(self.env, route=route, speed=0.0, acceleration=2.0, max_speed=drone_speed,
                                   pickup_time=drone_pickup, capacity=drone_capacity)
                drone_agents.append(drone)

            self.sim_canvas.stop()
            self.sim_canvas.setup_environment(self.env)
            self.sim_canvas.add_agents([human_agent], drone_agents)
            self.sim_canvas.start()
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please check your inputs.")

    def reset_simulation(self):
        self.sim_canvas.stop()
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
        self.env = SimulationEnvironment()
        self.sim_canvas.setup_environment(self.env)

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
            return (length / 2, width / 2)
        else:
            return (0, 0)


###############################################################################
# Main Window with Tabbed Interface
###############################################################################
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Trash Collection Simulation: Drones vs Humans")
        self.resize(1300, 700)
        self.init_ui()

    def init_ui(self):
        tabs = QTabWidget()
        self.business_tab = BusinessAnalysisWidget()
        self.operational_tab = OperationalSimulationWidget()
        tabs.addTab(self.business_tab, "Business Analysis")
        tabs.addTab(self.operational_tab, "Operational Simulation")
        self.setCentralWidget(tabs)


###############################################################################
# Main Execution
###############################################################################
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
