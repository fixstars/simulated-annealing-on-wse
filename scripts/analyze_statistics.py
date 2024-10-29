#!/usr/bin/env python3
import argparse
import json
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# ================================================================== #
# Target program version :[a035aee58fa8d7d592e49832debd9547558b4448] #
# ================================================================== #


def Import_statistics_data(input_dir: Path) -> list[dict, dict]:
    print("Import statistics data...")
    with (input_dir / "statistics.json").open("r", encoding="utf-8") as f:
        data = json.load(f)

    tile_info = {
        "grid_height": data["grid_height"],
        "grid_width": data["grid_width"],
        "iterations_per_collect": data["iterations_per_collect"],
    }
    tile_data = dict()
    tile: dict
    for tile in data["tile"]:
        tile_key = (tile["x"], tile["y"])

        def extract_key_data(tile: dict, key: str, T):
            return [T(statistics[key]) for statistics in tile["statistics"]]

        tile_data[tile_key] = {
            "temperature": extract_key_data(tile, "temperature", float),
            "energy": extract_key_data(tile, "energy", float),
            "flip_num": extract_key_data(tile, "flip_num", int),
            "iteration_num": extract_key_data(tile, "iteration_num", int),
        }
        tile_info[tile_key] = {"size": len(tile["statistics"])}
    print(f"{tile_info=}")
    return tile_data, tile_info


def parse_analyze_TILEs(
    tile_data: dict[tuple[int, int], dict], specified_TILEs: str
) -> list[tuple[int, int]]:
    print(f"{specified_TILEs=}")
    if specified_TILEs == "all":
        plot_TILEs = [TILE for TILE in tile_data.keys()]
    else:
        # Pattern1 : x,y
        if re.fullmatch(r"\d+,\d", specified_TILEs):
            x, y = map(int, specified_TILEs.split(","))
            plot_TILEs = [(x, y)]
        # Pattern2 : (x1,y1),(x2,y2),(x3,y3)
        elif re.fullmatch(r"\(\d+,\d+\)(,\(\d+,\d+\))*", specified_TILEs):
            plot_TILEs = [
                tuple(map(int, TILE.split(",")))
                for TILE in specified_TILEs.strip("()").split("),(")
            ]
        # Pattern3 : (x1,y1)-(x2,y2)
        elif re.fullmatch(r"\(\d+,\d+\)-\(\d+,\d+\)(,\(\d+,\d+\)-\(\d+,\d+\))*", specified_TILEs):
            ROI_TILEs = [
                Pre_ROI_TILE.split(")-(")
                for Pre_ROI_TILE in specified_TILEs.strip("()").split("),(")
            ]
            plot_TILEs: list[tuple[int, int]] = list()
            for ROI_TILE in ROI_TILEs:
                x1, y1 = map(int, ROI_TILE[0].split(","))
                x2, y2 = map(int, ROI_TILE[1].split(","))
                plot_TILEs += [(x, y) for x in range(x1, x2 + 1) for y in range(y1, y2 + 1)]
        else:
            print("Invalid TILE specific pattern.")
            exit(1)
    # sort, unique
    plot_TILEs = sorted(set(plot_TILEs))
    # intersect
    plot_TILEs = list(filter(lambda plot_TILE: plot_TILE in tile_data.keys(), plot_TILEs))
    print(f"{plot_TILEs=}")
    return plot_TILEs


