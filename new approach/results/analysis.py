import matplotlib.pyplot as plt


def analyze_logs(logs):
    """
    Create charts or tables from the logs.
    logs is a list of dicts recorded at each time step.
    """
    times = [entry['time'] for entry in logs]

    # Example: Plot each agent's x-position over time
    for agent_idx in range(len(logs[0]['agents'])):
        x_positions = []
        for entry in logs:
            x_positions.append(entry['agents'][agent_idx]['position'][0])

        plt.plot(times, x_positions, label=f"Agent {agent_idx}")

    plt.xlabel("Time (s)")
    plt.ylabel("X Position")
    plt.legend()
    plt.show()
