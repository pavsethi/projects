CC = clang
CFLAGS = -Wall -Werror -Wextra -Wpedantic -gdwarf-4 -g 


all: encode decode

encode: encode.o huffman.o io.o node.o pq.o stack.o code.o
	$(CC) -o $@ $^ 

decode: decode.o huffman.o io.o node.o pq.o stack.o code.o
	$(CC) -o $@ $^ 

%.o : %.c
	$(CC) $(CFLAGS) -c $<

clean:
	rm -f *.o

spotless:
	rm -f encode decode *.o

format:
	clang-format -i -style=file *.[c]