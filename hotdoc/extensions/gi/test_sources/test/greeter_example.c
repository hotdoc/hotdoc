#include "test-greeter.h"

void include_an_example_symbol (void);

void
include_an_example_symbol (void)
{
  TestGreeter * greeter =  g_object_new (TEST_TYPE_GREETER, NULL);

  /* Just some ellipsized text */

  test_greeter_greet (greeter, "Greet me please.", NULL);
}
