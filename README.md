![ ](https://travis-ci.org/cyberImperial/attack-graphs.svg?branch=master) [![Coverage Status](https://coveralls.io/repos/github/cyberImperial/attack-graphs/badge.svg?branch=master)](https://coveralls.io/github/cyberImperial/attack-graphs?branch=master)

# Attack-graphs

### Description

Attack graphs illustrate ways in which an adversary can exploit vulnerabilities to break into a system. System administrators evaluate attack graphs to find where their system’s weaknesses might be and to decide which security measures should be taken in order to defend their systems.

Our product helps security administrators reason about the risk posed to the various system components and to evaluate adversarial and defense strategies when signs of compromise have been found. For the future, this tool should be made available to anyone who wants to monitor and solve network vulnerability issues.

### Install
To install the dependecies:
```
apt-get install libboost-all-dev -y
apt-get install libpcap-dev -y
apt-get install libpq-dev -y
sudo python3 setup.py install
make
npm install
cd database && python3 load.py -r
```

Run tests:
```
make test
sudo python3 setup.py test
```

The inference engine depends on `mulval`. Please follow the instructions for installation from [here](http://people.cs.ksu.edu/~xou/mulval/). To run the inference engine, you need to set the following path variables: (in case they are not set, the module will try some default paths)
```
MULVALROOT=<mulval_path>
XSB_DIR=<xsb_path>
```

### Running the main application

The package needs elevated privileges as it runs the NIC in promiscuous mode.


Running a master node:
```
sudo python3 service.py master
```

Running a slave node:
```
sudo python3 service.py slave [master-ip]
``` 

Package options:
```
usage: service.py [-h] [-m MASTER] [-p PORT] [-i INTERFACE] [-s SIMULATION]
                  [-f FILTER] [-v] [-b] [-t BATCH_THREADS]
                  type

positional arguments:
  type                  The type of node run: 'master' or 'slave'

optional arguments:
  -h, --help            show this help message and exit
  -m MASTER, --master MASTER
                        Specify master IP for connecting a slave.
  -p PORT, --port PORT  Specify port for runnning a slave.
  -i INTERFACE, --interface INTERFACE
                        The network interface listened to.
  -s SIMULATION, --simulation SIMULATION
                        To run a simulated network from a network
                        configuration file use this flag.
  -f FILTER, --filter FILTER
                        Specify a mask for filtering the packets. (e.g.
                        '10.1.1.1/16' would keep packets starting with '10.1')
  -v, --verbose         Set the logging level to DEBUG.
  -b, --benchmark       Disables database and inference engine for
                        benchmarking.
  -t BATCH_THREADS, --batch_threads BATCH_THREADS
                        Number of threads that should run host discovery. (default is single-threaded)
```

Running on a simulated network:
```
sudo python3 service.py master -s [simulation-config]
```

The configuration files for the simulated network should be placed inside the folder `simulation/confs`. The simulation module looks only for the files inside `simulation/confs`. For an example configuration see [simulation/confs/simple.json](https://github.com/cyberImperial/attack-graphs/blob/master/simulation/confs/simple.json):
```
sudo python3 service.py master -s simple.json
```

### Python CLI

Once the main application is running you can try to use individual component using interactive Python cli:
```
python3 service/cli.py
```

CLI options:
```
  -h, --help            show this help message and exit
  --echo ECHO [ECHO ...]
                        Usual echo command.
  --exit                Exit.
  --quit                Exit.
  --gen                 Send a request to the inference engine.
  --vul VUL VUL         Send a request to the database service for a
                        vulnerability. The first argument is the product. The
                        second argument is the version.
  --priv PRIV PRIV      Send a request to the database service for privilege
                        level escalation for a vulnerability. The first
                        argument is the product. The second argument is the
                        version. (e.g. `priv windows_2000 *`)
  --graph               Send a request to the local graph service.
  --packet              Send a request to the local sniffer service.
```

### Benchmarks

To run benchmarks:
```
sudo python3 simulation/benchmarks.py
```

The simulations are run on random overlay topologies with fixed number of nodes and edges. Random packets get generated whenever the simulation module connection gets a call within a fixed timeout of 0.5 seconds, whereas the scans are generated within a timeout of 3 seconds.

Results of the simulations can be found in the folder `simulation/res` and were generated on a single machine.  

### Front-end

Staring the graphical user interface:
```
npm start
```
