#!/usr/bin/env cs_python

import argparse
import datetime
import itertools
import json
import math
import re
import shutil
import struct
import time
from pathlib import Path

import cerebras.sdk.runtime.sdkruntimepybind as csdk
import numpy as np
import tomli
from tqdm import tqdm

RANDOM_GENERATOR = np.random.default_rng(0)


def f32_to_u32(x) -> int:
    return struct.unpack("I", struct.pack("f", x))[0]


def u32_to_f32(x) -> float:
    return struct.unpack("f", struct.pack("I", x))[0]


def make_u48(words):
    return words[0] + (words[1] << 16) + (words[2] << 32)


def energy(Q, s):
    d = np.array(Q.diagonal(), copy=True)
    U = np.triu(Q) - np.diag(d)
    return s @ U @ s + d.T @ s


def read_last_lines(path: Path, line_num: int):
    buffer = bytearray()
    with path.open("rb") as f:
        f.seek(0, 2)
        f_loc = f.tell()
        while f_loc > 0 and (len(buffer.splitlines())) <= line_num:
            f.seek(f_loc)
            read_size = min(1024, f_loc)
            f.seek(f_loc - read_size)
            buffer.extend(f.read(read_size))
            f_loc -= read_size
    last_lines = buffer.decode("utf-8").splitlines()[-line_num:]
    return last_lines


# Read arguments
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", help="the test compile output dir")
    parser.add_argument("--cmaddr", help="IP:port for CS system")
    parser.add_argument("--input_dir", help="input directory for Q")
    parser.add_argument("--config", "-c", help="config file")
    return parser.parse_args()


def send_host_data(runner, Num, Q_triu, params, MEMCPYH2D_DATA_1_ID, height_offset=0):
    # send runtime parameters
    runtime_parameters = [
        # name , type (I: int, 'f': float)
        ("max_iters", "I"),
        ("log2_swap_interval", "I"),
        ("time_constant", "I"),
        ("log_init_temperature", "I"),
        ("iterations_per_collect", "I"),
    ]
    param_num = len(runtime_parameters)
    param_values = np.zeros(param_num, dtype=np.float32)
    for i, runtime_parameter in enumerate(runtime_parameters):
        param_name, param_type = runtime_parameter
        if param_type == "I":
            param_value = int(params[param_name])
            param_value_f32 = u32_to_f32(param_value)
        else:
            param_value = float(params[param_name])
            param_value_f32 = param_value
        print(f"Send runtime parameter : {param_name}={param_value} ({param_type})")
        param_values[i] = param_value_f32
    runner.memcpy_h2d(
        MEMCPYH2D_DATA_1_ID,
        param_values,
        0,
        height_offset,
        1,
        1,
        param_num,
        streaming=True,
        order=csdk.MemcpyOrder.ROW_MAJOR,
        data_type=csdk.MemcpyDataType.MEMCPY_32BIT,
        nonblock=False,
    )

    # send Q
    chunk_size = 32766  # Will not work if INT16_MAX or higher.
    rest = Num * (Num + 1) // 2
    send = 0
    while True:
        if rest >= chunk_size:
            runner.memcpy_h2d(
                MEMCPYH2D_DATA_1_ID,
                Q_triu[send:],
                0,
                height_offset,
                1,
                1,
                chunk_size,
                streaming=True,
                order=csdk.MemcpyOrder.ROW_MAJOR,
                data_type=csdk.MemcpyDataType.MEMCPY_32BIT,
                nonblock=False,
            )
            send += chunk_size
            rest -= chunk_size
        else:
            runner.memcpy_h2d(
                MEMCPYH2D_DATA_1_ID,
                Q_triu[send:],
                0,
                height_offset,
                1,
                1,
                rest,
                streaming=True,
                order=csdk.MemcpyOrder.ROW_MAJOR,
                data_type=csdk.MemcpyDataType.MEMCPY_32BIT,
                nonblock=False,
            )
            break


def load_test(dir: Path):
    return (
        np.load(dir / "Q.npy", allow_pickle=False),
        np.load(dir / "s.npy", allow_pickle=False),
        np.load(dir / "E.npy", allow_pickle=False),
    )


