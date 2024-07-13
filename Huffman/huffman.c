#include "huffman.h"
#include "code.h"
#include "io.h"
#include "node.h"
#include "pq.h"
#include "stack.h"

#include <stdio.h>
#include <stdlib.h>

Node *build_tree(uint64_t hist[static ALPHABET]) // constructs a huffman tree
                                                 // with a given histogram
{
  PriorityQueue *q = pq_create(ALPHABET); // creates a priority queue to hold
                                          // the Nodes where symbol exists
  for (uint32_t i = 0; i < ALPHABET; i++) // loop through histogram
  {
    if (hist[i] >
        0) { // check if frequency is greater than 0, meaning symbol exists
      Node *n = node_create(
          i, hist[i]); // create a node with the symbol and frequency
      enqueue(q, n);   // add node to priority queue
    }
  }

  while (pq_size(q) > 1) // while the priority queue has nodes
  {
    Node *left;         // initialize a left child node to dequeue
    Node *right;        // initialize a right child node to dequeue
    dequeue(q, &left);  // dequeue left node
    dequeue(q, &right); // dequeue right node
    Node *parent = node_join(left, right); // join the two nodes
    enqueue(q, parent); // add the joined nodes to the priority queue
  }

  Node *root;        // when the loop is finished, we are left with one node
  dequeue(q, &root); // dequeue the root node
  pq_delete(&q);     // delete the priority queue

  return root; // return root of huffman tree
}

static Code c; // declaring a code C
void build_codes(Node *root, Code table[static ALPHABET]) {
  uint8_t bit = 0; // will hold the popped bits

  if (root) // if the node exists
  {
    if (!root->left && !root->right) // if the node is a leaf node
    {

      table[root->symbol] = c; // the code is the path to the node and is it's
                               // symbol so we can just write it to table
    } else {                // if its an interior node
      code_push_bit(&c, 0); // push a 0 to the code
      build_codes(root->left,
                  table); // traverse down the left link. postorder traversal
      code_pop_bit(&c, &bit); // pop the bit

      code_push_bit(&c, 1);            // push a 1 to the code
      build_codes(root->right, table); // traverse down the right link.
      code_pop_bit(&c, &bit);          // pop the bit
    }
  }
}

void dump_tree(int outfile, Node *root) {
  if (root) // if the node exists
  {
    dump_tree(outfile, root->left); // post order traversal. go down the left
                                    // side of tree and write it to outfile
    dump_tree(
        outfile,
        root->right); // go down right side of tree and write it to outfile

    if (!root->left && !root->right) // if we are at a leaf node
    {
      uint8_t L_buffer[1]; // create a buffer to hold the symbol
      L_buffer[0] = 'L';   // store 'L' in buffer. symbol for leaf node
      write_bytes(outfile, L_buffer, 1); // write out the L
      write_bytes(outfile, &root->symbol,
                  1); // write out symbol of node. root->symbol return a uint8
    } else {
      uint8_t I_buffer[1]; // create a buffer to hold interior node I
      I_buffer[0] = 'I';   // store 'I' in buffer
      write_bytes(outfile, I_buffer, 1); // write out the I to outfile
    }
  }
}

Node *rebuild_tree(uint16_t nbytes, uint8_t tree[static nbytes]) {
  Stack *node_stack =
      stack_create(nbytes); // create a stack of nodes for reconstruction

  for (uint16_t i = 0; i < nbytes;
       i++) // loop through array containing dumped tree
  {
    if (tree[i] == 'L') // if the element in the array is a 'L'
    {
      Node *leaf = node_create(tree[i + 1], 1); // the next element is symbol of
                                                // leaf node, create a node with
                                                // that symbol
      stack_push(node_stack, leaf); // push the leaf node to the stack
    }
    if (tree[i] == 'I') {
      Node *right; // we are at interior node, initialize node for right child
      Node *left;  // initialize node for left child
      stack_pop(node_stack, &right); // pop the right child of interior node
      stack_pop(node_stack, &left);  // pop left child of interior node
      Node *parent = node_join(left, right); // join the nodes
      stack_push(node_stack, parent); // push the joined node to the stack
    }
  }

  Node *root;                   // loop ends with one node left
  stack_pop(node_stack, &root); // pop the node from the stack

  stack_delete(&node_stack); // delete the stack

  return root; // return root of rebuilt tree
}

void delete_tree(Node **root) {
  if (*root) {                             // if root exists
    if ((*root)->left && (*root)->right) { // if the left and right child exists
      delete_tree(&(*root)->left);  // post order traversal to delete left link
      delete_tree(&(*root)->right); // post order traversal to delete right link
    }
    node_delete(root); // deleting root node. node_delete sets to NULL
  }
}
