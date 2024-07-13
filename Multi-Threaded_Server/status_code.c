#include "status_code.h"
#include "asgn2_helper_funcs.h"

void BuildStatusCode(int statusCode, int contentLength, char response[]) {
    switch (statusCode) {
    case 2001:
        // for 200 with GET
        sprintf(response, "HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n", contentLength);
        break;
    case 2002:
        // for 200 with PUT
        sprintf(response, "HTTP/1.1 200 OK\r\nContent-Length: 3\r\n\r\nOK\n");
        break;
    case 201:
        sprintf(response, "HTTP/1.1 201 Created\r\nContent-Length: 8\r\n\r\nCreated\n");
        break;
    case 400:
        sprintf(response, "HTTP/1.1 400 Bad Request\r\nContent-Length: 12\r\n\r\nBad Request\n");
        break;
    case 403:
        sprintf(response, "HTTP/1.1 403 Forbidden\r\nContent-Length: 10\r\n\r\nForbidden\n");
        break;
    case 404:
        sprintf(response, "HTTP/1.1 404 Not Found\r\nContent-Length: 10\r\n\r\nNot Found\n");
        break;
    case 500:
        sprintf(response, "HTTP/1.1 500 Internal Server Error\r\nContent-Length: "
                          "22\r\n\r\nInternal Server Error\n");
        break;
    case 501:
        sprintf(response,
            "HTTP/1.1 501 Not Implemented\r\nContent-Length: 16\r\n\r\nNot Implemented\n");
        break;
    case 505:
        sprintf(response, "HTTP/1.1 505 Version Not Supported\r\nContent-Length: 22\r\n\r\nVersion "
                          "Not Supported\n");
        break;
    }
}

void WriteStatusCode(int outfd, int statusCode) {
    char response[1024];
    BuildStatusCode(statusCode, -1, response);
    write_n_bytes(outfd, response, strlen(response));
}
