#!/bin/bash

# "all-in-one" wrapper scripts around our CLI (and tox)

self=$(basename $0)

if [ ! -d venv ] ; then
  (set -x ; python3 -m venv venv)
  # Force an update of *requirements.txt for _this_ version of python
  # (for instance, 3.6 will want dataclasses==0.8 but that fails for 3.8)
  touch requirements.in dev-requirements.in
fi

if [ requirements.in -nt requirements.txt ] || [ dev-requirements.in -nt dev-requirements.txt ]
then
  (
    set -x
    venv/bin/pip install --upgrade pip
    venv/bin/pip install pip-tools
    venv/bin/pip-compile requirements.in
    venv/bin/pip-compile dev-requirements.in
  )
fi

[ -x venv/bin/JsonExpandOMatic ] || (set -x ; venv/bin/pip install -e .)

case ${self} in

  bumpversion.sh)
    exec venv/bin/bumpversion "$@"
    ;;

  tox.sh)
    [ -x venv/bin/tox ] || (set -x ; venv/bin/pip install tox)
    exec venv/bin/tox "$@"
    ;;

  wrapper.sh)
    for thing in expand contract tox bumpversion ; do ln -vf ${self} ${thing}.sh ; done
    exit 0
    ;;
esac

if [[ "$1" =~ --* ]] ; then
  exec venv/bin/JsonExpandOMatic "$@"
fi

exec venv/bin/JsonExpandOMatic "${self/.sh}" "$@"
