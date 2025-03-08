import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QFormLayout, QLineEdit, QPushButton,
    QVBoxLayout, QLabel, QComboBox, QHBoxLayout, QFrame
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
        """)

    def init_ui(self):
        # Create a main horizontal layout: left panel for controls, right panel for graph.
        main_layout = QHBoxLayout()

        # Left panel layout (controls, inputs, and stats)
        left_panel = QVBoxLayout()

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
            line_edit = QLineEdit()
            line_edit.setText(default)
            self.input_fields[key] = line_edit
            self.form_layout.addRow(label_text, line_edit)

        # Dropdown for starting/bin position with nine options.
        self.start_position_combo = QComboBox()
        options = [
            "Center", "Top Left", "Top Center", "Top Right",
            "Left Center", "Right Center", "Bottom Left", "Bottom Center", "Bottom Right"
        ]
        self.start_position_combo.addItems(options)
        self.form_layout.addRow("Starting/Bin Position:", self.start_position_combo)

        left_panel.addLayout(self.form_layout)

        # Run simulation button.
        self.run_button = QPushButton("Generate Graph")
        self.run_button.clicked.connect(self.run_simulation)
        left_panel.addWidget(self.run_button)

        # Label to display daily stats.
        self.stats_label = QLabel("Daily stats will appear here.")
        self.stats_label.setAlignment(Qt.AlignCenter)
        left_panel.addWidget(self.stats_label)

        left_panel.addStretch()  # Push content to the top.

        # Right panel layout for graph.
        right_panel = QVBoxLayout()
        self.graph_container = QFrame()
        self.graph_container.setFrameShape(QFrame.StyledPanel)
        self.graph_layout = QVBoxLayout()
        self.graph_container.setLayout(self.graph_layout)
        right_panel.addWidget(self.graph_container)
        right_panel.addStretch()

        # Add left and right panels to the main layout.
        main_layout.addLayout(left_panel, 1)
        main_layout.addLayout(right_panel, 1)

        self.setLayout(main_layout)

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
            self.stats_label.setText("Error: Please enter valid numeric values for all fields.")
            return

        if (
            n_drones < 0 or n_humans < 0 or
            drone_speed <= 0 or human_speed <= 0 or
            num_trash <= 0 or num_days < 0
        ):
            self.stats_label.setText("Error: Check that numbers are valid and speeds/trash/days > 0.")
            return

        # Determine starting/bin position.
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
            num_agents=n_drones,
            speed_m_s=drone_speed,
            trash_locations=trash_locations,
            capacity=drone_capacity,
            start=start
        )

        final_time_sec_humans, total_dist_humans = simulation.concurrency_simulation(
            num_agents=n_humans,
            speed_m_s=human_speed,
            trash_locations=trash_locations,
            capacity=human_capacity,
            start=start
        )

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
            f"  Concurrency Time: {daily_hours_drones:.2f} hrs\n"
            f"  Total Distance: {total_dist_drones:.2f} m\n"
            f"  Daily Cost: ${daily_cost_drones:.2f}\n"
            f"  (Capacity: {drone_capacity if drone_capacity > 0 else 'Unlimited'})\n\n"
            f"HUMANS:\n"
            f"  Concurrency Time: {daily_hours_humans:.2f} hrs\n"
            f"  Total Distance: {total_dist_humans:.2f} m\n"
            f"  Daily Cost: ${daily_cost_humans:.2f}\n"
            f"  (Capacity: {human_capacity if human_capacity > 0 else 'Unlimited'})"
        )
        self.stats_label.setText(stats_text)

        canvas = graph.create_cost_comparison_figure(days_list, drone_costs, human_costs)
        self.clear_layout(self.graph_layout)
        self.graph_layout.addWidget(canvas)

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
