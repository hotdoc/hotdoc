#ifndef TEST_GOBJECT_MACROS_H_
#define TEST_GOBJECT_MACROS_H_

#include <glib-object.h>

G_BEGIN_DECLS

#define TEST_TYPE_DERIVABLE (test_derivable_get_type ())

/**
 * TestDerivable:
 *
 * A derivable class.
 */
G_DECLARE_DERIVABLE_TYPE (TestDerivable, test_derivable, TEST, DERIVABLE, GObject)

struct _TestDerivableClass
{
  GObjectClass parent_class;

  gpointer _padding[10];
};

/**
 * test_derivable_new:
 *
 * Returns: A newly built derivable object
 */
TestDerivable * test_derivable_new (void);

/**
 * TestFinal:
 *
 * A final class, not meant to be inherited from, declared with convenience
 * macros.
 */

#define TEST_TYPE_FINAL (test_final_get_type ())
G_DECLARE_FINAL_TYPE (TestFinal, test_final, TEST, FINAL, GObject)

TestFinal * test_final_new (void);

G_END_DECLS

#endif
