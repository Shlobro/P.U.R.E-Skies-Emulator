import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QFormLayout, QLineEdit, QPushButton,
    QVBoxLayout, QLabel
)
from PySide6.QtCore import Qt
import data
import simulation
import graph
import math


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
            ("Number of Drones:", "n_drones", "2"),
            ("Number of Humans:", "n_humans", "2"),
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
            n_drones = int(self.input_fields["n_drones"].text())
            n_humans = int(self.input_fields["n_humans"].text())
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
        if (
                n_drones < 0 or n_humans < 0 or
                drone_speed <= 0 or human_speed <= 0 or
                num_trash <= 0 or num_days < 0
        ):
            self.stats_label.setText(
                "Error: Number of drones/humans, speeds, trash items, and days must be valid and > 0."
            )
            return

        # 1. Generate trash locations within the specified area (meters).
        trash_locations = data.generate_trash_locations(area_width, area_height, num_trash)

        # 2. Concurrency simulation for drones
        final_time_sec_drones, total_dist_drones = simulation.concurrency_simulation(
            num_agents=n_drones,
            speed_m_s=drone_speed,
            trash_locations=trash_locations
        )

        # 3. Concurrency simulation for humans
        final_time_sec_humans, total_dist_humans = simulation.concurrency_simulation(
            num_agents=n_humans,
            speed_m_s=human_speed,
            trash_locations=trash_locations
        )

        # 4. Compute cost arrays over days
        days_list, drone_costs, human_costs = simulation.compute_costs(
            final_time_seconds_drones=final_time_sec_drones,
            final_time_seconds_humans=final_time_sec_humans,
            n_drones=n_drones,
            n_humans=n_humans,
            drone_speed=drone_speed,
            human_speed=human_speed,
            drone_hourly_cost=drone_hourly_cost,
            human_hourly_cost=human_hourly_cost,
            drone_initial_cost=drone_initial_cost,
            days=num_days
        )

        # 5. Compute daily stats for concurrency
        (
            daily_hours_drones, daily_cost_drones,
            daily_hours_humans, daily_cost_humans
        ) = simulation.compute_daily_stats(
            final_time_seconds_drones=final_time_sec_drones,
            final_time_seconds_humans=final_time_sec_humans,
            n_drones=n_drones,
            n_humans=n_humans,
            drone_hourly_cost=drone_hourly_cost,
            human_hourly_cost=human_hourly_cost
        )

        stats_text = (
            f"DRONES:\n"
            f"  Concurrency Time Per Day: {daily_hours_drones:.2f} hrs\n"
            f"  Total Distance (all drones): {total_dist_drones:.2f} m\n"
            f"  Daily Cost (wages only): ${daily_cost_drones:.2f}\n\n"
            f"HUMANS:\n"
            f"  Concurrency Time Per Day: {daily_hours_humans:.2f} hrs\n"
            f"  Total Distance (all humans): {total_dist_humans:.2f} m\n"
            f"  Daily Cost (wages only): ${daily_cost_humans:.2f}"
        )
        self.stats_label.setText(stats_text)

        # 6. Create and embed the graph.
        canvas = graph.create_cost_comparison_figure(days_list, drone_costs, human_costs)

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
