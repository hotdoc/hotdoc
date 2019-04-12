/* Copyright (c) 2012 Artem Shinkarov <artyom.shinkaroff@gmail.com>
   Permission to use, copy, modify, and distribute this software for any
   purpose with or without fee is hereby granted, provided that the above
   copyright notice and this permission notice appear in all copies.
   THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
   WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
   MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
   ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
   WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
   ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
   OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.  */

/* Mathieu Duponchelle <mathieu@centricular.com> 2018:
 *   - Added encoding method
 */

#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <arpa/inet.h> /* For htonl */
#include <glib.h>

#include "trie.h"

#define TRIE_CHILDREN 4
#define TRIE_NOT_LAST	-1

struct child
{
  int symb;
  ssize_t last;
  struct trie *next;
  unsigned int bft_id;
  unsigned int bft_last;
};

struct trie
{
  unsigned int children_size;
  unsigned int children_count;
  struct child *children;
};

/* Allocate a new empty trie.  */
struct trie *
trie_new ()
{
  struct trie *trie = (struct trie *) malloc (sizeof (struct trie));
  trie->children_size = TRIE_CHILDREN;
  trie->children_count = 0;
  trie->children = (struct child *)
      malloc (TRIE_CHILDREN * sizeof (struct child));
  memset (trie->children, 0, TRIE_CHILDREN * sizeof (struct child));
  return trie;
}


/* Helper for bsearch and qsort.  */
static inline int
cmp_children (const void *k1, const void *k2)
{
  struct child *c1 = (struct child *) k1;
  struct child *c2 = (struct child *) k2;
  return c1->symb - c2->symb;
}


/* Search for a symbol in a children of a certain trie.  Uses binary search
   as the children are kept sorted.  */
static struct child *
trie_search_child (struct trie *trie, int symb)
{
  struct child s;

  if (trie->children_count == 0)
    return NULL;

  s.symb = symb;
  return (struct child *) bsearch (&s, trie->children, trie->children_count,
      sizeof (struct child), cmp_children);
}

/* Add a word to the trie.  */
void
trie_add_word (struct trie *trie, const char *word, size_t length, ssize_t info)
{
  struct child *child;
  struct trie *nxt = NULL;

  child = trie_search_child (trie, word[0]);

  if (child) {
    if (length == 1)
      child->last = info;
    if (length > 1 && child->next == NULL)
      child->next = trie_new ();

    nxt = child->next;
  } else {
    if (trie->children_count >= trie->children_size) {
      trie->children_size *= 2;
      trie->children = (struct child *)
          realloc (trie->children, trie->children_size * sizeof (struct child));
    }

    trie->children[trie->children_count].symb = word[0];
    if (length > 1) {
      trie->children[trie->children_count].next = trie_new ();
      trie->children[trie->children_count].last = TRIE_NOT_LAST;
    } else {
      trie->children[trie->children_count].next = NULL;
      trie->children[trie->children_count].last = info;
    }

    nxt = trie->children[trie->children_count].next;
    trie->children_count++;

    /* XXX This qsort may not perform ideally, as actually we are always
       just shifting a number of elements a the end of the array one
       element to the left.  Possibly qsort, can figure it out and work
       in O (N) time.  Otherwise better alternative is needed.  */
    qsort (trie->children, trie->children_count,
        sizeof (struct child), cmp_children);
  }

  if (length > 1)
    trie_add_word (nxt, &word[1], length - 1, info);
}

void
trie_free (struct trie *trie)
{
  unsigned int i;
  if (!trie)
    return;

  for (i = 0; i < trie->children_count; i++)
    trie_free (trie->children[i].next);

  if (trie->children)
    free (trie->children);
  free (trie);
}

/* From web.mit.edu/freebsd/head/contrib/wpa/src/utils/base64.c, BSD license */

static const unsigned char base64_table[65] =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

