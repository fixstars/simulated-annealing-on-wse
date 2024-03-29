#!/bin/sh
set -eux
width=4
height=8
cslc ./layout.csl \
    --fabric-dims=$((width + 7)),$((height + 2)) \
    --fabric-offsets=4,1 \
    --params=Num:6,width:$width,height:$height,max_iters:16,T:1000 \
    --params=MEMCPYH2D_DATA_1_ID:0,MEMCPYD2H_DATA_1_ID:1 \
    -o out --memcpy --channels 1
cs_python run.py --name out
