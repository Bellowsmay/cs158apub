import re
import matplotlib.pyplot as plt

#Note: only use the values that are greater than 186 (the control bytes_acked)
samples = []        #The list of samples (timestamp, cwnd, bytes acked)
sockets = []        #The list of sockets (cwnd, bytes acked) used to deiscern between data and control sockets
time_elapsed = 0.0  #Initialize just in case

def save_sample():
    #Once we have our socket and timestamp, save our sample to graph
    if sockets:
        #Each timestamp can have 2 sockets: data and control. Data has more bytes_acked
        data_socket = max(
            sockets,
            key=lambda s: s["bytes_acked"]
        )
        #create the sample with the timestamp and cwnd (and bytes_acked which we won't use anymore)
        samples.append({
            "timestamp": time_elapsed,
            **data_socket
        })

#with open("e1_b1_reno_t1_ss.txt", "r") as file:
with open("e1_b1_bbr_t1_ss.txt", "r") as file:
#with open("e1_b1_cubic_t1_ss.txt", "r") as file:
    #read the first line to get the first timestamp
    first_timestamp = float(file.readline().strip())
    #read each line int the file
    for line in file:
        line = line.strip()
        #find the timestamp. Even if the timestamp doesn't have a socket, it will be replaced by the most recent timestamp.
        if re.fullmatch(r"\d{10}\.\d+", line):
            save_sample()
            sockets = []    #clear socket list for the next timestamp so we don't pick old data/control sockets
            time_elapsed = float(line) - first_timestamp
        #find congestion window size
        cwnd = re.search(r"\bcwnd:(\d+)", line)
        #find the number of bytes acked
        acked = re.search(r"\bbytes_acked:(\d+)", line)
        #Once we find a cwnd (and subsequent bytes acked in the same line), group them as a socket. 
        if cwnd:
            sockets.append({
                #extract the cwnd
                "cwnd": int(cwnd.group(1)),
                #extract the bytes acked
                "bytes_acked": int(acked.group(1)) if acked else 0
            })
save_sample()

timestamps = [s["timestamp"] for s in samples]
cwnd_values = [s["cwnd"] for s in samples]
plt.plot(timestamps, cwnd_values)
plt.xlabel("Time (seconds)")
plt.ylabel("Congestion Window (packets)")
#plt.title("E1: Reno Congestion Window")
#plt.title("E1: Cubic Congestion Window")
plt.title("E1: BBR Congestion Window")
plt.show()