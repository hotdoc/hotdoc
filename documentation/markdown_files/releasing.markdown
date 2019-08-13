# Releasing hotdoc

To generate manylinux wheels and sdist, we use the `pypa/manylinux2014_x86_64` docker image,

Generate the wheels and sdist:

    podman run --rm -it -v $PWD:/hotdoc quay.io/pypa/manylinux2014_x86_64 /hotdoc/scripts/manylinux.sh

> NOTE: You need to disable selinux for `-v` to avoid obscude permission issues.

Then you have all the wheels in dist/, you can upload them with:

    twine upload dist/hotdoc.*manylinux.*whl
    twine upload dist/hotdoc.*.tar.gz