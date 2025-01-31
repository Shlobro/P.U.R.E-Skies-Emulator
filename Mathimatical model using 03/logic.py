#logic.py

#!/usr/bin/env python3
"""
Trash Collection Cost–Effectiveness Analysis:
Compare flying drones versus humans based on speed, capacity, search efficiency,
operational hourly cost, and (for drones) initial purchase cost.
The program simulates one “collection event” (or repeated daily events) and plots how
varying one input parameter (the “flexible parameter”) affects the performance.
"""

import numpy as np
import matplotlib.pyplot as plt
import json
import csv
import sys


# ---------------------------
# Helper functions
# ---------------------------

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
    scaling laws. The TSP route length for k points randomly distributed in an area A is roughly:

        TSP_length ≈ beta * sqrt(k * A)

    and we add an extra term (the distance from the bin to the tour) approximated by the
    distance from the bin to the center of the area.
    Finally, the search algorithm inefficiency multiplies the route length.
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

    Assumes:
      - Each trip collects up to 'capacity' items.
      - The number of trips required is divided evenly among the available agents.
      - Each trip takes (trip_distance / speed) seconds.
    """
    # Total trips required (each trip collects up to 'capacity' items)
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

    If drones are not operationally cheaper (i.e. drone_event_cost >= human_event_cost),
    then return None.
    """
    cost_diff = human_event_cost - drone_event_cost
    if cost_diff <= 0:
        return None  # no breakeven if drones cost more (or equal) per event
    # Breakeven day = initial cost / (daily savings)
    return initial_drone_cost_total / (cost_diff * events_per_day)


# ---------------------------
# Main simulation function
# ---------------------------
def run_simulation(params, flex_param_name, flex_range):
    """
    For each value of the flexible parameter (provided in flex_range) update the simulation
    input 'params' accordingly and compute event time and cost for drones and humans.

    Returns:
      results: a list of dictionaries containing the flexible parameter value and computed metrics.
    """
    results = []
    ineff_factor = get_inefficiency_factor(params["search_algorithm"])

    # For each value in the flexible range, update the parameter and compute metrics.
    for val in flex_range:
        # Make a copy of params
        sim_params = params.copy()
        sim_params[flex_param_name] = val

        # For drones:
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

        # For humans:
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

        # If the flexible parameter is the time frame, assume one event per day
        # and scale the cost to the cumulative cost over that time.
        if flex_param_name == "time_frame":
            # Determine the number of days in the time frame based on the unit
            unit = sim_params["time_frame_unit"]
            tf_val = val  # the current time frame value
            if unit.lower().startswith("day"):
                days = tf_val
            elif unit.lower().startswith("month"):
                days = tf_val * 30
            elif unit.lower().startswith("year"):
                days = tf_val * 365
            else:
                days = tf_val  # assume days if unknown
            # cumulative cost assuming one event per day
            drone_total_cost = drone_cost_event * days
            human_total_cost = human_cost_event * days
            # Add initial drone cost if provided
            if sim_params["initial_drone_cost"] > 0:
                drone_total_cost += sim_params["num_drones"] * sim_params["initial_drone_cost"]
            # For the “time frame” simulation we record cumulative cost.
            drone_cost = drone_total_cost
            human_cost = human_total_cost
            # We keep the event times as computed (for one event) for reference.
            drone_time_val = drone_time
            human_time_val = human_time
        else:
            # For a one–event simulation
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


# ---------------------------
# Export functions
# ---------------------------
def export_results_csv(results, filename):
    keys = results[0].keys()
    with open(filename, 'w', newline='') as csvfile:
        dict_writer = csv.DictWriter(csvfile, fieldnames=keys)
        dict_writer.writeheader()
        dict_writer.writerows(results)
    print(f"Results exported to {filename}")


def export_results_json(results, filename):
    with open(filename, 'w') as jsonfile:
        json.dump(results, jsonfile, indent=4)
    print(f"Results exported to {filename}")


