import multiprocessing
import time
import math

from cadrhelpers.dtnclient import send_context, build_url
from typing import List, Tuple, Dict
from dataclasses import dataclass


@dataclass()
class NS2Movement:
    """Single movement command"""

    timestamp: int
    x_dest: float
    y_dest: float
    speed: float


class NS2Movements:
    """A node's movements as specified in a ns2 movement script

    Attributes:
        node_name: Self explanatory
        rest_url: URL of the context-REST-interface
        step: Current position in the list of movements
        x_pos: X coordinate of current position
        y_pos: Y coordinate of current position
        movements: List of movement commands in the form (timestamp, dest_x_pos, dest_y_pos, speed)
    """

    def __init__(
        self,
        rest_url: str,
        node_name: str,
        start_x: float,
        start_y: float,
        movements: List[NS2Movement],
    ):
        self.node_name: str = node_name
        self.rest_url: str = rest_url
        self.x_pos = start_x
        self.y_pos = start_y
        self.movements: List[NS2Movement] = movements
        self.step: int = 0

    def run(self) -> None:
        """Performs periodic context updates when movement changes
        Spawns a new process
        """
        process = multiprocessing.Process(target=self._run)
        process.start()

    def _run(self) -> None:
        """Does the actual work"""
        # differentiate between node who start moving immediately and those who take a while to get going
        if self.movements[0].timestamp != 0:
            time.sleep(self.movements[0].timestamp)

        vector = self.compute_vector()
        self.update_context(vector)
        self.move_step()

        # main wait-and-update-loop
        while self.step < len(self.movements):
            wait_time: int = self.movements[self.step].timestamp - self.movements[
                self.step - 1
            ].timestamp
            time.sleep(wait_time)
            vector = self.compute_vector()
            self.update_context(vector)
            self.move_step()

    def move_step(self) -> None:
        """Update the node's internal position and step counter"""
        self.x_pos = self.movements[self.step].x_dest
        self.y_pos = self.movements[self.step].y_dest
        self.step += 1

    def update_context(self, vector: Tuple[float, float]) -> None:
        """Update node context in dtnd"""
        context: Dict[str, float] = {"x": vector[0], "y": vector[1]}
        send_context(
            rest_url=self.rest_url, context_name="movement", node_context=context
        )

    def compute_vector(self) -> Tuple[float, float]:
        """Take the node's current position and destination/speed and compute the movement vector"""
        x_move = self.movements[self.step].x_dest - self.x_pos
        y_move = self.movements[self.step].y_dest - self.y_pos

        # normalise vector
        length: float = math.sqrt(math.pow(x_move, 2) + math.pow(y_move, 2))
        x_move = x_move / length
        y_move = y_move / length

        # multiply with speed
        x_move = x_move * self.movements[self.step].speed
        y_move = y_move * self.movements[self.step].speed

        return x_move, y_move


def filter_ns2(path: str, node_name: str) -> List[str]:
    """Reads in a ns2-movement-script and filters out all commands which are not for the specified node or commented"""
    node_id: str = node_name[1:]

    commands: List[str] = []
    with open(path, "r") as f:
        for line in f:
            if f"node_({node_id})" in line:
                # filter out commented commands
                if not line[0] == "#":
                    commands.append(line.strip())
    return commands


def generate_movement(rest_url: str, path: str, node_name: str) -> NS2Movements:
    """Turns the ns2 text file into a NS2Movement object"""
    commands = filter_ns2(path=path, node_name=node_name)
    start_x: float = 0.0
    start_y: float = 0.0
    movements: List[NS2Movement] = []

    for command in commands:
        split: List[str] = command.split(" ")
        if "X_" in split:
            start_x = float(split[3])
        elif "Y_" in split:
            start_y = float(split[3])
        elif "setdest" in split:
            timestamp = int(float(split[2]))
            x_dest = float(split[5])
            y_dest = float(split[6])
            speed = float(split[7][:-1])
            movements.append(
                NS2Movement(
                    timestamp=timestamp, x_dest=x_dest, y_dest=y_dest, speed=speed
                )
            )

    return NS2Movements(
        rest_url=rest_url,
        node_name=node_name,
        start_x=start_x,
        start_y=start_y,
        movements=movements,
    )


if __name__ == "__main__":
    url = build_url(address="localhost", port=35043)
    ns2_movement = generate_movement(
        rest_url=url,
        path="/home/msommer/devel/cadr-evaluation/scenarios/randomWaypoint/randomWaypoint.ns_movements",
        node_name="n11",
    )
    ns2_movement._run()