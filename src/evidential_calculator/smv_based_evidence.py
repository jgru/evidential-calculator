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

    def normalize(_type: Union[Enum, str]):
        if isinstance(_type, EvidenceType):
            return _type
        else:
            if _type == EvidenceType.necessary.value:
                return EvidenceType.necessary
            elif _type == EvidenceType.sufficient.value:
                return EvidenceType.sufficient
            elif _type == EvidenceType.action_induced.value:
                return EvidenceType.action_induced
            else:
                raise ValueError(f"Can't convert {_type} to EvidenceType")


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
    def evidence_type_to_func(cls, _type: EvidenceType) -> Callable:
        if _type == EvidenceType.necessary:
            return cls.check_necessary_trace
        elif _type == EvidenceType.sufficient:
            return cls.check_sufficient_trace
        elif _type == EvidenceType.action_induced:
            return cls.check_action_induced_trace
        else:
            raise NotImplemented(
                "{_type.value} evidence sets are not implemented yet"
            )

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
        if _type == EvidenceType.sufficient and compound:
            return self.calc_set_compound(actions)

        check_func = self.evidence_type_to_func(_type)

        var_dict = self.get_model_vars()

        results = {}
        for action in actions:
            result = []
            for var, valuation in var_dict.items():
                values = self.get_values(valuation)
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

                a = [self.get_values(v) for v in d.values()]

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
    def check_action_induced_trace(
        action: pn.model.Identifier,
        d: dict[pn.model.Identifier, pn.model.Expression],
        action_name: str = "action",
    ):
        """
        Checks, wether setting of timestamp type ts of filepath is
        action-induced evidence of action

        FIXME: Check if this works with
        """
        ((var, val),) = d.items()
        # X (G ((A -> E) & Y (E -> O A)))
        s1 = f"X (G((({action_name} = {action}) -> ({var} = {val})) & Y(({var} = {val}) -> O ({action_name} = {action}))))"
        spec = pn.prop.Spec(pn.parser.parse_ltl_spec(s1))
        res = pn.mc.check_ltl_spec(spec)
        return res

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
    def get_values(valuation: pn.model.SimpleType):
        """
        Retrieves the values from pn.model.Scalar or pn.model.Boolean-objects.
        This is necessary, since Booleans do not have a values-member.
        """
        if isinstance(valuation, pn.model.Boolean):
            return [pn.model.Trueexp(), pn.model.Falseexp()]
        return valuation.values

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
