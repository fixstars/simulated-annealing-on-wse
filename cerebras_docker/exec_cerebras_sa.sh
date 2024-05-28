#!/bin/sh
set -e

SCRIPT_DIR="$( cd "$( dirname "$0" )"; pwd )"
cd "${SCRIPT_DIR}"

docker run \
       -it \
       --rm \
       --privileged \
       --name cerebras-${USER} \
       --env AMPLIFY_TOKEN="$AMPLIFY_TOKEN" \
       --env SA_WIDTH="$SA_WIDTH" \
       --env SA_HEIGHT="$SA_HEIGHT" \
       --mount "type=bind,source=$(realpath "${SCRIPT_DIR}"/../),target=/home/cerebras/cerebras_sa/" \
       cerebras:${USER} \
       /bin/bash -c "\$HOME/cerebras_sa/src/commands.sh"
