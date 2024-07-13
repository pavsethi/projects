# Assignment 4 directory

This directory contains source code and other files for Assignment 4.

This program runs a HTTP server for processing GET and PUT requests sent by multiple different threads/clients. The server builds on the HTTP server built in Assignment 2 and implements locking and synchronization through the use of Mutexes, Bounded Buffers, and Read-write locks. It takes in a port number which it then binds to a socket
and keeps listening on that socket for connection as well as a optional -t flag which specifies the number of threads to run. The server will never crash and will continue to listen for requests. As soon as it receives a connection, the main dispatcher thread pushes the socket file descriptor to a thread-safe queue which the worker threads pop from. Based on the request, it will return the respective Status Code. GET will get the contents of the specified file and PUT will write the message in the request to the specified file. Every file has its own reader-writer lock which is mapped using a Linked List ADT. Only one thread can have a reader-writer lock at a time. 

The files included are:

httpserver.c --> Implements the actual dispatcher thread and worker thread logic. 

asgn2_helper_funcs.h --> Contains the provided helper functions

queue.h --> Contains the interface for the provided thread-safe bounded buffer.

rwlock. h --> Contains the interface for the provided reader-writer lock implementation

parse_request.c --> Implements Regex parsing on the client request

parse_request.h --> Defines the struct to store the parsed request 

process_request.c --> Implements the GET/PUT logic. Adds mutexes while opening files and performs a lookup to get the reader/writer lock for the file. 

process_request.h --> Library for process_request.c

list.c --> Implements the Linked List ADT. List is made of nodes that store the file, the rwlock, and the pointer to the next node.

list.h --> Defines Node and List structure. 

status_code.c --> Builds out the status codes and writes them back to socket

status_code.h --> Library for status_code.c

Makefile --> Compiles the executable httpserve


Building:

To build the program, run:

...

$ make clean


$ make

...

Running:


To run the server:

...

$ ./httpserver [-t threads] <port>

...


The format that requests sent in should be in are:

Request-Line\r\n ; [Required]
(Header-Field\r\n)* ; [Optional, repeated]
\r\n
Message-Body          [Optional]


Request-Line must contain a: METHOD URI VERSION

For PUT commands, the Header-Field must contain: Content-Length


---------- CITATIONS ----------

https://linux.die.net/man/3/optind --> getopt()

CSE101 --> Linked List ADT
