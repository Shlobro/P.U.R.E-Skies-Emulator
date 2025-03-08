import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QFormLayout, QLineEdit, QPushButton,
    QVBoxLayout, QLabel
)
from PySide6.QtCore import Qt
import data
import simulation
import graph


class TrashCostApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Trash Collection Cost Comparison")
        self.init_ui()

    def init_ui(self):
        # Main layout
        main_layout = QVBoxLayout()

        # Form layout for inputs
        self.form_layout = QFormLayout()
        self.input_fields = {}

        # List of tuples: (label text, key, default value)
        parameters = [
            ("Drone Speed (m/s):", "drone_speed", "5"),
            ("Human Speed (m/s):", "human_speed", "1.2"),
            ("Hourly Cost of Operating Drone ($/hr):", "drone_hourly_cost", "10"),
            ("Hourly Cost of Human Collector ($/hr):", "human_hourly_cost", "15"),
            ("Initial Purchase Cost of Drone ($):", "drone_initial_cost", "1000"),
            ("Cleaning Area Width (m):", "area_width", "100"),
            ("Cleaning Area Height (m):", "area_height", "100"),
            ("Number of Trash Items:", "num_trash", "50"),
            ("Number of Days to Simulate:", "num_days", "30")
        ]

        for label_text, key, default in parameters:
            line_edit = QLineEdit()
            line_edit.setText(default)
            self.input_fields[key] = line_edit
            self.form_layout.addRow(label_text, line_edit)

        main_layout.addLayout(self.form_layout)

        # Button to run simulation
        self.run_button = QPushButton("Generate Graph")
        self.run_button.clicked.connect(self.run_simulation)
        main_layout.addWidget(self.run_button)

        # Label to display daily stats
        self.stats_label = QLabel("Daily stats will appear here.")
        self.stats_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.stats_label)

        # Area for the graph; using a QVBoxLayout to later add the canvas
        self.graph_container = QVBoxLayout()
        main_layout.addLayout(self.graph_container)

        self.setLayout(main_layout)

    def run_simulation(self):
        try:
            # Retrieve and convert user input.
            drone_speed = float(self.input_fields["drone_speed"].text())
            human_speed = float(self.input_fields["human_speed"].text())
            drone_hourly_cost = float(self.input_fields["drone_hourly_cost"].text())
            human_hourly_cost = float(self.input_fields["human_hourly_cost"].text())
            drone_initial_cost = float(self.input_fields["drone_initial_cost"].text())
            area_width = float(self.input_fields["area_width"].text())
            area_height = float(self.input_fields["area_height"].text())
            num_trash = int(self.input_fields["num_trash"].text())
            num_days = int(self.input_fields["num_days"].text())
        except ValueError:
            self.stats_label.setText("Error: Please enter valid numeric values for all fields.")
            return

        # Validate required parameters.
        if drone_speed <= 0 or human_speed <= 0 or num_trash <= 0 or num_days <= 0:
            self.stats_label.setText(
                "Error: Speeds, number of trash items, and number of days must be greater than zero.")
            return

        # Generate trash locations within the specified area (meters).
        trash_locations = data.generate_trash_locations(area_width, area_height, num_trash)

        # Compute the total route distance (in meters) using the nearest neighbor approach.
        route_distance = simulation.compute_route_distance(trash_locations, start=(0, 0))

        # Compute cumulative costs over the specified number of days.
        days, human_costs, drone_costs = simulation.compute_costs(
            distance=route_distance,
            human_speed=human_speed,
            drone_speed=drone_speed,
            human_hourly_cost=human_hourly_cost,
            drone_hourly_cost=drone_hourly_cost,
            drone_initial_cost=drone_initial_cost,
            days=num_days
        )

        # Compute daily statistics: working hours and daily cost.
        daily_hours_human, daily_cost_human, daily_hours_drone, daily_cost_drone = simulation.compute_daily_stats(
            distance=route_distance,
            human_speed=human_speed,
            drone_speed=drone_speed,
            human_hourly_cost=human_hourly_cost,
            drone_hourly_cost=drone_hourly_cost
        )

        stats_text = (
            f"Daily Stats:\n"
            f"Human Collector - Hours worked per day: {daily_hours_human:.2f} hrs, Daily Cost: ${daily_cost_human:.2f}\n"
            f"Drone - Hours worked per day: {daily_hours_drone:.2f} hrs, Daily Operational Cost: ${daily_cost_drone:.2f}"
        )
        self.stats_label.setText(stats_text)

        # Create and embed the graph.
        canvas = graph.create_cost_comparison_figure(days, human_costs, drone_costs)

        # Clear any previous graph widgets from the container.
        self.clear_layout(self.graph_container)
        self.graph_container.addWidget(canvas)

    def clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()


def run_app():
    app = QApplication(sys.argv)
    window = TrashCostApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()
