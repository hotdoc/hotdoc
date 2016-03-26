/*
 * re2c syntax scanner for hotdoc includes
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

#ifndef __CMARK_INCLUDE_SCANNER_H
#define __CMARK_INCLUDE_SCANNER_H

#include "cmark.h"

cmark_bufsize_t _include_ext_scan_at(cmark_bufsize_t (*scanner)(const unsigned char *), const char *c,
                   cmark_bufsize_t offset);
cmark_bufsize_t _scan_open_include_block(const unsigned char *p);
cmark_bufsize_t _scan_close_include_block(const unsigned char *p);

#define scan_open_include_block(c, n) _include_ext_scan_at(&_scan_open_include_block, c, n)
#define scan_close_include_block(c, n) _include_ext_scan_at(&_scan_close_include_block, c, n)

#endif
