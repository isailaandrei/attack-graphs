import logging
logger = logging.getLogger(__name__)


from clint.textui import colored

from threading import Lock

class Node():
    """
    The class used to encapsulate a node.

    Ip contains the mutable filds `ip` and `running`.
    """
    def __init__(self, ip):
        self.ip = ip
        self.running = {"scanned": "false"}

    def __eq__(self, other):
        """Override the default Equals behavior"""
        if isinstance(other, self.__class__):
            return self.ip == other.ip
        return False

    def __ne__(self, other):
        """Define a non-equality test"""
        return not self.__eq__(other)

    def __str__(self):
        if self.running == {"scanned": "false"}:
            return str(self.ip)
        return str((self.ip, self.running))

    def __hash__(self):
        numbers = [int(x) for x in self.ip.split(".")]
        return numbers[0] * 256 ** 3 + numbers[1] * 256 ** 2 + numbers[2] * 256 + numbers[3]

class Graph():
    """
    The class used to encapsulate a graph.

    The graph is modelled as the following sets:
      - edges
      - nodes
      - unpopulated
      - populated
    """
    def __init__(self):
        self.edges = set()
        self.nodes = set()
        self.lock = Lock()

        self.unpopulated = set()
        self.populated = set()

    def add_edge(self, n1, n2):
        """
        :param n1: the starting point of the edge
        :param n2: the arriving point of the edge
        :return: returns nothing
        """
        self.nodes.add(n1)
        self.nodes.add(n2)

        if n1 not in self.populated:
            self.unpopulated.add(n1)
        if n2 not in self.populated:
            self.unpopulated.add(n2)

        if n1 == n2:
            return

        self.edges.add((n1, n2))

    def merge(self, graph):
        """
        :param graph: a Graph structure to merge with the current graph
        :return: returns nothing
        """
        logger.info("Merging graphs.")
        graph1 = self
        graph2 = graph

        logger.info("Graph1 to merge: nodes[{}], populated [{}].".format(
            len(graph1.nodes),
            len(graph1.populated)
        ))
        logger.info("Graph2 to merge: nodes[{}], populated [{}].".format(
            len(graph2.nodes),
            len(graph2.populated)
        ))

        graph1.edges |= graph2.edges

        # (U1 + U2) - (P1 + P2)
        graph1.populated |= graph2.populated
        graph1.unpopulated |= graph2.unpopulated
        graph1.unpopulated -= graph1.populated

        # N = U + P
        graph1.nodes = graph1.populated | graph1.unpopulated

        logger.info("Finished merging: nodes[{}], populated [{}].".format(
            len(graph1.nodes),
            len(graph1.populated)
        ))

    def to_json(self):
        """
        :return: returns a JSON-convertible dictionary representing the graph
        """
        return {
            "hosts" : [{
                "ip" : node.ip,
                "running" : node.running
            } for node in self.nodes],
            "links" : [{
                "source" : n1.ip,
                "target" : n2.ip,
                "value"  : 1,
            } for n1, n2 in self.edges]
        }

    @staticmethod
    def from_json(json_input):
        """
        Static method that build a graph from a JSON-convertible dictionary.
        """
        res = Graph()

        for link in json_input["links"]:
            n1 = Node(link["source"])
            n2 = Node(link["target"])
            res.add_edge(n1, n2)
        res.populated = set()
        res.unpopulated = set()

        for host in json_input["hosts"]:
            n1 = Node(host["ip"])
            running = host["running"]
            for node in res.nodes:
                if node == n1:
                    node.running = running
                    if "scanned" in node.running:
                        if node.running["scanned"] == "true":
                            res.populated.add(node)
                        else:
                            res.unpopulated.add(node)
                    else:
                        res.unpopulated.add(node)
        return res

    def __str__(self):
         return str([(str(n1), str(n2)) for (n1, n2) in self.edges])
