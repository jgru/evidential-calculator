#!/usr/bin/python3

__author__ = "jgru"
__version__ = "0.0.1"

import csv
import io

from .smv_based_evidence import *


def output_evidence_set(es, output_format):
    if output_format == EvidenceFormat.csv.value:
        output = construct_csv(es)
    elif output_format == EvidenceFormat.org.value:
        output = construct_org_table(es)
    else:
        output = es

    print(output)


def construct_csv(action_to_evidence: dict[str, tuple[str, str]]):
    output = io.StringIO()
    header = ["action", "evidence"]
    w = csv.writer(
        output,
        sys.stdout,
        delimiter=",",
        quotechar='"',
        quoting=csv.QUOTE_MINIMAL,
    )

    w.writerow(header)

    for key in action_to_evidence:
        for evidences in action_to_evidence[key]:
            evidences = [key, evidences]
            w.writerow(evidences)
    return output.getvalue().strip("\r\n")


def construct_org_table(action_to_evidence, title="Evidence"):
    org_table_string = ""
    l = len(f"{max(action_to_evidence.keys(), key=len)} of {title} ")
    row_sep = f"|{l * '--'}|\n"

    org_table_string = (
        f"| Desc {l//3 * ' '}| Var {l//3 * ' '}| Val {l/3 * ' '}|\n"
    )

    for key in sorted(action_to_evidence.keys()):
        h = f"{title} of {key}"
        h += (l - len(h)) * " "
        org_table_string += row_sep
        values = action_to_evidence[key]
        if not values:
            org_table_string += f"| {h:>5} |  | \n"
        for value in values:
            f, v = value
            org_table_string += f"| {h:>5} | {f:>5} | {v:>5} |\n"
            h = " " * l

    org_table_string += row_sep

    return org_table_string