# ---------------------------
# Interactive CLI to get inputs
# ---------------------------
def get_user_input():
    print("=== Trash Collection Simulation ===")
    try:
        params = {}
        params["drone_speed"] = float(input("Enter Drone Speed (m/s): "))
        params["human_speed"] = float(input("Enter Human Speed (m/s): "))
        params["total_trash"] = int(input("Enter Number of Trash Items: "))
        params["width"] = float(input("Enter Width of Area (m): "))
        params["height"] = float(input("Enter Height of Area (m): "))
        params["drone_capacity"] = int(input("Enter Trash Capacity of a Drone (items per trip): "))
        params["human_capacity"] = int(input("Enter Trash Capacity of a Human (items per trip): "))
        params["num_drones"] = int(input("Enter Number of Drones: "))
        params["num_humans"] = int(input("Enter Number of Humans: "))
        params["search_algorithm"] = input(
            "Enter Searching Algorithm Used (e.g., Random Search, Grid Search, AI-Optimized Search): ")

        # Bin location as two numbers separated by comma
        bin_loc_str = input("Enter Bin Location as x,y (in meters): ")
        x_bin, y_bin = bin_loc_str.split(",")
        params["bin_location"] = (float(x_bin.strip()), float(y_bin.strip()))

        params["hourly_drone_cost"] = float(input("Enter Hourly Drone Cost ($/hour): "))
        params["hourly_human_cost"] = float(input("Enter Hourly Human Cost ($/hour): "))

        # Time frame input – if the user wishes to consider cumulative costs over repeated events
        params["time_frame"] = float(input("Enter Time Frame Value (if analyzing repeated daily events, e.g., 30): "))
        params["time_frame_unit"] = input("Enter Time Frame Unit (days, months, or years): ")

        # Initial drone cost (optional)
        init_cost = input("Enter Initial Cost of Drones (enter 0 if not applicable): ")
        params["initial_drone_cost"] = float(init_cost)

        print("\nSelect the flexible parameter (the one that will vary on the x-axis).")
        print(
            "Options: drone_speed, human_speed, total_trash, width, height, drone_capacity, human_capacity, num_drones, num_humans, hourly_drone_cost, hourly_human_cost, time_frame")
        flex_param = input("Enter the parameter name exactly as above: ").strip()
        if flex_param not in params:
            print("Invalid flexible parameter selection. Exiting.")
            sys.exit(1)

        # Ask for range for the flexible parameter:
        start = float(input(f"Enter starting value for {flex_param}: "))
        stop = float(input(f"Enter ending value for {flex_param}: "))
        step = float(input(f"Enter step value for {flex_param}: "))

        flex_range = np.arange(start, stop + step / 2, step)  # include stop

        return params, flex_param, flex_range
    except Exception as e:
        print("Error reading input:", e)
        sys.exit(1)


# ---------------------------
# Plotting functions
# ---------------------------
def plot_results(results, flex_param_name, params):
    x = [r[flex_param_name] for r in results]
    drone_times = [r["drone_event_time_hours"] for r in results]
    human_times = [r["human_event_time_hours"] for r in results]
    drone_costs = [r["drone_cost"] for r in results]
    human_costs = [r["human_cost"] for r in results]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 10), sharex=True)

    # Plot Time taken for collection (in hours)
    ax1.plot(x, drone_times, 'b-o', label="Drones")
    ax1.plot(x, human_times, 'r-s', label="Humans")
    ax1.set_ylabel("Event Collection Time (hours)")
    ax1.set_title(f"Effect of {flex_param_name} on Collection Time and Cost")
    ax1.legend()
    ax1.grid(True)

    # Plot total cost of operation
    ax2.plot(x, drone_costs, 'b-o', label="Drones")
    ax2.plot(x, human_costs, 'r-s', label="Humans")
    ax2.set_xlabel(f"{flex_param_name}")
    ax2.set_ylabel("Cost ($)")
    ax2.legend()
    ax2.grid(True)

    # If the flexible parameter is time_frame and initial cost is provided, add breakeven analysis.
    if flex_param_name == "time_frame" and params["initial_drone_cost"] > 0:
        # Use the first (baseline) event cost computed at the baseline parameter value
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

        # Assume one event per day.
        initial_drone_cost_total = params["num_drones"] * params["initial_drone_cost"]
        be_days = breakeven_days(initial_drone_cost_total, human_cost_event, drone_cost_event, events_per_day=1)
        if be_days is not None:
            # Plot a vertical dashed line at the breakeven day (if within the plotted range)
            if x[0] <= be_days <= x[-1]:
                ax2.axvline(x=be_days, color='k', linestyle='--', label=f"Breakeven at {be_days:.1f} days")
                ax2.legend()
            print(f"Breakeven analysis: Drones become cost-effective after approximately {be_days:.1f} days.")
        else:
            print("No breakeven point found (drones are not operationally cheaper per event).")

    plt.tight_layout()
    plt.show()


# ---------------------------
# Main
# ---------------------------
def main():
    # Get inputs from the user
    params, flex_param_name, flex_range = get_user_input()

    # Run simulation for the range of the flexible parameter
    results = run_simulation(params, flex_param_name, flex_range)

    # Print summary for the first simulation (as an example)
    print("\nExample simulation result for flexible parameter = {:.3f}:".format(results[0][flex_param_name]))
    print("  Drone event time (hours): {:.4f}".format(results[0]["drone_event_time_hours"]))
    print("  Human event time (hours): {:.4f}".format(results[0]["human_event_time_hours"]))
    print("  Drone cost for event: ${:.2f}".format(results[0]["drone_cost"]))
    print("  Human cost for event: ${:.2f}".format(results[0]["human_cost"]))

    # Plot results
    plot_results(results, flex_param_name, params)

    # Ask if the user wants to export results
    export_choice = input("Do you want to export the results? (y/n): ").strip().lower()
    if export_choice == 'y':
        file_format = input("Enter export format (csv or json): ").strip().lower()
        filename = input("Enter filename (e.g., results.csv or results.json): ").strip()
        if file_format == "csv":
            export_results_csv(results, filename)
        elif file_format == "json":
            export_results_json(results, filename)
        else:
            print("Unknown format. No export performed.")


if __name__ == '__main__':
    main()
