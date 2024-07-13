#include "process_request.h"
#include "status_code.h"
#include "asgn2_helper_funcs.h"

// pthread_mutex_t lock;
// pthread_mutex_init(&lock, NULL);

int get(Request *R, list_t *ll, pthread_mutex_t *lock, int socket_fd) {
    //printf("entered fxn\n");
    // // should lock be passed in from worker thread or is it fine here?
    //pthread_mutex_init(&lock, NULL);

    pthread_mutex_lock(lock);
    //printf("entered GET\n");
    //printf("file: %s\n", R->uri);

    int fd = open(R->uri, O_RDWR);

    rwlock_t *rwlock = ll_lookup(ll, R->uri);
    pthread_mutex_unlock(lock);
    reader_lock(rwlock);
    //pthread_mutex_unlock(lock);
    //printf("fd: %d\n", fd);
    if (fd == -1) {
        if (errno == EACCES) {
            // Not allowed access to file
            //printf("no access\n");
            WriteStatusCode(socket_fd, 403);
            fprintf(stderr, "GET,/%s,%d,%d\n", R->uri, 403, R->request_id);
            reader_unlock(rwlock);
            return -1;
        } else if (errno == EISDIR) {
            // file is a directory
            // CHECK IF THIS IS CORRECT STATUS CODE
            //printf("path is directory\n");
            WriteStatusCode(socket_fd, 403);
            fprintf(stderr, "GET,/%s,%d,%d\n", R->uri, 403, R->request_id);
            reader_unlock(rwlock);
            return -1;
        } else if (errno == ENFILE) {
            // Too many files already open on server
            // MAY NOT BE NECESSARY
            WriteStatusCode(socket_fd, 500);
            fprintf(stderr, "GET,/%s,%d,%d\n", R->uri, 500, R->request_id);
            reader_unlock(rwlock);
            return -1;
        } else if (errno == ENOENT) {
            WriteStatusCode(socket_fd, 404);
            fprintf(stderr, "GET,/%s,%d,%d\n", R->uri, 404, R->request_id);
            reader_unlock(rwlock);
            return -1;
        }
        // HOW TO CHECK IF FILE EXISTS
        // If error opening file and not one of errno ones above
        WriteStatusCode(socket_fd, 500);
        fprintf(stderr, "GET,/%s,%d,%d\n", R->uri, 500, R->request_id);
        reader_unlock(rwlock);
        return -1;
    }

    // get the rwlock for file --> where should hash table be declared
    // lock it down for readers
    //fprintf(stderr, "looking for rwlock in GET\n");
    //rwlock_t *rwlock = ll_lookup(ll, R->uri);
    //pthread_mutex_destroy(&lock);
    //fprintf(stderr, "got lock in GET\n");
    //pthread_mutex_unlock(lock);
    // reader_lock(rwlock);
    // pthread_mutex_unlock(lock);
    //pthread_mutex_destroy(&lock);
    //fprintf(stderr, "locked for reader\n");

    //HOW TO GET FILE SIZE
    struct stat buffer;
    fstat(fd, &buffer);

    // ASK HOW TO WRITE BACK RESPONSE
    char response[1024];
    BuildStatusCode(2001, buffer.st_size, response); // 2001 = 200
    int rc = write_n_bytes(socket_fd, response, strlen(response));
    //fprintf(stderr, "written bytes: %d\n", rc);
    if (rc == -1) {
        WriteStatusCode(socket_fd, 500);
        fprintf(stderr, "GET,/%s,%d,%d\n", R->uri, 500, R->request_id);
        reader_unlock(rwlock);
        return -1;
    }
    //printf("file size: %ld\n", buffer.st_size);
    rc = pass_n_bytes(fd, socket_fd, buffer.st_size);
    //printf("passed bytes: %d\n", rc);
    if (rc == -1) {
        WriteStatusCode(socket_fd, 500);
        fprintf(stderr, "GET,/%s,%d,%d\n", R->uri, 500, R->request_id);
        reader_unlock(rwlock);
        return -1;
    }

    // write to audit log
    fprintf(stderr, "GET,/%s,%d,%d\n", R->uri, 200, R->request_id);

    // close for readers
    reader_unlock(rwlock);
    //pthread_mutex_destroy(&lock);
    //fprintf(stderr, "released reader lock in get\n");

    close(fd);
    return 0;
}

