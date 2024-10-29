#!/usr/bin/env python3
import argparse
import json
import random
import re
from pathlib import Path

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np

# ================================================================== #
# Target program version :[a035aee58fa8d7d592e49832debd9547558b4448] #
# ================================================================== #

# Analyze helper variables
MAPPING_ID2TASK = {
    # pe_program.csl
    0: "BCAST_HOST_DATA",
    2: "STORE_HOST_DATA",
    4: "START_ITERATION",
    6: "RECV_FLIP_POSITION",
    8: "RECV_S",
    10: "X_SUM",
    12: "Y_SUM",
    14: "END_ITERATION",
    16: "GLOBAL_ENERGY_MIN_X",
    18: "GLOBAL_ENERGY_MIN_Y",
    20: "BCAST_GLOBAL_ENERGY",
    22: "RECV_MIN_ENERGY",
    # collector.csl
    24: "RECV_STATISTICS",
    26: "SEND_STATISTICS",
}

# https://matplotlib.org/stable/gallery/color/named_colors.html#css-colors
COLORS = mcolors.CSS4_COLORS.copy()
# remove light color
for color in list(COLORS.keys()):
    if "white" in color:
        COLORS.pop(color, None)
for light_color in [
    "gainsboro",
    "snow",
    "mistyrose",
    "seashell",
    "peachpuff",
    "linen",
    "bisque",
    "blanchedalmond",
    "papayawhip",
    "mocccasin",
    "oldlace",
    "ivory",
    "beige",
    "honeydew",
    "mintcream",
    "azure",
    "lightcyan",
    "aliceblue",
    "lavender",
    "lavenderblush",
]:
    COLORS.pop(light_color, None)
COLORS = list(COLORS.keys())
random.seed(3687)
random.shuffle(COLORS)
MAPPING_ID2COLOR = {2 * x: COLORS[x] for x in range(len(COLORS))}


def Import_trace_data(input_dir: Path) -> list[dict, dict]:
    print("Import trace data...")
    with (input_dir / "trace.json").open("r", encoding="utf-8") as f:
        data = json.load(f)

    pe_info = {
        "block_height": data["block_height"],
        "block_width": data["block_width"],
        "grid_height": data["grid_height"],
        "grid_width": data["grid_width"],
        "enable_collector": int(data["collector_buffer_size"]) > 0,
    }
    pe_data = dict()
    pe: dict
    for pe in data["pe"]:
        pe_key = (pe["x"], pe["y"])

        Id = [trace["id"] for trace in pe["trace"]]
        Cycle = [trace["cycle"] for trace in pe["trace"]]

        # check trace data
        assert all(
            np.array(Id[0::2]) + 1 == np.array(Id[1::2])
        ), "Even and Odd adjacent IDs are not continuous"
        assert len(Id) == len(Cycle), "Id and Cycle data must be same size."

        pe_data[pe_key] = {"id": Id, "cycle": Cycle}
        pe_info[pe_key] = {"size": len(Id)}

    print(f"{pe_info=}")
    return pe_data, pe_info


def get_stats_data(input_dir: Path) -> dict:
    print("Importing sim_stats data...")
    STATS_FILE = input_dir / "sim_stats.json"
    if not STATS_FILE.exists():
        print("sim_stats does not exist.")
        return dict()
    stats_data: dict
    with STATS_FILE.open("r", encoding="utf-8") as f:
        stats_data = json.load(f)
    print(f"{stats_data=}")
    return stats_data


def create_PE_coordinates(pe_info: dict):
    """
    one tile coordinates
      (leftmost PE) = (w_offset, h_offset)

      [w_offset, h_offset],     [w_offset + 1, h_offset],     ... , [w_offset + block_width - 1, h_offset]
      [w_offset, h_offset + 1], [w_offset + 1, h_offset + 1], ... , [w_offset + block_width - 1, h_offset + 1]
      ...
    """
    block_width = int(pe_info["block_width"])
    block_height = int(pe_info["block_height"]) + int(pe_info["enable_collector"])
    grid_width = int(pe_info["grid_width"])
    grid_height = int(pe_info["grid_height"])

    width = block_width * grid_width
    height = block_height * grid_height

    PE_coordinates = []
    for h_offset in range(0, height, block_height):
        for w_offset in range(0, width, block_width):
            PE_coordinates += [
                (w + w_offset, y + h_offset)
                for y in range(block_height)
                for w in range(block_width)
            ]
    return PE_coordinates


