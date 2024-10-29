#!/usr/bin/env python
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

import tomli


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", help="the test compile output dir")
    parser.add_argument("--real", "-r", action="store_true", help="run in real environment")
    parser.add_argument("--config", "-c", help="config file")
    parser.add_argument(
        "--jobs",
        "-j",
        help="Allow N jobs at once",
        default=len(os.sched_getaffinity(0)),
    )
    return parser.parse_args()


def build(name, params, trace, simulator, jobs):
    enable_collector = trace["collector"]["collector_buffer_size"] > 0
    height_offset = 1 if enable_collector else 0

    block_width = int(params["block_width"])
    block_height = int(params["block_height"])
    grid_width = int(params["grid_width"])
    grid_height = int(params["grid_height"])
    if simulator:
        # see https://sdk.cerebras.net/tensor-streaming.html
        # 7 = 1(left halo) + 3(left memcpy) + 2(right memcpy) + 1(right halo)
        # 2 = 1(top halo) + 1(bottom halo)
        width = block_width * grid_width + 7
        height = (block_height + height_offset) * grid_height + 2
    else:
        width = 757
        height = 996
    args = []
    args.append("sdk_debug_shell")
    args.append("compile")
    args.append(str(Path(__file__).parent / "layout.csl"))
    args.append(f"--fabric-dims={width},{height}")
    args.append("--fabric-offsets=4,1")
    for key in ["Num", "block_height", "block_width", "grid_height", "grid_width"]:
        val = params[key]
        args.append(f"--params={key}:{val}")
    for key in ["trace_buffer_size"]:
        val = trace["tracer"][key]
        args.append(f"--params={key}:{val}")
    for key in ["collector_buffer_size"]:
        val = trace["collector"][key]
        args.append(f"--params={key}:{val}")
    args.append(f"--params=enable_simprint:{int(simulator)}")
    args.append("--params=MEMCPYH2D_DATA_1_ID:0")
    args.append("--params=MEMCPYD2H_DATA_1_ID:1")
    args.append(f"-o={name}")
    args.append("--memcpy")
    args.append("--channels=1")
    args.append(f"--max-parallelism={jobs}")
    print(args)
    try:
        process = subprocess.Popen(args)
        while process.poll() is None:
            time.sleep(0.1)
        stdout, stderr = process.communicate()
        return_code = process.returncode
        if return_code != 0:
            raise subprocess.CalledProcessError(return_code, args, output=stdout, stderr=stderr)
    except (KeyboardInterrupt, subprocess.CalledProcessError):
        print("Build failed. Cleanup...")
        shutil.rmtree(name)
        return False
    return True


def calc_hash(file: Path):
    h = hashlib.sha256()
    with file.open("rb") as f:
        while True:
            data = f.read(4096)
            if len(data) == 0:
                break
            h.update(data)
    return h.hexdigest()


def need_build(name, simulator, config_params):
    # check build directory
    if not os.path.exists(f"{name}/out.json"):
        print(f"No pre build directory. {name}")
        return True
    # check real or simulator
    if not os.path.exists(f"{name}/run_env.txt"):
        print(f"No run_env file : {name}/run_env.txt")
        return True
    with open(f"{name}/run_env.txt", "r") as f:
        run_env = f.readline().strip()
    if run_env == "real":
        if simulator:
            print("Detect run_env change : real->simulator")
            return True
    elif run_env == "simulator":
        if not simulator:
            print("Detect run_env change : simulator->real")
            return True
    else:
        # invalid env
        run_env = "simulator" if simulator else "real"
        print("Detect run_env change : Invalid->{run_env}")
        return True
    # check code changes
    if not os.path.exists(f"{name}/src_hash.txt"):
        print(f"No src_hash file : {name}/src_hash.txt")
        return True
    with open(f"{name}/src_hash.txt", "r", encoding="utf-8") as f:
        hash_info = f.readlines()
    r = re.compile(r"(^[0-9A-Fa-f]+)\s+(\S.*)$")
    for line in hash_info:
        m = r.match(line)
        if not m:
            continue
        expect_hash = m.group(1)
        file_name = m.group(2)
        if calc_hash(Path(file_name)) != expect_hash:
            # Detect changes
            print("Detect src changes.")
            return True

    # check parameter
    with open(f"{name}/out.json", encoding="utf-8") as json_file:
        compile_params: dict[str, str] = json.load(json_file)["params"]

    mod_config_params = dict()
    mod_config_params.update(**config_params["params"])
    mod_config_params.update(**config_params["trace"]["tracer"])
    mod_config_params.update(**config_params["trace"]["collector"])
    # convert value type to str
    for key in mod_config_params.keys():
        mod_config_params[key] = str(mod_config_params[key])
    for compile_param in compile_params.items():
        if compile_param[0].startswith("MEMCPY") or compile_param[0] == "enable_simprint":
            # skip
            continue
        if compile_param not in mod_config_params.items():
            # Detect changes
            print("Detect static param changes.")
            return True
    print("Detect no changes. Skip Build")
    return False


def update_run_env(name, simulator):
    run_env = "simulator" if simulator else "real"
    with open(f"{name}/run_env.txt", "w+") as f:
        f.write(f"{run_env}\n")


def update_csl_hash(name):
    hash_info = []
    src_dir = Path(__file__).parent
    for csl_file in src_dir.glob("**/*.csl"):
        hash = calc_hash(csl_file)
        hash_info.append((str(csl_file), hash))
    with open(f"{name}/src_hash.txt", "w+") as f:
        for src, hash in hash_info:
            f.write(f"{hash} {src}\n")


def main():
    args = parse_args()

    with open(args.config, "rb") as f:
        config_params = tomli.load(f)
    if need_build(args.name, not args.real, config_params):
        params = config_params["params"]
        trace = config_params["trace"]
        if build(args.name, params, trace, not args.real, args.jobs):
            update_run_env(args.name, not args.real)
            update_csl_hash(args.name)


if __name__ == "__main__":
    main()
