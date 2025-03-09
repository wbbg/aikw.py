#! /bin/env sh
#
# set VENV and PYFILE according to project relative to project dir
#
VENV=.venv
PYFILE=aikw.py

## start with venv activated ####

PROJECTDIR=$(dirname $0)
VENVDIR=${PROJECTDIR}/${VENV}
RUN="python ${PROJECTDIR}/${PYFILE} $@"

if [ -d ${VENVDIR} ]; then
  export PATH="${VENVDIR}/bin:$PATH"
  ${RUN}
else
  echo directory ${VENVDIR} not found
exit
fi

## vim: sw=2
