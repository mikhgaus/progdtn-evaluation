#! /usr/bin/env python3

import toml
import argparse
import time
import os
import logging

from typing import Tuple

import cadrhelpers.movement_context as m_c
import cadrhelpers.util

from cadrhelpers.dtnclient import (
    build_url,
    send_context,
    register,
    RESTError,
    fetch_pending,
)
from cadrhelpers.traffic_generator import TrafficGenerator, DESTINATION
from cadrhelpers.node_context import SensorContext


def run(rest_url: str, logging_file: str, this_node: cadrhelpers.util.Node) -> None:
    logging.info("Starting store size logging")

    with open(logging_file, "w", buffering=1) as f:
        f.write("routing,node,timestamp,size\n")

        if this_node.type == "backbone":
            eid = DESTINATION
        else:
            eid = f"dtn://{this_node.name}/"

        try:
            registration_data = register(rest_url=rest_url, endpoint_id=eid)

            while True:
                time.sleep(60)
                # empty store of pending bundles
                fetch_pending(rest_url=rest_url, uuid=registration_data["uuid"])

        except RESTError as err:
            logging.error(err)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Will generate metadata and/or traffic depending on node type"
    )
    parser.add_argument("path", help="Path to the config file")
    args = parser.parse_args()

    config_data = toml.load(args.path)
    logging.info(f"Using config: {config_data}")

    logging.basicConfig(
        level=config_data["Node"]["log_level"], filename=config_data["Node"]["log_file"]
    )

    if os.path.isfile("/tmp/seed"):
        with open("/tmp/seed", "rb") as f:
            seed = f.read(4)
    else:
        seed = b"\x00\x00\x00\x00"
    logging.info(f"Seed: {seed}")

    if os.path.isfile("/tmp/routing"):
        with open("/tmp/routing", "r") as f:
            routing = f.read().strip()
    else:
        routing = "epidemic"
    logging.info(f"Routing Algorithm: {routing}")

    context = "context" in routing
    logging.info(f"Using Context: {context}")

    context_algorithm = ""
    if context:
        context_algorithm: str = routing.split("_")[1]

    routing_url = build_url(
        address=config_data["REST"]["address"], port=config_data["REST"]["routing_port"]
    )
    agent_url = build_url(
        address=config_data["REST"]["address"], port=config_data["REST"]["agent_port"]
    )

    nodes: cadrhelpers.util.Nodes = cadrhelpers.util.parse_scenario_xml(
        path=config_data["Scenario"]["xml"]
    )
    this_node = nodes.get_node_for_name(node_name=config_data["Node"]["name"])
    logging.info(f"This node's type: {this_node.type}")

    if context_algorithm == "complex":
        node_type = {"node_type": this_node.type}
        logging.info(f"Sending node type: {node_type}")
        send_context(rest_url=routing_url, context_name="role", node_context=node_type)

        if this_node.type == "sensor":
            logging.info("Initialising SensorContext")
            context_generator = SensorContext(
                rest_url=routing_url,
                node_name=config_data["Node"]["name"],
                wifi_range=config_data["Scenario"]["wifi_range"],
                nodes=nodes,
            )
            context_generator.run()
            logging.info("Initialised SensorContext")

    logging.info("Daemonising")
    run(
        rest_url=agent_url,
        logging_file=config_data["Node"]["store_log"],
        this_node=this_node,
    )
