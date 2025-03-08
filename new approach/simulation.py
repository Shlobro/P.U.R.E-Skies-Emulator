import math


def concurrency_simulation(num_agents, speed_m_s, trash_locations, capacity=0, start=(0, 0)):
    """
    Simulate trash collection with 'num_agents' all starting at 'start' (e.g. (0,0)),
    each moving at 'speed_m_s' (m/s). The trash locations are assigned one-by-one
    using a concurrency approach:

    1. Find the agent with the smallest 'time_to_free'.
    2. Advance the global "time_passed" by that amount (subtract from all agents).
    3. That agent picks up exactly one trash item (the closest). We add the travel
       time to that agent's 'time_to_free', update its position, and total distance.
    4. If capacity > 0, increment that agent's capacity usage. If capacity is reached,
       the agent must return to the starting point; the travel time to return is added,
       total distance updated, and capacity resets.
    5. Remove the trash item from the list. Repeat until no trash items remain.

    capacity = 0 means "unlimited capacity" (never forced to return until the end).

    Returns:
        final_time_seconds: total simulation time (in seconds) when the last trash is collected.
        total_distance: sum of distances traveled by all agents (for informational purposes).
    """
    if num_agents <= 0 or speed_m_s <= 0 or not trash_locations:
        return 0.0, 0.0

    # Each agent tracks: position, time_to_free, total_distance, capacity_used
    agents = []
    for _ in range(num_agents):
        agents.append({
            "position": start,
            "time_to_free": 0.0,
            "total_distance": 0.0,
            "capacity_used": 0
        })

    remaining_trash = trash_locations.copy()
    time_passed = 0.0

    while remaining_trash:
        # 1. Pick the agent with the smallest time_to_free
        i_min = min(range(num_agents), key=lambda i: agents[i]["time_to_free"])
        t_min = agents[i_min]["time_to_free"]

        # 2. Advance the global clock by t_min
        time_passed += t_min
        for ag in agents:
            ag["time_to_free"] -= t_min

        # Agent i_min is now free
        agents[i_min]["time_to_free"] = 0.0
        current_pos = agents[i_min]["position"]

        # 3. Assign the closest trash item to that agent
        closest_idx, closest_dist = None, float('inf')
        for idx, trash_pos in enumerate(remaining_trash):
            dist = math.hypot(trash_pos[0] - current_pos[0], trash_pos[1] - current_pos[1])
            if dist < closest_dist:
                closest_dist = dist
                closest_idx = idx

        if closest_idx is None:
            break

        # Remove the trash item and update agent's travel info
        trash_pos = remaining_trash.pop(closest_idx)
        travel_time = closest_dist / speed_m_s
        agents[i_min]["time_to_free"] += travel_time
        agents[i_min]["total_distance"] += closest_dist
        agents[i_min]["position"] = trash_pos

        # 4. Capacity check: if enabled (capacity > 0)
        if capacity > 0:
            agents[i_min]["capacity_used"] += 1
            if agents[i_min]["capacity_used"] >= capacity:
                # Agent returns to the starting point
                dist_back = math.hypot(trash_pos[0] - start[0], trash_pos[1] - start[1])
                travel_time_back = dist_back / speed_m_s
                agents[i_min]["time_to_free"] += travel_time_back
                agents[i_min]["total_distance"] += dist_back
                agents[i_min]["position"] = start
                agents[i_min]["capacity_used"] = 0

    # After assigning all trash, add the maximum remaining busy time to the global clock.
    final_time_seconds = time_passed + max(ag["time_to_free"] for ag in agents)
    total_distance = sum(ag["total_distance"] for ag in agents)

    return final_time_seconds, total_distance


def compute_costs(
        final_time_seconds_drones, final_time_seconds_humans,
        n_drones, n_humans,
        drone_hourly_cost, human_hourly_cost,
        drone_initial_cost, days
):
    """
    Compute the cumulative cost over the given number of days for both the drone and human environments,
    based on the simulation's final_time_seconds for each.

    Returns:
        days_list: list of day indices (0..days)
        drone_costs: cumulative cost for drones on each day
        human_costs: cumulative cost for humans on each day
    """
    final_time_hours_drones = final_time_seconds_drones / 3600.0
    final_time_hours_humans = final_time_seconds_humans / 3600.0

    days_list = list(range(days + 1))

    drone_costs = [
        (n_drones * drone_initial_cost) + d * (final_time_hours_drones * n_drones * drone_hourly_cost)
        for d in days_list
    ]
    human_costs = [
        d * (final_time_hours_humans * n_humans * human_hourly_cost)
        for d in days_list
    ]

    return days_list, drone_costs, human_costs


def compute_daily_stats(final_time_seconds_drones, final_time_seconds_humans, n_drones, n_humans, drone_hourly_cost,
                        human_hourly_cost):
    """
    Compute daily working hours and daily cost for each environment based on the simulation.
    """
    final_time_hours_drones = final_time_seconds_drones / 3600.0
    final_time_hours_humans = final_time_seconds_humans / 3600.0

    daily_hours_drones = final_time_hours_drones
    daily_hours_humans = final_time_hours_humans

    daily_cost_drones = daily_hours_drones * n_drones * drone_hourly_cost
    daily_cost_humans = daily_hours_humans * n_humans * human_hourly_cost

    return daily_hours_drones, daily_cost_drones, daily_hours_humans, daily_cost_humans