def parse_analyze_PEs(
    pe_data: dict[tuple[int, int], dict], specified_PEs: str
) -> list[tuple[int, int]]:
    print(f"{specified_PEs=}")
    if specified_PEs == "all":
        plot_PEs = [PE for PE in pe_data.keys()]
    else:
        # Pattern1 : x,y
        if re.fullmatch(r"\d+,\d", specified_PEs):
            x, y = map(int, specified_PEs.split(","))
            plot_PEs = [(x, y)]
        # Pattern2 : (x1,y1),(x2,y2),(x3,y3)
        elif re.fullmatch(r"\(\d+,\d+\)(,\(\d+,\d+\))*", specified_PEs):
            plot_PEs = [
                tuple(map(int, PE.split(","))) for PE in specified_PEs.strip("()").split("),(")
            ]
        # Pattern3 : (x1,y1)-(x2,y2)
        elif re.fullmatch(r"\(\d+,\d+\)-\(\d+,\d+\)(,\(\d+,\d+\)-\(\d+,\d+\))*", specified_PEs):
            ROI_PEs = [
                Pre_ROI_PE.split(")-(") for Pre_ROI_PE in specified_PEs.strip("()").split("),(")
            ]
            plot_PEs: list[tuple[int, int]] = list()
            for ROI_PE in ROI_PEs:
                x1, y1 = map(int, ROI_PE[0].split(","))
                x2, y2 = map(int, ROI_PE[1].split(","))
                plot_PEs += [(x, y) for x in range(x1, x2 + 1) for y in range(y1, y2 + 1)]
        else:
            print("Invalid PE specific pattern.")
            exit(1)
    # sort, unique
    plot_PEs = sorted(set(plot_PEs))
    # intersect
    plot_PEs = list(filter(lambda plot_PE: plot_PE in pe_data.keys(), plot_PEs))
    print(f"{plot_PEs=}")
    return plot_PEs


def plot_timeline(
    output_dir: Path,
    pe_data: dict,
    PE_coordinates: list[tuple[int, int]],
    plot_PEs: list[tuple[int, int]],
):
    print("[TIMELINE] Plot PE timeline")
    pe_num = len(plot_PEs)
    pe_cnt = 1
    fig, ax = plt.subplots(figsize=(24, 16), dpi=600)
    all_pe_end_cycle = 0
    for PE in PE_coordinates[::-1]:
        if PE not in plot_PEs:
            continue
        print(f"[TIMELINE] [{pe_cnt}/{pe_num}] Creating PE{PE} timeline...")
        pe_cnt += 1
        name = f"PE:{PE}"
        trace_size = len(pe_data[PE]["id"])
        if trace_size != 0:
            for s in range(0, trace_size, 2):
                id = pe_data[PE]["id"][s]
                start_cycle = pe_data[PE]["cycle"][s]
                end_cycle = pe_data[PE]["cycle"][s + 1]
                all_pe_end_cycle = max(all_pe_end_cycle, end_cycle)
                ax.barh(
                    y=name,
                    width=end_cycle - start_cycle,
                    left=start_cycle,
                    color=MAPPING_ID2COLOR[id],
                    label=MAPPING_ID2TASK[id],
                )
        else:
            # no trace, set dummy value
            ax.barh(
                y=name,
                width=0,
                left=0,
                color=MAPPING_ID2COLOR[0],
                label=MAPPING_ID2TASK[0],
            )

    def legend_without_duplicate_labels(ax):
        mapping_task2id = {v: k for k, v in MAPPING_ID2TASK.items()}
        handles, labels = ax.get_legend_handles_labels()
        unique = [
            (handle, label)
            for i, (handle, label) in enumerate(zip(handles, labels))
            if label not in labels[:i]
        ]
        unique = sorted(unique, key=lambda hl: mapping_task2id[hl[1]])
        ax.legend(
            *zip(*unique),
            bbox_to_anchor=(0.0, 1.0, 1.0, 0.01),
            loc="lower left",
            ncol=10,
            mode="expand",
            borderaxespad=0.0,
        )

    ax.set_xlim(0, all_pe_end_cycle)
    ax.set_ylim(-0.5, pe_num - 0.5)
    ax.set_xlabel("cycle")
    legend_without_duplicate_labels(ax)

    timeline_file = output_dir / "timeline.svg"
    print(f"[TIMELINE] Writing {timeline_file}...")
    plt.savefig(timeline_file, bbox_inches="tight")
    plt.close(fig)
    print("[TIMELINE] Done")