int put(Request *R, list_t *ll, pthread_mutex_t *lock, char *buf, int socket_fd) {
    // pthread_mutex_t lock;
    // // should lock be passed in from worker thread or is it fine here?

    //pthread_mutex_init(&lock, NULL);
    pthread_mutex_lock(lock);

    //fprintf(stderr, "entered PUT\n");

    int status_code = 0;
    int fd = open(R->uri, O_WRONLY | O_CREAT | O_EXCL, 0666);
    pthread_mutex_unlock(lock);
    rwlock_t *rwlock = ll_lookup(ll, R->uri);
    writer_lock(rwlock);
    // pthread_mutex_unlock(lock);

    //fprintf(stderr, "fd: %d\n", fd);
    status_code = 201;
    if (fd == -1) {
        if (errno == EEXIST) {
            //printf("exists\n");
            status_code = 200;
            fd = open(R->uri, O_WRONLY | O_TRUNC, 0666);
            if (fd == -1) {
                if (errno == EACCES) {
                    // Not allowed access to file
                    //printf("no access\n");
                    WriteStatusCode(socket_fd, 403);
                    fprintf(stderr, "PUT,/%s,%d,%d\n", R->uri, 403, R->request_id);
                    writer_unlock(rwlock);
                    return -1;
                }
                if (errno == EISDIR) {
                    // file is a directory
                    // CHECK IF THIS IS CORRECT STATUS CODE
                    //printf("file is directory\n");
                    WriteStatusCode(socket_fd, 403);
                    fprintf(stderr, "PUT,/%s,%d,%d\n", R->uri, 403, R->request_id);
                    writer_unlock(rwlock);
                    return -1;
                }
                if (errno == ENFILE) {
                    // Too many files already open on server
                    // MAY NOT BE NECESSARY
                    //printf("too many files\n");
                    WriteStatusCode(socket_fd, 500);
                    fprintf(stderr, "PUT,/%s,%d,%d\n", R->uri, 500, R->request_id);
                    writer_unlock(rwlock);
                    return -1;
                }
                if (errno == ENOENT) {
                    //printf("file not found\n");
                    WriteStatusCode(socket_fd, 404);
                    fprintf(stderr, "PUT,/%s,%d,%d\n", R->uri, 404, R->request_id);
                    writer_unlock(rwlock);
                    return -1;
                }

                // HOW TO CHECK IF FILE EXISTS
                // If error opening file and not one of errno ones above
                //printf("1 internal\n");
                WriteStatusCode(socket_fd, 500);
                fprintf(stderr, "PUT,/%s,%d,%d\n", R->uri, 500, R->request_id);
                writer_unlock(rwlock);
                return -1;
            }
        }
    }

    //fprintf(stderr, "looking for rwlock in PUT\n");
    // rwlock_t *rwlock = ll_lookup(ll, R->uri);
    // //fprintf(stderr, "got lock in PUT\n");
    // //pthread_mutex_destroy(&lock);
    // //pthread_mutex_unlock(lock);
    // writer_lock(rwlock);
    // pthread_mutex_unlock(lock);

    // fprintf(stderr, "locked for writing\n");
    // fprintf(stderr, "current read bytes: %d\n", R->current_read_bytes);
    // fprintf(stderr, "current content length: %d\n", R->content_length);
    //printf("status code: %d\n", status_code);
    int rc = 0;
    if ((R->current_read_bytes == R->content_length)
        || (R->current_read_bytes > R->content_length)) {
        //printf("buf + starting: %s\n", buf + R->start_content);
        rc = write_n_bytes(fd, buf + R->start_content, R->content_length);
        if (rc == -1) {
            //perror("2 internal\n");
            WriteStatusCode(socket_fd, 500);
            fprintf(stderr, "PUT,/%s,%d,%d\n", R->uri, 500, R->request_id);
            writer_unlock(rwlock);
            return -1;
        }
    } else {
        rc = write_n_bytes(fd, buf + R->start_content, R->current_read_bytes);
        //printf("written bytes: %d\n", rc);
        if (rc == -1) {
            //printf("4 internal\n");
            WriteStatusCode(socket_fd, 500);
            fprintf(stderr, "PUT,/%s,%d,%d\n", R->uri, 500, R->request_id);
            writer_unlock(rwlock);
            return -1;
        }
        int remaining = R->content_length - R->current_read_bytes;
        //printf("remaing: %d\n", remaining);
        rc = pass_n_bytes(socket_fd, fd, remaining);
        //printf("bytes passed: %d\n", rc);
        if (rc == -1) {
            //printf("5 internal\n");
            WriteStatusCode(socket_fd, 500);
            fprintf(stderr, "PUT,/%s,%d,%d\n", R->uri, 500, R->request_id);
            writer_unlock(rwlock);
            return -1;
        }
    }

    if (status_code == 200) {
        WriteStatusCode(socket_fd, 2002);
        fprintf(stderr, "PUT,/%s,%d,%d\n", R->uri, 200, R->request_id);
        writer_unlock(rwlock);
    } else if (status_code == 201) {
        WriteStatusCode(socket_fd, 201);
        fprintf(stderr, "PUT,/%s,%d,%d\n", R->uri, 201, R->request_id);
        writer_unlock(rwlock);
    }

    close(fd);
    return 0;
}
