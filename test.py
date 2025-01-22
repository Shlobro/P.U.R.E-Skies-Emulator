import sys
import random
import math
import time  # For real-time measurement
import numpy as np

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFormLayout, QLineEdit, QPushButton,
    QLabel, QHBoxLayout, QVBoxLayout, QMessageBox, QCheckBox, QSpinBox, QComboBox
)
from PyQt6.QtCore import QTimer, Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.patches import Circle, Rectangle

###############################################################################
# Helper Functions
###############################################################################
def distance(p1, p2):
    """Euclidean distance between two points (x1, y1) and (x2, y2)."""
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

def nearest_neighbor_path(start, trash_points):
    """
    A simple nearest neighbor path from 'start' visiting each point
    in 'trash_points' exactly once, then returning to start if desired.
    """
    if not trash_points:
        return [start]

    path = [start]
    remaining = trash_points.copy()
    current_pos = start
    while remaining:
        nearest = min(remaining, key=lambda p: distance(current_pos, p))
        path.append(nearest)
        remaining.remove(nearest)
        current_pos = nearest
    return path

def build_path_with_capacity(bin_pos, trash_points, capacity):
    """
    Build a path that picks trash in capacity chunks (via nearest neighbor),
    returning to the bin after each chunk. If capacity < 1, we treat it as
    an 'unlimited capacity', meaning the agent collects all trash in one loop
    before returning to the bin at the end.

    Steps:
      1) If capacity < 1 -> unlimited capacity:
         - Construct a nearest-neighbor path from bin to all trash, then back to bin.
      2) Otherwise (capacity >= 1):
         - Start at bin
         - While trash remains:
             * Nearest-neighbor sub-route of up to 'capacity' pieces
             * Return to bin
         - End at bin
    """
    # --------------------------------------------------
    # UNLIMITED CAPACITY CASE
    # --------------------------------------------------
    if capacity < 1:
        # Single route covering all trash
        base = nearest_neighbor_path(bin_pos, trash_points)
        if len(base) > 0 and base[-1] != bin_pos:
            base.append(bin_pos)
        return base

    # --------------------------------------------------
    # LIMITED CAPACITY CASE
    # --------------------------------------------------
    remaining = trash_points.copy()
    full_path = [bin_pos]
    current_pos = bin_pos

    while remaining:
        sub_path = []
        # We'll collect up to 'capacity' pieces in a sub-route
        for _ in range(min(capacity, len(remaining))):
            nearest = min(remaining, key=lambda p: distance(current_pos, p))
            sub_path.append(nearest)
            remaining.remove(nearest)
            current_pos = nearest

        # Add the sub-path (the chunk) to our final path
        full_path.extend(sub_path)

        # Return to bin
        full_path.append(bin_pos)
        current_pos = bin_pos

    return full_path

def split_trash_among_drones(trash_points, num_drones, start=(0, 0)):
    """
    Naive splitting of trash for multiple drones:
    1) Sort trash by distance from start.
    2) Assign in a round-robin fashion.
    """
    sorted_trash = sorted(trash_points, key=lambda p: distance(start, p))
    assignments = [[] for _ in range(num_drones)]
    idx = 0
    for pt in sorted_trash:
        assignments[idx].append(pt)
        idx = (idx + 1) % num_drones
    return assignments

def get_bin_position(selection, length, width):
    """
    Map combo box selection to (x,y) bin coordinates.
    """
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
        # Default
        return (0, 0)

