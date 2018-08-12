/*
 * Hotdoc python extension for fast retrieval of C code comments.
 *
 * Copyright 2015 Mathieu Duponchelle <mathieu.duponchelle@opencredd.com>
 * Copyright 2015 Collabora Ltd.
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA
 */

#ifndef _COMMENT_SCANNER_H_
#define _COMMENT_SCANNER_H_

#ifdef _POSIX_C_SOURCE
  #undef _POSIX_C_SOURCE
#endif

#ifdef _XOPEN_SOURCE
  #undef _XOPEN_SOURCE
#endif

#include <Python.h>

int scan_comments (const char *contents, PyObject *comments);

#endif
