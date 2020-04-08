from __future__ import absolute_import

import sys
import os
import subprocess
import time
import signal
import psutil
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import matplotlib.pyplot as plt
from service.server import config
from topology.graph.graph import Graph
from topology.graph.graph import Node
from service.client import LocalClient
from random import randint, random, shuffle
from dissemination.util import get_host_ip

from graph_gen import generate_graph

from math import exp

ROOT = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")
app = os.path.join(ROOT, "service.py")
processes = []

def get_path(benchmark):
    PATH = os.path.dirname(os.path.realpath(__file__))
    PATH = os.path.join(PATH, "confs")
    PATH = os.path.join(PATH, "{}.json".format(benchmark))
    return PATH

def clear_processes():
    this_proc = os.getpid()
    for proc in psutil.process_iter():
        procd = proc.as_dict(attrs=['pid', 'name'])
        if "python" in str(procd['name']) and procd['pid'] != this_proc:
            proc.kill()

def add_process(command):
    global processes

    print("> {}".format(command))
    slave_proc = subprocess.Popen(command.split(" "),  shell=False)
    processes.append(slave_proc)

def export_graph(graph, benchmark):
    os.system("touch {}".format(get_path(benchmark)))
    with open(get_path(benchmark), "w") as config:
        config.write(str(graph.to_json()))

def delete_simulation_config(benchmark):
    os.remove(get_path(benchmark))

def create_master(benchmark, batch_threads):
    add_process("sudo python3 {} master -s {}.json -t {}".format(app, benchmark, batch_threads))

def create_slave(benchmark, port, batch_threads):
    add_process("sudo python3 {} slave -m {} -p {} -s {}.json -t {}".format(app, get_host_ip(), port, benchmark, batch_threads))

def take_snapshot():
    t = time.clock()
    try:
        graph = LocalClient(config["graph"]).get("/graph")
        graph = Graph.from_json(graph)
        return t, graph
    except Exception as e:
        return None

def process_snapshots(snapshots, processor):
    return [processor(t, s) for t, s in snapshots]

def build_scenario(name, nodes, edges, slaves, snaps, pause, processor, batch_threads):
    graph = generate_graph(nodes, edges)
    export_graph(graph, name)

    create_master(name, batch_threads)
    for i in range(slaves):
        time.sleep(2)
        create_slave(name, 1000 + i, batch_threads)

    snapshots = [(time.clock(), graph)]
    for i in range(0, snaps):
        time.sleep(pause)
        snapshot = take_snapshot()
        if snapshot is not None:
            snapshots.append(snapshot)
    delete_simulation_config(name)
    nodes = process_snapshots(snapshots, processor)

    clear_processes()
    return nodes

def nbr_service(graph):
    return len(graph.populated)

def plot(file_name, all_stats, label, selector):
    for key, raw_data in sorted(all_stats.items()):
        batch_threads, slaves = key
        line = [selector(entry) for entry in raw_data][1:]
        if batch_threads > 1:
            plt.plot(line, label="slaves = {}, batch size = {}".format(slaves, batch_threads))
        else:
            plt.plot(line, label="slaves = {}".format(slaves))
    plt.xlabel('time')
    plt.ylabel(label)
    plt.grid(True)
    plt.legend()

    plt.savefig(os.path.join(ROOT, "simulation", "res", file_name))
    plt.gcf().clear()

def scenario_stats(name, nodes, edges, snaps, pause, slaves_list, batch_threads):
    """
    Generates graphics from periodic snapshots to evaluate performance.
    We do a run for each pair of (slaves, batch_size).

    Produces 3 files in the 'res' folder:
      - hosts
      - edges
      - scanned

    :param name: Simulation name.
    :param nodes: Number of nodes in the random graph.
    :param edges: Number of edges in the random graph.
    :param snaps: The total number of snapshots taken. When no more snapshots
        are to be taken all the processes are killed.
    :param pause: The time interval that between taking 2 snapshots from
        the master node.
    :param slaves_list: The list of slaves to select from during each run.
    :param batch_threads: The list of batch threads to select from during
        each run.
    """
    all_stats = {}
    for batch_threads in batch_threads:
        for slaves in slaves_list:
            all_stats[(batch_threads, slaves)] = build_scenario(
                name=name,
                nodes=nodes,
                edges=edges,
                slaves=slaves,
                batch_threads=batch_threads,
                snaps=snaps,
                pause=pause,
                processor=lambda t, graph: (t, len(graph.nodes), len(graph.edges), nbr_service(graph))
            )

    plot(file_name="{}_hosts.png".format(name), all_stats=all_stats, label="hosts detected", selector=lambda x: x[1])
    plot(file_name="{}_edges.png".format(name), all_stats=all_stats, label="edges detected", selector=lambda x: x[2])
    plot(file_name="{}_scanned.png".format(name), all_stats=all_stats, label="scanned hosts", selector=lambda x: x[3])

if __name__ == "__main__":
    scenario_stats("small", 20, 210, 20, 3, [0, 1, 2], [1])
    scenario_stats("small_thds", 20, 210, 20, 3, [0, 1], [1, 2])
    scenario_stats("medium_thds", 100, 10000, 15, 3, [0, 2], [1, 3])
    scenario_stats("medium1", 100, 10000, 20, 3, [0, 1, 2], [1])
    scenario_stats("medium2", 300, 50000, 20, 3, [0, 1, 2], [1])
    scenario_stats("sparse", 1000, 10000, 20, 3, [0, 1, 2], [1])