static unsigned char *
base64_encode (const unsigned char *src, size_t len, size_t * out_len)
{
  unsigned char *out, *pos;
  const unsigned char *end, *in;
  size_t olen;

  olen = len * 4 / 3 + 4;       /* 3-byte blocks to 4-byte */
  olen++;                       /* nul termination */
  if (olen < len)
    return NULL;                /* integer overflow */
  out = malloc (olen);
  if (out == NULL)
    return NULL;

  end = src + len;
  in = src;
  pos = out;
  while (end - in >= 3) {
    *pos++ = base64_table[in[0] >> 2];
    *pos++ = base64_table[((in[0] & 0x03) << 4) | (in[1] >> 4)];
    *pos++ = base64_table[((in[1] & 0x0f) << 2) | (in[2] >> 6)];
    *pos++ = base64_table[in[2] & 0x3f];
    in += 3;
  }

  if (end - in) {
    *pos++ = base64_table[in[0] >> 2];
    if (end - in == 1) {
      *pos++ = base64_table[(in[0] & 0x03) << 4];
      *pos++ = '=';
    } else {
      *pos++ = base64_table[((in[0] & 0x03) << 4) | (in[1] >> 4)];
      *pos++ = base64_table[(in[1] & 0x0f) << 2];
    }
    *pos++ = '=';
  }

  *pos = '\0';
  if (out_len)
    *out_len = pos - out;
  return out;
}

static void
write_out_trie (unsigned int *res, unsigned int len, const char *trie_path, const char *trie_js_path)
{
  unsigned char *b64;
  FILE *f;

  f = fopen (trie_path, "wb");
  fwrite (res, sizeof (unsigned int), len, f);
  fclose (f);

  f = fopen (trie_js_path, "w");
  fwrite ("var trie_data=\"", sizeof (char), 15, f);
  b64 =
      base64_encode ((const unsigned char *) res, len * sizeof (unsigned int),
      NULL);
  fwrite (b64, sizeof (char), strlen ((const char *) b64), f);
  free (b64);
  fwrite ("\";", sizeof (char), 2, f);
  fclose (f);
}

void
trie_encode (struct trie *t, const char *trie_path, const char *trie_js_path)
{
  GList *unrolled = NULL;
  GList *tmp;
  unsigned int bft_id = 1;
  unsigned int i;
  unsigned int len = 1;
  unsigned int *res = NULL;
  GQueue *q = g_queue_new();

  for (i = 0; i < t->children_count; i++) {
    g_queue_push_tail (q, &(t->children[i]));
    t->children[i].bft_id = bft_id++;
    t->children[i].bft_last = (i + 1 == t->children_count);
  }

  while (!g_queue_is_empty(q)) {
    struct child *node = g_queue_pop_head(q);

    if (node->next) {
      for (i = 0; i < node->next->children_count; i++) {
        g_queue_push_tail (q, &node->next->children[i]);
        node->next->children[i].bft_id = bft_id++;
        node->next->children[i].bft_last =
            (i + 1 == node->next->children_count);
      }
    }

    unrolled = g_list_prepend (unrolled, node);
    len++;
  }

  g_queue_free (q);

  res = malloc (sizeof (unsigned int) * len);
  res[0] = 1 << 9;
  res[0] |= (1 << 8);
  res[0] |= 30;
  res[0] = htonl (res[0]);

  i = 1;

  for (tmp = g_list_last(unrolled); tmp; tmp = tmp->prev) {
    struct child *node = tmp->data;
    unsigned int first_child_id = 0;
    unsigned int *encoded = &res[i++];

    if (node->next)
      first_child_id = node->next->children[0].bft_id;

    *encoded = first_child_id << 9;
    if (node->bft_last)
      *encoded |= (1 << 8);
    if (node->last != TRIE_NOT_LAST)
      *encoded |= (1 << 7);
    *encoded |= node->symb;
    *encoded = htonl (*encoded);
  }

  g_list_free (unrolled);

  write_out_trie (res, len, trie_path, trie_js_path);

  free (res);
}
