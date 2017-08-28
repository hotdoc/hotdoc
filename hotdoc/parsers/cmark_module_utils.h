/*
 * Utilities for the cmark hotdoc module
 *
 * Copyright 2016 Mathieu Duponchelle <mathieu.duponchelle@opencredd.com>
 * Copyright 2016 Collabora Ltd.
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

#ifndef __CMARK_MODULE_UTILS_H
#define __CMARK_MODULE_UTILS_H

typedef struct {
  char *ref;
  char *title;
  char *extra_attrs;
} NamedLink;

void free_named_link(NamedLink *link);

void diagnose(const char *code, const char *message, int lineno, int column);

#endif
