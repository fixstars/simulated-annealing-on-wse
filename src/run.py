#!/usr/bin/env cs_python

import argparse
import numpy as np
import json
import struct
import time

from cerebras.sdk.runtime.sdkruntimepybind import SdkRuntime, MemcpyDataType, MemcpyOrder # pylint: disable=no-name-in-module

# Read arguments
parser = argparse.ArgumentParser()
parser.add_argument('--name', help="the test compile output dir")
parser.add_argument('--cmaddr', help="IP:port for CS system")
args = parser.parse_args()

with open(f"{args.name}/out.json", encoding='utf-8') as json_file:
    compile_data = json.load(json_file)

Num = int(compile_data['params']['Num'])
width = int(compile_data['params']['width'])
height = int(compile_data['params']['height'])
MEMCPYH2D_DATA_1 = int(compile_data['params']['MEMCPYH2D_DATA_1_ID'])
MEMCPYD2H_DATA_1 = int(compile_data['params']['MEMCPYD2H_DATA_1_ID'])
inputs_len = Num * (Num + 1) // 2

# Construct a runner using SdkRuntime
runner = SdkRuntime(args.name, cmaddr=args.cmaddr)

rng = np.random.default_rng(42)
inputs = rng.uniform(-1.0, 1.0, inputs_len)
inputs = np.asarray(inputs, dtype=np.float32)
print(f"inputs = {inputs}")
best_s = np.zeros([Num + 1], dtype=np.int32)

st = time.time_ns()
# Load and run the program
runner.load()
runner.run()

# Streams inputs from host to upper left node
runner.memcpy_h2d(MEMCPYH2D_DATA_1, inputs, 0, 0, 1, 1, inputs_len, streaming=True,
  order=MemcpyOrder.ROW_MAJOR, data_type=MemcpyDataType.MEMCPY_32BIT, nonblock=False)

# Streams best_s from lower right node to host
runner.memcpy_d2h(best_s, MEMCPYD2H_DATA_1, width - 1, height - 1, 1, 1, Num + 1, streaming=True,
  order=MemcpyOrder.ROW_MAJOR, data_type=MemcpyDataType.MEMCPY_32BIT, nonblock=False)

# Stop the program
runner.stop()
et = time.time_ns()
print(f"{(et - st) / 1e9}s")

print(f"best_s = {best_s[0:Num]}")
f = struct.unpack('f', struct.pack('i', best_s[Num])) # int32 -> float32
print(f"energy = {f[0]}")
