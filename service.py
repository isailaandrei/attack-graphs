import sys
import threading
import os
import signal
import argparse
import random
import time

import logging
logger = logging.getLogger(__name__)

# Hide requests from the logs
import requests
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.ERROR)

from clint.textui import colored
from clint.textui.colored import ColoredString

from multiprocessing import Process, Value
from dissemination.util import get_host_ip

def signal_handler(siganl, frames):
    """
    Signal handler that kills all the processes created by the application.
    """
    logger.warn("Killing the running services.")
    for process in processes:
        logger.warn("Killing process {}".format(process.pid))
        os.system("kill -9 {}".format(process.pid))
    sys.exit(0)

def services(benchmark, device_name=None, filter_mask=None, batch_threads=1, no_scans=False):
    """
    Starts all the bussiness-logic microservices.

    :param benchmark: When benchmark parameter is True, we disable the database
        and inference services for the purpose of benchmarking.
    :param device_name: Device name passed to sniffing_service
    :param filter_mask: Filter mask passed to sniffing_service.
    :param batch_threads: Batch size passes to graph_service(and the populator).
    :param no_scans: When no scans is True, the populator is disabled.
    :return: returns nothing
    """

    from topology.graph.graph_service import graph_service
    from topology.sniffer.sniffing_service import sniffing_service
    from database.database_service import database_service
    from inference.inference_service import inference_service

    global processes
    if benchmark is not None:
        processes.append(Process(target=database_service))
        processes.append(Process(target=inference_service, kwargs ={'env' : os.environ.copy()}))

    processes.append(Process(target=graph_service, args=(str(batch_threads), str(no_scans))))
    processes.append(Process(target=sniffing_service, args=(device_name, filter_mask)))

def bind_simulation(simulation):
    """
    Overrides the default services with a simulation.

    The seam points are devices.open_connection and discovery.discovery_ip.
    """
    import topology.sniffer.devices as devices
    import topology.discovery.discovery as discovery

    devices.open_connection = lambda device_name: [simulation.connection()]
    discovery.discovery_ip  = lambda ip: simulation.discovery_ip(ip)

def set_ports(node_type):
    """
    Provides dynamic port binding for slave services and fixed port binding
    for master services.
    """
    import service.server as config_keeper

    port_offset = 30000

    if node_type == "slave":
        config = {
            'inference' : port_offset + random.randint(0, port_offset),
            'database' : port_offset + random.randint(0, port_offset),
            'sniffer' : port_offset + random.randint(0, port_offset),
            'graph' : port_offset + random.randint(0, port_offset)
        }
    elif node_type == "master":
        config = config_keeper.config
    else:
        logger.error("Wrong type specified.")
        os.kill(os.getpid(), signal.SIGINT)

    setattr(config_keeper, 'config', config)

def setup_loggers(verbose):
    """
    Sets up loggers by the given level of verbosity. We also provide file
    logging in the file 'attack-graph.log' (with DEBUG verbosity level).

    :param verbose: when the flag for verbosity is set, the logging level is set
        to DEBUG.
    :return: returns nothing
    """

    stderr_handler = logging.StreamHandler(sys.stderr)

    class ColoredFormatter(logging.Formatter):
        """
        Formatter that allows coloring logs via Clint library.
        """
        def format(self, record):
            msg = record.getMessage()

            out_msg = '{}:{}:{}'.format(
                str(record.levelname),
                record.name,
                str(msg)
            )

            if hasattr(record.msg, 'color'):
                color = record.msg.color

                colored_msg = str(ColoredString(color, str(out_msg)))
                return colored_msg

            return out_msg

    if args.verbose:
        stderr_handler.setLevel(logging.DEBUG)
    else:
        stderr_handler.setLevel(logging.INFO)
    stderr_handler.setFormatter(ColoredFormatter())

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Logging to file as well
    file_handler = logging.FileHandler('attack-graph.log')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[stderr_handler, file_handler]
    )

def setup_dissemination(args):
    """
    Dissemination module setup.

    :param args: the arguments received by the function are the arguments
        received by the main application under the form of a dictionary.
    :return: returns nothing
    """
    if args.type == "master":
        from dissemination.master import master_service
        from dissemination.slave import slave_service

        port_offset = 30000
        port = port_offset + random.randint(0, port_offset)

        # When running a master we need a slave as well as only the slave keeps the graph
        processes.append(Process(target=master_service))
        processes.append(Process(target=slave_service, args=(get_host_ip(), port)))

    if args.type == "slave":
        master_ip = args.master
        port      = args.port

        if master_ip is None or port is None:
            logger.error("Not enough arguments provided for slave mode.")
            os.kill(os.getpid(), signal.SIGINT)

        from dissemination.slave import slave_service
        processes.append(Process(target=slave_service, args=(master_ip, port)))

def setup_argparser():
    """
    Argument parser setup using argparse library.

    :return: returns an ArgumentParser
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("type", type=str,
        help="The type of node run: 'master' or 'slave'")
    parser.add_argument("-m", "--master", type=str, default=None,
        help="Specify master IP for connecting a slave.")
    parser.add_argument("-p", "--port", type=str, default=None,
        help="Specify port for runnning a slave.")
    parser.add_argument("-i", "--interface", type=str, default=None,
        help="The network interface listened to.")
    parser.add_argument("-s", "--simulation", type=str, default=None,
        help="To run a simulated network from a network configuration file use this flag.")
    parser.add_argument("-f", "--filter", type=str, default=None,
        help="Specify a mask for filtering the packets. (e.g. '10.1.1.1/16' would keep packets starting with '10.1')")
    parser.add_argument("-v", '--verbose', dest='verbose', action='store_true',
        help="Set the logging level to DEBUG.")
    parser.add_argument("-b" , "--benchmark", dest='benchmark', action='store_true',
        help="Disables database and inference engine for benchmarking.")
    parser.add_argument("-t", "--batch_threads", type=int, default=1,
        help="Number of threads that should run host discovery.")
    parser.add_argument("-n", "--no-scan", dest='no_scan', action='store_true',
        help="Disable port scanning.")
    parser.set_defaults(verbose=False)
    return parser


if __name__ == "__main__":
    parser = setup_argparser()
    args = parser.parse_args()

    setup_loggers(args.verbose)

    if os.getuid() != 0:
        logger.error("Must be run as root.")
        exit(1)

    if args.simulation is not None:
        from simulation.simulation import Simulation
        args.interface = "virtual_interface"

        bind_simulation(Simulation(args.simulation))

    global processes
    processes = []

    set_ports(args.type)
    services(args.benchmark, args.interface, args.filter, args.batch_threads)
    setup_dissemination(args)

    signal.signal(signal.SIGINT, signal_handler)

    for process in processes:
        process.start()
    for process in processes:
        process.join()
