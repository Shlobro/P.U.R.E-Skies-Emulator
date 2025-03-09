import math
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QBrush, QPen, QColor


def simulate_day_events(num_agents, speed_m_s, trash_locations, capacity, start):
    """
    Run a discrete-event simulation (similar to concurrency_simulation)
    but record each movement segment for every agent.

    Returns:
        agents: list of agents, each with a 'schedule' (list of segments).
          Each segment is a dict with:
              'start_time', 'end_time', 'from' (tuple), 'to' (tuple),
              'type': 'pickup' or 'return', 'trash_index' (or None)
        final_time: global simulation time (seconds) when simulation ends.
    """
    agents = []
    for i in range(num_agents):
        agents.append({
            'position': start,
            'time_to_free': 0.0,
            'capacity_used': 0,
            'schedule': []  # list of segments
        })
    remaining = list(enumerate(trash_locations))  # list of (trash_index, position)
    time_passed = 0.0
    while remaining:
        i_min = min(range(num_agents), key=lambda i: agents[i]['time_to_free'])
        t_min = agents[i_min]['time_to_free']
        time_passed += t_min
        for agent in agents:
            agent['time_to_free'] -= t_min
        agents[i_min]['time_to_free'] = 0.0
        current_pos = agents[i_min]['position']
        # Find closest trash item
        best = None
        best_dist = float('inf')
        for item in remaining:
            idx, pos = item
            d = math.hypot(pos[0] - current_pos[0], pos[1] - current_pos[1])
            if d < best_dist:
                best = item
                best_dist = d
        if best is None:
            break
        trash_idx, trash_pos = best
        travel_time = best_dist / speed_m_s
        segment = {
            'start_time': time_passed,
            'end_time': time_passed + travel_time,
            'from': current_pos,
            'to': trash_pos,
            'type': 'pickup',
            'trash_index': trash_idx
        }
        agents[i_min]['schedule'].append(segment)
        agents[i_min]['position'] = trash_pos
        agents[i_min]['time_to_free'] += travel_time
        remaining = [item for item in remaining if item[0] != trash_idx]
        if capacity > 0:
            agents[i_min]['capacity_used'] += 1
            if agents[i_min]['capacity_used'] >= capacity:
                d_back = math.hypot(agents[i_min]['position'][0] - start[0], agents[i_min]['position'][1] - start[1])
                travel_time_back = d_back / speed_m_s
                segment_return = {
                    'start_time': time_passed + travel_time,
                    'end_time': time_passed + travel_time + travel_time_back,
                    'from': agents[i_min]['position'],
                    'to': start,
                    'type': 'return',
                    'trash_index': None
                }
                agents[i_min]['schedule'].append(segment_return)
                agents[i_min]['position'] = start
                agents[i_min]['time_to_free'] += travel_time_back
                agents[i_min]['capacity_used'] = 0
    final_time = time_passed + max(agent['time_to_free'] for agent in agents)
    return agents, final_time


class VisualSimulationWidget(QGraphicsView):
    def __init__(self, agents_schedule, final_time, trash_locations, area_width, area_height, start, agent_color,
                 parent=None):
        super().__init__(parent)
        self.agents_schedule = agents_schedule
        self.final_time = final_time
        self.trash_locations = trash_locations
        self.area_width = area_width
        self.area_height = area_height
        self.start = start
        self.agent_color = agent_color
        self.sim_time = 0.0
        self.timer = QTimer()
        self.timer.setInterval(50)  # 50 ms update interval
        self.timer.timeout.connect(self.update_simulation)
        self.scene = QGraphicsScene(0, 0, area_width, area_height)
        self.setScene(self.scene)
        self.agent_items = []
        self.trash_items = {}  # mapping trash index -> QGraphicsEllipseItem
        self.init_scene()
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setViewportUpdateMode(QGraphicsView.BoundingRectViewportUpdate)

    def init_scene(self):
        # Draw border for the simulation area.
        border_pen = QPen(Qt.black)
        self.scene.addRect(0, 0, self.area_width, self.area_height, border_pen)
        # Draw bin as a dark green dot.
        bin_radius = 4
        bin_x, bin_y = self.start
        self.scene.addEllipse(bin_x - bin_radius, self.area_height - bin_y - bin_radius,
                              2 * bin_radius, 2 * bin_radius, QPen(Qt.darkGreen), QBrush(Qt.darkGreen))
        # Draw trash items as red dots.
        trash_radius = 3
        for idx, pos in enumerate(self.trash_locations):
            x, y = pos
            ellipse = self.scene.addEllipse(x - trash_radius, self.area_height - y - trash_radius,
                                            2 * trash_radius, 2 * trash_radius, QPen(Qt.red), QBrush(Qt.red))
            self.trash_items[idx] = ellipse
        # Create agent items using the given agent_color.
        agent_radius = 5
        for _ in range(len(self.agents_schedule)):
            ellipse = self.scene.addEllipse(-agent_radius, -agent_radius, 2 * agent_radius, 2 * agent_radius,
                                            QPen(self.agent_color), QBrush(self.agent_color))
            self.agent_items.append(ellipse)

    def start_animation(self):
        self.sim_time = 0.0
        self.timer.start()

    def update_simulation(self):
        dt = 0.1  # simulation time step (seconds)
        self.sim_time += dt
        if self.sim_time > self.final_time:
            self.sim_time = self.final_time
            self.timer.stop()
        # Update agents' positions.
        for i, agent in enumerate(self.agents_schedule):
            pos = self.get_agent_position(agent, self.sim_time)
            if pos is not None:
                x, y = pos
                self.agent_items[i].setPos(x - 5, self.area_height - y - 5)
        # Remove trash items that have been picked up.
        for agent in self.agents_schedule:
            for segment in agent['schedule']:
                if segment['type'] == 'pickup' and self.sim_time >= segment['end_time']:
                    trash_idx = segment['trash_index']
                    if trash_idx in self.trash_items:
                        self.scene.removeItem(self.trash_items[trash_idx])
                        del self.trash_items[trash_idx]

    def get_agent_position(self, agent, t):
        schedule = agent['schedule']
        if not schedule:
            return agent['position']
        if t < schedule[0]['start_time']:
            return schedule[0]['from']
        for segment in schedule:
            if segment['start_time'] <= t <= segment['end_time']:
                ratio = (t - segment['start_time']) / (segment['end_time'] - segment['start_time'])
                x = segment['from'][0] + ratio * (segment['to'][0] - segment['from'][0])
                y = segment['from'][1] + ratio * (segment['to'][1] - segment['from'][1])
                return (x, y)
        return schedule[-1]['to']

    def current_sim_time(self):
        return self.sim_time


