#include <HsFFI.h>

void doc_translator_init (void)
{
  static char *argv[] = { "libConvert.so", 0 }, **argv_ = argv;
  static int argc = 1;
  hs_init(&argc, &argv_);
}

void doc_translator_destroy (void)
{
  hs_exit();
}

