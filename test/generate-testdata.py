#!/usr/bin/env python3

import argparse
import numpy as np
from os import makedirs, getenv

import amplify

# Read arguments
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--Num', help="Number of rows and columns of Q", type=int, required=True)
    parser.add_argument('--token', help="amplify token", default=getenv("AMPLIFY_TOKEN"))
    parser.add_argument('--timeout', help="amplify timeout parameter", type=int, default=100)
    parser.add_argument('--output', '-o', help="output directory", default="output")
    
    return parser.parse_args()

def generate_q(rng, Num):
    inputs = rng.uniform(low=-1.0, high=1.0, size=(Num, Num)).astype(np.float32)
    Q = np.tril(inputs) + np.tril(inputs).T - np.diag(inputs.diagonal())
    return Q

def energy(Q, s):
    d = np.array(Q.diagonal(), copy=True)
    U = np.triu(Q) - np.diag(d)
    return s @ U @ s + d.T @ s

def solve_amplify(token, Q, Num, timeout):
    gen = amplify.VariableGenerator()
    s = gen.array("Binary", Num)
    energy_function = energy(Q, s)
    client = amplify.FixstarsClient()
    client.token = token
    client.parameters.timeout = timeout

    result = amplify.solve(energy_function, client)
    output = s.evaluate(result.best.values).astype(np.int32)
    return (output, result.best.objective)

def main():
    args = parse_args()
    Num = args.Num
    timeout = args.timeout
    output_dir = args.output

    rng = np.random.default_rng()
    Q = generate_q(rng, Num)

    print(f"{Q=}")
    s_amplify, e_amplify = solve_amplify(args.token, Q, Num, timeout)
    print(f"{s_amplify=}")
    print(f"{e_amplify=}")
    
    makedirs(f"{output_dir}", exist_ok=True)
    np.save(f"{output_dir}/Q.npy", Q, allow_pickle=False)
    np.save(f"{output_dir}/s.npy", s_amplify, allow_pickle=False)
    np.save(f"{output_dir}/E.npy", e_amplify, allow_pickle=False)

    print(f"generated test case {Num=} in {output_dir}")


if __name__ == '__main__':
    main()
