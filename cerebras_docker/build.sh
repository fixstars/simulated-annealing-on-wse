#!/bin/sh
set -e

SCRIPT_DIR="$( cd "$( dirname "$0" )"; pwd )"
cd "${SCRIPT_DIR}"

if [ -e ./Cerebras-SDK.tar.gz ]; then
  docker build \
    --build-arg UID="$(id -u)" \
    --build-arg GID="$(id -g)" \
    --tag cerebras:${USER} .
else
  echo "Please place the tar.gz of the Cerebras SDK in cerebras_docker directory under the name 'Cerabras SDK.tar.gz'."
  exit 1
fi
