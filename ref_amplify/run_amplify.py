#!/usr/bin/env python3
import argparse
from getpass import getpass
import os
import numpy as np
from amplify import FixstarsClient, VariableGenerator, solve
from amplify import sum as amplify_sum

N = 6
LEN = N * (N + 1) // 2
RNG = np.random.default_rng(42)


def run(token: str):
    inputs = np.asarray(RNG.uniform(-1.0, 1.0, LEN), dtype=np.float32)
    print(f"inputs = {inputs}")

    # setup Q
    Q = np.zeros((N, N), dtype=np.float32)

    counter: int = 0
    for i in range(N):
        for j in range(i, N):
            Q[i][j] = Q[j][i] = inputs[counter]
            counter += 1
    print(f"Q = \n{Q}")

    # setup sigma
    gen = VariableGenerator()
    s = gen.array("Binary", N)

    # setup model
    F = amplify_sum(
        [Q[i][j] * s[i] * s[j] for i in range(N) for j in range(i + 1, N)]
        + [Q[i][i] * s[i] for i in range(N)]
    )
    print(f"F = {F}")

    client = FixstarsClient()
    client.token = token

    print("solving...")
    result = solve(F, client)
    output = s.evaluate(result.best.values).astype(np.int8)
    print(f"best_s = {output}")
    print(f"energy = {result.best.objective}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="run_amplify", description="reference program by amplify"
    )
    parser.add_argument("-t", "--token", help="If not specified, input at runtime.")
    args = parser.parse_args()
    if args.token:
        token = args.token
    else:
        token = os.getenv('AMPLIFY_TOKEN', '')
        if not token:
            token = getpass("Input access token : ")
    run(token)
