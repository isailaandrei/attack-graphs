from __future__ import absolute_import

import logging
logger = logging.getLogger(__name__)

import os
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from topology.sniffer.sniffer import parse_packet

import threading
import pcapy

def timeout_dispach(function, timeout, *args):
    """
    Dispach a function in another thread and if the join fails after
    timeout, stops the function, raising an error.
    """
    t = threading.Thread(target=function, args=args)
    t.start()
    t.join(timeout=timeout)

def open_connection(device_name):
    logger.info("Openning connection with {}.".format(device_name))
    return [pcapy.open_live(device_name, 65536 , True , 100)]

def discover_devices():
    """
    Automatically discovers devices by counting the number of relevant
    IP packets recevied on the specific interface.

    This function is expensive, hence should be run rarely.
    """
    # return [pcapy.open_live("wlp8s0", 65536 , True , 100)]
    devices = pcapy.findalldevs()

    connections = []
    read_packets = {}
    received_eth_packets = {}
    for dev in devices:
        try:
            connection = pcapy.open_live(dev , 65536 , True , 100)
            connections.append(connection)

            # Decorate the objects with number of already read packets
            read_packets[connection] = 0
            received_eth_packets[connection] = 0

            if connection.getnonblock():
                # Set each connection to be blocking
                connection.setnonblock(False)
        except Exception as e:
            logger.error("Device {} failed.".format(dev))

    # Wait for a timeout capture and select only the interfaces that exchange packets
    logger.info("Waiting to test interfaces...")
    time.sleep(5)

    # Set a number of iterations in which we decide which interfaces to listen at
    iterations = 10
    logger.info("Checking for devices that have eth packets...")
    while iterations > 0:
        iterations -= 1
        for connection in connections:
            (received, dropped1, dropped2) = connection.stats()
            used = received - dropped1 - dropped2

            if used <= read_packets[connection] + 1:
                continue

            try:
                def next_packet():
                    (header, packet) = connection.next()
                    packet = parse_packet(packet)

                    # If we arrive here, then the packet is an eth packet
                    received_eth_packets[connection] += 1
                timeout_dispach(next_packet, 0.5)
            except Exception as e:
                # Ignore non-eth packets
                pass

    # Filter out the connection that did not receive any eth packet
    all_connections = [conn for conn in connections]
    logger.info("Filtering devices...")
    connections = []
    for connection in all_connections:
        if received_eth_packets[connection] > 0:
            connections.append(connection)
        else:
            # This will call __exit__, so the unused connections get closed
            del connection

    logger.info("Connections opened: " + str(len(connections)))
    return connections
