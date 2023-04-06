import socket
import threading
import time
import random

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

    def send_message(self, message):
        for member in self.group_members:
            if member != self.id:
                try:
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.connect((member.ip, member.port))
                    client_socket.send(message.encode())
                    client_socket.close()
                except:
                    print("Failed to send message to node", member)

    def receive_message(self, message):
        delay_time = random.randint(1, 5) # generate a random delay time
        print("Message received at node", self.id, "with delay of", delay_time)
        time.sleep(delay_time)
        self.handle_message(message)

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
            if message[1] == self.sequence_number:
                self.sequence_number += 1
                self.buffer.remove(message)
                return message
        return None
    
    def run(self):
        print("Node", self.id, "is running.")
        while True:
            client_socket, address = self.socket.accept()
            message = client_socket.recv(1024).decode()
            client_socket.close()
            threading.Thread(target=self.receive_message, args=(message,)).start()
    
if __name__ == "__main__":
    # create a list of group members
    group_members = [
    Node(0, "localhost", 5000, []),
    Node(1, "localhost", 5001, []),
    Node(2, "localhost", 5002, []),
    Node(3, "localhost", 5003, [])
    ]
    for node in group_members:
        node.group_members = [m for m in group_members if m != node]
    # start all the nodes in separate threads
    threads = []
    for node in group_members:
        thread = threading.Thread(target=node.run)
        thread.start()
        threads.append(thread)
    
    # wait for all the threads to complete
    for thread in threads:
        thread.join()

