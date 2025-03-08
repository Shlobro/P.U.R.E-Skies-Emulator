import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


def create_cost_comparison_figure(days, drone_costs, human_costs):
    """
    Create a Matplotlib figure and return a FigureCanvas widget that can be embedded in a PySide6 UI.

    X-axis: Days
    Y-axis: Total Cost
    """
    fig = Figure(figsize=(5, 4))
    ax = fig.add_subplot(111)
    ax.plot(days, drone_costs, label='Drone Collection Cost', marker='o')
    ax.plot(days, human_costs, label='Human Collector Cost', marker='o')
    ax.set_xlabel('Days')
    ax.set_ylabel('Total Cost')
    ax.set_title('Cost Comparison: Drones vs. Humans')
    ax.legend()
    ax.grid(True)
    canvas = FigureCanvas(fig)
    return canvas
