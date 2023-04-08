import socket
import threading
import time
import random
import pickle

class Node:
    def __init__(self, node_id, node_ip, node_port, group_members):
        self.id = node_id
        self.ip = node_ip
        self.port = node_port
        self.group_members = group_members
        self.sequence_number = 0
        self.buffer = []
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.ip, self.port))
        self.socket.listen()
        self.vectorclock = [0 for i in range(len(group_members))]
        self.n = 0
        random.seed(node_id)

    def send_message(self, message):
        self.vectorclock[self.id] += 1
        delay_time = random.randint(1, 10) # generate a random delay time
        # print('send', message, delay_time)
        time.sleep(delay_time)
        for i, member in enumerate(self.group_members):
            try:
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((member[0], member[1]))
                sendmessage = pickle.dumps((message,self.id, self.vectorclock))
                client_socket.send(sendmessage)
                client_socket.close()
            except:
                print("Failed to send message to node", member)

    def receive_message(self, message):
        delay_time = random.randint(1, 25) # generate a random delay time
        time.sleep(delay_time)
        message = pickle.loads(message)
        # print('recv', message[1], delay_time)
        
        for i in range(self.n):
            if message[2][i] > self.vectorclock[i] and i != message[1]:
                print('buffer',message[0],message[1],message[2],self.vectorclock)
                self.buffer.append(message)
                return
        if message[2][message[1]] == self.vectorclock[message[1]] + 1:
            print(message[0],message[1],message[2],self.vectorclock)
            for i in range(self.n):
                self.vectorclock[i] = max(self.vectorclock[i],message[2][i])
            self.get_next_message()
        else:
            print('buffer',message[0],message[1],message[2],self.vectorclock)
            self.buffer.append(message)
    
    def get_next_message(self):
        for message in self.buffer:
            for i in range(self.n):
                if message[2][i] > self.vectorclock[i] and i != message[1]:
                    # self.buffer.append((message[0],message[1],message[2]))
                    continue
            if message[2][message[1]] == self.vectorclock[message[1]] + 1:
                print(message[0],message[1],message[2],self.vectorclock)
                for i in range(self.n):
                    self.vectorclock[i] = max(self.vectorclock[i],message[2][i])
                self.buffer.remove(message)
                self.get_next_message()
                return message
        return None
    
    def run(self):
        print("Node", self.id, "is running.")
        while True:
            client_socket, address = self.socket.accept()
            message = client_socket.recv(1024)
            # print('run',message)
            client_socket.close()
            threading.Thread(target=self.receive_message, args=(message,)).start()
    
if __name__ == "__main__":
    # create a list of group members
    n = int(input('Enter number of Group members: '))
    port = int(input('Enter port number : '))
    group_members = []
    for i in range(n):
        group_members.append(["localhost",port+i])

    nodeId = int(input('Enter node id : '))

    node = Node(nodeId,"localhost",port+nodeId,group_members)
    node.n = n
    node.group_members = [m for m in group_members if m[1] != nodeId + port]
    print(node.group_members)
    # start all the nodes in separate threads
    threads = []
    thread = threading.Thread(target=node.run)
    thread.start()
    threads.append(thread)


    message = input('Enter send to send message : \n')
    for message in range(5):
        node.send_message(message)
    
    # wait for all the threads to complete
    for thread in threads:
        thread.join()

