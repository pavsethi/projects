#include "io.h"
#include "code.h"

#include <fcntl.h>
#include <stdio.h>
#include <unistd.h>

uint64_t bytes_read = 0;
uint64_t bytes_written = 0;

int read_bytes(int infile, uint8_t *buf, int nbytes) {
  ssize_t nbytes_read = 0; // will track the bytes read from read()
  ssize_t total_read = 0;  // tracks total bytes read

  do {
    nbytes_read =
        read(infile, buf + total_read,
             nbytes - total_read); // read nbytes into the buffer from infile.
                                   // increment buffer by bytes read to leave
                                   // space to continue reading  decrease bytes
                                   // read by nbytes to not read same block again
    total_read += nbytes_read; // keep incrementing bytes read

    if (total_read == nbytes) { // break once the total bytes read equals nbytes
      break;
    }

  } while (nbytes_read > 0); // keep looping through read() until it returns a 0

  bytes_read += total_read; // add total read to bytes read statistic
  return total_read;        // return total bytes read
}

int write_bytes(int outfile, uint8_t *buf, int nbytes) {
  ssize_t nbytes_wrote = 0; // will track bytes wrote from write()
  ssize_t total_wrote = 0;  // tracks total bytes wrote

  do {
    nbytes_wrote = write(outfile, buf + total_wrote,
                         nbytes - total_wrote); // write nbytes from buffer into
                                                // outfile. increment buffer to
                                                // create space to write more
                                                // bytes  decrease bytes wrote to
                                                // not write the same block again
    total_wrote += nbytes_wrote; // keep incrementing bytes wrote

    if (total_wrote ==
        nbytes) { // break once the total bytes wrote is equal to nbytes
      break;
    }

  } while (nbytes_wrote > 0); // keep looping through write() until it returns 0

  bytes_written +=
      total_wrote;    // add total bytes wrote to bytes written for statistics
  return total_wrote; // return total bytes wrote
}

bool read_bit(int infile, uint8_t *bit) {
  // psuedocode provided by Lev

  static uint8_t buffer[BLOCK];   // static buffer of bytes of size BLOCK(4096)
  static int index = BLOCK * 8;   // index to go through buffer and track bit
  static ssize_t buffer_size = 0; // tracks the size of the buffer that is read

  if (index ==
      (BLOCK * 8)) { // if all of the bits in the buffer have been visited
    buffer_size = read_bytes(infile, buffer,
                             BLOCK); // fill up the buffer again with bytes
    index = 0;                       // reset the index of the buffer
  }

  if (index == (buffer_size * 8)) { // if index reaches the end of bytes read
    return false;                   // return false
  }

  *bit = ((buffer[index / 8] >> (index % 8)) &
          1UL); // getting bit at the index and setting it to *bit
  index += 1;   // incrementing index

  return true; // return true if still more bits to read
}

static uint8_t write_buffer[BLOCK];
static int write_index = 0;

void write_code(int outfile, Code *c) {
  for (uint32_t i = 0; i < code_size(c); i++) // loop through the code
  {
    if (code_get_bit(c, i)) // get the bit at the index
    {
      write_buffer[write_index / 8] =
          write_buffer[write_index / 8] |
          1UL << (write_index % 8); // setting bit at index if it is 1
    } else {
      write_buffer[write_index / 8] =
          write_buffer[write_index / 8] &
          ~(1UL << (write_index % 8)); // clearing bit at index if it is 0
    }

    write_index += 1; // keep going through buffer

    if (write_index ==
        (BLOCK * 8)) { // if we reach the end of the buffer and it is filled
      write_bytes(outfile, write_buffer,
                  BLOCK); // write out the buffer to outfile
      for (int i = 0; i < BLOCK;
           i++) // after you write out the bytes, we want to 0 everything
      {
        write_buffer[i] = 0; // zeroing out buffer
      }
      write_index = 0; // reseting the index
    }
  }
}

void flush_codes(int outfile) {
  int index_byte = 0;
  if (write_index > 0) {     // checking that there are bits
    if (write_index % 8 > 0) // checking if bits are leftover
    {
      index_byte = (write_index / 8) +
                   1; // if theres leftover, add 1 to get the next byte
    } else {
      index_byte =
          (write_index / 8); // if there is no leftover then just get the byte
    }
  }

  write_bytes(outfile, write_buffer,
              index_byte); // write out the leftover bits to outfile
}
