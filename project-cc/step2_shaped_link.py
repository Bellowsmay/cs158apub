#!/usr/bin/env python3
"""Step 2: shape a link with TCLink (bandwidth + delay).

    h1 ==[bw, delay]== s1 --- h2

Run:  sudo python3 step2_shaped_link.py [--bw 10] [--delay 5ms]
"""
import argparse
import os

from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.net import Mininet
from mininet.node import OVSBridge
from mininet.topo import Topo


class ShapedPath(Topo):
    def build(self, bw=10, delay='5ms'):
        s1 = self.addSwitch('s1')
        h1 = self.addHost('h1', ip='10.0.0.1/24')
        h2 = self.addHost('h2', ip='10.0.0.2/24')
        # TCLink options apply to BOTH ends of the link (h1-eth0 and s1-eth1),
        # so the delay is added once in each direction.
        self.addLink(h1, s1, bw=bw, delay=delay)
        self.addLink(h2, s1)


if __name__ == '__main__':
    setLogLevel('info')
    p = argparse.ArgumentParser()
    p.add_argument('--bw', type=float, default=10, help='link rate in Mbps')
    p.add_argument('--delay', default='5ms', help='one-way delay, e.g. 5ms')
    a = p.parse_args()

    net = Mininet(topo=ShapedPath(bw=a.bw, delay=a.delay),
                  link=TCLink, switch=OVSBridge, controller=None)
    net.start()
    # node.cmd() runs a shell command on that node.
    # iperf3 -s runs iperf3 in server mode. It listens on TCP port 5201 and waits for a client.
    # -D runs it as a daemon in the background
    net.get('h2').cmd('iperf3 -s -D')
    CLI(net)
    os.system('pkill -f "iperf3 -s"')
    net.stop()
