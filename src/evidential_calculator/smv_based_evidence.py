import copy
import logging
import time
from enum import Enum, auto
from typing import OrderedDict, Union

import pynusmv as pn


class EvidenceType(Enum):
    necessary = "necessary"
    sufficient = "sufficient"
    action_induced = "action-induced"

    def __str__(self) -> str:
        return str.__str__(self)


class EvidenceFormat(Enum):
    org = "org"
    csv = "csv"
    raw = "raw"

    def __str__(self) -> str:
        return str.__str__(self)


class NuSMVEvidenceProcessor:
    ACTION_NAME = "action"

    def __init__(self, model):
        self.model_data = model
        self.parsed_model = pn.parser.parseAllString(
            pn.parser.module, self.model_data
        )
        self.is_initialized = False

    def __enter__(self):
        self.is_initialized = self.setup(self.model_data)

        assert (
            self.is_initialized
        ), "Failed to inititalize PySMV!\nCheck the given model."

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.deinit()

    @classmethod
    def setup(cls, model: str) -> bool:
        """
        Inititializes NuSMV and loads the model to check
        """
        pn.init.init_nusmv()
        t0 = time.time()
        pn.glob.load(model)
        pn.glob.compute_model()

        try:
            pn.glob.flatten_hierarchy()
        except (
            pn.exception.NuSMVNoReadModelError,
            pn.exception.NuSMVNeedFlatHierarchyError,
            pn.exception.NuSMVModelAlreadyFlattenedError,
        ) as e:
            if isinstance(e, pn.exception.NuSMVModelAlreadyFlattenedError):
                logging.info("Model already flat ", e)
            else:
                logging.error("NuSMV error loading or computing error  ", e)
                return False

        logging.info(f"Loading model took {time.time()-t0} secs")

        return True

    def deinit(self):
        pn.init.deinit_nusmv()
        self.is_initialized = False

    def get_model_vars(self, action: str = ACTION_NAME) -> OrderedDict:
        # Alternative implementation:
        # fh = pn.glob.flat_hierarchy()
        # Operate on strings due to PyNuSMV implementation specifics
        # (Throws segfault on _vars.remove(pn.model.Identifier(action))
        # _vars = [str(v) for v in fh.variables]
        _vars = copy.deepcopy(self.parsed_model.VAR)

        if pn.model.Identifier(action) in _vars.keys():
            del _vars[pn.model.Identifier(action)]

        return _vars

    def get_model_actions(self, action: str = ACTION_NAME) -> list:
        actions = []
        _vars = self.parsed_model.VAR

        if pn.model.Identifier(action) in _vars.keys():
            actions = _vars[pn.model.Identifier(action)].values

        return actions

    @classmethod
    def evidence_type_to_func(cls, _type: Union[EvidenceType, str]):

        if isinstance(_type, EvidenceType):
            _type = _type.value

        if _type == EvidenceType.necessary.value:
            return cls.check_necessary_trace
        elif _type == EvidenceType.sufficient.value:
            return cls.check_sufficient_trace
        else:
            raise NotImplemented("Action-induced evicence not implemented yet")

    def calc_set(
        self, action: str, _type: EvidenceType, with_constants: bool = False
    ):
        check_func = self.evidence_type_to_func(_type)

        # Either calculate evidence set for a single action
        if action:
            actions = [action]
        else:  # Or for all actions in the model
            actions = self.get_model_actions()
        var_dict = self.get_model_vars()

        results = {}
        result = []

        for action in actions:
            for var in var_dict.keys():
                valuation = var_dict[var].values
                for val in valuation:
                    if _type == EvidenceType.sufficient:
                        is_evidence = check_func(
                            action, var, val=val, with_constants=with_constants
                        )
                    else:
                        is_evidence = check_func(action, var, val=val)

                    if is_evidence:
                        result.append((str(var), str(val)))

            results[str(action)] = result

        return results

    @staticmethod
    def check_necessary_trace(
        action: pn.model.Identifier,
        var: pn.model.Identifier,
        val: pn.model.Expression = pn.model.Trueexp(),
        action_name: str = ACTION_NAME,
    ):
        s1 = f"X (G({action_name} = {action} ->  (G {var} = {val})))"
        spec = pn.prop.Spec(pn.parser.parse_ltl_spec(s1))
        res = pn.mc.check_ltl_spec(spec)

        return res

    @staticmethod
    def check_sufficient_trace(
        action: pn.model.Identifier,
        var: pn.model.Identifier,
        val: pn.model.Expression = pn.model.Trueexp(),
        action_name: str = ACTION_NAME,
        with_constants: bool = False,
    ):
        """
        Checks, wether setting of timestamp type ts of filepath is
        sufficient evidence of action

        This is done by the LTL formulae (a denotes the action and
        filepath its trace). E.g.,

        (X action = a) V filepath__ts_cr = FALSE


        This formula checks if the timestamp type is differing until the
        action a is executed in the next step.

        Note: If the model contains constants, you need to check the
        following formula as well

        (G(path.ts_cr = FALSE))  <- this should yield False

        This ensures that the timestamp type is actually set somewhere
        and does not always remain FALSE. Please note, that the
        conjunct of those two formulae is not the same as checking
        them in order.

        Parameters:
        action      -- symbolic enum of the action in question
        filepath_ts -- filepath with the TS type as suffix of the file to check
        action_name -- identifier of the action in NuSMV model

        """

        s1 = f"(X {action_name} = {action}) V {var} != {val}"
        spec = pn.prop.Spec(pn.parser.parse_ltl_spec(s1))

        releases = pn.mc.check_ltl_spec(spec)

        # Early exit since the trace is definitely not characteristic
        if not releases or not with_constants:
            return releases

        # Checks, if the variable is actually modified at some point
        s2 = f"(G({var} != {val}))"
        spec = pn.prop.Spec(pn.parser.parse_ltl_spec(s2))
        is_unreachable = pn.mc.check_ltl_spec(spec)

        return releases and not is_unreachable
