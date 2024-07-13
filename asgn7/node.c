#include "node.h"

#include <ctype.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>

Node *node_create(uint8_t symbol, uint64_t frequency) {
  Node *n = (Node *)malloc(sizeof(Node)); // allocate memory for node

  if (n) {                    // if memory was allocated
    n->left = NULL;           // initialize left child
    n->right = NULL;          // initialize right child node
    n->symbol = symbol;       // initialize symbol to symbol
    n->frequency = frequency; // initialize frequency
  }
  return n;
}

void node_delete(Node **n) {
  if (*n) {
    free(*n);  // free allocated memory for node
    *n = NULL; // set node pointer to NULL
  }
}

Node *node_join(Node *left, Node *right) {
  Node *parent = node_create(
      '$', left->frequency + right->frequency); // create a parent node that has
                                                // the symbol $ and frequency is
                                                // sum of left and right
                                                // frequencies
  parent->left = left;   // set left child node of created node to left
  parent->right = right; // set right child node of created node to right

  return parent;
}

void node_print(Node *n) {

  if (iscntrl(n->symbol) != 0 &&
      isprint(n->symbol) !=
          0) { // if symbol is a control character and printable
    printf("symbol: 0x%02" PRIx8 "\n", n->symbol); // print symbol as hex
  } else {
    printf("symbol: %c\n", n->symbol); // else print symbol as character
  }

  printf("frequency: %lu\n", n->frequency); // print node frequency
}

bool node_cmp(Node *n, Node *m) {
  if ((n->frequency) >
      (m->frequency)) { // if frequency of first node is greater than other node
    return true;        // return true
  } else {
    return false; // else return false
  }
}

void node_print_sym(Node *n) {
  if (iscntrl(n->symbol) != 0 &&
      isprint(n->symbol) != 0) { // if symbol is control character and printable
    printf("symbol: 0x%02" PRIx8 "\n", n->symbol); // print symbol as hex
  } else {
    printf("symbol: %c\n", n->symbol); // else print character
  }
}
