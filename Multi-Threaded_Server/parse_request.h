#pragma once

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <errno.h>
#include <regex.h>

typedef struct Request Request;

struct Request {
    char *command;
    char *uri;
    char *version;
    char *content_header;
    int content_length;
    int request_id;
    int start_content;
    int current_read_bytes;
};

// this method will parse the input using regex and fill up the Request struct accordingly
int parse_input(Request *R, char *request, int fd);
