#include "parse_request.h"
#include "asgn2_helper_funcs.h"
#include "status_code.h"

//              method              uri                 version                 header key             header value
#define REGEX                                                                                      \
    "^([a-zA-Z]{1,8}) /([a-zA-Z0-9.-]{1,63}) (HTTP/[0-9]\\.[0-9])\r\n([a-zA-Z0-9.-]{1,128}: [ "    \
    "-~]+{0,128}\r\n)*\r\n"
#define HEADER_REGEX "([a-zA-Z0-9.-]{1,128}): ([ -~]+{0,128})\r\n"

// matching ASCII stack overflow link: https://stackoverflow.com/questions/3203190/regex-any-ascii-character

// this method will parse the input using regex and fill up the Request struct accordingly
int parse_input(Request *R, char *request, int socket_fd) {
    //printf("incoming parse request: |%s|\n", request);
    regex_t regex;
    ssize_t nmatch = 5;
    regmatch_t pmatch[nmatch];
    //printf("before compile\n");
    int rc_comp = regcomp(&regex, REGEX, REG_NEWLINE | REG_EXTENDED);
    //printf("after compile\n");

    if (rc_comp != 0) {
        //printf("error compiling regex\n");
        WriteStatusCode(socket_fd, 500);
        return -1;
    }

    //printf("before execution\n");
    int rc_exec = regexec(&regex, request, nmatch, pmatch, 0);
    //printf("after execution\n");

    if (rc_exec != 0) {
        //printf("no match with regex\n");
        WriteStatusCode(socket_fd, 400);
        return -1;
    }

    if (pmatch[0].rm_so == -1) {
        //printf("0th index did not match\n");
        WriteStatusCode(socket_fd, 400);
        return -1;
    }
    // checking if any of the sub parts did not match
    //MIGHT NOT BE NECESSARY
    for (uint i = 0; i < nmatch - 1; i++) {
        //printf("i: %u\n", i);
        if (pmatch[i].rm_so == -1) {
            //printf("something did not match\n");
            WriteStatusCode(socket_fd, 400);
            return -1;
        }
    }

    /** BY NOW SHOULD HAVE VALIDATED THAT EVERYTHING IN REQUEST IS VALID **/

    // Storing the command from the request
    R->command = request + pmatch[1].rm_so;
    R->command[pmatch[1].rm_eo - pmatch[1].rm_so] = '\0';

    //storing the file location
    R->uri = request + pmatch[2].rm_so;
    R->uri[pmatch[2].rm_eo - pmatch[2].rm_so] = '\0';

    //storing the version
    R->version = request + pmatch[3].rm_so;
    R->version[pmatch[3].rm_eo - pmatch[3].rm_so] = '\0';

    // validating version
    if (strcmp(R->version, "HTTP/1.1") != 0) {
        WriteStatusCode(socket_fd, 505);
        return -1;
    }

    // storing where content body should start
    R->start_content = pmatch[0].rm_eo;
    //printf("start content body: %c\n", request[R->start_content]);
    //if (request[R])

    // loop through headers
    R->content_length = -1;
    R->request_id = 0;
    request += pmatch[3].rm_eo + 2;
    //printf("request before looping header fields: %s\n", request);
    regmatch_t header_match[3];
    rc_comp = regcomp(&regex, HEADER_REGEX, REG_EXTENDED);
    if (rc_comp != 0) {
        WriteStatusCode(socket_fd, 500);
        return -1;
    }
    rc_exec = regexec(&regex, request, 3, header_match, 0);
    while (rc_exec == 0) {
        char *key = request + header_match[1].rm_so;
        //printf("char that null terminator is being placed at val: %c\n", key[header_match[1].rm_eo - header_match[1].rm_so]);
        key[header_match[1].rm_eo - header_match[1].rm_so] = '\0';
        //printf("key: %s\n", key);

        char *val = request + header_match[2].rm_so;
        //printf("char that null terminator is being placed at val: %c\n", val[header_match[2].rm_eo - header_match[2].rm_so]);
        val[header_match[2].rm_eo - header_match[2].rm_so] = '\0';
        //printf("val: %s\n", val);

        if (strcmp(key, "Content-Length") == 0) {
            char *endptr;
            int value = strtol(val, &endptr, 10);
            if (endptr == val || *endptr != '\0') {
                WriteStatusCode(socket_fd, 400);
                return -1;
            }
            R->content_length = value;
        }
        if (strcmp(key, "Request-Id") == 0) {
            char *endptr;
            int value = strtol(val, &endptr, 10);
            if (endptr == val || *endptr != '\0') {
                WriteStatusCode(socket_fd, 400);
                return -1;
            }
            R->request_id = value;
        }

        request += header_match[0].rm_eo;
        //printf("request after catching header: %s\n", request);
        rc_exec = regexec(&regex, request, 3, header_match, 0);
    }

    // if (R->request_id == -1) {
    //     WriteStatusCode(socket_fd, 400);
    //     return -1;
    // }

    // printf("command: %s\n", R->command);
    // printf("location: %s\n", R->uri);
    // printf("version: %s\n", R->version);
    // //printf("header: %s\n", R->content_header);
    // printf("content length: %d\n", R->content_length);
    // printf("request id: %d\n", R->request_id);
    // printf("start content body: %d\n", R->start_content);
    //printf("before regex free\n");
    regfree(&regex);
    return 0;
}
