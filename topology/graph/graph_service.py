from __future__ import absolute_import

import logging
logger = logging.getLogger(__name__)

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from service.components import Component
from service.server import Server, config
from service.client import LocalClient

from topology.graph.populator import Populator
from topology.graph.graph import Graph
from topology.graph.graph import Node

import ast
import time
import requests
import json
import threading

from threading import Lock

class GraphExporter(Component):
    """
    A component that allows exporting a graph.
    """
    def __init__(self, graph):
        self.graph = graph

    def process(self, unused):
        """
        :return: returns a Graph class instance in json form
        """
        self.graph.lock.acquire()
        export = self.graph.to_json()
        self.graph.lock.release()

        return export

class GraphMerge(Component):
    """
    A component that allows listening for merge requests for a graph.
    """
    def __init__(self, graph):
        self.graph = graph

    def process(self, graph):
        """
        :param graph: a Graph class instance to be merged
        :return: returns {"success" : "true"} if merge sucessful
        """
        self.graph.lock.acquire()
        self.graph.merge(Graph.from_json(graph))
        self.graph.lock.release()
        return {
            "success" : "true"
        }

class GraphService():
    """
    The GraphService encapsulates all the dependecies of the
    graph service:
      * a local client to the sniffer
      * a server
      * a populator
    """
    def __init__(self, graph, sniffer_client=LocalClient(config["sniffer"]), batch_threads=1):
        self.graph = graph
        self.populator = Populator(self.graph, batch_threads=batch_threads)

        self.server = Server("graph", config["graph"])
        self.server.add_component_get("/graph", GraphExporter(graph))
        self.server.add_component_post("/merge", GraphMerge(graph))

        self.sniffer_client = sniffer_client

    def get_edge(self, packet):
        """
        Returns an edges from a packet dictionary. The packet must have
        fields "src" and "dest".
        """
        src, dest = packet["src"], packet["dest"]
        return Node(src), Node(dest)

    def update(self):
        """
        Updates a graph with new packets requested from the sniffer
        microservice.
        """
        new_packets = self.sniffer_client.get("/newpackets", default=[])

        self.graph.lock.acquire()
        for packet in new_packets:
            edge = self.get_edge(packet)
            if edge is not None:
                self.graph.add_edge(*edge)
        self.graph.lock.release()

def graph_service(batch_threads=1, no_scan=False):
    """
    The graph_service method represents the runtime of the GraphService class.

    Args:
    - batch_threads: the number of threads in a parallel scan
    - no_scan: if the no_scan flag is on, don't start the populator
    """
    no_scan = bool(no_scan)

    graph = Graph()
    service = GraphService(graph, batch_threads=int(batch_threads))

    threading.Thread(target=service.server.run).start()
    # if not no_scan:
    threading.Thread(target=service.populator.populate_loop).start()

    while True:
        service.update()

        time.sleep(10)
        # logger.debug(LocalClient(config["graph"]).get("/graph"))

if __name__ == "__main__":
    graph_service()
