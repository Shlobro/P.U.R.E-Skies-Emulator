import math


def concurrency_simulation(num_agents, speed_m_s, trash_locations):
    """
    Simulate trash collection with 'num_agents' all starting at (0,0),
    each moving at 'speed_m_s' (m/s). The trash locations are assigned one by one
    using a concurrency approach:

    1. Find the agent with the smallest 'time_to_free'.
    2. Advance time by that amount (subtract from all agents).
    3. Assign that agent the closest trash item, update its 'time_to_free', 'position',
       and 'total_distance'.
    4. Repeat until no trash items remain.

    Returns:
        final_time_seconds: total concurrency time (in seconds) when the last trash is collected.
        total_distance: sum of distances traveled by all agents (for informational purposes).
    """
    if num_agents <= 0 or speed_m_s <= 0 or not trash_locations:
        return 0.0, 0.0

    # Initialize agents
    agents = []
    for _ in range(num_agents):
        agents.append({
            "position": (0, 0),
            "time_to_free": 0.0,
            "total_distance": 0.0
        })

    # Copy the trash list so we can pop items
    remaining_trash = trash_locations.copy()

    # Keep track of total "simulation time" that has passed
    time_passed = 0.0

    # While there are still trash items to assign
    while remaining_trash:
        # 1. Pick agent with smallest time_to_free
        i_min = min(range(num_agents), key=lambda i: agents[i]["time_to_free"])
        t_min = agents[i_min]["time_to_free"]

        # 2. Advance time by t_min
        time_passed += t_min
        for ag in agents:
            ag["time_to_free"] -= t_min

        # Now agent i_min is free at time_to_free = 0
        agents[i_min]["time_to_free"] = 0.0

        # 3. Assign the closest trash item to that agent
        current_pos = agents[i_min]["position"]
        closest_idx, closest_dist = None, float('inf')
        for idx, trash_pos in enumerate(remaining_trash):
            dist = math.hypot(trash_pos[0] - current_pos[0], trash_pos[1] - current_pos[1])
            if dist < closest_dist:
                closest_dist = dist
                closest_idx = idx

        # If we found a closest trash item, remove it and update the agent
        if closest_idx is not None:
            trash_pos = remaining_trash.pop(closest_idx)
            agents[i_min]["position"] = trash_pos
            agents[i_min]["total_distance"] += closest_dist
            # Compute travel time for this new trash item
            travel_time = closest_dist / speed_m_s  # in seconds
            agents[i_min]["time_to_free"] = travel_time

    # After all trash is assigned, we need to let the last assigned tasks finish
    # The final time is the current time plus the max of any agent's time_to_free
    final_time_seconds = time_passed + max(ag["time_to_free"] for ag in agents)
    total_distance = sum(ag["total_distance"] for ag in agents)

    return final_time_seconds, total_distance


def compute_costs(
        final_time_seconds_drones, final_time_seconds_humans,
        n_drones, n_humans,
        drone_speed, human_speed,
        drone_hourly_cost, human_hourly_cost,
        drone_initial_cost, days
):
    """
    Compute the cumulative cost over the given number of days for both the drone environment
    and the human environment, given the concurrency simulation's final_time_seconds for each.

    final_time_seconds_drones: concurrency-based total time (seconds) for drones
    final_time_seconds_humans: concurrency-based total time (seconds) for humans

    Returns:
        days_list: list of day indices (0..days)
        drone_costs: cumulative cost for drones on each day
        human_costs: cumulative cost for humans on each day
    """
    # Convert concurrency times to hours
    final_time_hours_drones = final_time_seconds_drones / 3600.0
    final_time_hours_humans = final_time_seconds_humans / 3600.0

    # For drones: cost(d) = (n_drones * drone_initial_cost) + d * (final_time_hours_drones * n_drones * drone_hourly_cost)
    # For humans: cost(d) = d * (final_time_hours_humans * n_humans * human_hourly_cost)
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
    Compute daily working hours and daily cost for the concurrency approach in each environment.
    We assume each environment runs once per day.
    """
    # Convert to hours
    final_time_hours_drones = final_time_seconds_drones / 3600.0
    final_time_hours_humans = final_time_seconds_humans / 3600.0

    # If we assume each drone/human is "on the clock" from start to finish:
    # daily_hours = final_time_hours
    # daily_cost = daily_hours * (n_agents * hourly_cost)
    # But typically you'd do total_time_hours * n_agents if each agent is paid for the entire concurrency window.

    daily_hours_drones = final_time_hours_drones  # total concurrency time
    daily_hours_humans = final_time_hours_humans

    daily_cost_drones = daily_hours_drones * n_drones * drone_hourly_cost
    daily_cost_humans = daily_hours_humans * n_humans * human_hourly_cost

    return daily_hours_drones, daily_cost_drones, daily_hours_humans, daily_cost_humans
