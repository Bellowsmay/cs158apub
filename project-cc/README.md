# Mininet Hands-On

| Step | Script | You learn |
|---|---|---|
| 0 | – | Check your `mininet` setup is ready |
| 1 | `step1_basic.py` | Topology class, hosts, switches, links, interface names, the `mininet>` CLI |
| 2 | `step2_shaped_link.py` | `TCLink`: bandwidth and delay, and how to verify them |
| 3 | `step3_per_side.py` | `params1` / `params2`: configuring only one end of a link |
| 4 | (reuses step 2) | Running one trial: the `ss` sampler + `iperf3`, and reading their output |
| – | – | Wrap-up: from here to `dumbbell.py` |

## Before class
- Mininet runs on Linux only. If you use macOS or Windows, use [Multipass](https://canonical.com/multipass) to run an Ubuntu VM. From your own machine, in this directory:
  ```bash
  multipass launch --name cc --cpus 2 --memory 4G --disk 10G                     # create the VM
  multipass transfer step1_basic.py step2_shaped_link.py step3_per_side.py cc:   # copy this directory's scripts into the VM
  multipass shell cc                                                             # open a shell inside it
  ```
- Inside the Ubuntu VM, install the tools and load BBR:
  ```bash
  sudo apt update
  sudo apt install mininet openvswitch-switch iperf3 ethtool
  sudo modprobe tcp_bbr                                # load the BBR kernel module (Reno and CUBIC are built in)
  sysctl net.ipv4.tcp_available_congestion_control    # must list reno cubic bbr
  ```
- **Apple Silicon Macs only: keep the VM's CPUs awake.** When a VM CPU goes idle, macOS wakes it late, so Mininet's delays fire tens of milliseconds late. Before using Mininet, open a second VM shell (`multipass shell cc`), run this, and leave that shell open:
  ```bash
  for i in $(seq $(nproc)); do chrt -i 0 sh -c 'while :; do :; done' & done   # one busy loop per VM CPU
  ```
  `chrt -i 0` runs the loops at the lowest scheduling priority, so they only use CPU time that nothing else wants. Stop them with `pkill -f 'while :'` when you are done.

---

## Step 0: Check your VM
Inside the VM:
```bash
ls                                                   # the three step*.py files
sudo mn -c                                           # clean up anything left from earlier runs
```
`sudo mn -c` is the command to remember. **Whenever a Mininet script crashes, run it before trying again.**

---

## Step 1: Your first topology
```
h1 --- s1 --- h2
```
Open `step1_basic.py` and read it. It has three parts:
1. A `Topo` subclass whose `build()` adds a switch, two hosts with fixed IP addresses, and two links.
2. `Mininet(topo=..., switch=OVSBridge, controller=None)`, which creates the network. `OVSBridge` with no controller is a plain learning switch, which is all we need.
3. `net.start()`, `CLI(net)` (the interactive prompt), and `net.stop()`.

Run it:
```bash
sudo python3 step1_basic.py
```
Try these at the `mininet>` prompt:
```
mininet> nodes                  # all hosts and switches
mininet> net                    # who is connected to whom, through which interface
mininet> h1 ip addr show h1-eth0
mininet> h1 ping -c 3 h2        # the CLI replaces "h2" with h2's IP address
mininet> pingall
mininet> exit
```
- A line that starts with a host name runs the rest of the line **on that host**. Each host has its own network interfaces, but all hosts share the VM's files.
- **Interface names come from the order you add links.** In `net`, `h1` is on `s1-eth1` and `h2` on `s1-eth2`, because the `h1` link was added first. The dumbbell template relies on this: the bottleneck must be the first link so that it becomes `s1-eth1`.

---

## Step 2: Shape a link with `TCLink`
```
h1 ==[bw, delay]== s1 --- h2
```
In `step2_shaped_link.py`, the only new parts are `link=TCLink` in `Mininet(...)` and the options on the first link:
```python
self.addLink(h1, s1, bw=bw, delay=delay)
```
Run it with a 10 Mbps, 5 ms link:
```bash
sudo python3 step2_shaped_link.py --bw 10 --delay 5ms
```

**Predict first, then measure.** Write down your predictions for the RTT and the throughput, then run:
```
mininet> h1 ping -c 5 10.0.0.2
mininet> h1 iperf3 -c 10.0.0.2 -t 5
```
Expected:
- **RTT ≈ 10 ms, not 5 ms.** `TCLink` applies the options to **both ends** of the link, so the 5 ms delay is added once on the way out (`h1-eth0`) and once on the way back (`s1-eth1`). In general, `RTT = 2 × delay`. Ignore the first ping, which also waits for ARP.
  - The other RTTs should be nearly identical (e.g. all 10.1 ms). If they jump around between 10 and 50 ms, your VM's CPUs are going idle: on an Apple Silicon Mac, start the CPU loops from **Before class**.
- **Throughput ≈ 9.5 Mbps.** That is the 10 Mbps rate minus packet headers. Read it from the **`receiver`** line of the final summary. The per-second lines are measured at the sender, which can get ahead of the link, so a few of them may read above 10 Mbps.

See how Mininet implemented it:
```
mininet> h1 tc qdisc show dev h1-eth0
```
- `htb` is the rate limiter (the `bw`), and `netem` adds the `delay`. Its `limit` is the queue size in **packets**. Here it is netem's default, 1000, because we did not set `max_queue_size`.

**Exercise.** `exit`, restart with `--delay 20ms`, and check that the RTT is now about 40 ms.

---

## Step 3: Configure only one end with `params1` / `params2`
```
h1 --- s1 ==[loss on one side]== h2
```
Options passed directly to `addLink` apply to both ends, as in Step 2. To configure **only one end**, pass a dictionary for each end:
```python
self.addLink(s1, h2, params1=lossy, params2={})   # params1 -> s1's end (s1-eth2), params2 -> h2's end (h2-eth0)
```
A queue (qdisc) only affects packets **leaving** its interface. So the lossy end decides which direction loses packets.

Run it with 5% loss on `s1`'s end. This drops data going from `h1` to `h2`:
```bash
sudo python3 step3_per_side.py --side s1
```
```
mininet> sh tc qdisc show dev s1-eth2    # netem with loss 5% and limit 50
mininet> h2 tc qdisc show dev h2-eth0    # no netem: this end is untouched
mininet> h1 ping -c 50 -i 0.2 10.0.0.2
mininet> h1 iperf3 -c 10.0.0.2 -t 5      # note the Retr (retransmissions) column
mininet> exit
```
Now put the loss on `h2`'s end. This drops the ACKs going back from `h2` to `h1` instead:
```bash
sudo python3 step3_per_side.py --side h2
```
Run the same `ping` and `iperf3` commands and compare:
- **`ping` loses about 5% both times.** A ping needs both the request and the reply, so it can't tell which direction drops packets. Check the statistics.
- **`iperf3` is very different.** With `--side s1`, data packets are lost: you see many retransmissions and much lower throughput. With `--side h2`, only ACKs are lost, and TCP barely notices because the next ACK covers the lost one.
- Check `Retr` and the smaller `Cwnd` compared to the previous cases without losses.
- `max_queue_size=50` shows up as `limit 50`. That is how you set the buffer `B` (in packets).

---

## Step 4: Run one trial and read the output
Restart Step 2's network:
```bash
sudo python3 step2_shaped_link.py --bw 10 --delay 5ms
```
A trial is two commands: start the sampler in the background, then run the flow.
```
mininet> h1 timeout 25 sh -c 'while :; do date +%s.%N; ss -tin dst 10.0.0.2:5201; sleep 0.01; done' > demo_ss.txt &
mininet> h1 iperf3 -c 10.0.0.2 -C cubic -t 20 -i 0.5 -J --logfile demo.json
```

**Line 1: the sampler**

| Part | Meaning |
|---|---|
| `h1` | Run the rest of the line on host `h1`, the sender |
| `timeout 25` | Kill the command after 25 s, so the sampler stops on its own a few seconds after the 20 s flow ends |
| `sh -c '...'` | Run the quoted text as a small shell script |
| `while :; do ...; done` | Loop forever (`:` always succeeds); `timeout` ends it |
| `date +%s.%N` | Print the current time in seconds with nanoseconds, e.g. `1760000000.123456789`. This is the timestamp before each sample |
| `ss -tin` | Print TCP sockets (`-t`) with internal info such as cwnd and RTT (`-i`), using numeric addresses (`-n`) |
| `dst 10.0.0.2:5201` | Only the connections going to the `iperf3` server on `h2` (port 5201) |
| `sleep 0.01` | Wait 10 ms before the next sample |
| `> demo_ss.txt` | Save everything to `demo_ss.txt` instead of printing it |
| `&` | Run in the background, so the prompt returns and you can type line 2 right away |

**Line 2: the flow**

| Part | Meaning |
|---|---|
| `h1 iperf3 -c 10.0.0.2` | Run `iperf3` as a client on `h1` and connect to the server at `10.0.0.2` (`h2`) |
| `-C cubic` | Use CUBIC congestion control for this connection (`reno`, `cubic`, or `bbr`) |
| `-t 20` | Send for 20 s |
| `-i 0.5` | Report throughput every 0.5 s |
| `-J` | Write the report as JSON, which is easy to parse in Python |
| `--logfile demo.json` | Save the report to `demo.json` instead of printing it |

Line 2 runs in the foreground, so the prompt returns when the flow ends. When it does, look at what you recorded:
```
mininet> sh head -20 demo_ss.txt
mininet> sh grep -o 'cwnd:[0-9]*' demo_ss.txt | head -40
mininet> sh python3 -c "import json; d = json.load(open('demo.json')); print([round(i['sum']['bits_per_second'] / 1e6, 1) for i in d['intervals']])"
mininet> exit
```
- `demo_ss.txt` holds a timestamp line, then the `ss` output: `cwnd:` (packets), `rtt:` (ms), `bytes_acked:`, and more.
- **Each sample shows two connections.** `iperf3` opens a control connection to port 5201 next to the data connection. The data connection is the one with the much larger `bytes_acked:`. Only its cwnd is interesting.
- `demo.json` holds one throughput value per 0.5 s interval, which the last command prints in Mbps.
