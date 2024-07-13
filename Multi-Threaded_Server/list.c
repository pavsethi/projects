#include <stdlib.h>
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <assert.h>

#include "rwlock.h"
#include "list.h"

pthread_mutex_t listLock;

// Function to create a new hash table item
node *node_create(char *uri) {
    node *entry = (node *) malloc(sizeof(node));
    if (entry != NULL) {
        entry->uri = strdup(uri);
        entry->rwlock = rwlock_new(N_WAY, 1);
        entry->next = NULL;
    }
    return entry;
}

// free_ht_item
// Frees heap memory pointed to by *newItem, sets *pN to NULL.
void free_node(node **item) {
    if (*item != NULL) {
        rwlock_delete(&(*item)->rwlock);
        free(*item);
        *item = NULL;
    }
}

list_t *list_create() {
    list_t *ll = (list_t *) malloc(sizeof(list_t));
    if (ll) {
        ll->head = NULL;
        pthread_mutex_init(&listLock, NULL);
    }

    return ll;
}

void list_destroy(list_t **ll) {
    if (ll && *ll) {
        node *next = NULL;
        while ((*ll)->head != NULL) {
            next = (*ll)->head->next;
            free_node(&(*ll)->head);
            (*ll)->head = next;
        }
        pthread_mutex_destroy(&listLock);
        free(*ll);
        *ll = NULL;
    }
}

rwlock_t *ll_lookup(list_t *ll, char *uri) {
    // should lock be passed in from worker thread or is it fine here?

    //fprintf(stderr, "entered ht\n");
    pthread_mutex_lock(&listLock);
    const node *current = ll->head;
    while (current != NULL) {
        if (strcmp(current->uri, uri) == 0) {
            pthread_mutex_unlock(&listLock);
            return current->rwlock; // Found the URI, return the associated rwlock
        }
        current = current->next;
    }

    // URI not found
    node *newItem = node_create(uri);
    if (newItem == NULL) {
        exit(EXIT_FAILURE);
    }

    // Insert at the beginning of the linked list
    newItem->next = ll->head;
    ll->head = newItem;

    pthread_mutex_unlock(&listLock);
    return newItem->rwlock;
}
