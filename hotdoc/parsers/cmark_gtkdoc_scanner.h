#include "cmark.h"

#ifdef __cplusplus
extern "C" {
#endif

cmark_bufsize_t _ext_scan_at(cmark_bufsize_t (*scanner)(const unsigned char *), const char *c,
                   cmark_bufsize_t offset);
cmark_bufsize_t _scan_open_gtkdoc_code_block(const unsigned char *p);
cmark_bufsize_t _scan_close_gtkdoc_code_block(const unsigned char *p);
cmark_bufsize_t _scan_language_comment(const unsigned char *p);

#define scan_open_gtkdoc_code_block(c, n) _ext_scan_at(&_scan_open_gtkdoc_code_block, c, n)
#define scan_close_gtkdoc_code_block(c, n) _ext_scan_at(&_scan_close_gtkdoc_code_block, c, n)
#define scan_language_comment(c, n) _ext_scan_at(&_scan_language_comment, c, n)

#ifdef __cplusplus
}
#endif