def load_trace_and_stop(runner, params):
    # trace pre-settings
    trace_buffer_symbol = runner.get_id("trace_buffer")
    trace_buffer_size = int(params["trace_buffer_size"])

    # collector pre-settings
    collector_buffer_symbol = runner.get_id("collector_buffer")
    collector_buffer_size = int(params["collector_buffer_size"])
    enable_collector = collector_buffer_size > 0
    height_offset = 1 if enable_collector else 0

    # check tile size
    block_height = int(params["block_height"])
    block_width = int(params["block_width"])
    grid_height = int(params["grid_height"])
    grid_width = int(params["grid_width"])
    height = (block_height + height_offset) * grid_height
    width = block_width * grid_width

    # trace settings
    trace_buffer = np.zeros(height * width * trace_buffer_size, dtype=np.uint32)
    # collector settings
    collector_buffer = np.zeros((grid_height, width * collector_buffer_size), dtype=np.float32)

    print("Loading traces... Please wait a few minutes.")

    cur_dir = Path().cwd()
    trace_dir = cur_dir / "log"
    trace_dir.mkdir(exist_ok=True)
    log_dir = trace_dir / f"{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    log_dir.mkdir(exist_ok=True)

    if trace_buffer_size > 0:
        print("[TRACER]Detect tracer enabled. Loading tracer info...")
        runner.memcpy_d2h(
            trace_buffer,
            trace_buffer_symbol,
            0,
            0,
            width,
            height,
            trace_buffer_size,
            streaming=False,
            order=csdk.MemcpyOrder.ROW_MAJOR,
            data_type=csdk.MemcpyDataType.MEMCPY_16BIT,
            nonblock=False,
        )
        trace_buffer = trace_buffer.reshape((height, width, trace_buffer_size))
        print("[TRACER]Loading completed.")
        tracer_data = dict()
        tracer_data.update(**params)
        tracer_data["pe"] = []
        for w in range(width):
            for h in range(height):
                pe_data: dict[str, int | list] = {"x": w, "y": h, "trace": []}
                for i in range(0, trace_buffer_size, 4):
                    if np.all(trace_buffer[h, w, i : i + 4] == 0):
                        # trace end
                        break
                    pe_data["trace"].append(
                        {
                            "id": int(trace_buffer[h, w, i]),
                            "cycle": int(make_u48(trace_buffer[h, w, i + 1 : i + 4])),
                        }
                    )
                tracer_data["pe"].append(pe_data)
        # DEBUG
        # import pprint
        # pprint.pprint(trace_data)

        tracer_log = log_dir / "trace.json"
        with tracer_log.open(mode="w", encoding="utf-8") as f:
            json.dump(tracer_data, f)
        print(f"[TRACER]LOG FILE : {tracer_log}")

    if collector_buffer_size > 0:
        print("[COLLECTOR]Detect collector enabled. Loading collector info...")
        for gy in range(grid_height):
            print(f"[COLLECTOR]Loading info from the collection row ({gy+1}/{grid_height=})...")
            y = (block_height + height_offset) * gy
            runner.memcpy_d2h(
                collector_buffer[gy],
                collector_buffer_symbol,
                0,
                y,
                width,
                1,
                collector_buffer_size,
                streaming=False,
                order=csdk.MemcpyOrder.ROW_MAJOR,
                data_type=csdk.MemcpyDataType.MEMCPY_32BIT,
                nonblock=False,
            )
        print("[COLLECTOR]Loading completed.")
        collector_data = dict()
        collector_data.update(**params)
        collector_data["tile"] = []
        for gy in range(grid_height):
            for gx in range(grid_width):
                L = gx * collector_buffer_size * block_width
                R = (gx + 1) * collector_buffer_size * block_width
                statistics = collector_buffer[gy][L:R]
                statistics[2::4] = np.vectorize(f32_to_u32)(statistics[2::4])
                statistics[3::4] = np.vectorize(f32_to_u32)(statistics[3::4])

                tile_data: dict[str, int | list] = {"x": gx, "y": gy, "statistics": []}
                for i in range(0, len(statistics), 4):
                    if np.all(statistics[i : i + 4] == 0):
                        # statistics end
                        break
                    tile_data["statistics"].append(
                        {
                            "temperature": f"{statistics[i]:.9f}",
                            "energy": f"{statistics[i+1]:.9f}",
                            "flip_num": int(statistics[i + 2]),
                            "iteration_num": int(statistics[i + 3]),
                        }
                    )
                collector_data["tile"].append(tile_data)
        # DEBUG
        # import pprint
        # pprint.pprint(collector_data)

        collector_log = log_dir / "statistics.json"
        with collector_log.open(mode="w", encoding="utf-8") as f:
            json.dump(collector_data, f)
        print(f"[COLLECTOR]STATISTICS FILE : {collector_log}")

    runner.stop()
    print("Complete load trace (D2H).")
    # copy sim_stats.json
    sim_stats_file = cur_dir / "sim_stats.json"
    sim_stats_log_file = log_dir / "sim_stats.json"
    if sim_stats_file.exists():
        shutil.copy(sim_stats_file, sim_stats_log_file)
        print(f"SIM_STATS : {sim_stats_log_file}")


