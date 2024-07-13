#pragma once

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <errno.h>
#include <pthread.h>

#include "parse_request.h"
#include "list.h"

int get(Request *R, list_t *ll, pthread_mutex_t *lock, int socket_fd);

int put(Request *R, list_t *ll, pthread_mutex_t *lock, char *buf, int socket_fd);
