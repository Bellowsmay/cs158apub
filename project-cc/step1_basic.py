#!/usr/bin/env python3
"""Step 1: the smallest useful Mininet script.

    h1 --- s1 --- h2

Run:  sudo python3 step1_basic.py
"""
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.net import Mininet
from mininet.node import OVSBridge
from mininet.topo import Topo


class TwoHosts(Topo):
    def build(self):
        s1 = self.addSwitch('s1')
        h1 = self.addHost('h1', ip='10.0.0.1/24')
        h2 = self.addHost('h2', ip='10.0.0.2/24')
        self.addLink(h1, s1)    # first link on s1  -> s1-eth1
        self.addLink(h2, s1)    # second link on s1 -> s1-eth2


if __name__ == '__main__':
    setLogLevel('info')
    # OVSBridge + controller=None: a plain learning switch, no OpenFlow controller
    net = Mininet(topo=TwoHosts(), switch=OVSBridge, controller=None)
    net.start()
    CLI(net)        # the mininet> prompt; type exit to leave
    net.stop()
