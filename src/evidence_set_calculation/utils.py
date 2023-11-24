#!/usr/bin/python3

__author__ = "jgru"
__version__ = "0.0.1"

import csv
import io
from enum import Enum
from typing import Union

from .smv_based_evidence import EvidenceType


class EvidenceFormat(Enum):
    org = "org"
    csv = "csv"
    raw = "raw"

    def __str__(self) -> str:
        return str.__str__(self)


def output_evidence_set(
    es: dict[str, tuple[str, str]],
    _type: Union[EvidenceType, str],
    output_format: Union[EvidenceFormat, str]
):

    assert _type != None, "Specify type!"
    _type = EvidenceType.normalize(_type)

    if output_format == EvidenceFormat.csv.value:
        output = construct_csv(es, _type)
    elif output_format == EvidenceFormat.org.value:
        output = construct_org_table(es, _type)
    else:
        output = es

    print(output)


AND = r" & "
OR = r" | "

ALT_AND = " and " # r" /\ "
ALT_OR = " or " # r" \/ "


def evidence_elem_to_formula(
    pe: tuple[str, str], _type: EvidenceType, use_alt_syms: bool = False
):
    _and = AND if not use_alt_syms else ALT_AND
    _or = OR if not use_alt_syms else ALT_OR

    trace_connective = _or if _type == EvidenceType.necessary else _and
    return trace_connective.join([f"{e}={v}" for e, v in pe.items()])


def evidence_to_formula(
    evidence: list[tuple[str, str]], _type: EvidenceType, use_alt_syms: bool = False
):
    # Determin style of boolean connectives
    _and = AND if not use_alt_syms else ALT_AND
    _or = OR if not use_alt_syms else ALT_OR

    elem_connective = _and if _type == EvidenceType.necessary else _or

    formula = ""
    is_first = True

    for e in evidence:
        pred = evidence_elem_to_formula(e, _type, use_alt_syms)
        if len(e.items()) > 1:
            pred = f"( {pred} )"

        if is_first:
            is_first = False
            formula += f"{pred}"
        else:
            formula += f"{elem_connective}{pred}"

    return formula


def construct_csv(action_to_evidence: dict[str, tuple[str, str]], _type: EvidenceType):
    output = io.StringIO()
    header = ["action", "evidence"]
    w = csv.writer(
        output,
        delimiter=",",
        quotechar='"',
        quoting=csv.QUOTE_MINIMAL,
        dialect="unix",
    )

    w.writerow(header)

    for action in sorted(action_to_evidence):
        formula = evidence_to_formula(action_to_evidence[action], _type)
        w.writerow([action, formula])

    return output.getvalue().strip("\r\n").strip("\r").strip("\n")


def construct_org_table(action_to_evidence, _type, title="Evidence"):
    """A very naive implementation to print evidence sets as
    org-mode-tables. This should _only_ be used with org-babel and
    `:results output table raw'
    """
    org_table_string = ""
    l = len(f"{max(action_to_evidence.keys(), key=len)} of {title} ")

    row_sep = f"|{l * '--'}|\n"
    col_heading_1 = "Desc"
    col_heading_2 = "Assignments"
    org_table_string = (
        f"{row_sep}| "
        + f"{col_heading_1} {(l//2- len(col_heading_1)) * ' ' }|"
        + f" {col_heading_2} {(l//2- len(col_heading_2)) * ' '}\n"
    )

    # Construct entries for each action
    for action in sorted(action_to_evidence.keys()):
        h = f"{title} of {action}"
        h += (l - len(h)) * " "
        org_table_string += row_sep

        # Raw variable/value assignments
        if not _type:
            values = action_to_evidence[action]
            if not values:
                org_table_string += f"| {h:>5} | \n"
            for value in values:
                org_table_string += f"| {h:>5} | {value} |\n"
                h = " " * l
        # Formula
        else:
            org_table_string += (
                f"| {h:>5} |"
                + evidence_to_formula(
                    action_to_evidence[action], _type, use_alt_syms=True
                )
                + "|\n"
            )

    org_table_string += row_sep

    return org_table_string
