#include <pthread.h>

#include "parse_request.h"
#include "asgn2_helper_funcs.h"
#include "status_code.h"
#include "process_request.h"
#include "queue.h"
#include "list.h"

#define BUFF_SIZE 4096

int InvalidPort(void) {
    fprintf(stderr, "Invalid Port\n");
    exit(1);
}

queue_t *q;
list_t *ll;
pthread_mutex_t lock;

void *handle_request() {
    char buffer[BUFF_SIZE];
    while (1) {
        uintptr_t socket_fd;
        //uintptr_t *socket_fdt;
        queue_pop(q, (void **) &socket_fd);
        //socket_fd = *socket_fdt;                // TA Pratik

        //fprintf(stderr, "socket id popped: %lu\n", socket_fd);
        // printf("socket id popped: %d\n", (int) socket_fd);

        //pthread_mutex_lock(&outlock);
        ssize_t bytesRead = read_until(socket_fd, buffer, sizeof(buffer), "\r\n\r\n");
        //fprintf(stderr, "bytes read: %zd\n", bytesRead);
        //fprintf(stderr, "buffer: %s\n", buffer);

        if (bytesRead == -1) {
            if (errno == EWOULDBLOCK && errno == EAGAIN) {
                // error due to timeout
                WriteStatusCode(socket_fd, 400);
                //printf("closing for timeout");
                close(socket_fd);
                //pthread_mutex_unlock(&outlock);
                continue;
            } else {
                //printf("closing for internal error\n");
                WriteStatusCode(socket_fd, 500);
                close(socket_fd);
                //pthread_mutex_unlock(&outlock);
                continue;
            }
        }
        // fprintf(stderr, "before parse\n");
        //buffer[bytesRead] = '\0';

        Request R;
        int rc = parse_input(&R, buffer, socket_fd);
        if (rc == -1) {
            //printf("parsing failed\n");
            close(socket_fd);
            //pthread_mutex_unlock(&outlock);
            continue;
        }

        R.current_read_bytes = bytesRead - R.start_content;
        //fprintf(stderr, "current bytes read from message body: %ld\n", bytesRead - R.start_content);
        //pthread_mutex_lock(&outlock);
        if (strcmp(R.command, "GET") == 0) {
            if (R.current_read_bytes > 0) {
                WriteStatusCode(socket_fd, 400);
                close(socket_fd);
                //pthread_mutex_unlock(&outlock);
                continue;
            }
            //printf("command was a get at the server\n");

            int rc = get(&R, ll, &lock, socket_fd);
            if (rc == -1) {
                close(socket_fd);
                //pthread_mutex_unlock(&outlock);
                continue;
            }
        } else if (strcmp(R.command, "PUT") == 0) {
            //printf("command was a put at the server\n");
            if (R.content_length == -1) {
                WriteStatusCode(socket_fd, 400);
                close(socket_fd);
                //pthread_mutex_unlock(&outlock);
                continue;
            }
            //printf("sending to put method\n");
            int rc = put(&R, ll, &lock, buffer, socket_fd);
            if (rc == -1) {
                close(socket_fd);
                //pthread_mutex_unlock(&outlock);
                continue;
            }
        } else {
            WriteStatusCode(socket_fd, 501);
            close(socket_fd);
            //pthread_mutex_unlock(&outlock);
            continue;
        }
        //fprintf(stderr, "closing");
        //pthread_mutex_unlock(&outlock);
        close(socket_fd);
    }
}

int main(int argc, char *argv[]) {
    int opt;
    int threads = 4; // Default number of threads
    q = queue_new(500);
    ll = list_create();
    pthread_mutex_init(&lock, NULL);

    // Process command-line options
    while ((opt = getopt(argc, argv, "t:")) != -1) {
        switch (opt) {
        case 't':
            threads = atoi(optarg);
            if (threads <= 0) {
                //fprintf(stderr, "Number of threads must be positive.\n");
                exit(EXIT_FAILURE);
            }
            break;
        default:
            //fprintf(stderr, "Usage: %s [-t threads] <port>\n", argv[0]);
            exit(EXIT_FAILURE);
        }
    }

    if (optind >= argc) {
        //fprintf(stderr, "Expected port number after threads\n");
        exit(EXIT_FAILURE);
    }

    //checking if port number was valid number
    char *endptr = NULL;
    uint port = strtol(argv[optind], &endptr, 10);
    if (endptr == argv[1] || *endptr != '\0') {
        InvalidPort();
    }

    // check if port is in valid range??
    if (port < 1 || port > 65535) {
        //printf("range\n");
        InvalidPort();
    }

    //fprintf(stdout, "threads: %d\n", threads);
    //fprintf(stdout, "port: %d\n", port);

    //printf("port: %d\n", port);

    pthread_t worker_thread[threads];

    // creating the worker threads
    for (int i = 0; i < threads; i++) {
        pthread_create(&worker_thread[i], NULL, handle_request, NULL);
    }

    Listener_Socket socket;
    int init_socket = listener_init(&socket, port);

    if (init_socket == -1) {
        //printf("could not initialize\n");
        InvalidPort();
    }

    while (1) {
        uintptr_t socket_fd = listener_accept(&socket);
        //fprintf(stderr, "socket: %d\n", (int)socket_fd);
        //fprintf(stderr, "1: %lu\n", (uintptr_t) -1);
        if ((int) socket_fd == -1) {
            close(socket_fd);
            continue;
        }

        //fprintf(stderr, "socket id pushed: %lu\n", socket_fd);
        queue_push(q, (void *) socket_fd);
    }
    queue_delete(&q);
    list_destroy(&ll);
    pthread_mutex_destroy(&lock);
    return 0;
}
