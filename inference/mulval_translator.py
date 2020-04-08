from __future__ import absolute_import

import logging
logger = logging.getLogger(__name__)

import os, sys, time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json, subprocess
from service.client import LocalClient
from service.server import Server, config

import xml.etree.ElementTree as ET

from inference.mulval_data import TranslatorBuilder

class MulvalTranslator():
    def __init__(self):
        self.mulval_file = open('mulval_input.P', 'w')
        self.active_set = set()

    def _make_topology(self):
        """ Translates information about the topology to MulVAL predicates"""

        self.mulval_file.write("attackerLocated(internet).\n")
        self.mulval_file.write("attackGoal(execCode(_, _)).\n")

        # Hardcoded...
        self.mulval_file.write("hacl(internet, '{}', _, _).\n".format(self.data["links"][0]["source"]))

        def add_edge(edge_from, edge_to):
            if not (edge_from, edge_to) in self.active_set:
                self.mulval_file.write("hacl('{}', '{}', _, _).\n".format(edge_from, edge_to))
                self.active_set.add((edge_from, edge_to))

        for link in self.data["links"]:
            add_edge(link["source"], link["target"])

    def _add_vulnerabilities(self):
        """ Translates vulnerabilities of hosts to MulVAL predicates """

        for host in self.data["hosts"]:
            if host["running"]["scanned"] == "false":
                continue
            running = host["running"]
            if running != {"scanned" : "true"}:
                running = running["Host"]
                for service in running["RunningServices"]:
                    # Getting service information
                    ip = host["ip"]
                    application = service["Service"]["product"]
                    port = service["Port"]["portid"]
                    protocol = service["Port"]["protocol"]

                    # We look at all probabilities
                    for idx in range(len(service["Privileges"])):
                        if "unknown" in service["Privileges"][idx]:
                            continue

                        # Privileges are combined privileges for all the vulenrabilities
                        if service["Privileges"][idx]["user"]:
                            privileges = "user"
                        if service["Privileges"][idx]["all"]:
                            privileges = "root"

                        vulnerability = service["Vulnerability"][idx]["id"]
                        access = service["Vulnerability"][idx]["impact"]["baseMetricV2"]["cvssV2"]["accessVector"]

                        if access == "LOCAL": access = "localExploit"
                        if access == "NETWORK": access = "remoteExploit"

                        self.mulval_file.write("networkServiceInfo('%s', '%s', '%s', '%s', '%s').\n" % (ip, application, protocol, port, privileges))
                        self.mulval_file.write("vulExists('%s', '%s', '%s').\n" % (ip, vulnerability, application))
                        self.mulval_file.write("vulProperty('%s', %s, %s).\n" % (vulnerability, access, 'privEscalation'))

    def _cleanup(self, files_before):
        # clean all the files produced by mulval
        to_clean = list(set(os.listdir()) - set(files_before))
        logger.info("Files cleaned: {}".format(to_clean))
        for f in to_clean:
            os.system("rm {}".format(f))

    def _save_output(self):
        with open('AttackGraph.txt', 'r') as output:
            return output.read()

    def _graphXMLtoJSON(self):
        tree = ET.parse('AttackGraph.xml')
        root = tree.getroot()
        arcs = root[0]
        nodes = root[1]
        return json.dumps({
            "nodes" : [{
                "id" : node[0].text,
                "fact" : node[1].text,
                "metric" : node[2].text,
                "type" : node[3].text,
            } for node in nodes],
            "arcs" : [{
                "source" : arc[1].text,
                "target" : arc[0].text,
            } for arc in arcs]
        })

    def generate_attack_graph(self, env):
        logger.info("Generating attack graph.")
        files_before = os.listdir()

        self._make_topology()
        self._add_vulnerabilities()
        self.mulval_file.close()

        def missing_env(name):
            # checks that all environment variables needed to run MulVAL are defined
            if name not in env:
                logger.error("{} not present in environment.".format(name))
                return True
            return False

        if missing_env("MULVALROOT"): return None
        if missing_env("XSB_DIR"): return None

        env["PATH"] = "{}:{}".format(env["PATH"], os.path.join(env["MULVALROOT"], "bin"))
        env["PATH"] = "{}:{}".format(env["PATH"], os.path.join(env["MULVALROOT"], "utils"))
        env["PATH"] = "{}:{}".format(env["PATH"], os.path.join(env["XSB_DIR"], "bin"))

        # Handle some types of installation for different distributions
        if "JAVA_HOME" in env:
            env["PATH"] = "{}:{}".format(env["PATH"], os.path.join(env["JAVA_HOME"], "bin"))

        subprocess.Popen(['graph_gen.sh mulval_input.P -p'], shell=True, env=env).wait()
        # self._save_output()
        attackGraphJSON = self._graphXMLtoJSON()

        self._cleanup(files_before)

        return attackGraphJSON

def generate_attack_graph(client, env=os.environ.copy()):
    return TranslatorBuilder(client) \
        .from_client_data() \
        .build(MulvalTranslator()) \
        .generate_attack_graph(env)

if __name__ == "__main__":
    logger.info(generate_attack_graph(LocalClient(config["graph"])))
