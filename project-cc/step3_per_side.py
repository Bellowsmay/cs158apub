#!/usr/bin/env python3
"""Step 3: configure only ONE end of a link with params1 / params2.

    h1 --- s1 ==[loss on one side]== h2

Run:  sudo python3 step3_per_side.py --side s1   # loss on s1-eth2 (s1 -> h2)
      sudo python3 step3_per_side.py --side h2   # loss on h2-eth0 (h2 -> s1)
"""
import argparse
import os

from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.net import Mininet
from mininet.node import OVSBridge
from mininet.topo import Topo


class OneSidedLoss(Topo):
    def build(self, side='s1', loss=5):
        s1 = self.addSwitch('s1')
        h1 = self.addHost('h1', ip='10.0.0.1/24')
        h2 = self.addHost('h2', ip='10.0.0.2/24')
        self.addLink(h1, s1)

        # In addLink(a, b, params1=..., params2=...):
        #   params1 configures a's interface, params2 configures b's.
        # A qdisc only affects packets LEAVING its interface.
        lossy = dict(loss=loss, max_queue_size=50)
        if side == 's1':
            self.addLink(s1, h2, params1=lossy, params2={})   # s1-eth2 is lossy
        else:
            self.addLink(s1, h2, params1={}, params2=lossy)   # h2-eth0 is lossy


if __name__ == '__main__':
    setLogLevel('info')
    p = argparse.ArgumentParser()
    p.add_argument('--side', choices=['s1', 'h2'], default='s1',
                   help='which end of the s1-h2 link drops packets')
    p.add_argument('--loss', type=float, default=5, help='loss in percent')
    a = p.parse_args()

    net = Mininet(topo=OneSidedLoss(side=a.side, loss=a.loss),
                  link=TCLink, switch=OVSBridge, controller=None)
    net.start()
    net.get('h2').cmd('iperf3 -s -D')
    CLI(net)
    os.system('pkill -f "iperf3 -s"')
    net.stop()
