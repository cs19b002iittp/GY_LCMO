#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <pthread.h>
#include <signal.h>
#include <errno.h>

#define PORT 8888
#define MAX_CLIENTS 10
#define MAX_MESSAGE_LENGTH 256

struct message {
    int sender_id;
    int timestamp;
    char text[MAX_MESSAGE_LENGTH];
};

struct client {
    int id;
    int socket;
    int *lamport_clock;
    int message_queue_size;
    struct message **message_queue;
};

struct client clients[MAX_CLIENTS];
int client_count;
pthread_mutex_t client_mutex = PTHREAD_MUTEX_INITIALIZER;
pthread_mutex_t message_mutex = PTHREAD_MUTEX_INITIALIZER;
int use_fifo = 0;
int running = 1;

void handle_sigint(int sig) {
    running = 0;
}

void *client_handler(void *arg) {
    int client_id = *(int *) arg;
    free(arg);
    struct client *client = &clients[client_id];

    // Receive messages from client and broadcast them to all other clients
    while (running) {
        struct message *msg = (struct message *) malloc(sizeof(struct message));
        int n = recv(client->socket, msg, sizeof(struct message), 0);
        if (n <= 0) {
            // Client disconnected or error occurred
            printf("Client %d disconnected\n", client_id);
            close(client->socket);
            // Remove client from client list
            pthread_mutex_lock(&client_mutex);
            for (int i = client_id; i < client_count - 1; i++) {
                clients[i] = clients[i + 1];
            }
            client_count--;
            pthread_mutex_unlock(&client_mutex);
            break;
        }

        // Update Lamport clock
        pthread_mutex_lock(&client_mutex);
        *(client->lamport_clock) = (*(client->lamport_clock) > msg->timestamp) ? *(client->lamport_clock) + 1 : msg->timestamp + 1;
        msg->timestamp = *(client->lamport_clock);
        pthread_mutex_unlock(&client_mutex);

        // Add message to queue
        pthread_mutex_lock(&message_mutex);
        client->message_queue[client->message_queue_size++] = msg;
        pthread_mutex_unlock(&message_mutex);

        // Broadcast message to all clients
        for (int i = 0; i < client_count; i++) {
            if (use_fifo) {
                // Send message after delay with FIFO ordering
                pthread_t thread_id;
                int *delay_ptr = (int *) malloc(sizeof(int));
                *delay_ptr = abs(i - client_id);
                pthread_create(&thread_id, NULL, usleep, delay_ptr);
                pthread_detach(thread_id);
                send(clients[i].socket, msg, sizeof(struct message), 0);
            } else {
                // Send message immediately with total ordering
                send(clients[i].socket, msg, sizeof(struct message), 0);
            }
        }
    }

    return NULL;
}

void start_client_threads() {
    // Start client threads
    for (int i = 0; i < client_count; i++) {
        int *client_id_ptr = (int *) malloc(sizeof(int));
        *client_id_ptr = i;
        pthread_t thread_id;
        pthread_create(&thread_id, NULL, client_handler, client_id_ptr);
        pthread_detach(thread_id);
    }
}

void print_message_queue() {
pthread_mutex_lock(&message_mutex);
printf("Message queue:\n");
for (int i = 0; i < client_count; i++) {
struct client *client = &clients[i];
printf("Client %d message queue:\n", client->id);
for (int j = 0; j < client->message_queue_size; j++) {
struct message *msg = client->message_queue[j];
printf(" Sender ID: %d, Timestamp: %d, Text: %s\n", msg->sender_id, msg->timestamp, msg->text);
}
}
pthread_mutex_unlock(&message_mutex);
}

int main() {
// Initialize client list
client_count = 0;
// Initialize Lamport clocks for each client
int lamport_clocks[MAX_CLIENTS] = {0};

// Create server socket
int server_socket = socket(AF_INET, SOCK_STREAM, 0);
if (server_socket < 0) {
    perror("socket() failed");
    exit(EXIT_FAILURE);
}

// Bind server socket to port
struct sockaddr_in server_addr;
server_addr.sin_family = AF_INET;
server_addr.sin_addr.s_addr = INADDR_ANY;
server_addr.sin_port = htons(PORT);
if (bind(server_socket, (struct sockaddr *) &server_addr, sizeof(server_addr)) < 0) {
    perror("bind() failed");
    exit(EXIT_FAILURE);
}

// Listen for incoming connections
if (listen(server_socket, 5) < 0) {
    perror("listen() failed");
    exit(EXIT_FAILURE);
}

// Handle SIGINT to gracefully exit program
signal(SIGINT, handle_sigint);

printf("Server listening on port %d\n", PORT);

// Accept incoming connections
while (running) {
    struct sockaddr_in client_addr;
    socklen_t client_addr_len = sizeof(client_addr);
    int client_socket = accept(server_socket, (struct sockaddr *) &client_addr, &client_addr_len);
    if (client_socket < 0) {
        if (errno == EINTR) {
            continue;
        }
        perror("accept() failed");
        exit(EXIT_FAILURE);
    }

    // Add new client to client list
    pthread_mutex_lock(&client_mutex);
    struct client *client = &clients[client_count++];
    client->id = client_count - 1;
    client->socket = client_socket;
    client->lamport_clock = &lamport_clocks[client->id];
    client->message_queue_size = 0;
    client->message_queue = (struct message **) malloc(sizeof(struct message *) * MAX_CLIENTS);
    pthread_mutex_unlock(&client_mutex);

    // Start client threads
    start_client_threads();
}

// Close sockets and free memory
close(server_socket);
for (int i = 0; i < client_count; i++) {
    close(clients[i].socket);
    for (int j = 0; j < clients[i].message_queue_size; j++) {
        free(clients[i].message_queue[j]);
    }
    free(clients[i].message_queue);
}

return 0;
}
