#include "stack.h"

#include <stdio.h>
#include <stdlib.h>

struct Stack {
  uint32_t top;
  uint32_t capacity;
  Node **items;
};

Stack *stack_create(uint32_t capacity) {
  Stack *s = (Stack *)malloc(sizeof(Stack)); // allocate memory for stack

  if (s) {      // if memory is allocated
    s->top = 0; // set top of stack to 0, will push and pop from the top
    s->capacity = capacity; // initialize capacity of stack to capacity
    s->items = (Node **)calloc(capacity, sizeof(Node **)); // allocating memory
                                                           // to hold the list of
                                                           // nodes. initialized
                                                           // to 0
    if (s->items == NULL) { // if memory for items not allocated
      free(s);              // free memory allocated for stack
      s = NULL;             // set stack to NULL
    }
  }

  return s;
}

void stack_delete(Stack **s) {
  if (*s && (*s)->items) { // if stack and list of nodes is not NULL
    free((*s)->items);     // free memory allocated for list of nodes
    free(*s);              // free memory allocated for stack
    *s = NULL;             // set stack pointer to NULL
  }
}

bool stack_empty(Stack *s) {
  if (s->top == 0) { // if the top of the stack is 0
    return true;     // stack is empty and return true
  } else {
    return false; // else return false
  }
}

bool stack_full(Stack *s) {
  if (s->top == s->capacity) { // if top of stack is equal to stacks capacity
    return true;               // stack is full and return true
  } else {
    return false; // else return false
  }
}

uint32_t stack_size(Stack *s) {
  return s->top; // top of stack tracks the stack size
}

bool stack_push(Stack *s, Node *n) {
  if (stack_full(s)) { // if the stack is already full then we can't push to it
    return false;      // return false for pushing
  } else {
    s->items[s->top] = n; // set the top node in the stack to the input node
    s->top += 1;          // increment the top to have space for the stack push
    return true;          // return true for successful pushing
  }
}

bool stack_pop(Stack *s, Node **n) {
  if (stack_empty(
          s)) {   // if the stack is empty then there is nothing to pop from it
    return false; // return false
  } else {
    s->top -= 1; // decrement top to get top of stack that actually has a node
    *n = s->items[s->top]; // set pointer node to the node at the top of the
                           // stack
    return true; // return true for successful pop
  }
}

void stack_print(Stack *s) {
  for (uint32_t i = 0; i < stack_size(s); i++) { // loop through stack size
    node_print(s->items[i]);                     // print each node
  }
}
