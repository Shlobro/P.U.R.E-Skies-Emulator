import math


class BaseAgent:
    def __init__(self, name, position=(0, 0), capacity=10):
        self.name = name
        self.position = position
        self.route = []
        self.current_index = 0
        self.capacity = capacity
        self.current_load = 0
        self.done = False

    def assign_route(self, route):
        self.route = route
        self.current_index = 0

    def is_done(self):
        return self.done

    def get_state(self):
        """
        Return agent state for logging or visualization.
        """
        return {
            'name': self.name,
            'position': self.position,
            'current_load': self.current_load,
            'route_remaining': len(self.route) - self.current_index
        }

    def update(self, dt, environment):
        """
        Base update (no physics). Subclasses will override for actual movement.
        """
        if self.current_index >= len(self.route):
            self.done = True
            return
        # Move to next waypoint (placeholder: instant move)
        next_waypoint = self.route[self.current_index]
        if self.at_position(next_waypoint):
            self.current_index += 1
            if self.current_index >= len(self.route):
                self.done = True
        else:
            # Move (no actual physics, just a direct step)
            self.position = next_waypoint

    def at_position(self, waypoint):
        return (abs(self.position[0] - waypoint[0]) < 0.01 and
                abs(self.position[1] - waypoint[1]) < 0.01)


class HumanAgent(BaseAgent):
    def __init__(self, name, max_speed=1.0, fatigue_rate=0.01, **kwargs):
        super().__init__(name, **kwargs)
        self.max_speed = max_speed
        self.fatigue_rate = fatigue_rate
        self.fatigue = 0.0

    def update(self, dt, environment):
        if self.is_done():
            return

        # Simple fatigue model: speed decreases as fatigue increases
        speed = self.max_speed * (1 - self.fatigue)
        next_waypoint = self.route[self.current_index]
        dx, dy = next_waypoint[0] - self.position[0], next_waypoint[1] - self.position[1]
        distance = math.sqrt(dx * dx + dy * dy)

        if distance < 0.01:
            self.current_index += 1
            if self.current_index >= len(self.route):
                self.done = True
            self.fatigue -= 0.05  # recover a bit at each waypoint
            self.fatigue = max(self.fatigue, 0.0)
        else:
            # Move towards next waypoint
            angle = math.atan2(dy, dx)
            move_dist = min(distance, speed * dt)
            self.position = (
                self.position[0] + move_dist * math.cos(angle),
                self.position[1] + move_dist * math.sin(angle)
            )
            # Increase fatigue slightly
            self.fatigue += self.fatigue_rate * dt
            self.fatigue = min(self.fatigue, 1.0)


class DroneAgent(BaseAgent):
    def __init__(self, name, max_acceleration=1.0, max_speed=5.0, **kwargs):
        super().__init__(name, **kwargs)
        self.velocity = (0.0, 0.0)
        self.max_accel = max_acceleration
        self.max_speed = max_speed

    def update(self, dt, environment):
        if self.is_done():
            return

        next_waypoint = self.route[self.current_index]
        dx = next_waypoint[0] - self.position[0]
        dy = next_waypoint[1] - self.position[1]
        distance = math.sqrt(dx * dx + dy * dy)

        if distance < 0.1:
            # Arrived at waypoint
            self.current_index += 1
            if self.current_index >= len(self.route):
                self.done = True
            return

        # Calculate desired acceleration direction
        angle = math.atan2(dy, dx)

        # Update velocity with a simple model
        vx, vy = self.velocity
        ax = self.max_accel * math.cos(angle)
        ay = self.max_accel * math.sin(angle)

        # New velocity
        new_vx = vx + ax * dt
        new_vy = vy + ay * dt
        new_speed = math.sqrt(new_vx * new_vx + new_vy * new_vy)

        # Limit speed
        if new_speed > self.max_speed:
            scale = self.max_speed / new_speed
            new_vx *= scale
            new_vy *= scale

        self.velocity = (new_vx, new_vy)
        # Move
        self.position = (
            self.position[0] + self.velocity[0] * dt,
            self.position[1] + self.velocity[1] * dt
        )
