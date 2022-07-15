#!/usr/bin/python3

__author__ = "jgru"
__version__ = "0.0.1"

import csv
import io
from enum import Enum
from typing import Union


class EvidenceFormat(Enum):
    org = "org"
    csv = "csv"
    raw = "raw"

    def __str__(self) -> str:
        return str.__str__(self)


def output_evidence_set(es, output_format: Union[EvidenceFormat, str]):
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
    """
    A very naive (and incomplete) implementation to print evidence
    sets as org-mode-tables. This should only be used with org-babel
    and `:results output table raw'
    """
    org_table_string = ""
    l = len(f"{max(action_to_evidence.keys(), key=len)} of {title} ")
    row_sep = f"|{l * '--'}|\n"
    col_heading_1 = "Desc"
    col_heading_2 = "Assignments"
    org_table_string = f"| {col_heading_1} {(l//2- len(col_heading_1)) * ' ' }| {col_heading_2} {(l//2- len(col_heading_2)) * ' '}\n"

    for key in sorted(action_to_evidence.keys()):
        h = f"{title} of {key}"
        h += (l - len(h)) * " "
        org_table_string += row_sep
        values = action_to_evidence[key]
        if not values:
            org_table_string += f"| {h:>5} | \n"
        for value in values:
            org_table_string += f"| {h:>5} | {value} |\n"
            h = " " * l

    org_table_string += row_sep

    return org_table_string
