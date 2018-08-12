#include "test-interface.h"

/**
 * TestInterface::TestInterface:
 *
 * Documenting the TestInterface interface.
 */

G_DEFINE_INTERFACE (TestInterface, test_interface, TEST_TYPE_GREETER);

static void
test_interface_default_init (TestInterfaceInterface *iface)
{
}

/**
 * test_interface_do_something:
 * @self: the instance
 * @error: pointer to a #GError
 *
 * This will make @self do something, can't swear what.
 */
void
test_interface_do_something (TestInterface  *self,
                      			 GError         **error)
{
  TestInterfaceInterface *iface;

  g_return_if_fail (TEST_IS_INTERFACE (self));
  g_return_if_fail (error == NULL || *error == NULL);

  iface = TEST_INTERFACE_GET_IFACE (self);
  g_return_if_fail (iface->do_something != NULL);
}