###############################################################################
# SideBySideCanvas
###############################################################################
class SideBySideCanvas(FigureCanvasQTAgg):
    """
    Two subplots side by side:
        Left  -> Human cleaning
        Right -> Drone cleaning
    Each uses real elapsed time for precise physics.
    """
    def __init__(self, parent=None):
        fig = Figure(figsize=(10, 5))
        super().__init__(fig)
        self.setParent(parent)

        # Create two subplots
        self.ax_human, self.ax_drone = fig.subplots(1, 2)
        self.ax_human.set_aspect('equal', adjustable='box')
        self.ax_drone.set_aspect('equal', adjustable='box')

        # Simulation parameters (defaults)
        self.area_length = 25
        self.area_width = 25
        self.num_trash = 20
        self.human_speed = 1.4
        self.drone_speed = 16.0
        self.multiple_drones = False
        self.num_drones = 1
        self.drone_return_after_each = True

        # Pickup times
        self.human_pickup_time = 2.0
        self.drone_pickup_time = 4.0

        # Capacities
        # If capacity == 0, we interpret that as unlimited capacity
        self.human_capacity = 20
        self.drone_capacity = 1

        # Bin position
        self.bin_pos = (0, 0)

        # Human scenario states
        self.human_trash_positions = []
        self.human_path = []
        self.human_position_index = 0
        self.human_current_position = (0, 0)
        self.human_distance_traveled = 0.0
        self.human_time = 0.0
        self.human_current_pickup_timer = 0.0

        # Drone scenario states
        self.drone_trash_positions = []
        self.drone_paths = []
        self.drone_position_indices = []
        self.drone_current_positions = []
        self.drone_distance_traveled = []
        self.drone_times = []
        self.drone_pickup_timers = []

        # Visualization elements
        self.agent_radius = 0.3
        self.human_trash_scat = None
        self.drone_trash_scat = None
        self.human_patch = None
        self.drone_patches = []
        self.bin_patch_human = None
        self.bin_patch_drone = None

        # Info text (stats) placed outside the grid
        self.human_info_text = None
        self.drone_info_text = None

        # For real-time measurement
        self.last_update_time = None

        # Master distribution of trash
        self.global_trash_positions = []

        # Timer for animation (~20 FPS)
        self.timer = QTimer()
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.update_simulation)

        # Initial setup
        self.setup_plots()

    def setup_plots(self):
        """
        Basic configuration for the subplots. We'll place legends
        and the info text outside the main grid.
        """
        self.ax_human.clear()
        self.ax_human.set_title("Human Cleaning")
        self.ax_human.set_xlim(0, self.area_length)
        self.ax_human.set_ylim(0, self.area_width)

        self.ax_drone.clear()
        self.ax_drone.set_title("Drone Cleaning")
        self.ax_drone.set_xlim(0, self.area_length)
        self.ax_drone.set_ylim(0, self.area_width)

        self.human_info_text = self.ax_human.text(
            0.5, -0.1, "", transform=self.ax_human.transAxes,
            fontsize=10, color="blue", va="top", ha="left", clip_on=False
        )
        self.drone_info_text = self.ax_drone.text(
            0.5, -0.1, "", transform=self.ax_drone.transAxes,
            fontsize=10, color="green", va="top", ha="left", clip_on=False
        )
        self.draw()

    def initialize_simulation(self,
                              area_length,
                              area_width,
                              num_trash,
                              human_speed,
                              drone_speed,
                              multiple_drones=False,
                              num_drones=1,
                              drone_return_after_each=True,
                              human_pickup_time=2.0,
                              drone_pickup_time=4.0,
                              human_capacity=20,
                              drone_capacity=1,
                              bin_pos=(0, 0)):
        """
        Generate random trash, compute paths for both scenarios,
        and reset all counters.
        """
        # Save parameters
        self.area_length = area_length
        self.area_width = area_width
        self.num_trash = num_trash
        self.human_speed = human_speed
        self.drone_speed = drone_speed
        self.multiple_drones = multiple_drones
        self.num_drones = num_drones

        self.drone_return_after_each = drone_return_after_each
        self.human_pickup_time = human_pickup_time
        self.drone_pickup_time = drone_pickup_time
        self.human_capacity = human_capacity
        self.drone_capacity = drone_capacity
        self.bin_pos = bin_pos

        max_dim = max(area_length, area_width)
        self.agent_radius = 0.02 * max_dim

        # Clear plots
        self.ax_human.clear()
        self.ax_human.set_title("Human Cleaning")
        self.ax_human.set_xlim(0, area_length)
        self.ax_human.set_ylim(0, area_width)

        self.ax_drone.clear()
        self.ax_drone.set_title("Drone Cleaning")
        self.ax_drone.set_xlim(0, area_length)
        self.ax_drone.set_ylim(0, area_width)

        # Redo text
        self.human_info_text = self.ax_human.text(
            0.0, 1.15, "", transform=self.ax_human.transAxes,
            fontsize=10, color="blue", va="top", ha="left", clip_on=False
        )
        self.drone_info_text = self.ax_drone.text(
            0.0, 1.15, "", transform=self.ax_drone.transAxes,
            fontsize=10, color="green", va="top", ha="left", clip_on=False
        )

        # Generate random trash
        self.global_trash_positions = [
            (random.uniform(0, area_length), random.uniform(0, area_width))
            for _ in range(num_trash)
        ]
        self.last_update_time = time.time()

        # ----------------- HUMAN SETUP -----------------
        self.human_trash_positions = list(self.global_trash_positions)
        self.human_path = build_path_with_capacity(
            bin_pos,
            self.human_trash_positions,
            capacity=self.human_capacity
        )
        self.human_position_index = 0
        self.human_current_position = self.human_path[0]
        self.human_distance_traveled = 0.0
        self.human_time = 0.0
        self.human_current_pickup_timer = 0.0

        hx = [p[0] for p in self.human_trash_positions]
        hy = [p[1] for p in self.human_trash_positions]
        self.human_trash_scat = self.ax_human.scatter(hx, hy, c='red', label='Trash')

        self.human_patch = Circle(
            self.human_current_position,
            self.agent_radius,
            color='blue',
            label='Human'
        )
        self.ax_human.add_patch(self.human_patch)

        # Bin patch (human subplot)
        bin_size = 0.04 * max_dim
        bx, by = bin_pos
        self.bin_patch_human = Rectangle(
            (bx - bin_size/2, by - bin_size/2),
            bin_size, bin_size,
            color='brown', label='Bin'
        )
        self.ax_human.add_patch(self.bin_patch_human)

        # ----------------- DRONE SETUP -----------------
        self.drone_trash_positions = list(self.global_trash_positions)
        self.drone_paths.clear()
        self.drone_position_indices.clear()
        self.drone_current_positions.clear()
        self.drone_distance_traveled.clear()
        self.drone_times.clear()
        self.drone_pickup_timers.clear()

        # You can decide how to handle "return after each trash" here.
        # By default, we ignore that checkbox and always use capacity-based approach.
        #
        # If you do want the checkbox to force capacity=1, you can do so in an "Approach A"
        # block. But here, we keep it simple and rely purely on 'drone_capacity'.

        if not multiple_drones:
            # Single drone: use capacity
            self.drone_paths = [
                build_path_with_capacity(bin_pos,
                                         self.drone_trash_positions,
                                         capacity=self.drone_capacity)
            ]
        else:
            # Multiple drones
            assignments = split_trash_among_drones(self.drone_trash_positions,
                                                   self.num_drones, bin_pos)
            for assign in assignments:
                path = build_path_with_capacity(
                    bin_pos,
                    assign,
                    self.drone_capacity
                )
                self.drone_paths.append(path)

        # Initialize each drone's position, distance, time, pickup
        for path in self.drone_paths:
            self.drone_position_indices.append(0)
            start_pt = path[0] if path else bin_pos
            self.drone_current_positions.append(start_pt)
            self.drone_distance_traveled.append(0.0)
            self.drone_times.append(0.0)
            self.drone_pickup_timers.append(0.0)

        dx = [p[0] for p in self.drone_trash_positions]
        dy = [p[1] for p in self.drone_trash_positions]
        self.drone_trash_scat = self.ax_drone.scatter(dx, dy, c='red', label='Trash')

        self.drone_patches.clear()
        for i, path in enumerate(self.drone_paths):
            start_pt = path[0] if path else bin_pos
            drone_circle = Circle(
                start_pt,
                self.agent_radius,
                color='green',
                label='Drone' if i == 0 else None
            )
            self.ax_drone.add_patch(drone_circle)
            self.drone_patches.append(drone_circle)

        # Bin patch (drone subplot)
        self.bin_patch_drone = Rectangle(
            (bx - bin_size/2, by - bin_size/2),
            bin_size, bin_size,
            color='brown', label='Bin'
        )
        self.ax_drone.add_patch(self.bin_patch_drone)

        self.ax_human.legend(loc='upper left', bbox_to_anchor=(1.05, 1.0),
                             borderaxespad=0., frameon=True)
        self.ax_drone.legend(loc='upper left', bbox_to_anchor=(1.05, 1.0),
                             borderaxespad=0., frameon=True)

        self.draw()

    def start_animation(self):
        self.timer.start()

    def stop_animation(self):
        self.timer.stop()

    def update_simulation(self):
        """
        Called ~20 times/sec. We measure real dt from the previous frame
        for accurate speeds & times.
        """
        current_time = time.time()
        if self.last_update_time is None:
            self.last_update_time = current_time

        dt = current_time - self.last_update_time
        self.last_update_time = current_time

        # --- Update Human ---
        if self.human_position_index < len(self.human_path) - 1:
            # If we are in the middle of a pickup, decrement that first
            if self.human_current_pickup_timer > 0:
                self.human_current_pickup_timer -= dt
                if self.human_current_pickup_timer < 0:
                    self.human_current_pickup_timer = 0
            else:
                # Move if we are not picking up right now
                next_pos = self.human_path[self.human_position_index + 1]
                current_pos = self.human_current_position
                dist_to_next = distance(current_pos, next_pos)

                step_dist = self.human_speed * dt
                if step_dist >= dist_to_next:
                    # Arrive
                    self.human_current_position = next_pos
                    self.human_distance_traveled += dist_to_next
                    self.human_position_index += 1

                    # If it's trash, remove and start pickup timer
                    if next_pos in self.human_trash_positions:
                        self.human_trash_positions.remove(next_pos)
                        self.update_human_trash_scatter()
                        self.human_current_pickup_timer = self.human_pickup_time
                else:
                    ratio = step_dist / dist_to_next
                    nx = current_pos[0] + ratio * (next_pos[0] - current_pos[0])
                    ny = current_pos[1] + ratio * (next_pos[1] - current_pos[1])
                    self.human_current_position = (nx, ny)
                    self.human_distance_traveled += step_dist

            self.human_time += dt
            self.human_patch.center = self.human_current_position

        # --- Update Drone(s) ---
        for i, path in enumerate(self.drone_paths):
            # If no path or we've reached the end, skip
            if not path or self.drone_position_indices[i] >= len(path) - 1:
                continue

            # If drone is currently picking up, decrement that timer
            if self.drone_pickup_timers[i] > 0:
                self.drone_pickup_timers[i] -= dt
                if self.drone_pickup_timers[i] < 0:
                    self.drone_pickup_timers[i] = 0
            else:
                # Move if not in pickup
                next_pos = path[self.drone_position_indices[i] + 1]
                current_pos = self.drone_current_positions[i]
                dist_to_next = distance(current_pos, next_pos)

                step_dist = self.drone_speed * dt
                if step_dist >= dist_to_next:
                    # Arrive
                    self.drone_current_positions[i] = next_pos
                    self.drone_distance_traveled[i] += dist_to_next
                    self.drone_position_indices[i] += 1

                    # If it's trash, remove and start pickup timer
                    if next_pos in self.drone_trash_positions:
                        self.drone_trash_positions.remove(next_pos)
                        self.update_drone_trash_scatter()
                        self.drone_pickup_timers[i] = self.drone_pickup_time
                else:
                    ratio = step_dist / dist_to_next
                    nx = current_pos[0] + ratio * (next_pos[0] - current_pos[0])
                    ny = current_pos[1] + ratio * (next_pos[1] - current_pos[1])
                    self.drone_current_positions[i] = (nx, ny)
                    self.drone_distance_traveled[i] += step_dist

            self.drone_times[i] += dt
            self.drone_patches[i].center = self.drone_current_positions[i]

        # Update on-screen stats: Human
        human_collected = self.num_trash - len(self.human_trash_positions)
        self.human_info_text.set_text(
            f"Time: {self.human_time:.2f} s\n"
            f"Dist: {self.human_distance_traveled:.2f} m\n"
            f"Trash: {human_collected} / {self.num_trash}"
        )

        # Update on-screen stats: Drone
        drone_collected = self.num_trash - len(self.drone_trash_positions)
        max_drone_time = max(self.drone_times) if self.drone_times else 0.0
        total_drone_distance = sum(self.drone_distance_traveled)
        self.drone_info_text.set_text(
            f"Time: {max_drone_time:.2f} s\n"
            f"Dist: {total_drone_distance:.2f} m\n"
            f"Trash: {drone_collected} / {self.num_trash}"
        )

        self.draw()

        # Check completion
        human_done = (self.human_position_index == len(self.human_path) - 1)
        drones_done = True
        for i, path in enumerate(self.drone_paths):
            if self.drone_position_indices[i] < len(path) - 1:
                drones_done = False
                break

        if human_done and drones_done:
            self.stop_animation()
            self.generate_summary()

    def update_human_trash_scatter(self):
        """Re-draw the human's remaining trash scatter."""
        if self.human_trash_scat:
            self.human_trash_scat.remove()
        hx = [p[0] for p in self.human_trash_positions]
        hy = [p[1] for p in self.human_trash_positions]
        self.human_trash_scat = self.ax_human.scatter(hx, hy, c='red')

    def update_drone_trash_scatter(self):
        """Re-draw the drone's remaining trash scatter."""
        if self.drone_trash_scat:
            self.drone_trash_scat.remove()
        dx = [p[0] for p in self.drone_trash_positions]
        dy = [p[1] for p in self.drone_trash_positions]
        self.drone_trash_scat = self.ax_drone.scatter(dx, dy, c='red')

    def generate_summary(self):
        """Print or store final results to console and optional file."""
        total_human_time = self.human_time
        total_human_distance = self.human_distance_traveled

        if self.drone_times:
            max_drone_time = max(self.drone_times)
            total_drone_distance = sum(self.drone_distance_traveled)
        else:
            max_drone_time = 0.0
            total_drone_distance = 0.0

        print("\n=== Simulation Summary ===")
        print("Human Results:")
        print(f"  - Time: {total_human_time:.2f} s")
        print(f"  - Distance: {total_human_distance:.2f} m")

        print("Drone Results:")
        print(f"  - Longest Time (if multiple drones): {max_drone_time:.2f} s")
        print(f"  - Sum of Distances (if multiple drones): {total_drone_distance:.2f} m")

        if total_human_time > 0:
            speed_up = (total_human_time - max_drone_time) / total_human_time * 100
        else:
            speed_up = 0.0
        print(f"Drone is faster by: {speed_up:.2f}%")

        with open("simulation_summary.txt", "w") as f:
            f.write("=== Simulation Summary ===\n")
            f.write(f"Area: {self.area_length} x {self.area_width}\n")
            f.write(f"Number of Trash Pieces: {self.num_trash}\n")
            f.write(f"Human Speed: {self.human_speed}\n")
            f.write(f"Drone Speed: {self.drone_speed}\n")
            f.write(f"Multiple Drones? {self.multiple_drones}\n")
            f.write(f"Number of Drones: {self.num_drones}\n")
            f.write(f"Drone Returns After Each Trash? {self.drone_return_after_each}\n")
            f.write(f"Human Pickup Time: {self.human_pickup_time}\n")
            f.write(f"Drone Pickup Time: {self.drone_pickup_time}\n")
            f.write(f"Human Capacity: {self.human_capacity}\n")
            f.write(f"Drone Capacity: {self.drone_capacity}\n")
            f.write(f"Bin Position: {self.bin_pos}\n")
            f.write("\n--- Results ---\n")
            f.write(f"Human Time: {total_human_time:.2f} s\n")
            f.write(f"Human Distance: {total_human_distance:.2f} m\n")
            f.write(f"Drone Time (Longest among drones): {max_drone_time:.2f} s\n")
            f.write(f"Drone Distance (Sum of drones): {total_drone_distance:.2f} m\n")
            f.write(f"Drone Speed-Up: {speed_up:.2f}%\n")


