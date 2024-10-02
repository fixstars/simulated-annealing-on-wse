#!/usr/bin/env cs_python

import argparse
import numpy as np
import json
import struct
import time
from pathlib import Path

import cerebras.sdk.runtime.sdkruntimepybind as csdk
import tomli


def f32_to_u32(x) -> int:
    return struct.unpack('I', struct.pack('f', x))[0]

def energy(Q, s):
    d = np.array(Q.diagonal(), copy=True)
    U = np.triu(Q) - np.diag(d)
    return s @ U @ s + d.T @ s

# Read arguments
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', help="the test compile output dir")
    parser.add_argument('--cmaddr', help="IP:port for CS system")
    parser.add_argument('--input_dir', help="input directory for Q")
    parser.add_argument('--config', '-c', help="config file")
    return parser.parse_args()

def send_Q(runner, Num, Q, MEMCPYH2D_DATA_1_ID):
    chunk_size = 32766 # Will not work if INT16_MAX or higher.
    rest = Num * Num
    send = 0
    while True:
        if rest >= chunk_size:
            runner.memcpy_h2d(MEMCPYH2D_DATA_1_ID, Q[send:], 0, 0, 1, 1, chunk_size, streaming=True,
                    order=csdk.MemcpyOrder.ROW_MAJOR, data_type=csdk.MemcpyDataType.MEMCPY_32BIT, nonblock=False)
            send += chunk_size
            rest -= chunk_size
        else:
            runner.memcpy_h2d(MEMCPYH2D_DATA_1_ID, Q[send:], 0, 0, 1, 1, rest, streaming=True,
                    order=csdk.MemcpyOrder.ROW_MAJOR, data_type=csdk.MemcpyDataType.MEMCPY_32BIT, nonblock=False)
            break

def load_test(dir: Path):
    return (np.load(dir / "Q.npy", allow_pickle=False), 
            np.load(dir / "s.npy", allow_pickle=False),
            np.load(dir / "E.npy", allow_pickle=False))

def run(runner, Num, params, Q):
    MEMCPYH2D_DATA_1_ID = int(params['MEMCPYH2D_DATA_1_ID'])
    MEMCPYD2H_DATA_1_ID = int(params['MEMCPYD2H_DATA_1_ID'])
    block_height = int(params['block_height'])
    block_width = int(params['block_width'])
    M = Num // block_width
    print(f"{params=}")

    Q = np.ravel(Q)
    min_energy_and_position = np.zeros(2, dtype=np.float32)
    best_s = np.zeros(Num, dtype=np.int32)

    t0 = time.time_ns()
    # Load and run the program
    runner.load()
    t1 = time.time_ns()
    print(f"runner.load {(t1 - t0) / 1e9}s")
    runner.run()
    t2 = time.time_ns()
    print(f"runner.run {(t2 - t1) / 1e9}s")

    send_Q(runner, Num, Q, MEMCPYH2D_DATA_1_ID)

    t3 = time.time_ns()
    print(f"memcpy_h2d {(t3 - t2) / 1e9}s")
    runner.memcpy_d2h(min_energy_and_position, MEMCPYD2H_DATA_1_ID, 0, 0, 1, 1, 2, streaming=True,
        order=csdk.MemcpyOrder.ROW_MAJOR, data_type=csdk.MemcpyDataType.MEMCPY_32BIT, nonblock=False)
    t4 = time.time_ns()
    print(f"memcpy_d2h {(t4 - t3) / 1e9}s")
    p = f32_to_u32(min_energy_and_position[1])
    gy = p >> 16
    gx = p & 0xFFFF
    runner.memcpy_d2h(best_s, MEMCPYD2H_DATA_1_ID, gx * block_width, gy * block_height, block_width, 1, M, streaming=True,
        order=csdk.MemcpyOrder.ROW_MAJOR, data_type=csdk.MemcpyDataType.MEMCPY_32BIT, nonblock=False)
    t5 = time.time_ns()
    print(f"memcpy_d2h {(t5 - t4) / 1e9}s")

    # Stop the program
    runner.stop()
    t6 = time.time_ns()
    print(f"runner.stop {(t6 - t5) / 1e9}s")
    print(f"total {(t6 - t0) / 1e9}s")

    min_energy = min_energy_and_position[0]
    return (best_s, min_energy)


def main():
    args = parse_args()

    with open(args.config, "rb") as f:
        config = tomli.load(f)
    params = config['params']
    test = config['test']

    with open(f"{args.name}/out.json", encoding='utf-8') as json_file:
        compile_data = json.load(json_file)

    Num = int(params['Num'])

    # Construct a runner using SdkRuntime
    runner = csdk.SdkRuntime(args.name, cmaddr=args.cmaddr, suppress_simfab_trace=config["sdk"]["suppress_simfab_trace"])
    Q, opt_s, opt_E = load_test(Path(test['directory']))

    print(f"{Q=}")

    best_s, min_energy = run(runner, Num, compile_data["params"], Q)
    print(f"{best_s=}")
    print(f"{min_energy=}")
    
    # Because the energy calculated in the WSE has insufficient precision, we compare to the recalculated energy in Python.
    comp_energy = energy(Q, best_s)

    if opt_E >= comp_energy:
        print(f"opt_s\t= {opt_E:7.3f}, {opt_s}")
        print(f"best_s\t= {min_energy:7.3f}, {best_s}")
        print("OK")
    else:
        print(f"opt_s\t= {opt_E:7.3f}, {opt_s}")
        print(f"best_s\t= {min_energy:7.3f}, {best_s}")
        print("NG")
        exit(1)



if __name__ == '__main__':
    main()