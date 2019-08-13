#!/bin/sh -e

curl -sL https://rpm.nodesource.com/setup_10.x | bash -
yum install -y nodejs libxml2-devel libxslt-devel libyaml-devel clang-devel llvm-devel glib2-devel flex gettext-devel

PPATH=$PATH

cd /hotdoc/

echo "FIXME build sdist as soon as meson 0.52 is release with https://github.com/mesonbuild/meson/pull/5738"
# export PATH=/opt/python/cp35-cp35m/bin/:$PPATH
# pip install pep517
# export MESON_ARGS="-Dglib:selinux=disabled -Dglib:libmount=false"
# python -m pep517.build -s /hotdoc/

for PYBIN in /opt/python/cp3*/bin; do
    if [[ $PYBIN == *"cp34"* ]]; then
        echo "Skipping py34 as it is not supported."
        continue
    fi
    if [[ $PYBIN == *"cp35"* ]]; then
        echo "Skipping py35 as it is not supported."
        continue
    fi
    echo "Building against ${PYBIN}"
    export PATH=${PYBIN}:$PPATH
    export MESON_ARGS="-Ddefault_library=static -Dglib:selinux=disabled -Dglib:libmount=false -Dpython=${PYBIN}/python"
    ${PYBIN}/pip wheel -w dist/ /hotdoc/
done

for whl in dist/*.whl; do
    auditwheel repair "$whl" --plat manylinux2010_x86_64 -w dist/
done

ls dist/