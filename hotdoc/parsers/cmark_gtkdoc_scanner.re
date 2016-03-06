#include <stdlib.h>
#include <string.h>
#include "cmark_gtkdoc_scanner.h"

cmark_bufsize_t _ext_scan_at(cmark_bufsize_t (*scanner)(const unsigned char *),
	const char *s, cmark_bufsize_t offset)
{
	cmark_bufsize_t res;
	cmark_bufsize_t len = strlen(s);
	unsigned char *ptr = (unsigned char *)s;

        if (ptr == NULL || offset > len) {
          return 0;
        } else {
	  res = scanner(ptr + offset);
        }

	return res;
}

/*!re2c
  re2c:define:YYCTYPE  = "unsigned char";
  re2c:define:YYCURSOR = p;
  re2c:define:YYMARKER = marker;
  re2c:define:YYCTXMARKER = marker;
  re2c:yyfill:enable = 0;

  spacechar = [ \t\v\f];
  newline = [\r]?[\n];

  escaped_char = [\\][|!"#$%&'()*+,./:;<=>?@[\\\]^_`{}~-];
*/

// Scan an opening gtk-doc code block.
cmark_bufsize_t _scan_open_gtkdoc_code_block(const unsigned char *p)
{
  const unsigned char *marker = NULL;
  const unsigned char *start = p;
/*!re2c
  [|][\[] { return (cmark_bufsize_t)(p - start); }
  .?                        { return 0; }
*/
}

// Scan a language comment
cmark_bufsize_t _scan_language_comment(const unsigned char *p)
{
  const unsigned char *marker = NULL;
  const unsigned char *start = p;
/*!re2c
  "<!-- language=\"" [^`\r\n\x00]* " -->" / [ \t]*[\r\n] { return (cmark_bufsize_t)(p - start); }
  .?                        { return 0; }
*/
}

// Scan a closing gtk-doc code block.
cmark_bufsize_t _scan_close_gtkdoc_code_block(const unsigned char *p)
{
  const unsigned char *marker = NULL;
  const unsigned char *start = p;
/*!re2c
  [\]][|] / [ \t]*[\r\n] { return (cmark_bufsize_t)(p - start); }
  .?                        { return 0; }
*/
}