class PePos:
    block_width: int
    block_height: int
    height_offset: int

    def __init__(self, block_width: int, block_height: int, height_offset: int):
        self.block_width = block_width
        self.block_height = block_height
        self.height_offset = height_offset

    def pe_pos(self, gx: int, gy: int, bx: int, by: int):
        x = gx * self.block_width + bx
        y = gy * (self.block_height + self.height_offset) + self.height_offset + by
        return (x, y)


def swap_temperature(
    new_temperature, energy_and_temperature, grid_height: int, grid_width: int
) -> int:
    def swap_probability(p1, p2):
        e1, t1 = energy_and_temperature[p1]
        e2, t2 = energy_and_temperature[p2]
        delta_e = e1 - e2
        delta_beta = 1.0 / t1 - 1.0 / t2
        try:
            return math.exp(delta_e * delta_beta)
        except OverflowError:
            return float("inf")

    y = np.arange(grid_height)
    x = np.arange(grid_width)
    indices = list(itertools.product(y, x))
    RANDOM_GENERATOR.shuffle(indices)
    i = 0
    s = 0
    while i + 1 < grid_height * grid_width:
        p1 = (indices[i + 0][0], indices[i + 0][1])
        p2 = (indices[i + 1][0], indices[i + 1][1])
        p = swap_probability(p1, p2)
        if RANDOM_GENERATOR.random() < p:
            s += 1
            t = np.copy(energy_and_temperature[p1])
            energy_and_temperature[p1] = np.copy(energy_and_temperature[p2])
            energy_and_temperature[p2] = t
        i += 2
    new_temperature[:, :] = energy_and_temperature[:, :, 1]
    return s


def is_all_task_done(runner, tasks) -> bool:
    for task in tasks:
        if not runner.is_task_done(task):
            return False
    return True


def get_progress():
    simlog = Path("sim.log")
    pattern = r"@\d+\sTile\(\d+,\d+\):\s\d+/\d+"
    last_10lines = read_last_lines(simlog, line_num=10)
    for line in reversed(last_10lines):
        if not re.fullmatch(pattern, line):
            continue
        if line.startswith("@0"):
            continue
        try:
            return int(line.split(" ")[-1].split("/")[0])
        except Exception:
            # do nothing
            pass
    return 0


annealing_progress = 0


