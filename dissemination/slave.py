from __future__ import absolute_import

import logging
logger = logging.getLogger(__name__)

import sys
import os
import time
import threading
import random
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from service.client import Client
from service.server import Server
from service.components import Component
from clint.textui import colored

from dissemination.master import MASTER_DEFAULT_PORT
from dissemination.graph_sharing import GraphSharing
from dissemination.util import get_host_ip

class SlaveMembership(Component):
    def __init__(self, slave):
        self.slave = slave

    def process(self, membership_list):
        """
        REST component request processing. Register the master on the slave.
        """
        logging.info(colored.green("Received membership list."))
        self.slave.update_membership(membership_list)

class HealthCheck(Component):
    def process(self, _):
        """The health check component is responsible for anouncing
        each slave that the master is working."""
        return {
            "healty" : "true"
        }

class MessageReceiver(Component):
    def __init__(self, slave):
        self.slave = slave

    def process(self, message):
        """Graph partial component receiver."""
        logger.info(colored.green("Received message."))
        self.slave.graph_sharing.update(message["graph"])

class Slave():
    def __init__(self, slave_port, master_ip, master_port, client_cls=Client):
        self.slave_port = slave_port
        self.slave_ip = get_host_ip()
        self.client_cls = client_cls

        self.master_client = self.client_cls("http://" + master_ip, master_port)
        self.membership_list = []

        self.server = Server("slave", slave_port)
        self.server.add_component_get("/healty", HealthCheck())
        self.server.add_component_post("/membership", SlaveMembership(self))
        self.server.add_component_post("/multicast", MessageReceiver(self))

        self.dissemination_constant = 5
        self.graph_sharing = GraphSharing()

    def join(self):
        """Send request to the master for addition to membership list.
        Slave sends its IP and port number."""
        logger.info(colored.yellow("Slave requesting join."))
        self.master_client.post("/register", {
            "ip" : self.slave_ip,
            "port" : self.server.port
        })

    def update_membership(self, membership_list):
        """Epidemic style dissemination to slave neighbours."""
        logger.info(colored.green("Updating membership...."))
        if "members" not in membership_list:
            return
        membership_list = membership_list["members"]

        self.membership_list = []
        for member in membership_list:
            if self.slave_ip == member["ip"] and self.slave_port == member["port"]:
                continue
            client = self.client_cls("http://" + member["ip"], member["port"])
            self.membership_list.append(client)
        logger.info("Membership list updated: {} members.".format(len(self.membership_list)))

    def get_current_broadcast(self):
        """Returns the membership list for this slave."""
        return self.membership_list

    def get_current_multicast(self):
        """Returns the list of slaves this slave can send messages to.
        This is the randomized part that can be proven to be O(log n) for
        the whole dissemination."""
        multicast_list = list(self.membership_list[:])
        random.shuffle(multicast_list)

        return multicast_list[:self.dissemination_constant]

    def disseminate(self, multicast_list, message):
        """Send message to all multicast nodes this slave can communicate to."""
        logger.info("Running dissemination.")
        for client in multicast_list:
            logger.info("Sending message to {}:{}.".format(client.url, client.port))
            client.post("/multicast", message)

    def run(self):
        """Slave main function loop."""
        self.join()
        time.sleep(5)

        while True:
            time.sleep(10)
            multicast_list = self.get_current_multicast()
            multicast_message = {
                "ip" : self.slave_ip,
                "port" : self.slave_port,
                "graph" : self.graph_sharing.snapshoot()
            }
            self.disseminate(multicast_list, multicast_message)

def slave_service(master_ip, slave_port):
    time.sleep(3)

    master_port = MASTER_DEFAULT_PORT
    slave = Slave(slave_port, master_ip, master_port)

    threading.Thread(target=slave.server.run).start()
    slave.run()
