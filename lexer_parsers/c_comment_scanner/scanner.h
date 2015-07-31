#ifndef _COMMENT_SCANNER_H_
#define _COMMENT_SCANNER_H_

#ifdef _POSIX_C_SOURCE
  #undef _POSIX_C_SOURCE
#endif

#ifdef _XOPEN_SOURCE
  #undef _XOPEN_SOURCE
#endif

#include <Python.h>

int
scan_filename (const char *filename, PyObject *comments);

#endif
