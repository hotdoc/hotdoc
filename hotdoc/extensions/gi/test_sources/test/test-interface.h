#ifndef __TEST_INTERFACE_H__
#define __TEST_INTERFACE_H__

#include <glib-object.h>
#include "test-greeter.h"

/**
 * SECTION:test-interface.h
 * @short_description: Just a test GObject interface
 * @title: Test Interface
 *
 * Testing GObject interfaces definition.
 */

G_BEGIN_DECLS

#define TEST_TYPE_INTERFACE test_interface_get_type ()


/**
 * TestInterface:
 *
 * Opaque #TestInterface data structure.
 */
G_DECLARE_INTERFACE (TestInterface, test_interface, TEST, INTERFACE, GObject)

/**
 * TestInterfaceInterface:
 * @parent: parent interface type
 * @do_something: virtual method to do something.
 *
 * #TestInterface interface.
 */
struct _TestInterfaceInterface
{
  GTypeInterface parent_iface;

  void (*do_something) (TestInterface  *self,
                        GError         **error);
};

void test_interface_do_something (TestInterface  *self,
                           			  GError         **error);

G_END_DECLS

#endif
