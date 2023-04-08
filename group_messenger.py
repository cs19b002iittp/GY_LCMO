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
        self.timestamp = 0
        self.buffer = []
        self.holdback_queue = []
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.ip, self.port))
        self.socket.listen()
        self.vectorclock = [0 for i in range(len(group_members))]

    def send_message(self, message):
        self.vectorclock[self.id] += 1
        for i, member in enumerate(self.group_members):
            try:
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((member[0], member[1]))
                sendmessage = pickle.dumps((message,self.id, self.vectorclock[self.id]))
                client_socket.send(sendmessage)
                client_socket.close()
            except:
                print("Failed to send message to node", member)

    def receive_message(self, message):
        delay_time = random.randint(1, 5) # generate a random delay time
        time.sleep(delay_time)
        msg,id,seqnum = pickle.loads(message)
        if self.vectorclock[id]+1 == seqnum:
            print(msg,id,seqnum,self.vectorclock)
            self.vectorclock[id] += 1
            self.get_next_message()
        else:
            print('buffer',msg,id,seqnum,self.vectorclock)
            self.buffer.append((msg,id,seqnum))
        #print(receivemessage)
        # self.handle_message(message)

    def handle_message(self, message):
        message_parts = message.split(";")
        message_type = message_parts[0]
        sender_id = int(message_parts[1])
        message_content = message_parts[2]
        if message_type == "MSG":
            self.handle_group_message(sender_id, message_content)
        elif message_type == "TS":
            self.handle_timestamp(sender_id, message_content)

    def handle_group_message(self, sender_id, message_content):
        message_sequence_number = self.sequence_number
        self.sequence_number += 1
        message = "MSG;" + str(sender_id) + ";" + str(message_sequence_number) + ";" + message_content
        self.send_message(message)

    def handle_timestamp(self, sender_id, message_content):
        timestamp_parts = message_content.split(",")
        message_timestamp = int(timestamp_parts[0])
        message_sequence_number = int(timestamp_parts[1])
        self.timestamp = max(self.timestamp, message_timestamp) + 1
        self.buffer.append((sender_id, message_sequence_number, message_content))
        self.deliver_messages()
    
    def deliver_messages(self):
        while len(self.buffer) > 0:
            next_message = self.get_next_message()
            if next_message is None:
                break
            sender_id, message_sequence_number, message_content = next_message
            message_timestamp = message_content.split(",")[0]
            if int(message_timestamp) == self.timestamp:
                self.timestamp += 1
                self.handle_group_message(sender_id, message_content.split(",")[1])
            else:
                self.holdback_queue.append(next_message)
    
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

