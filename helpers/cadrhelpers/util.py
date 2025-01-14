import math
from typing import Tuple, List, Union
from xml.etree import ElementTree as ElementTree


def is_context(name: str) -> Tuple[bool, str]:
    context = "cadr" in name

    context_algorithm = ""
    if context:
        context_algorithm: str = name.split("_")[1]

    return context, context_algorithm


class Node:
    """Simulation node"""

    def __init__(self, id: int, name: str, type: str, x_pos: float, y_pos: float):
        self.id: int = id
        self.name: str = name
        self.type: str = type
        self.x_pos: float = x_pos
        self.y_pos: float = y_pos

    def __repr__(self) -> str:
        return f"Node(id={self.id}, name='{self.name}', type='{self.type}', x_pos={self.x_pos}, y_pos={self.y_pos})"


def compute_euclidean_distance(node_a: Node, node_b: Node) -> float:
    x_diff = math.pow(node_a.x_pos - node_b.x_pos, 2)
    y_diff = math.pow(node_a.y_pos - node_b.y_pos, 2)
    return math.sqrt(x_diff + y_diff)


class Nodes:
    """All the nodes in the simulation"""

    def __init__(self, responders: List[Node], civilians: List[Node], coordinators: List[Node]):
        self.responders: List[Node] = responders
        self.civilians: List[Node] = civilians
        self.coordinators: List[Node] = coordinators

    def get_node_for_name(self, node_name: str) -> Node:
        ourself: Union[Node, None] = None

        for node in self.responders + self.civilians + self.coordinators:
            if node.name == node_name:
                ourself = node

        assert (
            ourself is not None
        ), "This node should really show up in the list of nodes"
        return ourself

    def __str__(self) -> str:
        return f"Responders: {self.responders}\nCivilians: {self.civilians}\nCoordinators: {self.coordinators}"


def parse_scenario_xml(path: str) -> Nodes:
    """Parse the scenario's xml definition and separate the different types of nodes

    Returns:
        Three lists (visitors, sensors, backbone)
    """
    tree = ElementTree.parse(path)
    root = tree.getroot()

    responders: List[Node] = []
    civilians: List[Node] = []
    coordinators: List[Node] = []

    for child in root:
        if child.tag == "devices":
            for node_data in child:
                node = get_node_info(node_data)
                if node.type == "responder":
                    responders.append(node)
                elif node.type == "civilian":
                    civilians.append(node)
                elif node.type == "coordinator":
                    coordinators.append(node)

    return Nodes(responders=responders, civilians=civilians, coordinators=coordinators)


def get_node_info(element: ElementTree.Element) -> Node:
    """Extract the info aof a node from the xml tree"""
    node_id: int = int(element.attrib["id"])
    node_name: str = element.attrib["name"]
    node_type: str = element.attrib["type"]
    x_pos: float = 0.0
    y_pos: float = 0.0

    for sub_element in element:
        if sub_element.tag == "position":
            x_pos = float(sub_element.attrib["x"])
            y_pos = float(sub_element.attrib["y"])

    return Node(id=node_id, name=node_name, type=node_type, x_pos=x_pos, y_pos=y_pos)


def get_node_type(nodes: Nodes, name: str) -> str:
    for node in nodes.civilians:
        if node.name == name:
            return "civilian"

    for node in nodes.coordinators:
        if node.name == name:
            return "coordinator"

    for node in nodes.responders:
        if node.name == name:
            return "responder"

    return ""