class VisualSimulatorTab(QWidget):
    def __init__(self, params, parent=None):
        super().__init__(parent)
        self.params = params  # Dictionary of simulation parameters
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        title = QLabel("Visual Simulation: Single Day Animation")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Horizontal layout for side-by-side simulation views.
        sim_layout = QHBoxLayout()
        from data import generate_trash_locations
        area_width = self.params['area_width']
        area_height = self.params['area_height']
        num_trash = self.params['num_trash']
        trash_locations = generate_trash_locations(area_width, area_height, num_trash)
        start = self.params['start']

        from visual_simulator import simulate_day_events
        # Drones simulation (using blue)
        drones_schedule, drones_final_time = simulate_day_events(
            self.params['n_drones'],
            self.params['drone_speed'],
            trash_locations,
            self.params['drone_capacity'],
            start
        )
        # Humans simulation (using orange)
        humans_schedule, humans_final_time = simulate_day_events(
            self.params['n_humans'],
            self.params['human_speed'],
            trash_locations,
            self.params['human_capacity'],
            start
        )
        # Timer labels for each simulation.
        self.drones_timer_label = QLabel("Drones Time: 0.0 s")
        self.drones_timer_label.setAlignment(Qt.AlignCenter)
        self.humans_timer_label = QLabel("Humans Time: 0.0 s")
        self.humans_timer_label.setAlignment(Qt.AlignCenter)

        from PySide6.QtGui import QColor
        self.drones_sim = VisualSimulationWidget(drones_schedule, drones_final_time, trash_locations,
                                                 area_width, area_height, start, QColor(0, 122, 204))
        self.humans_sim = VisualSimulationWidget(humans_schedule, humans_final_time, trash_locations,
                                                 area_width, area_height, start, QColor(255, 165, 0))

        # Wrap each simulation in a vertical layout with its timer label.
        left_vbox = QVBoxLayout()
        left_vbox.addWidget(QLabel("Drones Simulation"))
        left_vbox.addWidget(self.drones_timer_label)
        left_vbox.addWidget(self.drones_sim)

        right_vbox = QVBoxLayout()
        right_vbox.addWidget(QLabel("Humans Simulation"))
        right_vbox.addWidget(self.humans_timer_label)
        right_vbox.addWidget(self.humans_sim)

        sim_layout.addLayout(left_vbox)
        sim_layout.addLayout(right_vbox)
        layout.addLayout(sim_layout)

        self.start_button = QPushButton("Start Visual Simulation")
        self.start_button.clicked.connect(self.start_simulation)
        layout.addWidget(self.start_button)

        # QTimer to update the simulation timer labels.
        self.update_timer = QTimer()
        self.update_timer.setInterval(100)  # update every 100 ms
        self.update_timer.timeout.connect(self.update_timer_labels)

        self.setLayout(layout)

    def start_simulation(self):
        self.drones_sim.start_animation()
        self.humans_sim.start_animation()
        self.update_timer.start()

    def update_timer_labels(self):
        self.drones_timer_label.setText(f"Drones Time: {self.drones_sim.current_sim_time():.1f} s")
        self.humans_timer_label.setText(f"Humans Time: {self.humans_sim.current_sim_time():.1f} s")
        if (not self.drones_sim.timer.isActive()) and (not self.humans_sim.timer.isActive()):
            self.update_timer.stop()