###############################################################################
# Main Window
###############################################################################
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cleaning Simulation (Human vs. Drone)")

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QHBoxLayout()
        self.form_layout = QFormLayout()
        self.central_widget.setLayout(self.main_layout)

        # Controls
        self.length_edit = QLineEdit("25")
        self.width_edit = QLineEdit("25")
        self.trash_edit = QLineEdit("20")
        self.human_speed_edit = QLineEdit("1.4")
        self.drone_speed_edit = QLineEdit("16.0")

        # Pickup times
        self.human_pickup_edit = QLineEdit("2.0")
        self.drone_pickup_edit = QLineEdit("4.0")

        # Capacities (0 => unlimited)
        self.human_capacity_edit = QLineEdit("20")
        self.drone_capacity_edit = QLineEdit("1")

        # Multiple drones
        self.multiple_drones_checkbox = QCheckBox("Use Multiple Drones?")
        self.drones_spin = QSpinBox()
        self.drones_spin.setValue(2)
        self.drones_spin.setMinimum(2)
        self.drones_spin.setEnabled(False)

        # Drone returns each time
        self.drone_return_bin_checkbox = QCheckBox("Drone returns to bin after each trash?")
        self.drone_return_bin_checkbox.setChecked(True)

        # Bin position combo
        self.bin_position_combo = QComboBox()
        self.bin_position_combo.addItems([
            "Bottom-Left",
            "Top-Left",
            "Bottom-Right",
            "Top-Right",
            "Center"
        ])
        self.bin_position_combo.setCurrentIndex(0)

        # Buttons
        self.start_button = QPushButton("Start Simulation")
        self.reset_button = QPushButton("Reset")

        # Connect signals
        self.start_button.clicked.connect(self.start_simulation)
        self.reset_button.clicked.connect(self.reset_parameters)
        self.multiple_drones_checkbox.stateChanged.connect(self.on_multiple_drones_checked)

        # Populate form layout
        self.form_layout.addRow("Area Length (m):", self.length_edit)
        self.form_layout.addRow("Area Width (m):", self.width_edit)
        self.form_layout.addRow("Number of Trash Pieces:", self.trash_edit)
        self.form_layout.addRow("Human Speed (m/s):", self.human_speed_edit)
        self.form_layout.addRow("Drone Speed (m/s):", self.drone_speed_edit)
        self.form_layout.addRow("Human Pickup Time (s):", self.human_pickup_edit)
        self.form_layout.addRow("Drone Pickup Time (s):", self.drone_pickup_edit)
        self.form_layout.addRow("Human Capacity (0=unlimited):", self.human_capacity_edit)
        self.form_layout.addRow("Drone Capacity (0=unlimited):", self.drone_capacity_edit)
        self.form_layout.addRow(self.multiple_drones_checkbox, self.drones_spin)
        self.form_layout.addRow(self.drone_return_bin_checkbox)
        self.form_layout.addRow("Bin Position:", self.bin_position_combo)
        self.form_layout.addRow(self.start_button, self.reset_button)

        self.main_layout.addLayout(self.form_layout)

        self.sim_canvas = SideBySideCanvas()
        self.main_layout.addWidget(self.sim_canvas)

    def on_multiple_drones_checked(self, state):
        if state == Qt.CheckState.Checked.value:
            self.drones_spin.setEnabled(True)
        else:
            self.drones_spin.setEnabled(False)

    def start_simulation(self):
        try:
            length = float(self.length_edit.text())
            width = float(self.width_edit.text())
            trash_count = int(self.trash_edit.text())
            human_speed = float(self.human_speed_edit.text())
            drone_speed = float(self.drone_speed_edit.text())

            # Pickup times
            human_pickup_time = float(self.human_pickup_edit.text())
            drone_pickup_time = float(self.drone_pickup_edit.text())

            # Capacities (0 => unlimited)
            human_capacity = int(self.human_capacity_edit.text())
            drone_capacity = int(self.drone_capacity_edit.text())

            # Basic validation
            if (
                length <= 0 or width <= 0
                or trash_count < 0
                or human_speed <= 0
                or drone_speed <= 0
                or human_pickup_time < 0
                or drone_pickup_time < 0
                or human_capacity < 0
                or drone_capacity < 0
            ):
                QMessageBox.warning(self, "Invalid Input",
                                    "Please enter valid positive values.\n"
                                    "Use 0 only for unlimited capacity.")
                return

            multiple_drones = self.multiple_drones_checkbox.isChecked()
            num_drones = self.drones_spin.value() if multiple_drones else 1
            drone_return_after_each = self.drone_return_bin_checkbox.isChecked()

            bin_choice = self.bin_position_combo.currentText()
            bin_pos = get_bin_position(bin_choice, length, width)

            self.sim_canvas.initialize_simulation(
                area_length=length,
                area_width=width,
                num_trash=trash_count,
                human_speed=human_speed,
                drone_speed=drone_speed,
                multiple_drones=multiple_drones,
                num_drones=num_drones,
                drone_return_after_each=drone_return_after_each,
                human_pickup_time=human_pickup_time,
                drone_pickup_time=drone_pickup_time,
                human_capacity=human_capacity,
                drone_capacity=drone_capacity,
                bin_pos=bin_pos
            )
            self.sim_canvas.start_animation()

        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please check your input fields.")

    def reset_parameters(self):
        self.sim_canvas.stop_animation()

        # Defaults
        self.length_edit.setText("25")
        self.width_edit.setText("25")
        self.trash_edit.setText("20")
        self.human_speed_edit.setText("1.4")
        self.drone_speed_edit.setText("16.0")
        self.human_pickup_edit.setText("2.0")
        self.drone_pickup_edit.setText("4.0")
        self.human_capacity_edit.setText("20")  # positive => limited
        self.drone_capacity_edit.setText("1")   # positive => limited
        self.multiple_drones_checkbox.setChecked(False)
        self.drones_spin.setEnabled(False)
        self.drones_spin.setValue(2)
        self.drone_return_bin_checkbox.setChecked(True)
        self.bin_position_combo.setCurrentIndex(0)

        self.sim_canvas.setup_plots()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(1300, 600)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
