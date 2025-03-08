# trashCollector.py
from utils import distance
from utils import time_to_travel


class TrashCollector:
    def __init__(self, speed: float, capacity_items: float, hourly_cost: float, capacity_kg = float('inf')):
        self.speed = speed
        self.capacity_kg = capacity_kg
        self.capacity_items = capacity_items
        self.current_items = 0
        self.current_weight = 0
        self.x = 0
        self.y = 0
        self.total_time = 0
        self.hourly_cost = hourly_cost

    def return_home(self, bin_x, bin_y):
        self.x = bin_x
        self.y = bin_y
        self.current_items = 0
        self.current_weight = 0
        dis = distance(self.x, self.y, bin_x, bin_y)
        self.total_time += time_to_travel(dis, self.speed)


class Human(TrashCollector):
    def __init__(self, speed: float, capacity_items: float, hourly_cost: float, capacity_kg = float('inf')):
        super().__init__(speed, capacity_kg, capacity_items, hourly_cost)



class Drone(TrashCollector):
    def __init__(self, speed: float, capacity_items: float, hourly_cost: float, initial_cost: float, capacity_kg = float('inf')):
        super().__init__(speed, capacity_kg, capacity_items, hourly_cost)
        self.initial_cost = initial_cost