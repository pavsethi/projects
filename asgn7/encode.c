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
    fprintf(stderr, "  A Huffman encoder.\n");
    fprintf(stderr,
            "  Compresses a file using the Huffman coding algorithm.\n");
    fprintf(stderr, "\n");
    fprintf(stderr, "USAGE\n");
    fprintf(stderr, "  ./encode [-h] [-i infile] [-o outfile]\n");
    fprintf(stderr, "\n");
    fprintf(stderr, "OPTIONS\n");
    fprintf(stderr, "  -h             Program usage and help.\n");
    fprintf(stderr, "  -v             Print compression statistics.\n");
    fprintf(stderr, "  -i infile      Input file to compress.\n");
    fprintf(stderr, "  -o outfile     Output of compressed data.\n");
    return 0;
  }

  if (help_error) {
    fprintf(stderr, "SYNOPSIS\n");
    fprintf(stderr, "  A Huffman encoder.\n");
    fprintf(stderr,
            "  Compresses a file using the Huffman coding algorithm.\n");
    fprintf(stderr, "\n");
    fprintf(stderr, "USAGE\n");
    fprintf(stderr, "  ./encode [-h] [-i infile] [-o outfile]\n");
    fprintf(stderr, "\n");
    fprintf(stderr, "OPTIONS\n");
    fprintf(stderr, "  -h             Program usage and help.\n");
    fprintf(stderr, "  -v             Print compression statistics.\n");
    fprintf(stderr, "  -i infile      Input file to compress.\n");
    fprintf(stderr, "  -o outfile     Output of compressed data.\n");
    return 444;
  }

  uint64_t histogram[ALPHABET]; // initialize histogram to hold 256 uint64_t's.
                                // will hold symbol and frequency

  for (uint64_t i = 0; i < ALPHABET; i++) {
    histogram[i] =
        0; // zeroing out the histogram in case there were garbage values
  }

  uint8_t buffer[BLOCK]; // initialize buffer to hold symbols

  for (int i = 0; i < BLOCK; i++) {
    buffer[i] = 0; // zeroing out buffer
  }

  int read_byte = 0;
  do {
    read_byte = read_bytes(infile, buffer, BLOCK); // similar logic to
                                                   // read_byte/write_byte. reads
                                                   // in BLOCK to buffer
    for (int i = 0; i < read_byte; i++) { // loops through BLOCK read in
      histogram[buffer[i]] += 1; // the buffer contains the symbols which is
                                 // index of histogram. increment frequency of
                                 // symbol
    }
  } while (read_byte > 0); // keep looping until read_bytes returns 0

  lseek(infile, 0, SEEK_SET); // reset the cursor to start of infile

  if (histogram[0] == 0) { // if the first element of histogram is 0
    histogram[0] = 1;      // set the element to a 1
  }

  if (histogram[1] == 0) { // if the second element of histogram is 0
    histogram[0] = 1;      // set the element to 1
  }
  // this ensures that at least 2 symbols in the histogram have a frequency

  Node *root = build_tree(
      histogram); // creating the huffman tree and storing the root of the tree

  Code table[ALPHABET]; // code table will hold 256 Codes

  build_codes(root,
              table); // building code table by traversing through huffman tree

  Header header; // construct a Header struct

  header.magic = MAGIC; // set headers magic number field to MAGIC. identifies
                        // file which has been compressed

  struct stat
      buf; // fstat takes in a buffer argument to store status information
  fstat(infile, &buf); // storing status info of infile into buffer
  header.permissions =
      buf.st_mode; // setting permissions of header to permissions of infile
  fchmod(outfile, buf.st_mode); // setting permissions of outfile to match
                                // infile

  uint64_t unique_symbol = 0; // finds unique symbols in histogram

  for (uint64_t i = 0; i < ALPHABET; i++) {
    if (histogram[i] > 0) // if frequency of symbol exists
    {
      unique_symbol += 1; // increment unique symbol count
    }
  }

  header.tree_size = (3 * unique_symbol) - 1; // setting header tree size.
                                              // represents number of bytes that
                                              // make up huffman tree

  header.file_size =
      buf.st_size; // set header file size to size of file to compress

  write_bytes(outfile, (uint8_t *)&header,
              sizeof(Header)); // nishant said to type cast header for buffer.
                               // writing out header to outfile

  dump_tree(outfile, root); // writing huffman tree to outfile

  int read = 0;

  do { // similar do while logic
    read = read_bytes(infile, buffer,
                      BLOCK); // read in a BLOCK into the buffer from infile
    for (int i = 0; i < read; i++) { // loop through the bits
      write_code(
          outfile,
          &table[buffer[i]]); // write the codes from the code table to outfile
    }
  } while (read > 0); // keep looping until no more bytes to read

  if (statistics) { // prints compression statistics
    fprintf(stderr, "Uncompressed file size: %lu bytes\n", header.file_size);
    fprintf(stderr, "Compressed file size: %lu bytes\n", bytes_written);
    float space = 100 * (1 - ((float)bytes_written / (float)header.file_size));
    fprintf(stderr, "Space saving: %3.2f%%\n", space);
  }
  flush_codes(outfile); // flush all leftover codes to outfile

  delete_tree(&root); // delete the huffman tree
  close(infile);      // close the files
  close(outfile);
  return 0;
}
