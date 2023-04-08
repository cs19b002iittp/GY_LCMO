import socket
import threading
import time
import random
import pickle

class Node:
    def __init__(self, node_ip, node_port, group_members):
        self.ip = node_ip
        self.port = node_port
        self.group_members = group_members
        self.sequence_number = 0
        self.timestamp = 0
        self.buffer = []
        self.holdback_queue = []
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.ip, self.port))
        self.socket.listen()
        self.vectorclock = [0 for i in range(len(group_members)+1)]

    def receive_message(self, message):
        delay_time = random.randint(1, 15) # generate a random delay time
        time.sleep(delay_time)
        msg,id = pickle.loads(message)
        self.sequence_number += 1
        for i, member in enumerate(self.group_members):
            try:
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((member[0], member[1]))
                sendmessage = pickle.dumps((msg, id, self.sequence_number))
                client_socket.send(sendmessage)
                client_socket.close()
            except:
                print("Failed to send message to node", member)
    
    def get_next_message(self):
        for message in self.buffer:
            if message[2] == self.vectorclock[message[1]] + 1:
                self.vectorclock[message[1]] += 1
                self.buffer.remove(message)
                print(message[0],message[1],message[2],self.vectorclock)
                self.get_next_message()
                return message
        return None
    
    def run(self):
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

    node = Node("localhost",port+n,group_members)
    node.run()