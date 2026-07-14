This program implements a Huffman encoder and decoder. The Huffman encoder will read an input file, find its Huffman encoding, and use the encoding to compress the file. The decoder will take in a compressed file and decompress it, bringing it back to its original size. We will create four abstract data types: nodes, priority queues, codes, and stacks. 

The files included are:

encode.c --> This file implements Huffman encoder

decode.c --> This file implements Huffman decoder

defines.h --> This file contains macro definitions

header.h --> Contains struct definition for file Header

node.h --> Contains the node ADT interface

node.c --> Implements node ADT interface

pq.h --> Contains the Priority Queue ADT interface

pq.c --> Contains implementation of Priority Queue ADT

code.h --> File contains the code ADT interface

code.c --> Implements Code data structure

io.h --> Contains the I/O module interface

io.c --> Implements I/O module

stack.h --> Contains stack ADT

stack.c --> Implements Stack data structure

huffman.h --> Contains Huffman coding module interface

huffman.c --> Implements Huffman coding module

Makefile --> creates the executable

DESIGN.pdf --> Contains psuedocode for functions

README.md --> Describes how to use the program



Building:

To build the program, run:

...

$ make clean


$ make format


$ make

...

Running:


To run the program:

...

$ ./encode [hi:o:v] 


Commands:

-h: prints help message

-i: Takes input file to encode

-o: Takes output file to write compressed input to

-v: prints compression statistics to stderr

...

$ ./decode [hi:o:v]


Commands:

-h: prints help message

-i: Takes input file to decode

-o: Takes output file to write decompressed input to

-v: prints decompression statistics to stderr
