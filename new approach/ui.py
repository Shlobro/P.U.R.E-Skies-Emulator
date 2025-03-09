import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QTabWidget, QFormLayout, QLineEdit, QPushButton,
    QVBoxLayout, QLabel, QComboBox, QHBoxLayout, QFrame
)
from PySide6.QtCore import Qt
import data, simulation, graph
from visual_simulator import VisualSimulatorTab


class CostSimulatorWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.setStyleSheet("""
            QWidget {
                font-family: 'Segoe UI', sans-serif;
                font-size: 12pt;
                background-color: #f7f7f7;
            }
            QLineEdit, QComboBox {
                background-color: #ffffff;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 4px;
            }
            QPushButton {
                background-color: #007ACC;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #005999;
            }
            QLabel {
                color: #333333;
            }
            QFrame {
                background-color: #ffffff;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
        """)

    def init_ui(self):
        layout = QVBoxLayout()
        self.form_layout = QFormLayout()
        self.input_fields = {}
        parameters = [
            ("Number of Drones:", "n_drones", "2"),
            ("Drone Speed (m/s):", "drone_speed", "5"),
            ("Drone Capacity (0=unlimited):", "drone_capacity", "0"),
            ("Number of Humans:", "n_humans", "2"),
            ("Human Speed (m/s):", "human_speed", "1.2"),
            ("Human Capacity (0=unlimited):", "human_capacity", "0"),
            ("Hourly Cost of Operating Drone ($/hr):", "drone_hourly_cost", "10"),
            ("Hourly Cost of Human Collector ($/hr):", "human_hourly_cost", "15"),
            ("Initial Purchase Cost of Drone ($):", "drone_initial_cost", "1000"),
            ("Cleaning Area Width (m):", "area_width", "100"),
            ("Cleaning Area Height (m):", "area_height", "100"),
            ("Number of Trash Items:", "num_trash", "50"),
            ("Number of Days to Simulate:", "num_days", "30")
        ]
        for label_text, key, default in parameters:
            le = QLineEdit(default)
            self.input_fields[key] = le
            self.form_layout.addRow(label_text, le)
        self.start_position_combo = QComboBox()
        options = ["Center", "Top Left", "Top Center", "Top Right",
                   "Left Center", "Right Center", "Bottom Left", "Bottom Center", "Bottom Right"]
        self.start_position_combo.addItems(options)
        self.form_layout.addRow("Starting/Bin Position:", self.start_position_combo)

        layout.addLayout(self.form_layout)
        self.run_button = QPushButton("Run Cost Simulation")
        self.run_button.clicked.connect(self.run_simulation)
        layout.addWidget(self.run_button)
        self.stats_label = QLabel("Stats will appear here.")
        self.stats_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.stats_label)
        self.graph_container = QFrame()
        self.graph_layout = QVBoxLayout()
        self.graph_container.setLayout(self.graph_layout)
        layout.addWidget(self.graph_container)
        self.setLayout(layout)

    def run_simulation(self):
        try:
            n_drones = int(self.input_fields["n_drones"].text())
            drone_speed = float(self.input_fields["drone_speed"].text())
            drone_capacity = int(self.input_fields["drone_capacity"].text())
            n_humans = int(self.input_fields["n_humans"].text())
            human_speed = float(self.input_fields["human_speed"].text())
            human_capacity = int(self.input_fields["human_capacity"].text())
            drone_hourly_cost = float(self.input_fields["drone_hourly_cost"].text())
            human_hourly_cost = float(self.input_fields["human_hourly_cost"].text())
            drone_initial_cost = float(self.input_fields["drone_initial_cost"].text())
            area_width = float(self.input_fields["area_width"].text())
            area_height = float(self.input_fields["area_height"].text())
            num_trash = int(self.input_fields["num_trash"].text())
            num_days = int(self.input_fields["num_days"].text())
        except ValueError:
            self.stats_label.setText("Error: Invalid numeric input.")
            return
        start_choice = self.start_position_combo.currentText()
        start_options = {
            "Center": lambda w, h: (w / 2, h / 2),
            "Top Left": lambda w, h: (0, h),
            "Top Center": lambda w, h: (w / 2, h),
            "Top Right": lambda w, h: (w, h),
            "Left Center": lambda w, h: (0, h / 2),
            "Right Center": lambda w, h: (w, h / 2),
            "Bottom Left": lambda w, h: (0, 0),
            "Bottom Center": lambda w, h: (w / 2, 0),
            "Bottom Right": lambda w, h: (w, 0)
        }
        start = start_options.get(start_choice, lambda w, h: (0, 0))(area_width, area_height)
        trash_locations = data.generate_trash_locations(area_width, area_height, num_trash)
        final_time_sec_drones, total_dist_drones = simulation.concurrency_simulation(
            n_drones, drone_speed, trash_locations, drone_capacity, start
        )
        final_time_sec_humans, total_dist_humans = simulation.concurrency_simulation(
            n_humans, human_speed, trash_locations, human_capacity, start
        )
        days_list, drone_costs, human_costs = simulation.compute_costs(
            final_time_sec_drones, final_time_sec_humans,
            n_drones, n_humans, drone_hourly_cost, human_hourly_cost, drone_initial_cost, num_days
        )
        daily_hours_drones, daily_cost_drones, daily_hours_humans, daily_cost_humans = simulation.compute_daily_stats(
            final_time_sec_drones, final_time_sec_humans, n_drones, n_humans, drone_hourly_cost, human_hourly_cost
        )
        saving_per_day = daily_cost_humans - daily_cost_drones
        if saving_per_day > 0:
            intersection_day = (n_drones * drone_initial_cost) / saving_per_day
            intersection_str = f"Intersection Day: {intersection_day:.1f}"
        else:
            intersection_str = "No cost intersection (drones not cost–effective)."
        savings_str = f"Daily Savings: ${saving_per_day:.2f} per day"
        stats_text = (
            f"DRONES: Time: {daily_hours_drones:.2f} hrs, Distance: {total_dist_drones:.2f} m, Cost: ${daily_cost_drones:.2f}\n"
            f"HUMANS: Time: {daily_hours_humans:.2f} hrs, Distance: {total_dist_humans:.2f} m, Cost: ${daily_cost_humans:.2f}\n"
            f"{intersection_str}\n{savings_str}")
        self.stats_label.setText(stats_text)
        canvas = graph.create_cost_comparison_figure(days_list, drone_costs, human_costs)
        self.clear_layout(self.graph_layout)
        self.graph_layout.addWidget(canvas)

    def clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

class VisualSimulatorInputWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    def init_ui(self):
        layout = QVBoxLayout()
        self.form_layout = QFormLayout()
        self.input_fields = {}
        parameters = [
            ("Number of Drones:", "n_drones", "2"),
            ("Drone Speed (m/s):", "drone_speed", "5"),
            ("Drone Capacity (0=unlimited):", "drone_capacity", "0"),
            ("Number of Humans:", "n_humans", "2"),
            ("Human Speed (m/s):", "human_speed", "1.2"),
            ("Human Capacity (0=unlimited):", "human_capacity", "0"),
            ("Cleaning Area Width (m):", "area_width", "100"),
            ("Cleaning Area Height (m):", "area_height", "100"),
            ("Number of Trash Items:", "num_trash", "50")
        ]
        for label, key, default in parameters:
            le = QLineEdit(default)
            self.input_fields[key] = le
            self.form_layout.addRow(label, le)
        self.start_position_combo = QComboBox()
        options = ["Center", "Top Left", "Top Center", "Top Right",
                   "Left Center", "Right Center", "Bottom Left", "Bottom Center", "Bottom Right"]
        self.start_position_combo.addItems(options)
        self.form_layout.addRow("Starting/Bin Position:", self.start_position_combo)
        layout.addLayout(self.form_layout)
        self.start_button = QPushButton("Start Visual Simulation")
        self.start_button.clicked.connect(self.start_simulation)
        layout.addWidget(self.start_button)
        self.visual_container = QVBoxLayout()
        layout.addLayout(self.visual_container)
        self.setLayout(layout)
    def start_simulation(self):
        try:
            n_drones = int(self.input_fields["n_drones"].text())
            drone_speed = float(self.input_fields["drone_speed"].text())
            drone_capacity = int(self.input_fields["drone_capacity"].text())
            n_humans = int(self.input_fields["n_humans"].text())
            human_speed = float(self.input_fields["human_speed"].text())
            human_capacity = int(self.input_fields["human_capacity"].text())
            area_width = float(self.input_fields["area_width"].text())
            area_height = float(self.input_fields["area_height"].text())
            num_trash = int(self.input_fields["num_trash"].text())
        except:
            return
        start_choice = self.start_position_combo.currentText()
        start_options = {
            "Center": lambda w, h: (w/2, h/2),
            "Top Left": lambda w, h: (0, h),
            "Top Center": lambda w, h: (w/2, h),
            "Top Right": lambda w, h: (w, h),
            "Left Center": lambda w, h: (0, h/2),
            "Right Center": lambda w, h: (w, h/2),
            "Bottom Left": lambda w, h: (0, 0),
            "Bottom Center": lambda w, h: (w/2, 0),
            "Bottom Right": lambda w, h: (w, 0)
        }
        start = start_options.get(start_choice, lambda w, h: (0,0))(area_width, area_height)
        params = {
            'n_drones': n_drones,
            'drone_speed': drone_speed,
            'drone_capacity': drone_capacity,
            'n_humans': n_humans,
            'human_speed': human_speed,
            'human_capacity': human_capacity,
            'area_width': area_width,
            'area_height': area_height,
            'num_trash': num_trash,
            'start': start
        }
        self.clear_layout(self.visual_container)
        sim_tab = VisualSimulatorTab(params)
        self.visual_container.addWidget(sim_tab)
    def clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()


class MainTabWidget(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.cost_tab = CostSimulatorWidget()
        self.visual_tab = VisualSimulatorInputWidget()
        self.addTab(self.cost_tab, "Cost Simulation")
        self.addTab(self.visual_tab, "Visual Simulation")


def run_app():
    app = QApplication(sys.argv)
    main_win = MainTabWidget()
    main_win.resize(1000, 600)
    main_win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()
