#!/usr/bin/python3

__author__ = "jgru"
__version__ = "0.0.1"

import argparse
import sys

from evidence_set_calculation.smv_based_evidence import *
from evidence_set_calculation.utils import *


def main():
    """Entry point for the CLI-tool

    Parses the CLI-arguments. constructs a NuSMVEvidenceProcessor and
    initiates the calculation of evidence sets.

    """
    args = parse_args()

    model_data = None

    # Checks, if stdin should be read
    if sys.stdin.isatty():
        if not args.model.name == "<stdin>":
            with open(args.model.name, "r") as f:
                model_data = f.read()
        else:
            exit("Supply SMV model via STDIN or file!")
    else:
        model_data = sys.stdin.read()

    with NuSMVEvidenceProcessor(model_data) as ep:
        es = ep.calc_set(
            EvidenceType.normalize(args.etype), [args.action]
        )
        output_evidence_set(es, args.output_format)


def parse_args():
    """Parses CLI-arguments with the help of argparse"""
    parser = argparse.ArgumentParser(description="")

    parser.add_argument(
        "-a",
        "--action",
        required=False,
        help="Name of the action of interest",
    )
    parser.add_argument(
        "-t",
        "--etype",
        default=EvidenceType.sufficient.value,
        choices=[EvidenceType.sufficient.value, EvidenceType.necessary.value],
        help="Type of evidence to calculate",
    )
    parser.add_argument(
        "-o",
        "--output-format",
        default=EvidenceFormat.csv.value,
        choices=[
            EvidenceFormat.csv.value,
            EvidenceFormat.raw.value,
        ],
        help="Output format of the calculated sets",
    )
    parser.add_argument(
        "model",
        nargs="?",
        type=argparse.FileType("r"),
        default=sys.stdin,
        help="Model specified in NuSMV's input language",
    )
    args = parser.parse_args()

    return args


if __name__ == "__main__":
    main()
