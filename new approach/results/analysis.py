import matplotlib.pyplot as plt


def analyze_logs(logs):
    """
    Simple analysis: Plot each agent's X-position over time.
    """
    times = [entry['time'] for entry in logs]

    # Ensure there's at least one log
    if not logs:
        return

    num_agents = len(logs[0]['agents'])

    for agent_idx in range(num_agents):
        x_positions = []
        for entry in logs:
            x_positions.append(entry['agents'][agent_idx]['position'][0])

        plt.plot(times, x_positions, label=f"Agent {agent_idx}")

    plt.xlabel("Time (s)")
    plt.ylabel("X Position")
    plt.legend()
    plt.show()
