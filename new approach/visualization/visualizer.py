import pygame
import sys


class PygameVisualizer:
    def __init__(self, width=800, height=600):
        pygame.init()
        self.screen = pygame.display.set_mode((width, height))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 24)

    def update(self, environment, agents, current_time):
        """
        Render the environment and agents each frame.
        """
        # Basic event loop
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        self.screen.fill((255, 255, 255))  # White background

        # Draw obstacles
        for obs in environment.obstacles:
            pygame.draw.rect(self.screen, (150, 150, 150), obs)

        # Draw agents
        for agent in agents:
            x, y = agent.position
            color = (0, 255, 0) if 'Drone' in agent.name else (0, 0, 255)
            pygame.draw.circle(self.screen, color, (int(x), int(y)), 5)

        # Text overlay
        text_surface = self.font.render(f"Time: {current_time:.1f}s", True, (0, 0, 0))
        self.screen.blit(text_surface, (10, 10))

        pygame.display.flip()
        self.clock.tick(60)  # Limit to 60 FPS

    def finalize(self):
        """
        Cleanup if needed.
        """
        pygame.quit()
