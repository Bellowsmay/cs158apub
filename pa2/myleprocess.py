import uuid, socket, threading, time, json
BUFFER_SIZE = 59 #size of data to send
myUUID = uuid.uuid4() #create my process's uuid
leader_id: uuid.UUID
clientSocket = None
serverSocket = None
conn = None
leaderFound = 0 #If the leader is found flag
amLeader = 0 #If this process is the leader
logfile = "log1.txt" #File name for the log
config = "config.txt" #File name for the config

#The message format
class Message:
    def __init__(self, sender_uuid: uuid.UUID, flag: int):
        self.uuid = sender_uuid #The id of who sent the message
        self.flag = flag #If the leader has been elected or not. Default not

#method to thread for the server
def serverListen():
    global serverSocket, conn
    #read the IP and port from the config file. Should be first line
    with open(config, "r") as file:
        line = file.readline().strip()
    ip, port = line.split(",")
    serverAddress = (ip, int(port))
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #Create the socket
    serverSocket.bind(serverAddress) #Claim the IP and Port from the config file (should be first line)
    serverSocket.listen(1) #listen for client connections
    print('waiting for connection')
    conn, addr = serverSocket.accept() #accept the client connection and store the socket
    print('conn set')

#method to thread for the client
def clientConnect():
    global clientSocket
    #read the IP and port from the config file. Should be second line
    with open(config, "r") as file:
        file.readline() #Skip first line
        line = file.readline().strip()
    ip, port = line.split(",")
    serverAddress = (ip, int(port))
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #Create client socket
    #Repeatedly try to connect just in case server isn't up yet
    while True:
        try:
            clientSocket.connect(serverAddress)
            break
        except ConnectionRefusedError:
            print("Server not ready. Trying again...")
            time.sleep(1)

#Helper method to send a message from a given socket
def forward(sock, uuidToSend, leaderFlag):
    #send the message in json format
    message = Message(uuidToSend, leaderFlag);
    messageToSend = json.dumps({
        "uuid": str(message.uuid),
        "flag": message.flag
    })
    sock.send(messageToSend.encode())
    #log that we have sent a message
    with open(logfile, "a") as log:
        log.write(f"Sent: {message.uuid}, {message.flag}\n")

#write this process's UUID to the log
with open(logfile, "a") as log:
    log.write(f"ID:{myUUID}\n")

#start a new thread for the server to listen for clients
serverThread = threading.Thread(target = serverListen)
serverThread.start()

#start a new thread for the client to try to connect
clientThread = threading.Thread(target = clientConnect)
clientThread.start()

#Wait for sockets to find connections before continuing
clientThread.join()
serverThread.join()

#send the first message of just this process's uuid and leader found (default 0)
forward(clientSocket, myUUID, leaderFound)

#Repeatedly accept and forward messages while the leader isn't found
while(not leaderFound):
    #recieve message stream until }
    incomingMessage = ""
    while "}" not in incomingMessage:
        chunk = conn.recv(BUFFER_SIZE) #recieve chunk of message
        if not chunk: #Stop if we recieve empty chunk
            break
        incomingMessage += chunk.decode()
    messageReceived = json.loads(incomingMessage)
    receivedUUID = messageReceived["uuid"]
    receivedFlag = messageReceived["flag"]

    #If the incoming message found the leader, set the leader id
    if receivedFlag == 1:
        leaderFound = 1
        leader_id = uuid.UUID(receivedUUID)

    #Log that we recieved a message with the uuid comparison then forward if needed
    with open(logfile, "a") as log:
        log.write(f"Recieved: {receivedUUID }, Flag={receivedFlag}, ")
        #Ignore a message if the uuid is less than our's. Ends the ring
        if(myUUID > uuid.UUID(receivedUUID)):
            log.write("less, ")
            #Log our leader found flag
            log.write(f"{amLeader}\n")
            log.write("\tIgnore Message\n")
        #Forward the message if it has a greater uuid than our's
        elif(myUUID < uuid.UUID(receivedUUID)):
            log.write("more, ")
            #Log our leader found flag
            log.write(f"{amLeader}\n")
            forward(clientSocket, uuid.UUID(receivedUUID), receivedFlag)
        #If the message id is the same as our's, then we had the greatest id and are the leader
        else:
            log.write("same, ")
            leaderFound = 1
            amLeader = 1
            leader_id = myUUID
            #Log our leader found flag
            log.write(f"{amLeader}\n")
            forward(clientSocket, leader_id, leaderFound)
        if(leaderFound):
            log.write(f"Leader is decided to:{leader_id}\n")

#Print the leader to console
print(f"Leader is {leader_id}")









