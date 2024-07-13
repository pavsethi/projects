#include "code.h"

#include <stdio.h>
#include <stdlib.h>

Code code_init(void) {
  Code c;    // creating a Code
  c.top = 0; // setting top of code to 0
  for (uint32_t i = 0; i < code_size(&c);
       i++) {      // looping through code size to initialize bits
    c.bits[i] = 0; // initializing each code bit to 0
  }

  return c;
}

uint32_t code_size(Code *c) {
  return c->top; // code top tracks the size of the code
}

bool code_empty(Code *c) {
  if (c->top == 0) { // if the top of the code is equal to 0
    return true;     // return true if code is empty
  } else {
    return false; // else return false
  }
}

bool code_full(Code *c) {
  if (c->top == ALPHABET) { // if the top of code is equal to 256, which is the
                            // maximum length of a code
    return true; // return true because is code is full
  } else {
    return false; // else return false
  }
}

bool code_set_bit(Code *c, uint32_t i) {
  if (i > ALPHABET) { // first check if the index to set bit is out range
    return false;     // if index is out of range, return false
  }
  c->bits[i / 8] = c->bits[i / 8] | 1UL << (i % 8); // set the bit at the index.
                                                    // taken from BitVector in
                                                    // assignment 6
  return true;
}

bool code_clr_bit(Code *c, uint32_t i) {
  if (i > ALPHABET) { // first check if the index to set bit is out range
    return false;     // if index is out of range, return false
  }
  c->bits[i / 8] =
      c->bits[i / 8] & ~(1UL << (i % 8)); // clear the bit at the index. taken
                                          // from BitVector in assignment 6
  return true; // return true if bit is clear
}

bool code_get_bit(Code *c, uint32_t i) {
  if (i > ALPHABET) { // check if index is out of range
    return false;     // return false if index out of range
  }
  int bit = ((c->bits[i / 8] >> (i % 8)) &
             1UL);   // get bit logic taken from BitVector in assignment 6
  if (bit == true) { // if the bit is 1, return true
    return true;
  } else {
    return false; // return false if the bit is 0
  }
}

bool code_push_bit(Code *c, uint8_t bit) {
  if (code_full(c) ==
      true) {     // if the code is already full then we can't push anything
    return false; // return false since can't push
  } else {
    if (bit == 1) {                  // if the bit to push is 1
      bit = code_set_bit(c, c->top); // set the bit at the top of the code
    }
    c->top += 1; // increment top of code to have space for next push
    return true; // return true for successful push
  }
}

bool code_pop_bit(Code *c, uint8_t *bit) {
  if (code_empty(c) == true) { // if code is empty then we can't pop from it
    return false;              // return false since can't pop
  } else {
    *bit = code_get_bit(c, c->top - 1); // set pointer to bit to the bit in the
                                        // code that is right before top
    code_clr_bit(
        c, c->top - 1); // clear the bit in the spot that we just got it from
    c->top -= 1;        // decrease top of code
    return true;        // return true for successful pop
  }
}

void code_print(Code *c) {
  for (uint32_t i = 0; i < code_size(c); i++) { // loop through code size
    printf("%u", code_get_bit(c, i));           // print the bits in the code
  }
  printf("\n");
}