def plot_statistics(
    output_dir: Path,
    tile_data: dict,
    tile_info: dict,
    plot_TILEs: list[tuple[int, int]],
):
    print("[PLOT] Plot statistics")
    grid_height = int(tile_info["grid_height"])
    grid_width = int(tile_info["grid_width"])
    iterations_per_collect = int(tile_info["iterations_per_collect"])

    fig_files: dict[tuple[int, int], str] = dict()
    TEMP_DIR = Path(tempfile.mkdtemp())

    TITLE_FONTSIZE = 30
    BASE_FONTSIZE = 18
    BASE_LINE_WIDTH = 3

    def add_svg_line(svg, x1, y1, x2, y2, stroke="black", stroke_width="10"):
        line = ET.SubElement(
            svg,
            "line",
            {
                "x1": str(x1),
                "y1": str(y1),
                "x2": str(x2),
                "y2": str(y2),
                "stroke": stroke,
                "stroke-width": stroke_width,
            },
        )
        return line

    def create_plot(adjust_xlim=False):
        if adjust_xlim:
            output_file_name = "statistics"
        else:
            output_file_name = "statistics_all_iteration"
        x_right = -1
        if adjust_xlim:
            x_right = 0
            for data in tile_data.values():
                for right in reversed(range(0, len(data["iteration_num"]))):
                    if all(
                        [
                            data[key][right] == data[key][-1]
                            for key in ["temperature", "energy", "flip_num"]
                        ]
                    ):
                        continue
                    else:
                        # update x_right with offset
                        x_right = max(min(right + 10, len(data["iteration_num"]) - 1), x_right)
            if x_right == 0:
                # plot all
                x_right = -1

        grid_ul = [grid_width, grid_height]
        grid_br = [0, 0]
        for gy in range(grid_height):
            for gx in range(grid_width):
                TILE = (gx, gy)
                name = f"Tile{TILE}"
                if TILE not in plot_TILEs:
                    print(f"Skip {name} plot...")
                    continue
                print(f"Creating {name} plot...")
                grid_ul[0] = min(gx, grid_ul[0])
                grid_ul[1] = min(gy, grid_ul[1])
                grid_br[0] = max(gx + 1, grid_br[0])
                grid_br[1] = max(gy + 1, grid_br[1])

                temperature = tile_data[TILE]["temperature"]
                energy = tile_data[TILE]["energy"]
                flip_num = tile_data[TILE]["flip_num"]
                iteration_num = tile_data[TILE]["iteration_num"]
                flip_probability = np.array(flip_num) / iterations_per_collect

                fig = plt.figure(figsize=(15, 10), tight_layout=True)
                plt.suptitle(name, fontsize=TITLE_FONTSIZE)
                fig.add_subplot(3, 1, 1)
                plt.plot(iteration_num, temperature, linewidth=BASE_LINE_WIDTH)
                plt.yscale("log")
                plt.xlim([0, iteration_num[x_right]])
                plt.yticks(fontsize=BASE_FONTSIZE)
                plt.xticks(fontsize=BASE_FONTSIZE)
                plt.ylabel("Temperature", fontsize=BASE_FONTSIZE * 1.5)
                plt.xlabel("Iteration", fontsize=BASE_FONTSIZE)

                fig.add_subplot(3, 1, 2)
                minimum_energy = [min(energy[: i + 1]) for i in range(len(energy))]
                plt.plot(
                    iteration_num,
                    energy,
                    linewidth=BASE_LINE_WIDTH,
                    label="current energy",
                )
                plt.plot(
                    iteration_num,
                    minimum_energy,
                    "r--",
                    linewidth=BASE_LINE_WIDTH * 0.8,
                    label="minimum energy",
                )
                plt.xlim([0, iteration_num[x_right]])
                plt.yticks(fontsize=BASE_FONTSIZE)
                plt.xticks(fontsize=BASE_FONTSIZE)
                plt.ylabel("Energy", fontsize=BASE_FONTSIZE * 1.5)
                plt.xlabel("Iteration", fontsize=BASE_FONTSIZE)
                plt.legend(fontsize=BASE_FONTSIZE)

                fig.add_subplot(3, 1, 3)
                plt.plot(
                    range(1, len(flip_probability) + 1),
                    flip_probability,
                    linewidth=BASE_LINE_WIDTH,
                )
                plt.ylim([0, 1.1])
                plt.xlim([0, iteration_num[x_right] // iterations_per_collect])
                plt.yticks(fontsize=BASE_FONTSIZE)
                plt.xticks(fontsize=BASE_FONTSIZE)
                plt.ylabel("Flip probability", fontsize=BASE_FONTSIZE * 1.5)
                plt.xlabel(
                    f"Number of collection ({iterations_per_collect=})",
                    fontsize=BASE_FONTSIZE,
                )
                output_file = TEMP_DIR / f"tile_{gx}_{gy}.svg"
                plt.savefig(output_file, bbox_inches="tight")
                plt.close(fig)
                fig_files[TILE] = output_file

        grid_ul = tuple(grid_ul)
        grid_br = tuple(grid_br)
        subgrid_width = grid_br[0] - grid_ul[0]
        subgrid_height = grid_br[1] - grid_ul[1]

        result_svg: ET.Element
        merged_width: float
        merged_height: float
        tile_width: float
        tile_height: float
        first = True
        for gy in range(grid_ul[1], grid_br[1]):
            for gx in range(grid_ul[0], grid_br[0]):
                TILE = (gx, gy)
                if TILE not in fig_files:
                    continue
                tile = ET.parse(fig_files[TILE]).getroot()
                if first:
                    first = False
                    tile_width = float(tile.get("width").rstrip("pt"))
                    tile_height = float(tile.get("height").rstrip("pt"))
                    merged_width = tile_width * subgrid_width + 10 * (subgrid_width + 1)
                    merged_height = tile_height * subgrid_height + 10 * (subgrid_height + 1)
                    result_svg = ET.Element(
                        "svg",
                        width=f"{merged_width}",
                        height=f"{merged_height}",
                        xmlns="http://www.w3.org/2000/svg",
                    )
                TILE_sub_offset = (TILE[0] - grid_ul[0], TILE[1] - grid_ul[1])
                g = ET.Element("g")
                g.set(
                    "transform",
                    f"translate({TILE_sub_offset[0] * tile_width + 10 * (TILE_sub_offset[0] + 1)}, {TILE_sub_offset[1] * tile_height + 10 * (TILE_sub_offset[1] + 1)})",
                )
                for element in tile:
                    g.append(element)
                result_svg.append(g)

        # add lines
        for gx_sub_offset in range(subgrid_width + 1):
            add_svg_line(
                result_svg,
                gx_sub_offset * tile_width + 10 * (gx_sub_offset + 1) - 5,
                0,
                gx_sub_offset * tile_width + 10 * (gx_sub_offset + 1) - 5,
                merged_height,
            )
        for gy_sub_offset in range(subgrid_height + 1):
            add_svg_line(
                result_svg,
                0,
                gy_sub_offset * tile_height + 10 * (gy_sub_offset + 1) - 5,
                merged_width,
                gy_sub_offset * tile_height + 10 * (gy_sub_offset + 1) - 5,
            )

        tree = ET.ElementTree(result_svg)
        output_file = output_dir / f"{output_file_name}.svg"
        print(f"Create svg result file : {output_file}")
        tree.write(output_file)
        print("Done")

    print("===========================\n< ALL ITERATION PLOT >\n===========================")
    create_plot(False)
    print("===========================\n< ADJUST ITERATION PLOT >\n===========================")
    create_plot(True)

    # clean temp directory
    shutil.rmtree(TEMP_DIR)


def analyze(input_dir: Path, output_dir: Path, specified_TILEs: str):
    tile_data, tile_info = Import_statistics_data(input_dir)
    plot_TILEs = parse_analyze_TILEs(tile_data, specified_TILEs)
    plot_statistics(output_dir, tile_data, tile_info, plot_TILEs)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", help="input log directory")
    parser.add_argument("--output", "-o", help="output data directory", default=".")
    parser.add_argument(
        "--analyze-TILEs",
        help="TILE specific pattern: x,y OR (x1,y1),(x2,y2),(x3,y3) OR (x1,y1)-(x2,y2) OR all",
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
    analyze(input_dir, output_dir, args.analyze_TILEs)


if __name__ == "__main__":
    main()
