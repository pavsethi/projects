#include "pq.h"

#include <stdio.h>
#include <stdlib.h>

struct PriorityQueue { // idea taken from lecture 9 slides on struct for Queue
  uint32_t size;
  uint32_t capacity;
  Node **items;
};

PriorityQueue *pq_create(uint32_t capacity) {
  PriorityQueue *q = (PriorityQueue *)malloc(
      sizeof(PriorityQueue)); // allocate memory for priority queue

  if (q) {                  // if memory allocated
    q->size = 0;            // set pq size to 0, this is similar to top in stack
    q->capacity = capacity; // set pq capacity to capacity
    q->items = (Node **)calloc(capacity, sizeof(Node **)); // allocating memory
                                                           // to hold the list of
                                                           // nodes. initialized
                                                           // to 0

    if (q->items == NULL) { // if memory for items not allocated
      free(q);              // free priority queue
      q = NULL;             // set pq to NULL
    }
  }

  return q;
}

void pq_delete(PriorityQueue **q) // taken from lecture 9 slides
{
  if (*q) {              // if priority queue existss
    if ((*q)->items) {   // if nodes exist
      free((*q)->items); // free list of nodes
    }
    free(*q);  // free priority queue
    *q = NULL; // set pointer to pq to NULL
  }
}

bool pq_empty(PriorityQueue *q) {
  if (q->size == 0) { // if pq size is equal to 0
    return true;      // return true because pq is empty
  } else {
    return false;
  }
}

bool pq_full(PriorityQueue *q) {
  if (q->size == q->capacity) { // if top of pq is equal to the capacity
    return true;                // return true because pq is full
  } else {
    return false; // return false if not full
  }
}

uint32_t pq_size(PriorityQueue *q) {
  return q->size; // pq size is the top of the pq so return this for size
}

// swap lchild, rchild, parent, up_heap, and down_heap taken from assignment 4

void swap(Node **x,
          Node **y) { // swap function taken from asgn4, changed int to Node
  Node *t = *x;
  *x = *y;
  *y = t;
}

uint32_t l_child(uint32_t n) {
  return (2 * n) + 1; // left child is always (2*n) + 1
}

uint32_t r_child(uint32_t n) {
  return (2 * n) + 2; // right child is always (2*n) + 2
}

uint32_t parent(uint32_t n) {
  return (n - 1) / 2; // parent is always (n-1) / 2
}

void up_heap(Node **items, uint32_t n) {
  while (
      n > 0 &&
      (node_cmp(items[parent(n)],
                items[n]))) // while the parent node is greater than the child
  {
    swap(&items[n], &items[parent(n)]); // swap the parent and the child since
                                        // parent should be less in min heap
    n = parent(n); // set n as parent node for next iteration
  }
}

void down_heap(Node **items, uint32_t heap_size) {
  uint32_t n = 0;
  uint32_t smaller;
  while (l_child(n) < heap_size) // while the left child is less than the heap
  {
    if (r_child(n) == heap_size) // if the right child doesn't exist, then left
                                 // child is smaller one
    {
      smaller = l_child(n); // set left child as smaller
    } else {
      if (node_cmp(items[r_child(n)], items[l_child(n)])) // if right child does
                                                          // exist, then check if
                                                          // the right child or
                                                          // left child are
                                                          // bigger
      {
        smaller = l_child(
            n); // if right child is bigger, then left child is set as smaller
      } else {
        smaller = r_child(n); // else set right child as smaller
      }
    }

    if (node_cmp(items[smaller], items[n])) // end the loop if the current node
                                            // is smaller than the smallest node
    {
      break;
    }

    swap(&items[n], &items[smaller]); // swap current node and smallest node

    n = smaller; // set current node as small node
  }
}

bool enqueue(PriorityQueue *q, Node *n) {
  if (pq_full(q)) // can't enqueue if priority queue already full
  {
    return false; // return false if thats the case
  } else {
    q->items[q->size] = n;      // enqueue node at the top of the list of nodes
    up_heap(q->items, q->size); // call up_heap to re-sort the priority queue
    q->size++;                  // increment top of pq for next enqueue
    return true;                // return true for successful enqueue
  }
}

bool dequeue(PriorityQueue *q, Node **n) {
  if (pq_empty(q)) { // can't dequeue if priority queue is empty
    return false;    // return false for fail dequeue
  }
  *n = q->items[0]; // set the node pointer to the node at the first index of
                    // queue, the top
  q->items[0] =
      q->items[q->size -
               1]; // set the last node as the first node for re-sorting
  down_heap(q->items, q->size); // call down heap to re sort
  q->size--;                    // decrease q size for next dequeue
  return true;                  // return true for successful dequeue
}

void pq_print(PriorityQueue *q) {
  for (uint32_t i = 0; i < pq_size(q); i++) { // loop through pq size
    node_print(q->items[i]);                  // print each node
  }
}
