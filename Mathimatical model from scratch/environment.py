# environment.py
import random

from trash import Trash
from utils import distance

class Environment:
    def __init__(self, width = 50, height = 50, number_of_trash = 20, bin_position = (0,0)):
        self.width = width
        self.height = height
        self.number_of_trash = number_of_trash
        self.trash_list = []
        self.generate_trash()
        self.bin_position = bin_position


    def generate_trash(self):
        for i in range(self.number_of_trash):
            x = random.uniform(0, self.width)
            y = random.uniform(0, self.height)
            self.trash_list.append(Trash(x,y))

    def closest_trash(self, x, y):
        """Finds and removes the closest trash to the given (x, y) coordinates.
           Returns a tuple (closest_trash, distance)."""
        if not self.trash_list:  # Check if the list is empty
            return None, None

        # Find the closest trash and its distance
        closest_trash = min(self.trash_list, key=lambda trash: distance(x, y, trash.x, trash.y))
        closest_distance = distance(x, y, closest_trash.x, closest_trash.y)

        # Remove it from the list
        self.trash_list.remove(closest_trash)

        return closest_trash, closest_distance

