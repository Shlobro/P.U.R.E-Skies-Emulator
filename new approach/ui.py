import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QFormLayout, QLineEdit, QPushButton,
    QVBoxLayout, QLabel, QComboBox
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
        main_layout = QVBoxLayout()

        # Form layout for inputs
        self.form_layout = QFormLayout()
        self.input_fields = {}

        # List of parameters with default values
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
            line_edit = QLineEdit()
            line_edit.setText(default)
            self.input_fields[key] = line_edit
            self.form_layout.addRow(label_text, line_edit)

        # Dropdown for selecting starting/bin position with all possible options.
        self.start_position_combo = QComboBox()
        # Options for starting position relative to the cleaning area.
        options = [
            "Center",
            "Top Left",
            "Top Center",
            "Top Right",
            "Left Center",
            "Right Center",
            "Bottom Left",
            "Bottom Center",
            "Bottom Right"
        ]
        self.start_position_combo.addItems(options)
        self.form_layout.addRow("Starting/Bin Position:", self.start_position_combo)

        main_layout.addLayout(self.form_layout)

        # Button to run simulation
        self.run_button = QPushButton("Generate Graph")
        self.run_button.clicked.connect(self.run_simulation)
        main_layout.addWidget(self.run_button)

        # Label to display daily stats
        self.stats_label = QLabel("Daily stats will appear here.")
        self.stats_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.stats_label)

        # Area for the graph
        self.graph_container = QVBoxLayout()
        main_layout.addLayout(self.graph_container)

        self.setLayout(main_layout)

    def run_simulation(self):
        try:
            # Retrieve and convert user input.
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
            self.stats_label.setText("Error: Please enter valid numeric values for all fields.")
            return

        # Validate basic parameters.
        if (
            n_drones < 0 or n_humans < 0 or
            drone_speed <= 0 or human_speed <= 0 or
            num_trash <= 0 or num_days < 0
        ):
            self.stats_label.setText("Error: Check that numbers are valid and speeds/trash/days > 0.")
            return

        # Determine the starting/bin position based on the dropdown selection.
        start_choice = self.start_position_combo.currentText()
        # Mapping for starting positions using area dimensions.
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

        # Generate trash locations.
        trash_locations = data.generate_trash_locations(area_width, area_height, num_trash)

        # Run concurrency simulation for drones.
        final_time_sec_drones, total_dist_drones = simulation.concurrency_simulation(
            num_agents=n_drones,
            speed_m_s=drone_speed,
            trash_locations=trash_locations,
            capacity=drone_capacity,
            start=start
        )

        # Run concurrency simulation for humans.
        final_time_sec_humans, total_dist_humans = simulation.concurrency_simulation(
            num_agents=n_humans,
            speed_m_s=human_speed,
            trash_locations=trash_locations,
            capacity=human_capacity,
            start=start
        )

        # Compute cost arrays over days.
        days_list, drone_costs, human_costs = simulation.compute_costs(
            final_time_seconds_drones=final_time_sec_drones,
            final_time_seconds_humans=final_time_sec_humans,
            n_drones=n_drones,
            n_humans=n_humans,
            drone_hourly_cost=drone_hourly_cost,
            human_hourly_cost=human_hourly_cost,
            drone_initial_cost=drone_initial_cost,
            days=num_days
        )

        # Compute daily stats.
        (daily_hours_drones, daily_cost_drones,
         daily_hours_humans, daily_cost_humans) = simulation.compute_daily_stats(
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
            f"  Daily Cost (wages only): ${daily_cost_drones:.2f}\n"
            f"  (Capacity: {drone_capacity if drone_capacity > 0 else 'Unlimited'})\n\n"
            f"HUMANS:\n"
            f"  Concurrency Time Per Day: {daily_hours_humans:.2f} hrs\n"
            f"  Total Distance (all humans): {total_dist_humans:.2f} m\n"
            f"  Daily Cost (wages only): ${daily_cost_humans:.2f}\n"
            f"  (Capacity: {human_capacity if human_capacity > 0 else 'Unlimited'})"
        )
        self.stats_label.setText(stats_text)

        # Create and embed the graph.
        canvas = graph.create_cost_comparison_figure(days_list, drone_costs, human_costs)
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
