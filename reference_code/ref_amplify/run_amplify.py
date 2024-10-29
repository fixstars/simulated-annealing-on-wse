#!/usr/bin/env python3
import argparse
import os
from getpass import getpass

import numpy as np
from amplify import FixstarsClient, VariableGenerator, solve

N = 6
RNG = np.random.default_rng(42)


def run(token: str):
    inputs = np.asarray(RNG.uniform(-1.0, 1.0, size=(N, N)), dtype=np.float32)
    print(f"inputs = {inputs}")

    # setup Q
    Q = np.tril(inputs) + np.tril(inputs).T - np.diag(inputs.diagonal())
    print(f"Q = \n{Q}")

    # setup sigma
    gen = VariableGenerator()
    m = gen.matrix("Binary", N)

    # setup model
    d = np.array(Q.diagonal(), copy=True)
    U = np.triu(Q) - np.diag(d)
    m.quadratic = U
    m.linear = d
    print(f"Model : {m}")

    client = FixstarsClient()
    client.token = token

    print("solving...")
    result = solve(m, client)
    output = m.variable_array.evaluate(result.best.values).astype(np.int8)
    print(f"best_s = {output}")
    print(f"energy = {result.best.objective}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="run_amplify", description="reference program by amplify")
    parser.add_argument("-t", "--token", help="If not specified, input at runtime.")
    args = parser.parse_args()
    if args.token:
        token = args.token
    else:
        token = os.getenv("AMPLIFY_TOKEN", "")
        if not token:
            token = getpass("Input access token : ")
    run(token)