def parallel_tempering(runner, params, height_offset: int, sim: bool):
    global annealing_progress
    MEMCPYH2D_DATA_1_ID = int(params["MEMCPYH2D_DATA_1_ID"])
    MEMCPYD2H_DATA_1_ID = int(params["MEMCPYD2H_DATA_1_ID"])
    log2_swap_interval = int(params["log2_swap_interval"])
    max_iters = int(params["max_iters"])
    n = max_iters >> log2_swap_interval
    block_height = int(params["block_height"])
    block_width = int(params["block_width"])
    grid_height = int(params["grid_height"])
    grid_width = int(params["grid_width"])
    energy_and_temperature = np.zeros((grid_height, grid_width, 2), dtype=np.float32)
    new_temperature = np.zeros((grid_height, grid_width), dtype=np.float32)
    pe_pos = PePos(block_width, block_height, height_offset)

    if n > 0 and sim:
        pbar = tqdm(total=max_iters, desc="processing", dynamic_ncols=True)

    def gather_energy_and_temperature():
        global annealing_progress
        tasks = []
        for y in range(grid_height):
            for x in range(grid_width):
                px, py = pe_pos.pe_pos(x, y, 0, 0)
                task = runner.memcpy_d2h(
                    energy_and_temperature[y][x],
                    MEMCPYD2H_DATA_1_ID,
                    px,
                    py,
                    1,
                    1,
                    2,
                    streaming=True,
                    order=csdk.MemcpyOrder.ROW_MAJOR,
                    data_type=csdk.MemcpyDataType.MEMCPY_32BIT,
                    nonblock=True,
                )
                tasks.append(task)
        if n > 0 and sim:
            pbar.n = annealing_progress
            pbar.refresh()

            while not is_all_task_done(runner, tasks):
                annealing_progress = max(annealing_progress, get_progress())
                pbar.n = annealing_progress
                pbar.refresh()
                time.sleep(0.1)
        for task in tasks:
            time.sleep(1e-6)
            runner.task_wait(task)

    for i in range(n):
        gather_energy_and_temperature()
        s = swap_temperature(new_temperature, energy_and_temperature, grid_height, grid_width)
        print(f"[{i=}/{n-1}] swapped {s} pairs")
        px, py = pe_pos.pe_pos(0, 0, 0, 0)
        runner.memcpy_h2d(
            MEMCPYH2D_DATA_1_ID,
            new_temperature.ravel(),
            px,
            py,
            1,
            1,
            grid_height * grid_width,
            streaming=True,
            order=csdk.MemcpyOrder.ROW_MAJOR,
            data_type=csdk.MemcpyDataType.MEMCPY_32BIT,
            nonblock=False,
        )
    if n > 0 and sim:
        pbar.close()


def run(runner_name, runner_cmaddr, Num, Q_triu, params):
    runner = csdk.SdkRuntime(
        runner_name,
        cmaddr=runner_cmaddr,
        suppress_simfab_trace=params["suppress_simfab_trace"],
    )

    sim = runner_cmaddr is None
    enable_collector = int(params["collector_buffer_size"]) > 0
    height_offset = 1 if enable_collector else 0

    MEMCPYH2D_DATA_1_ID = int(params["MEMCPYH2D_DATA_1_ID"])
    MEMCPYD2H_DATA_1_ID = int(params["MEMCPYD2H_DATA_1_ID"])
    block_height = int(params["block_height"])
    block_width = int(params["block_width"])
    M = Num // block_width
    log2_swap_interval = int(params["log2_swap_interval"])
    max_iters = int(params["max_iters"])
    enable_parallel_tempering = (max_iters >> log2_swap_interval) > 0

    min_energy_and_position = np.zeros(2, dtype=np.float32)
    slen = (M + 31) // 32
    best_s = np.zeros(slen * block_width, dtype=np.int32)
    out_best_s = np.zeros(Num, dtype=np.int32)

    print("started")
    t0 = time.time_ns()
    # Load and run the program
    runner.load()
    t1 = time.time_ns()
    print(f"runner.load {(t1 - t0) / 1e9}s")
    runner.run()
    t2 = time.time_ns()
    print(f"runner.run {(t2 - t1) / 1e9}s")
    runner.launch("init", nonblock=False)
    t3 = time.time_ns()
    print(f"init {(t3 - t2)/1e9}s")
    send_host_data(runner, Num, Q_triu, params, MEMCPYH2D_DATA_1_ID, height_offset)
    t4 = time.time_ns()
    print(f"memcpy_h2d {(t4 - t3) / 1e9}s")
    parallel_tempering(runner, params, height_offset, sim)
    t5 = time.time_ns()
    print(f"swap_temperature {(t5 - t4) / 1e9}s")
    b = not enable_parallel_tempering and sim
    task = runner.memcpy_d2h(
        min_energy_and_position,
        MEMCPYD2H_DATA_1_ID,
        0,
        height_offset,
        1,
        1,
        2,
        streaming=True,
        order=csdk.MemcpyOrder.ROW_MAJOR,
        data_type=csdk.MemcpyDataType.MEMCPY_32BIT,
        nonblock=b,
    )
    if b:
        with tqdm(total=max_iters, desc="processing", dynamic_ncols=True) as pbar:
            annealing_progress = 0
            pbar.n = annealing_progress
            pbar.refresh()

            while not runner.is_task_done(task):
                annealing_progress = max(annealing_progress, get_progress())
                pbar.n = annealing_progress
                pbar.refresh()
                time.sleep(0.1)
            pbar.n = max_iters
            pbar.refresh()
    t6 = time.time_ns()
    print(f"memcpy_d2h {(t6 - t5) / 1e9}s")
    pe_pos = PePos(block_width, block_height, height_offset)
    p = f32_to_u32(min_energy_and_position[1])
    gy = p >> 16
    gx = p & 0xFFFF
    x, y = pe_pos.pe_pos(gx, gy, 0, 0)
    runner.memcpy_d2h(
        best_s,
        MEMCPYD2H_DATA_1_ID,
        x,
        y,
        block_width,
        1,
        slen,
        streaming=True,
        order=csdk.MemcpyOrder.ROW_MAJOR,
        data_type=csdk.MemcpyDataType.MEMCPY_32BIT,
        nonblock=False,
    )
    t7 = time.time_ns()
    print(f"memcpy_d2h {(t7 - t6) / 1e9}s")
    if int(params["trace_buffer_size"]) == 0 and int(params["collector_buffer_size"]) == 0:
        # Stop the program
        runner.stop()
        t8 = time.time_ns()
        print(f"runner.stop {(t8 - t7) / 1e9}s")
    else:
        load_trace_and_stop(runner, params)
        t8 = time.time_ns()
        print(f"load_trace_and_stop {(t7 - t6) / 1e9}s")
    print(f"total {(t8 - t0) / 1e9}s")

    min_energy = min_energy_and_position[0]
    for by, offset_index in enumerate(range(0, Num, M)):
        s_per_pe = best_s[by * slen : (by + 1) * slen]
        for i in range(M):
            index_per_pe = i // 32
            bit_per_pe_index = i % 32
            out_best_s[offset_index + i] = (s_per_pe[index_per_pe] >> bit_per_pe_index) & 0x1
    return (out_best_s, min_energy)


