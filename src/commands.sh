#!/bin/sh
set -eux
SCRIPT_DIR="$( cd "$( dirname "$0" )"; pwd )"
cd "${SCRIPT_DIR}"
if ! command -v sdk_debug_shell >/dev/null; then
    echo "sdk_debug_shell not found"
    exit 1
fi
sif_path="$(dirname "$(command -v sdk_debug_shell)")/sdk-cbcore-202404122356-8-a1162951.sif"
width=${SA_WIDTH:-2}
height=${SA_HEIGHT:-3}
if ! singularity instance list | grep cerebras >/dev/null; then
    singularity instance start $sif_path cerebras
fi
if ! singularity exec instance://cerebras python -c "import amplify" >/dev/null 2>&1; then
    singularity exec instance://cerebras pip install amplify
fi
singularity exec instance://cerebras sdk_debug_shell compile ./layout.csl \
    --fabric-dims=$((width + 7)),$((height + 2)) \
    --fabric-offsets=4,1 \
    --params=Num:6,width:$width,height:$height,max_iters:128,T:100 \
    -o out --memcpy --channels 1

if [ "${SA_DEBUG:-false}" = "false" ]; then
    singularity exec instance://cerebras python run.py --name out --token $AMPLIFY_TOKEN
else
    singularity exec instance://cerebras python run.py --name out --token $AMPLIFY_TOKEN --debug
fi
