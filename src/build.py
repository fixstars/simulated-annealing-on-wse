#!/usr/bin/env python
import argparse
import subprocess
from pathlib import Path

import tomli


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', help="the test compile output dir")
    parser.add_argument('--real', '-r', action="store_true", help="run in real environment")
    parser.add_argument('--config', '-c', help="config file")
    return parser.parse_args()


def build(name, params, simulator):
    block_width = int(params["block_width"])
    block_height = int(params["block_height"])
    grid_width = int(params["grid_width"])
    grid_height = int(params["grid_height"])
    if simulator:
        # see https://sdk.cerebras.net/tensor-streaming.html
        # 7 = 1(left halo) + 3(left memcpy) + 2(right memcpy) + 1(right halo)
        # 2 = 1(top halo) + 1(bottom halo)
        width = block_width * grid_width + 7
        height =block_height * grid_height + 2
    else:
        width = 757
        height = 996
    args = []
    args.append("sdk_debug_shell")
    args.append("compile")
    args.append(str(Path(__file__).parent / "layout.csl"))
    args.append(f"--fabric-dims={width},{height}")
    args.append("--fabric-offsets=4,1")
    for key in ["Num", "block_height", "block_width", "grid_height", "grid_width", "max_iters", "time_constant", "log_init_temperature"]:
        val = params[key]
        args.append(f"--params={key}:{val}")
    args.append("--params=MEMCPYH2D_DATA_1_ID:0")
    args.append("--params=MEMCPYD2H_DATA_1_ID:1")
    args.append(f"-o={name}")
    args.append("--memcpy")
    args.append("--channels=1")
    print(args)
    subprocess.run(args, check=True)


def main():
    args = parse_args()

    with open(args.config, "rb") as f:
        config = tomli.load(f)
    params = config['params']

    build(args.name, params, not args.real)


if __name__ == '__main__':
    main()
