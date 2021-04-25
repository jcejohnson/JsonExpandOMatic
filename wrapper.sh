#!/bin/bash

# "all-in-one" wrapper scripts around our CLI (and tox)

self=$(basename $0)

[ -d venv ] || python3 -m venv venv

if [ requirements.in -nt requirements.txt ] || [ dev-requirements.in -nt dev-requirements.txt ]
then
  venv/bin/pip install --upgrade pip
  venv/bin/pip install pip-tools
  venv/bin/pip-compile requirements.in
  venv/bin/pip-compile dev-requirements.in
fi

[ -x venv/bin/JsonExpandOMatic ] || venv/bin/pip install -e .

case ${self} in

  bumpversion.sh)
    exec venv/bin/bumpversion "$@"
    ;;

  tox.sh)
    [ -x venv/bin/tox ] || venv/bin/pip install tox
    exec venv/bin/tox "$@"
    ;;

  wrapper.sh)
    for thing in expand contract tox bumpversion ; do ln -f ${self} ${thing}.sh ; done
    exit 0
    ;;
esac

if [[ "$1" =~ --* ]] ; then
  exec venv/bin/JsonExpandOMatic "$@"
fi

exec venv/bin/JsonExpandOMatic "${self/.sh}" "$@"
