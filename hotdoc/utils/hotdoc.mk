# hotdoc.mk
#
# Copyright 2016 Mathieu Duponchelle <mathieu.duponchelle@opencreed.com>.
# Copyright 2016 Collabora Ltd.
# Written by Mathieu Duponchelle
#
# Copying and distribution of this file, with or without modification,
# is permitted in any medium without royalty provided the copyright
# notice and this notice are preserved.
#
# The latest version of this file is maintained in hotdoc itself, at
# <https://github.com/hotdoc/hotdoc/blob/master/hotdoc/utils/hotdoc.mk>
#
# This Makefile fragment is intended to be used in conjunction with
# <https://github.com/hotdoc/hotdoc/blob/master/hotdoc/utils/hotdoc.m4>.
# It is advised not to check it in the project's sources but, if hotdoc
# has been verified to be present, to include it through the
# `--makefile-path` argument to hotdoc, like so:
#
# ```
# if ENABLE_DOCUMENTATION
# -include $(HOTDOC_MAKEFILE)
# endif
# ```
#
# An implementation of GNU make is required to take advantage of this
# fragment, and automake should be inited with `-Wno-portability` in
# order to avoid configure-time warnings.
#
# ## Parsed Variables
#
# The public variables used in this fragment are:
#
# * `HOTDOC_PROJECTS`, which must be a list of project names, for
#   example `HOTDOC_PROJECTS = lib1 lib2`. Each project's html documentation
#   will be installed in `$(DESTDIR)$(htmldir)/$(project_name)`.
#
# * `$(project_name)_HOTDOC_FLAGS`, which must list arguments that should
#   be used to invoke hotdoc for one project name, for example
#   `lib1_HOTDOC_FLAGS = --index index.markdown --sitemap sitemap.txt`.
#   For each project name listed in `HOTDOC_PROJECTS` there must be a
#   pending `$(project_name)_HOTDOC_FLAGS` variable set to a non-empty
#   string, otherwise this fragment will error out.
#
# * `$(project_name)_HOTDOC_EXTRA_DEPS`, which may list additional
#   dependencies for building the documentation, for example:
#
#   ```
#   lib1_HOTDOC_EXTRA_DEPS = lib1.gir
#   ```
#
#   will ensure `lib1.gir` was generated before hotdoc is invoked for `lib1`.
#
# * `HOTDOC_FLAGS`, which may list extra arguments passed by the user of
#   the calling Makefile, for example `make HOTDOC_FLAGS="-vv"` will make
#   the hotdoc invocation extra verbose. The user of the Makefile may use
#   this argument to override default values set by the maintainer of the
#   Makefile.
#
# ## Exposed functions
#
# * `HOTDOC_TARGET $(project_name)` may be used in the calling Makefile
#   to retrieve the name of the built target, in order for example to
#   add it to GITIGNOREFILES if the project uses git.mk.
#
# * `HOTDOC_PROJECT_COMMAND $(project_name)` may be used to obtain the
#   command invoked by this fragment to build `$(project_name)`, in
#   order for example to query hotdoc for the location of its private
#   folder, or its output directory, for example:
#   `$(call HOTDOC_PROJECT_COMMAND,lib1) --get-conf-path output`.

$(if $(HOTDOC),,$(error Need to define HOTDOC))

HOTDOC_TARGET = HOTDOC-$(addsuffix .stamp, $(_HOTDOC_PROJECT_NAME))
HOTDOC_PROJECT_COMMAND = $(HOTDOC) $($(_HOTDOC_PROJECT_NAME)_HOTDOC_FLAGS) $(HOTDOC_FLAGS)

# Private constants

_HOTDOC_DEPDIR := $(top_builddir)/.hotdoc.d

# Private functions

