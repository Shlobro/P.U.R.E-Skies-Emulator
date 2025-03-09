import math


def concurrency_simulation(num_agents, speed_m_s, trash_locations, capacity=0, start=(0, 0)):
    """
    Simulate trash collection with 'num_agents' all starting at 'start' (e.g. (0,0)),
    each moving at 'speed_m_s' (m/s). The trash locations are assigned one-by-one
    using a concurrency approach:

    1. Find the agent with the smallest 'time_to_free'.
    2. Advance the global clock by that amount (subtract it from all agents).
    3. That agent picks up the closest trash item. Its travel time is added to its timer,
       its position updated, and its total distance accumulated.
    4. If capacity > 0, increment its capacity usage; when capacity is reached, the agent
       immediately returns to the starting point (bin), adding the travel time and resetting capacity.
    5. Remove the trash item and repeat until all trash is collected.

    (capacity = 0 means "unlimited capacity.")

    Returns:
        final_time_seconds: total simulation time (seconds) when the last trash is collected.
        total_distance: total distance traveled by all agents.
    """
    if num_agents <= 0 or speed_m_s <= 0 or not trash_locations:
        return 0.0, 0.0

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
        i_min = min(range(num_agents), key=lambda i: agents[i]["time_to_free"])
        t_min = agents[i_min]["time_to_free"]

        time_passed += t_min
        for ag in agents:
            ag["time_to_free"] -= t_min

        agents[i_min]["time_to_free"] = 0.0
        current_pos = agents[i_min]["position"]

        closest_idx, closest_dist = None, float('inf')
        for idx, trash_pos in enumerate(remaining_trash):
            dist = math.hypot(trash_pos[0] - current_pos[0], trash_pos[1] - current_pos[1])
            if dist < closest_dist:
                closest_dist = dist
                closest_idx = idx

        if closest_idx is None:
            break

        trash_pos = remaining_trash.pop(closest_idx)
        travel_time = closest_dist / speed_m_s
        agents[i_min]["time_to_free"] += travel_time
        agents[i_min]["total_distance"] += closest_dist
        agents[i_min]["position"] = trash_pos

        if capacity > 0:
            agents[i_min]["capacity_used"] += 1
            if agents[i_min]["capacity_used"] >= capacity:
                dist_back = math.hypot(trash_pos[0] - start[0], trash_pos[1] - start[1])
                travel_time_back = dist_back / speed_m_s
                agents[i_min]["time_to_free"] += travel_time_back
                agents[i_min]["total_distance"] += dist_back
                agents[i_min]["position"] = start
                agents[i_min]["capacity_used"] = 0

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
    Compute the cumulative cost over the given number of days for drones and humans,
    based on the simulation’s final_time (in seconds) for each environment.

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
    Compute daily working hours and daily cost for each environment.
    """
    final_time_hours_drones = final_time_seconds_drones / 3600.0
    final_time_hours_humans = final_time_seconds_humans / 3600.0

    daily_hours_drones = final_time_hours_drones
    daily_hours_humans = final_time_hours_humans

    daily_cost_drones = daily_hours_drones * n_drones * drone_hourly_cost
    daily_cost_humans = daily_hours_humans * n_humans * human_hourly_cost

    return daily_hours_drones, daily_cost_drones, daily_hours_humans, daily_cost_humans
