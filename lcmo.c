#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/ipc.h>
#include <sys/shm.h>

#define MAX_MESSAGES 100
#define MAX_DELAY 5

typedef struct message {
    int sender_id;
    int timestamp;
    char content[256];
} message_t;

int group_size;
int shmid;
message_t *messages;

void* node_function(void* arg) {
    int node_id = *(int*)arg;
    int i;
    int delay;
    message_t msg;

    for (i = 0; i < MAX_MESSAGES; i++) {
        // Wait for a random amount of time
        delay = rand() % MAX_DELAY;
        sleep(delay);

        // Generate a message
        msg.sender_id = node_id;
        msg.timestamp = i;
        sprintf(msg.content, "Message %d from node %d", i, node_id);

        // Add the message to the shared memory space
        messages[i] = msg;

        // Wait for all messages up to this one to be delivered
        while (messages[i-1].timestamp != i-1);

        // Deliver the message to the group
        printf("Node %d delivered message %d: %s\n", node_id, i, msg.content);
    }

    return NULL;
}

int main(int argc, char* argv[]) {
    int i;
    pthread_t *threads;
    int *node_ids;

    if (argc != 2) {
        printf("Usage: %s group_size\n", argv[0]);
        return 1;
    }

    // Initialize the shared memory space
    group_size = atoi(argv[1]);
    shmid = shmget(IPC_PRIVATE, MAX_MESSAGES * sizeof(message_t), 0666 | IPC_CREAT);
    messages = (message_t*)shmat(shmid, NULL, 0);

    // Create threads for each node in the group
    threads = malloc(group_size * sizeof(pthread_t));
    node_ids = malloc(group_size * sizeof(int));
    for (i = 0; i < group_size; i++) {
        node_ids[i] = i;
        pthread_create(&threads[i], NULL, node_function, &node_ids[i]);
    }

    // Wait for all threads to finish
    for (i = 0; i < group_size; i++) {
        pthread_join(threads[i], NULL);
    }

    // Clean up the shared memory space
    shmdt(messages);
    shmctl(shmid, IPC_RMID, NULL);

    return 0;
}
