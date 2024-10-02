#!/bin/sh
set -eu
print_help() {
    echo "usage: commands.sh [-r] [-h] [-c config_path]"
    echo "    options:"
    echo "        -r                run in real environment"
    echo "        -c config_path    set config file(TOML) path"
    echo "        -h                show this help message and exit"
}
run_env=simurator
config_path=src/config.toml
while getopts rhc: OPT; do
    case $OPT in
        r) run_env=real;;
        c) config_path=$OPTARG;;
        h) print_help; exit 0;;
        *) echo "unkown option $OPT"; print_help; exit 1;;
    esac
done

SCRIPT_DIR="$( cd "$( dirname "$0" )"; pwd )"
cd "${SCRIPT_DIR}"
if ! command -v sdk_debug_shell >/dev/null; then
    echo "sdk_debug_shell not found"
    exit 1
fi
sif_path="$(dirname "$(command -v sdk_debug_shell)")/sdk-cbcore-202406260214-3-f03c8e31.sif"
if ! singularity instance list | grep cerebras >/dev/null; then
    singularity instance start $sif_path cerebras
fi
if ! singularity exec instance://cerebras python -c "import tomli" >/dev/null 2>&1; then
    singularity exec instance://cerebras pip install tomli
fi
if [ $run_env = "real" ]; then
    singularity exec instance://cerebras python src/build.py \
        --name out --config "$config_path" --real
    flock /tmp/run_cs2.lock singularity exec instance://cerebras python src/run.py \
        --name out --config "$config_path" --cmaddr 192.168.0.199:9000
else
    singularity exec instance://cerebras python src/build.py --name out --config "$config_path"
    singularity exec instance://cerebras python src/run.py --name out --config "$config_path"
fi
