import copy
import sys
import time
from collections.abc import Callable
from enum import Enum
from functools import partial
from itertools import chain, combinations, product
from typing import OrderedDict, Union

import pynusmv as pn


class EvidenceType(Enum):
    necessary = "necessary"
    sufficient = "sufficient"
    action_induced = "action-induced"

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
                pass
                # print(f"Model already flat {e}")
            else:
                print(
                    f"NuSMV error loading or computing error {e}",
                    file=sys.stderr,
                )
                return False

        # print(f"Loading model took {time.time()-t0} secs", file=sys.stderr)

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
    def evidence_type_to_func(
        cls, _type: Union[EvidenceType, str]
    ) -> Callable:

        if isinstance(_type, EvidenceType):
            _type = _type.value

        if _type == EvidenceType.necessary.value:
            return cls.check_necessary_trace
        elif _type == EvidenceType.sufficient.value:
            return cls.check_sufficient_trace
        else:
            raise NotImplemented("Action-induced evicence not implemented yet")

    def calc_set(
        self,
        action: pn.model.Identifier,
        _type: EvidenceType,
        compound: bool = False,
    ):

        # Either calculate evidence set for a single action
        if action:
            actions = [action]
        else:  # Or for all actions in the model
            actions = self.get_model_actions()

        # Calculate compound SE differently
        if _type == EvidenceType.sufficient.value and compound:
            return self.calc_set_compound(actions)

        check_func = self.evidence_type_to_func(_type)

        var_dict = self.get_model_vars()

        results = {}
        for action in actions:
            result = []
            for var, valuation in var_dict.items():
                if isinstance(valuation, pn.model.Boolean):
                    values = [pn.model.Trueexp(), pn.model.Falseexp()]
                else:
                    values = valuation.values
                for d in [{var: val} for val in values]:
                    if check_func(action, d):
                        # ((var, val),) = d.items()
                        result.append(d)

            results[str(action)] = result
        return results

    def calc_set_compound(self, actions: list[pn.model.Identifier]):
        results = {}
        _vars = self.get_model_vars()

        for action in actions:
            result = []
            for d in self.powerdict(_vars):
                a = [v.values for v in d.values()]

                combos = [
                    dict(zip(d.keys(), comb))
                    for comb in product(*a)
                    if len(comb)
                ]
                result = []

                for c in combos:
                    if self.check_sufficient_trace(action, c):
                        result.append(c)
            results[str(action)] = result
        return results

    @staticmethod
    def check_necessary_trace(
        action: pn.model.Identifier,
        d: dict[pn.model.Identifier, pn.model.Expression],
        action_name: str = ACTION_NAME,
    ):
        ((var, val),) = d.items()
        s1 = f"X (G({action_name} = {action} ->  (G {var} = {val})))"
        spec = pn.prop.Spec(pn.parser.parse_ltl_spec(s1))
        res = pn.mc.check_ltl_spec(spec)

        return res

    @staticmethod
    def check_sufficient_trace(
        action: pn.model.Identifier,
        d: dict,
        action_name: str = ACTION_NAME,
    ):
        """ """
        s1 = (
            f"(X {action_name} = {action}) V ("
            + " | ".join([f"{var} != {val}" for var, val in d.items()])
            + ")"
        )
        spec = pn.prop.Spec(pn.parser.parse_ltl_spec(s1))

        releases = pn.mc.check_ltl_spec(spec)

        # Early exit since the trace is definitely not characteristic
        if not releases:
            return releases

        # FIXME, is this correct for _compound_ traces?
        # Checks, if the variable is actually modified at some point
        s2 = (
            "("
            + " | ".join([f"G({var} != {val})" for var, val in d.items()])
            + ")"
        )

        spec = pn.prop.Spec(pn.parser.parse_ltl_spec(s2))
        is_unreachable = pn.mc.check_ltl_spec(spec)

        return releases and not is_unreachable

    @staticmethod
    def powerset(set_):
        """
        Constructs a powerset, like so
        powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)

        Taken from
        http://jim-holmstroem.github.io/python/itertools/2014/09/28/powerset-powerdict.html

        """
        return chain.from_iterable(
            map(partial(combinations, set_), range(len(set_) + 1))
        )

    @staticmethod
    def powerdict(dict_):
        return map(dict, NuSMVEvidenceProcessor.powerset(dict_.items()))
