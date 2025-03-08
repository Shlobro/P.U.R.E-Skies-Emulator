import math


def compute_route_distance(trash_locations, start=(0, 0)):
    """
    Compute the total distance to collect all trash items using a nearest neighbor heuristic.
    Starting from 'start', the function finds the nearest trash item, adds the distance,
    and repeats until all items are visited.

    Distance is computed in meters.
    """
    if not trash_locations:
        return 0

    total_distance = 0
    current_pos = start
    remaining = trash_locations.copy()

    while remaining:
        # Find the nearest trash item to the current position.
        next_item = min(remaining, key=lambda pos: math.hypot(pos[0] - current_pos[0], pos[1] - current_pos[1]))
        distance = math.hypot(next_item[0] - current_pos[0], next_item[1] - current_pos[1])
        total_distance += distance
        current_pos = next_item
        remaining.remove(next_item)

    return total_distance


def compute_costs(distance, human_speed, drone_speed, human_hourly_cost, drone_hourly_cost, drone_initial_cost, days):
    """
    Compute the cumulative cost over the given number of days for both human and drone collection.

    With the inputs in meters and m/s:
        time (in seconds) = distance / speed.
    Convert to hours by dividing by 3600.

    Cumulative cost for each day:
        human_cost(day) = day * (time_human_in_hours * human_hourly_cost)
        drone_cost(day) = drone_initial_cost + day * (time_drone_in_hours * drone_hourly_cost)

    Returns:
        days_list: List of day numbers (0 to days)
        human_cost_list: Cumulative cost for human collection
        drone_cost_list: Cumulative cost for drone collection
    """
    # Calculate time (in hours) required to complete the route.
    time_human = (distance / human_speed) / 3600 if human_speed > 0 else float('inf')
    time_drone = (distance / drone_speed) / 3600 if drone_speed > 0 else float('inf')

    days_list = list(range(days + 1))
    human_cost_list = [day * (time_human * human_hourly_cost) for day in days_list]
    drone_cost_list = [drone_initial_cost + day * (time_drone * drone_hourly_cost) for day in days_list]

    return days_list, human_cost_list, drone_cost_list


def compute_daily_stats(distance, human_speed, drone_speed, human_hourly_cost, drone_hourly_cost):
    """
    Compute the daily working hours and daily cost for each collector.

    Returns:
        daily_hours_human: Hours worked per day by the human collector.
        daily_cost_human: Daily cost for the human collector.
        daily_hours_drone: Hours worked per day by the drone.
        daily_cost_drone: Daily operational cost for the drone.
    """
    daily_hours_human = (distance / human_speed) / 3600 if human_speed > 0 else float('inf')
    daily_hours_drone = (distance / drone_speed) / 3600 if drone_speed > 0 else float('inf')
    daily_cost_human = daily_hours_human * human_hourly_cost
    daily_cost_drone = daily_hours_drone * drone_hourly_cost
    return daily_hours_human, daily_cost_human, daily_hours_drone, daily_cost_drone
