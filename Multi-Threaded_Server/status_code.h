#pragma once

#include <string.h>
#include <stdio.h>

void BuildStatusCode(int statusCode, int contentLength, char response[]);

void WriteStatusCode(int outfd, int statusCode);
