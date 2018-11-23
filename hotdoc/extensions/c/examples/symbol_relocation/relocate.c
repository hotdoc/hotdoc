/**
 * SECTION:relocate.h
 * @title: Relocation test
 * @short_description: Symbols will be relocated here
 * @symbols:
 *   - simple_function
 */

/**
 * simple_other_function:
 * @arg1: A string
 *
 * Another simple function
 *
 * Returns: an integer
 */
int simple_other_function(char *arg1)
{
  return 42;
}