def main():
    args = parse_args()

    with open(args.config, "rb") as f:
        config_params = tomli.load(f)
    with open(f"{args.name}/out.json", encoding="utf-8") as json_file:
        compile_params = json.load(json_file)["params"]
    merged_params = dict()
    merged_params.update(**compile_params)
    merged_params.update(**config_params["params"])
    merged_params.update(**config_params["trace"]["tracer"])
    merged_params.update(**config_params["trace"]["collector"])
    merged_params.update(**config_params["sdk"])
    print(f"{merged_params=}")

    Num = int(merged_params["Num"])
    Q, opt_s, opt_E = load_test(Path(config_params["test"]["directory"]))

    if Q.dtype != np.float32:
        print(f"Convert Q type : {Q.dtype} -> float32")
        Q = Q.astype(np.float32)

    if Q.size == Num * Num:
        # Extract elements of upper triangular matrix
        Q_triu = Q[np.triu_indices(Num)]
    elif Q.size == Num * (Num + 1) // 2:
        Q_triu = Q

        # restore the square matrix Q
        TriuIndex = np.triu_indices(Num)
        Q = np.zeros((Num, Num), dtype=np.float32)
        Q[TriuIndex] += Q_triu
        Q = Q + Q.T - np.diag(Q.diagonal())
    else:
        print(f"Error: The size of Q is different from the Num set in {args.config}")
        exit(1)
    print(f"{Q_triu=}")

    best_s, min_energy_wse = run(args.name, args.cmaddr, Num, Q_triu, merged_params)
    # Because the energy calculated in the WSE has insufficient precision, we compare to the recalculated energy in Python.
    min_energy = energy(Q, best_s)
    print(f"{best_s=}")
    print(f"{min_energy_wse=} (in WSE)")
    print(f"{min_energy=} (in Python)")

    if opt_E >= min_energy:
        print(f"opt_s\t= {opt_E:7.3f}, {opt_s}")
        print(f"best_s\t= {min_energy:7.3f}, {best_s}")
        print("OK")
    else:
        print(f"opt_s\t= {opt_E:7.3f}, {opt_s}")
        print(f"best_s\t= {min_energy:7.3f}, {best_s}")
        print("NG")
        exit(1)


if __name__ == "__main__":
    main()
