#!/bin/bash
# Install native dependencies needed to build hotdoc wheels on macOS.
# Homebrew installs libxml2's pkg-config files in a keg-only prefix, so link
# them into the main Homebrew prefix where pkg-config will find them.
set -euxo pipefail

brew install glib libxml2 json-glib cmake
ln -sf "$(brew --prefix libxml2)"/lib/pkgconfig/*.pc "$(brew --prefix)/lib/pkgconfig/"
