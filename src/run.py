#!/usr/bin/env cs_python

import argparse
import numpy as np
import json
import struct
import time

import cerebras.sdk.runtime.sdkruntimepybind as csdk
import amplify


# Read arguments
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', help="the test compile output dir")
    parser.add_argument('--cmaddr', help="IP:port for CS system")
    parser.add_argument('--token', help="amplify token")
    parser.add_argument('--debug', '-d', action='store_false', help='set suppress_simfab_trace to False')
    return parser.parse_args()


def generate_q(rng, Num):
    inputs_len = Num * (Num + 1) // 2
    inputs = np.asarray(rng.uniform(-1.0, 1.0, inputs_len), dtype=np.float32)
    Q = np.zeros((Num, Num), dtype=np.float32)
    c = 0
    for i in range(Num):
        for j in range(i, Num):
            Q[i][j] = inputs[c]
            Q[j][i] = inputs[c]
            c += 1
    return Q


def solve_amplify(token, Q, Num):
    gen = amplify.VariableGenerator()
    s = gen.array("Binary", Num)
    energy_function = amplify.sum(
        [Q[i][j] * s[i] * s[j] for i in range(Num) for j in range(i + 1, Num)]
        + [Q[i][i] * s[i] for i in range(Num)]
    )
    print(f"{energy_function=}")
    client = amplify.FixstarsClient()
    client.token = token
    client.parameters.timeout = 100

    result = amplify.solve(energy_function, client)
    output = s.evaluate(result.best.values).astype(np.int32)
    return (output, result.best.objective)


def run(runner, width, height, N, M, Q):
    Q_symbol = runner.get_id('Q')
    best_s_symbol = runner.get_id('best_s')
    min_energy_symbol = runner.get_id('min_energy')

    best_s = np.zeros(width * M, dtype=np.int32)
    min_energy = np.zeros(1, dtype=np.float32)

    Q = Q.reshape((height, N, width, M)).transpose(0, 2, 1, 3)
    Q = Q.ravel()

    st = time.time_ns()
    # Load and run the program
    runner.load()
    runner.run()

    runner.memcpy_h2d(Q_symbol, Q, 0, 0, width, height, N * M, streaming=False,
        order=csdk.MemcpyOrder.ROW_MAJOR, data_type=csdk.MemcpyDataType.MEMCPY_32BIT, nonblock=False)

    runner.launch('main', nonblock=False)

    runner.memcpy_d2h(best_s, best_s_symbol, 0, 0, width, 1, M, streaming=False,
        order=csdk.MemcpyOrder.ROW_MAJOR, data_type=csdk.MemcpyDataType.MEMCPY_32BIT, nonblock=False)
    runner.memcpy_d2h(min_energy, min_energy_symbol, 0, 0, 1, 1, 1, streaming=False,
        order=csdk.MemcpyOrder.ROW_MAJOR, data_type=csdk.MemcpyDataType.MEMCPY_32BIT, nonblock=False)

    # Stop the program
    runner.stop()
    et = time.time_ns()
    print(f"{(et - st) / 1e9}s")
    return (best_s, min_energy[0])


def main():
    args = parse_args()

    with open(f"{args.name}/out.json", encoding='utf-8') as json_file:
        compile_data = json.load(json_file)

    Num = int(compile_data['params']['Num'])
    width = int(compile_data['params']['width'])
    height = int(compile_data['params']['height'])
    N = Num // height
    M = Num // width

    # Construct a runner using SdkRuntime
    runner = csdk.SdkRuntime(args.name, cmaddr=args.cmaddr, suppress_simfab_trace=args.debug)

    rng = np.random.default_rng()
    Q = generate_q(rng, Num)

    print(f"{Q=}")
    s_amplify, e_amplify = solve_amplify(args.token, Q, Num)
    print(f"{s_amplify=}")
    print(f"{e_amplify=}")

    best_s, min_energy = run(runner, width, height, N, M, Q)
    print(f"{best_s=}")
    min_energy = np.sum(
        [Q[i][j] * best_s[i] * best_s[j] for i in range(Num) for j in range(i + 1, Num)]
        + [Q[i][i] * best_s[i] for i in range(Num)]
    )
    print(f"{min_energy=}")

    if all(s_amplify == best_s):
        print("OK")
    else:
        print(f"amplify = {e_amplify:7.3f}, {s_amplify}")
        print(f"best_s  = {min_energy:7.3f}, {best_s}")
        print("NG")
        exit(1)


if __name__ == '__main__':
    main()