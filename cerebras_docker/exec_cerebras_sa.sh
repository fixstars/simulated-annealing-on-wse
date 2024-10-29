#!/bin/sh
set -e
print_help() {
    echo "usage: exec_cerebras_sa.sh [-p port] [-h]"
    echo "    options:"
    echo "        -p port           visualizer port (default to 50000)"
    echo "        -h                show this help message and exit"
}
visualizer_port=50000
while getopts hp: OPT; do
    case $OPT in
        p) visualizer_port=$OPTARG;;
        h) print_help; exit 0;;
        *) echo "unkown option $OPT"; print_help; exit 1;;
    esac
done

# check visualizer port usage
if ss -tuln | grep -q ":$visualizer_port\b"; then
  echo "Port $visualizer_port is in use."
  echo "Please set another port with the p option."
  print_help;
  exit 1
fi

SCRIPT_DIR="$( cd "$( dirname "$0" )"; pwd )"
cd "${SCRIPT_DIR}"

docker run \
       -it \
       --rm \
       --privileged \
       --name cerebras-${USER} \
       --env-file "${SCRIPT_DIR}/config/cerebras_docker.env" \
       --mount "type=bind,source=$(realpath "${SCRIPT_DIR}"/../),target=/home/cerebras/cerebras_sa/" \
       -p $visualizer_port:8000 \
       cerebras:${USER} \
       /bin/bash -c "\$HOME/cerebras_sa/commands.sh -c \$HOME/cerebras_sa/config/small.toml"