def output_pe_detail_data(
    output_dir: Path,
    pe_data: dict,
    stats_data: dict,
    PE_coordinates: list[tuple[int, int]],
    plot_PEs: list[tuple[int, int]],
):
    pe_detail_file = output_dir / "pe_detail.txt"
    print("Analyzing pe detail data...")

    output_data = [
        f"[Simulation]Total cycles : {stats_data.get('cycle_count', 'sim_stats does not exist.')}\n",
        f"[Simulation]Cycles per second : {stats_data.get('cycles_per_second', 'sim_stats does not exist.')}\n",
    ]
    for PE in PE_coordinates:
        if PE not in plot_PEs:
            continue
        output_data += [
            "---------------------------------------------------------\n",
            f"PE(w,h) = {PE}\n",
            "---------------------------------------------------------\n",
        ]

        task_cycles = {task: [] for task in MAPPING_ID2TASK.values()}
        cycle_sum = 0
        pe_begin_cycle = 1e9
        pe_end_cycle = 0
        trace_size = len(pe_data[PE]["id"])
        for s in range(0, trace_size, 2):
            id = pe_data[PE]["id"][s]
            start_cycle = pe_data[PE]["cycle"][s]
            end_cycle = pe_data[PE]["cycle"][s + 1]

            task = MAPPING_ID2TASK[id]
            cycle_diff = end_cycle - start_cycle
            task_cycles[task].append(cycle_diff)
            cycle_sum += cycle_diff

            pe_begin_cycle = min(pe_begin_cycle, start_cycle)
            pe_end_cycle = max(pe_end_cycle, end_cycle)

        output_data += [
            f"Startup cycle : {pe_begin_cycle}\n",
            f"Shutdown cycle : {pe_end_cycle}\n",
            f"-> Shutdown - Startup : {pe_end_cycle - pe_begin_cycle}\n",
            f"Operation cycle : {cycle_sum}\n",
            f"Operation rate : {cycle_sum / (pe_end_cycle - pe_begin_cycle) * 100:.2f}%\n",
            "Operation cycle details of each measurement target\n",
        ]
        for task in MAPPING_ID2TASK.values():
            output_data += [f"[{task} Cycle Detail]\n"]
            if len(task_cycles[task]) > 0:
                all_cycle_per_task = np.sum(task_cycles[task])
                mean_cycle_per_task = np.mean(task_cycles[task])
                median_cycle_per_task = np.median(task_cycles[task])
                max_cycle_per_task = np.max(task_cycles[task])
                min_cycle_per_task = np.min(task_cycles[task])
                output_data += [
                    "\tsum, mean, median, max, min\n",
                    f"\t{all_cycle_per_task:.1f}, {mean_cycle_per_task:.1f}, {median_cycle_per_task:.1f}, {max_cycle_per_task:.1f}, {min_cycle_per_task:.1f}\n",
                ]
            else:
                output_data += ["\tNONE\n"]

    print(f"Save PE detail data to {pe_detail_file}")
    with pe_detail_file.open(mode="w", encoding="utf-8") as f:
        f.writelines(output_data)


def analyze(input_dir: Path, output_dir: Path, specified_PEs: str):
    pe_data, pe_info = Import_trace_data(input_dir)
    stats_data = get_stats_data(input_dir)

    PE_coordinates = create_PE_coordinates(pe_info)
    plot_PEs = parse_analyze_PEs(pe_data, specified_PEs)
    plot_timeline(output_dir, pe_data, PE_coordinates, plot_PEs)
    output_pe_detail_data(output_dir, pe_data, stats_data, PE_coordinates, plot_PEs)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", help="input log directory")
    parser.add_argument("--output", "-o", help="output data directory", default=".")
    parser.add_argument(
        "--analyze-PEs",
        help="PE specific pattern: x,y OR (x1,y1),(x2,y2),(x3,y3) OR (x1,y1)-(x2,y2) OR all",
        default="all",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Setting input directory
    if args.input:
        input_dir = Path(args.input)
    else:
        # search latest log data
        log_base_dir = (Path(__file__).parent / ".." / "log").resolve()
        candidate_dirs = sorted([p.name for p in log_base_dir.glob("[0-9]*-[0-9]*") if p.is_dir()])
        if candidate_dirs:
            found_dir = log_base_dir / candidate_dirs[-1]
        else:
            print("The log directory does not exist.")
            exit(1)

        print("The latest log directory already exists.")
        print(f"The latest log file directory : [{found_dir}]")
        while True:
            ans = input("Analyze file [y/N]? : ")
            if ans in ["y", "Y"]:
                break
            elif ans in ["n", "N"]:
                print("quit")
                exit(1)
        input_dir = found_dir

    # Setting output directory
    output_dir = Path(args.output).resolve()
    print(f"output directory : {output_dir}")
    analyze(input_dir, output_dir, args.analyze_PEs)


if __name__ == "__main__":
    main()
