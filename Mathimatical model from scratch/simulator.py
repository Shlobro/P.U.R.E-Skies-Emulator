# simulator.py
import copy

from environment import Environment
from utils import time_to_travel


class Simulator:
    def __init__(self, environment: Environment, drone_list, human_list):
        self.drone_env = environment
        self.human_env = environment
        self.human_list = human_list
        self.drone_list = drone_list



    # notice that the collection algorithm currently is working on the greedy algorithm at the moment
    # TODO this will only work with one collector. need to change the code to be able to handle multiple collectors
    def calc_time(self, collector, environment):
        for i in range(len(environment.number_of_trash)):
            # find the trash that is closest and how close it is
            trash, distance = environment.closest_trash(collector.x, collector.y)

            #simulate going to the trash
            collector.x = trash.x
            collector.y = trash.y
            collector.total_time += time_to_travel(distance, collector.speed)

            # if there is too much weight then leave the trash and return home
            if collector.current_weight >= collector.max_weight:
                environment.trash_list.append(trash)
                collector.return_home(*environment.bin_position)
                continue

            # simulate picking up the trash
            collector.current_items += 1
            collector.current_weight += trash.weight

            # if we reached the maximum amount of trash items need to return home
            if collector.current_items >= collector.max_items:
                collector.return_home(*environment.bin_position)