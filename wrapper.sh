#!/bin/bash

# "all-in-one" wrapper scripts around our CLI (and tox)

self=$(basename $0)

[ -d venv ] || python3 -m venv venv

if [ requirements.in -nt requirements.txt ] || [ dev-requirements.in -nt dev-requirements.txt ]
then
  venv/bin/pip install pip-tools
  venv/bin/pip-compile requirements.in
  venv/bin/pip-compile dev-requirements.in
fi

[ -x venv/bin/JsonExpandOMatic ] || venv/bin/pip install -e .

if [ ${self} = 'wrapper.sh' ] ; then
  for thing in expand contract tox ; do ln -f ${self} ${thing}.sh ; done
  exit 0
fi

if [ ${self} = 'tox.sh' ]
then
  [ -x venv/bin/tox ] || venv/bin/pip install tox
  exec venv/bin/tox "$@"
fi

exec venv/bin/JsonExpandOMatic "${self/.sh}" "$@"
