#!/bin/bash
# Install native dependencies needed to build hotdoc wheels inside the
# manylinux_2_28 (AlmaLinux 8) container used by cibuildwheel.
set -euxo pipefail

dnf install -y 'dnf-command(config-manager)'
dnf config-manager --set-enabled powertools
dnf install -y glib2-devel libxml2-devel json-glib-devel cmake flex
dnf module install -y nodejs:18