_HOTDOC_PROJECT_NAME = $(subst /,_,$(subst -,_,$(subst .,_,$(1))))
_HOTDOC = $(call HOTDOC_PROJECT_COMMAND,$(1))
_HOTDOC_TARGET = $(call HOTDOC_TARGET,$(1))
_HOTDOC_DEPFILE = $(_HOTDOC_DEPDIR)/$(addsuffix .d, $(1))
_HOTDOC_DEVHELP_DIR = $(shell $(_HOTDOC) --get-conf-path output)/devhelp
_HOTDOC_DEVHELP_SUBDIRS = $(wildcard $(_HOTDOC_DEVHELP_DIR)/*)

define hotdoc-rules

$(if $($(_HOTDOC_PROJECT_NAME)_HOTDOC_FLAGS),,$(error Need to define $(_HOTDOC_PROJECT_NAME)_HOTDOC_FLAGS))

$(_HOTDOC_TARGET): Makefile $($(_HOTDOC_PROJECT_NAME)_HOTDOC_EXTRA_DEPS)
$(_HOTDOC_TARGET): Makefile $($(_HOTDOC_PROJECT_NAME)_HOTDOC_EXTRA_DEPS) $(_HOTDOC_DEPFILE)
	$$(AM_V_GEN) \
	set -e ; \
	$(_HOTDOC) run \
		--deps-file-dest $(_HOTDOC_DEPFILE) \
	        --deps-file-target $$@; \
	touch $$@ ;

all: $(_HOTDOC_TARGET)

-include $(_HOTDOC_DEPFILE)

install-$(_HOTDOC_TARGET)-html: $(_HOTDOC_TARGET)
	@set -e ; \
	archive_name=`mktemp -p .` ; \
	hotdoc_html_dir=`$(_HOTDOC) --get-conf-path output`/html ; \
	if [ -d "$$$$hotdoc_html_dir" ]; then \
	  dest_subdir=$(DESTDIR)$(htmldir)/$(1) ; \
	  $$(AMTAR) -C "$$$$hotdoc_html_dir" --mode="u=rwX,og=r-X" -cf $$$$archive_name . ; \
          $(mkinstalldirs) $$$$dest_subdir ; \
          $$(AMTAR) -C $$$$dest_subdir -p -xf $$$$archive_name ; \
	  echo "Installed html documentation in $$$$dest_subdir" ; \
       else \
	  echo "Nothing to install in $$$$hotdoc_html_dir" ; \
       fi; \
       rm -f $$$$archive_name ;

install-$(_HOTDOC_TARGET)-devhelp: $(_HOTDOC_TARGET)
	@set -e ; \
	archive_name=`mktemp -p .` ; \
	hotdoc_devhelp_dir=`$(_HOTDOC) --get-conf-path output`/devhelp ; \
	dest_subdir=$(DESTDIR)$(prefix)/share/devhelp/books ; \
	\
	if [ -d "$$$$hotdoc_devhelp_dir" ]; then \
	  $$(AMTAR) -C "$$$$hotdoc_devhelp_dir" --mode="u=rwX,og=r-X" -cf $$$$archive_name . ; \
          $(mkinstalldirs) $$$$dest_subdir ; \
          $$(AMTAR) -C $$$$dest_subdir -p -xf $$$$archive_name ; \
	  echo "Installed devhelp books in $$$$dest_subdir" ; \
	else \
	  echo "Nothing to install in $$$$hotdoc_devhelp_dir" ; \
	fi; \
	rm -f $$$$archive_name ;

install: install-$(_HOTDOC_TARGET)-html install-$(_HOTDOC_TARGET)-devhelp

clean-$(_HOTDOC_TARGET):
	rm -rf `$(_HOTDOC) --get-conf-path output` ; \
	rm -f $(_HOTDOC_TARGET)

clean: clean-$(_HOTDOC_TARGET)

distclean: clean-$(_HOTDOC_TARGET)

uninstall-hotdoc-$(_HOTDOC_TARGET)-devhelp:
	for subdir in $(_HOTDOC_DEVHELP_SUBDIRS); do \
	  rm -rf $(DESTDIR)$(prefix)/share/devhelp/books/`basename $$$$subdir` ; \
	done

uninstall-hotdoc-$(_HOTDOC_TARGET)-html:
	@rm -rf $(DESTDIR)$(htmldir)/$(1)

uninstall: uninstall-hotdoc-$(_HOTDOC_TARGET)-devhelp uninstall-hotdoc-$(_HOTDOC_TARGET)-html

.PHONY: uninstall-hotdoc-$(_HOTDOC_TARGET)-html uninstall-hotdoc-$(_HOTDOC_TARGET)-devhelp clean-$(_HOTDOC_TARGET) install-$(_HOTDOC_TARGET)-devhelp install-$(_HOTDOC_TARGET)-html

endef

$(_HOTDOC_DEPDIR)/%.d: ;
.PRECIOUS: $(_HOTDOC_DEPDIR)/%.d

clean-hotdoc:
	rm -rf $(_HOTDOC_DEPDIR)
	rm -rf hotdoc-private-*

clean: clean-hotdoc

distclean: clean-hotdoc

.PHONY: clean-hotdoc

$(foreach project, $(HOTDOC_PROJECTS),$(eval $(call hotdoc-rules,$(project))))
