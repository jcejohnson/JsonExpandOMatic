#!/bin/bash

# "all-in-one" wrapper scripts around our CLI (and tox)

self=$(basename $0)

# This supposedly makes pip faster in WSL.
export DISPLAY=

venv=${VENV:-.venv}

if [ ! -d ${venv} ] ; then
  (
    set -x
    python3 -m venv ${venv}
    ${venv}/bin/pip install --upgrade pip
    ${venv}/bin/pip install pip-tools
  )
fi

[ -x ${venv}/bin/JsonExpandOMatic ] || (set -x ; ${venv}/bin/pip install -e '.[all]')

case ${self} in

  bumpversion.sh)
    exec ${venv}/bin/bumpversion "$@"
    ;;

  tox.sh)
    which tox >/dev/null || [ -x ${venv}/bin/tox ] || (set -x ; ${venv}/bin/pip install tox)
    [ ! -x ${venv}/bin/tox ] || exec ${venv}/bin/tox "$@"
    exec tox "$@"
    ;;

  wrapper.sh)
    for thing in expand contract bumpversion tox; do ln -vf ${self} ${thing}.sh ; done
    exit 0
    ;;
esac

exec ${venv}/bin/JsonExpandOMatic "${self/.sh}" "$@"
