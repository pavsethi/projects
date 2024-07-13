#include "code.h"
#include "defines.h"
#include "header.h"
#include "huffman.h"
#include "io.h"
#include "node.h"
#include "pq.h"
#include "stack.h"

#include <fcntl.h>
#include <inttypes.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <unistd.h>

int main(int argc, char **argv) {
  int opt = 0;
  int infile = STDIN_FILENO; // setting input file to standard-in file
                             // descriptor
  int outfile =
      STDOUT_FILENO; // setting output file to standard-out file descriptor

  bool help = false;       // bool flag for help message
  bool help_error = false; // bool flag for default case
  bool statistics = false; // bool flag for statistics

  while ((opt = getopt(argc, argv, "hi:o:v")) != -1) {
    switch (opt) {
    case 'h':
      help = true; // bool flag for help turned true if option given
      break;
    case 'i':
      infile = open(optarg, O_RDONLY); // set infile to open provided input file
                                       // for read only purposes. return file
                                       // descriptor
      if (infile == -1) {
        fprintf(stderr,
                "Error opening input file.\n"); // error if failure to open file
        return 12;
      }
      break;
    case 'o':
      outfile = open(optarg, O_WRONLY | O_CREAT); // set outfile to open
                                                  // provided output file for
                                                  // write only purposes. create
                                                  // file if doesn't exist
      if (outfile == -1) {
        fprintf(
            stderr,
            "Error opening output file.\n"); // error if failure to open file
        return 12;
      }
      break;
    case 'v':
      statistics = true; // bool flag for stats turned true if option given
      break;
    default:
      help_error = true; // bool flag for error help message
      break;
    }
  }

  if (help) {
    fprintf(stderr, "SYNOPSIS\n");
    fprintf(stderr, "  A Huffman decoder.\n");
    fprintf(stderr,
            "  Decompresses a file using the Huffman coding algorithm.\n");
    fprintf(stderr, "\n");
    fprintf(stderr, "USAGE\n");
    fprintf(stderr, "  ./decode [-h] [-i infile] [-o outfile]\n");
    fprintf(stderr, "\n");
    fprintf(stderr, "OPTIONS\n");
    fprintf(stderr, "  -h             Program usage and help.\n");
    fprintf(stderr, "  -v             Print compression statistics.\n");
    fprintf(stderr, "  -i infile      Input file to decompress.\n");
    fprintf(stderr, "  -o outfile     Output of decompressed data.\n");
    return 0;
  }

  if (help_error) {
    fprintf(stderr, "SYNOPSIS\n");
    fprintf(stderr, "  A Huffman decoder.\n");
    fprintf(stderr,
            "  Decompresses a file using the Huffman coding algorithm.\n");
    fprintf(stderr, "\n");
    fprintf(stderr, "USAGE\n");
    fprintf(stderr, "  ./decode [-h] [-i infile] [-o outfile]\n");
    fprintf(stderr, "\n");
    fprintf(stderr, "OPTIONS\n");
    fprintf(stderr, "  -h             Program usage and help.\n");
    fprintf(stderr, "  -v             Print compression statistics.\n");
    fprintf(stderr, "  -i infile      Input file to decompress.\n");
    fprintf(stderr, "  -o outfile     Output of decompressed data.\n");
    return 444;
  }

  Header header; // construct a header struct

  read_bytes(infile, (uint8_t *)&header,
             sizeof(Header)); // read in the header from infile

  if (header.magic != MAGIC) // make sure that the magic number matches
  {
    fprintf(stderr, "Error with input file. Magic number invalid.\n");
    return 12;
  }

  fchmod(outfile, header.permissions); // set the permissions of outfile

  uint8_t dumped_tree[header.tree_size]; // create an array to read in the
                                         // dumped tree from infile

  read_bytes(infile, dumped_tree, header.tree_size); // read in dumped tree

  Node *root =
      rebuild_tree(header.tree_size, dumped_tree); // rebuild a huffman tree

  uint64_t decoded_symbol = 0; // will track leaf node symbol
  uint8_t bit;                 // store bit read in
  Node *curr_node = root;      // node used to traverse down the tree

  while (decoded_symbol !=
         header.file_size) // while you haven't reached the file size
  {
    read_bit(infile, &bit); // read in a bit
    if (bit == 0) {         // if the bit is a 0, then we go down the left link
      curr_node = curr_node->left; // set the current node to its left child
    } else if (bit == 1) { // if the bit is a 1, then we go down the right link
      curr_node = curr_node->right; // set the current node to its right child
    }

    if (!curr_node->left &&
        !curr_node->right) { // if we are at a leaf node, meaning no children
      write_bytes(outfile, &curr_node->symbol,
                  1);      // write out the nodes symbol to outfile
      decoded_symbol += 1; // increment leaf node symbol by 1
      curr_node = root; // reset the current node back to the root of the tree
    }
  }

  if (statistics) { // print decompression statistics
    fprintf(stderr, "Compressed file size: %lu bytes\n", bytes_read);
    fprintf(stderr, "Decompressed file size: %lu bytes\n", header.file_size);
    float space = 100 * (1 - ((float)bytes_read / (float)header.file_size));
    fprintf(stderr, "Space saving: %3.2f%%\n", space);
  }
  delete_tree(&root); // delete the huffman tree

  close(infile); // close files
  close(outfile);

  return 0;
}
