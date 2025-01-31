#UI.py

#!/usr/bin/env python3




"""
Trash Collection Simulation with UI:
This program models and compares the efficiency and cost–effectiveness of using flying drones versus humans
for trash collection. The GUI built with Tkinter allows the user to enter all input parameters, choose the flexible
parameter (the one plotted on the x-axis), and then view the simulation results (collection time and cost)
in an embedded matplotlib graph.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


# ===============================
# Simulation Functions (Model)
# ===============================
def get_inefficiency_factor(search_algorithm):
    """
    Return an inefficiency factor based on the search algorithm string.
    (Lower factor means more efficient path planning.)
    """
    algo = search_algorithm.lower()
    if "random" in algo:
        return 1.5
    elif "grid" in algo:
        return 1.0
    elif "ai" in algo:
        return 0.8
    else:
        return 1.2  # default factor if not recognized


def compute_trip_distance(capacity, width, height, bin_location, ineff_factor, beta=0.75):
    """
    Estimate the distance (in meters) traveled in one trip when collecting up to
    'capacity' trash items in an area of size width x height.

    We use an approximation inspired by known Traveling Salesman Problem (TSP)
    scaling laws.
    """
    area = width * height
    tsp_length = beta * np.sqrt(capacity * area)
    center = (width / 2.0, height / 2.0)
    d_center = np.sqrt((bin_location[0] - center[0]) ** 2 + (bin_location[1] - center[1]) ** 2)
    trip_distance = ineff_factor * (tsp_length + d_center)
    return trip_distance


def compute_event_time(total_trash, capacity, num_agents, speed, width, height, bin_location, ineff_factor):
    """
    Compute the time (in hours) required to collect all trash items during one event.
    """
    trips_total = np.ceil(total_trash / capacity)
    trips_per_agent = np.ceil(trips_total / num_agents)

    trip_distance = compute_trip_distance(capacity, width, height, bin_location, ineff_factor)
    trip_time_seconds = trip_distance / speed  # seconds for one trip
    total_time_seconds = trips_per_agent * trip_time_seconds
    total_time_hours = total_time_seconds / 3600.0
    return total_time_hours


def compute_event_cost(total_time_hours, num_agents, hourly_cost):
    """Compute the operational cost for one event (in dollars)."""
    return total_time_hours * num_agents * hourly_cost


def breakeven_days(initial_drone_cost_total, human_event_cost, drone_event_cost, events_per_day=1):
    """
    Compute the number of days required for the cumulative cost of drones (including
    initial cost) to become lower than that for human collection.
    """
    cost_diff = human_event_cost - drone_event_cost
    if cost_diff <= 0:
        return None  # No breakeven if drones cost more (or equal) per event
    return initial_drone_cost_total / (cost_diff * events_per_day)


def run_simulation(params, flex_param_name, flex_range):
    """
    For each value of the flexible parameter (provided in flex_range), update the simulation
    input 'params' accordingly and compute event time and cost for drones and humans.

    Returns a list of dictionaries with the simulation results.
    """
    results = []
    ineff_factor = get_inefficiency_factor(params["search_algorithm"])

    for val in flex_range:
        # Update a copy of the parameters with the current flexible value.
        sim_params = params.copy()
        sim_params[flex_param_name] = val

        # Compute results for drones.
        drone_time = compute_event_time(
            total_trash=sim_params["total_trash"],
            capacity=sim_params["drone_capacity"],
            num_agents=sim_params["num_drones"],
            speed=sim_params["drone_speed"],
            width=sim_params["width"],
            height=sim_params["height"],
            bin_location=sim_params["bin_location"],
            ineff_factor=ineff_factor
        )
        drone_cost_event = compute_event_cost(drone_time, sim_params["num_drones"], sim_params["hourly_drone_cost"])

        # Compute results for humans.
        human_time = compute_event_time(
            total_trash=sim_params["total_trash"],
            capacity=sim_params["human_capacity"],
            num_agents=sim_params["num_humans"],
            speed=sim_params["human_speed"],
            width=sim_params["width"],
            height=sim_params["height"],
            bin_location=sim_params["bin_location"],
            ineff_factor=ineff_factor
        )
        human_cost_event = compute_event_cost(human_time, sim_params["num_humans"], sim_params["hourly_human_cost"])

        # If the flexible parameter is time_frame, scale to cumulative cost.
        if flex_param_name == "time_frame":
            unit = sim_params["time_frame_unit"]
            tf_val = val
            if unit.lower().startswith("day"):
                days = tf_val
            elif unit.lower().startswith("month"):
                days = tf_val * 30
            elif unit.lower().startswith("year"):
                days = tf_val * 365
            else:
                days = tf_val
            drone_total_cost = drone_cost_event * days
            human_total_cost = human_cost_event * days
            if sim_params["initial_drone_cost"] > 0:
                drone_total_cost += sim_params["num_drones"] * sim_params["initial_drone_cost"]
            drone_cost = drone_total_cost
            human_cost = human_total_cost
            drone_time_val = drone_time
            human_time_val = human_time
        else:
            drone_cost = drone_cost_event
            human_cost = human_cost_event
            drone_time_val = drone_time
            human_time_val = human_time

        results.append({
            flex_param_name: val,
            "drone_event_time_hours": drone_time_val,
            "human_event_time_hours": human_time_val,
            "drone_cost": drone_cost,
            "human_cost": human_cost
        })
    return results


# ===============================
# Tkinter User Interface Class
# ===============================
class TrashCollectionSimulatorUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Trash Collection Simulation: Drones vs Humans")
        self.create_widgets()

    def create_widgets(self):
        # Input Frame for parameters.
        input_frame = ttk.LabelFrame(self, text="Input Parameters", padding=10)
        input_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nw")

        row = 0
        # Drone Speed (m/s)
        ttk.Label(input_frame, text="Drone Speed (m/s):").grid(row=row, column=0, sticky="w")
        self.drone_speed_var = tk.StringVar(value="5.0")
        ttk.Entry(input_frame, textvariable=self.drone_speed_var, width=10).grid(row=row, column=1)
        row += 1
        # Human Speed (m/s)
        ttk.Label(input_frame, text="Human Speed (m/s):").grid(row=row, column=0, sticky="w")
        self.human_speed_var = tk.StringVar(value="1.0")
        ttk.Entry(input_frame, textvariable=self.human_speed_var, width=10).grid(row=row, column=1)
        row += 1
        # Number of Trash Items
        ttk.Label(input_frame, text="Number of Trash Items:").grid(row=row, column=0, sticky="w")
        self.total_trash_var = tk.StringVar(value="1000")
        ttk.Entry(input_frame, textvariable=self.total_trash_var, width=10).grid(row=row, column=1)
        row += 1
        # Width of Area (m)
        ttk.Label(input_frame, text="Width of Area (m):").grid(row=row, column=0, sticky="w")
        self.width_var = tk.StringVar(value="100")
        ttk.Entry(input_frame, textvariable=self.width_var, width=10).grid(row=row, column=1)
        row += 1
        # Height of Area (m)
        ttk.Label(input_frame, text="Height of Area (m):").grid(row=row, column=0, sticky="w")
        self.height_var = tk.StringVar(value="100")
        ttk.Entry(input_frame, textvariable=self.height_var, width=10).grid(row=row, column=1)
        row += 1
        # Drone Trash Capacity
        ttk.Label(input_frame, text="Drone Trash Capacity (items/trip):").grid(row=row, column=0, sticky="w")
        self.drone_capacity_var = tk.StringVar(value="50")
        ttk.Entry(input_frame, textvariable=self.drone_capacity_var, width=10).grid(row=row, column=1)
        row += 1
        # Human Trash Capacity
        ttk.Label(input_frame, text="Human Trash Capacity (items/trip):").grid(row=row, column=0, sticky="w")
        self.human_capacity_var = tk.StringVar(value="10")
        ttk.Entry(input_frame, textvariable=self.human_capacity_var, width=10).grid(row=row, column=1)
        row += 1
        # Number of Drones
        ttk.Label(input_frame, text="Number of Drones:").grid(row=row, column=0, sticky="w")
        self.num_drones_var = tk.StringVar(value="5")
        ttk.Entry(input_frame, textvariable=self.num_drones_var, width=10).grid(row=row, column=1)
        row += 1
        # Number of Humans
        ttk.Label(input_frame, text="Number of Humans:").grid(row=row, column=0, sticky="w")
        self.num_humans_var = tk.StringVar(value="10")
        ttk.Entry(input_frame, textvariable=self.num_humans_var, width=10).grid(row=row, column=1)
        row += 1
        # Searching Algorithm
        ttk.Label(input_frame, text="Searching Algorithm:").grid(row=row, column=0, sticky="w")
        self.search_algorithm_var = tk.StringVar(value="Grid Search")
        ttk.Entry(input_frame, textvariable=self.search_algorithm_var, width=15).grid(row=row, column=1)
        row += 1
        # Bin Location X
        ttk.Label(input_frame, text="Bin Location X (m):").grid(row=row, column=0, sticky="w")
        self.bin_x_var = tk.StringVar(value="50")
        ttk.Entry(input_frame, textvariable=self.bin_x_var, width=10).grid(row=row, column=1)
        row += 1
        # Bin Location Y
        ttk.Label(input_frame, text="Bin Location Y (m):").grid(row=row, column=0, sticky="w")
        self.bin_y_var = tk.StringVar(value="50")
        ttk.Entry(input_frame, textvariable=self.bin_y_var, width=10).grid(row=row, column=1)
        row += 1
        # Hourly Drone Cost
        ttk.Label(input_frame, text="Hourly Drone Cost ($/hour):").grid(row=row, column=0, sticky="w")
        self.hourly_drone_cost_var = tk.StringVar(value="20")
        ttk.Entry(input_frame, textvariable=self.hourly_drone_cost_var, width=10).grid(row=row, column=1)
        row += 1
        # Hourly Human Cost
        ttk.Label(input_frame, text="Hourly Human Cost ($/hour):").grid(row=row, column=0, sticky="w")
        self.hourly_human_cost_var = tk.StringVar(value="15")
        ttk.Entry(input_frame, textvariable=self.hourly_human_cost_var, width=10).grid(row=row, column=1)
        row += 1
        # Time Frame Value
        ttk.Label(input_frame, text="Time Frame Value:").grid(row=row, column=0, sticky="w")
        self.time_frame_var = tk.StringVar(value="30")
        ttk.Entry(input_frame, textvariable=self.time_frame_var, width=10).grid(row=row, column=1)
        row += 1
        # Time Frame Unit
        ttk.Label(input_frame, text="Time Frame Unit:").grid(row=row, column=0, sticky="w")
        self.time_frame_unit_var = tk.StringVar(value="days")
        ttk.Combobox(input_frame, textvariable=self.time_frame_unit_var,
                     values=["days", "months", "years"], width=8).grid(row=row, column=1)
        row += 1
        # Initial Cost of Drones
        ttk.Label(input_frame, text="Initial Cost of Drones ($):").grid(row=row, column=0, sticky="w")
        self.initial_drone_cost_var = tk.StringVar(value="0")
        ttk.Entry(input_frame, textvariable=self.initial_drone_cost_var, width=10).grid(row=row, column=1)
        row += 1
        # Flexible Parameter Selection
        ttk.Label(input_frame, text="Flexible Parameter (x-axis):").grid(row=row, column=0, sticky="w")
        self.flex_param_var = tk.StringVar(value="num_drones")
        flex_options = ["drone_speed", "human_speed", "total_trash", "width", "height",
                        "drone_capacity", "human_capacity", "num_drones", "num_humans",
                        "hourly_drone_cost", "hourly_human_cost", "time_frame"]
        ttk.Combobox(input_frame, textvariable=self.flex_param_var, values=flex_options, width=15).grid(row=row,
                                                                                                        column=1)
        row += 1
        # Flexible Parameter Range: Start, Stop, Step
        ttk.Label(input_frame, text="Flexible Param Range Start:").grid(row=row, column=0, sticky="w")
        self.flex_range_start_var = tk.StringVar(value="1")
        ttk.Entry(input_frame, textvariable=self.flex_range_start_var, width=10).grid(row=row, column=1)
        row += 1
        ttk.Label(input_frame, text="Flexible Param Range Stop:").grid(row=row, column=0, sticky="w")
        self.flex_range_stop_var = tk.StringVar(value="10")
        ttk.Entry(input_frame, textvariable=self.flex_range_stop_var, width=10).grid(row=row, column=1)
        row += 1
        ttk.Label(input_frame, text="Flexible Param Range Step:").grid(row=row, column=0, sticky="w")
        self.flex_range_step_var = tk.StringVar(value="1")
        ttk.Entry(input_frame, textvariable=self.flex_range_step_var, width=10).grid(row=row, column=1)
        row += 1

        # Run Simulation Button
        ttk.Button(input_frame, text="Run Simulation", command=self.run_simulation).grid(row=row, column=0,
                                                                                         columnspan=2, pady=10)

        # Output Frame for the simulation graph.
        self.output_frame = ttk.LabelFrame(self, text="Simulation Results", padding=10)
        self.output_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

    def run_simulation(self):
        """Read inputs, run simulation, and display the results in the graph."""
        try:
            # Gather and convert inputs.
            params = {
                "drone_speed": float(self.drone_speed_var.get()),
                "human_speed": float(self.human_speed_var.get()),
                "total_trash": int(self.total_trash_var.get()),
                "width": float(self.width_var.get()),
                "height": float(self.height_var.get()),
                "drone_capacity": int(self.drone_capacity_var.get()),
                "human_capacity": int(self.human_capacity_var.get()),
                "num_drones": int(self.num_drones_var.get()),
                "num_humans": int(self.num_humans_var.get()),
                "search_algorithm": self.search_algorithm_var.get(),
                "bin_location": (float(self.bin_x_var.get()), float(self.bin_y_var.get())),
                "hourly_drone_cost": float(self.hourly_drone_cost_var.get()),
                "hourly_human_cost": float(self.hourly_human_cost_var.get()),
                "time_frame": float(self.time_frame_var.get()),
                "time_frame_unit": self.time_frame_unit_var.get(),
                "initial_drone_cost": float(self.initial_drone_cost_var.get())
            }
            flex_param = self.flex_param_var.get()
            start = float(self.flex_range_start_var.get())
            stop = float(self.flex_range_stop_var.get())
            step = float(self.flex_range_step_var.get())
            flex_range = np.arange(start, stop + step / 2, step)

            # Run the simulation.
            results = run_simulation(params, flex_param, flex_range)
            self.plot_results(results, flex_param, params)
        except Exception as e:
            messagebox.showerror("Input Error", f"An error occurred:\n{e}")

    def plot_results(self, results, flex_param_name, params):
        """Plot the simulation results (time and cost) using matplotlib in the output frame."""
        # Clear previous content.
        for widget in self.output_frame.winfo_children():
            widget.destroy()

        # Extract data for plotting.
        x = [r[flex_param_name] for r in results]
        drone_times = [r["drone_event_time_hours"] for r in results]
        human_times = [r["human_event_time_hours"] for r in results]
        drone_costs = [r["drone_cost"] for r in results]
        human_costs = [r["human_cost"] for r in results]

        # Create a matplotlib figure with two subplots.
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6, 8), sharex=True)
        ax1.plot(x, drone_times, 'b-o', label="Drones")
        ax1.plot(x, human_times, 'r-s', label="Humans")
        ax1.set_ylabel("Collection Time (hours)")
        ax1.set_title(f"Effect of '{flex_param_name}' on Collection Time and Cost")
        ax1.legend()
        ax1.grid(True)

        ax2.plot(x, drone_costs, 'b-o', label="Drones")
        ax2.plot(x, human_costs, 'r-s', label="Humans")
        ax2.set_xlabel(f"{flex_param_name}")
        ax2.set_ylabel("Cost ($)")
        ax2.legend()
        ax2.grid(True)

        # Optionally, add breakeven analysis if the flexible parameter is time_frame.
        if flex_param_name == "time_frame" and params["initial_drone_cost"] > 0:
            ineff_factor = get_inefficiency_factor(params["search_algorithm"])
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
            drone_cost_event = compute_event_cost(drone_time_event, params["num_drones"], params["hourly_drone_cost"])
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
            human_cost_event = compute_event_cost(human_time_event, params["num_humans"], params["hourly_human_cost"])
            initial_drone_cost_total = params["num_drones"] * params["initial_drone_cost"]
            be_days = breakeven_days(initial_drone_cost_total, human_cost_event, drone_cost_event, events_per_day=1)
            if be_days is not None and x[0] <= be_days <= x[-1]:
                ax2.axvline(x=be_days, color='k', linestyle='--', label=f"Breakeven at {be_days:.1f} days")
                ax2.legend()

        # Embed the matplotlib figure in the output frame.
        canvas = FigureCanvasTkAgg(fig, master=self.output_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


# ===============================
# Main Execution
# ===============================
if __name__ == '__main__':
    app = TrashCollectionSimulatorUI()
    app.mainloop()
