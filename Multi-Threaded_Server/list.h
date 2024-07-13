#pragma once

#include <stdlib.h>
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <assert.h>
#include <pthread.h>

#include "rwlock.h"

typedef struct NodeObj node;
typedef struct List list_t;

typedef struct NodeObj {
    char *uri; //key
    rwlock_t *rwlock; //val
    node *next;
} NodeObj;

typedef struct List {
    node *head; // Assuming 'node' is properly defined somewhere
} list_t;

node *node_create(char *uri);

void free_node(node **item);

list_t *list_create();

void list_destroy(list_t **ll);

rwlock_t *ll_lookup(list_t *ll, char *uri);
