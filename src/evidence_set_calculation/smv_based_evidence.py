from __future__ import annotations

import copy
import sys
from collections.abc import Callable
from enum import Enum
from functools import partial, reduce
from itertools import chain, combinations, product
from operator import iconcat
from typing import OrderedDict, Union

import pynusmv as pn


class EvidenceType(Enum):
    """Defines the classes of evidence

    necessary: X(G(A_i -> E))
    sufficient: X (A_i) V !E
    action-induced: X (G ((A_i -> E) & Y (E -> O A_i)))

    """

    necessary = "necessary"
    sufficient = "sufficient"
    action_induced = "action-induced"

    def __str__(self) -> str:
        return str.__str__(self)

    def normalize(_type: Union[Enum, str]) -> EvidenceType:
        """
        Ensures that _type is converted to an EvidenceType-object
        if necessary.

        Returns the corresponding EvidenceType
        """
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
    """Houses the necessary functionality to process a model and extract
    actions and variables, in order to calculate sets of evidence.

    """

    # Identifier used by the SMV-model to denote
    # the encoding of the action
    ACTION_NAME = "action"

    def __init__(self, model) -> None:
        """Initializes the processor. To do so, the model data is
        stored in its string version and as well in a parsed version
        for later use.

        """
        self.model_data = model
        self.parsed_model = pn.parser.parseAllString(pn.parser.module, self.model_data)
        self.is_initialized = False

    def __enter__(self) -> self:
        """
        Establishes a context manager and initializes pynusmv.
        """
        self.is_initialized = self.setup(self.model_data)

        assert (
            self.is_initialized
        ), "Failed to inititalize PySMV!\nCheck the given model."

        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """
        Exits the context manager and tears down pynusmv.
        """
        self.deinit()

    @classmethod
    def setup(cls, model: str) -> bool:
        """Inititializes NuSMV and loads the model to check."""
        pn.init.init_nusmv()
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
                # NuSMVModelAlreadyFlattenedError is irrelevant
                pass
            else:
                print(
                    f"NuSMV error loading or computing error {e}",
                    file=sys.stderr,
                )
                return False

        return True

    def deinit(self) -> None:
        """Quits and cleans up NuSMV."""
        pn.init.deinit_nusmv()
        self.is_initialized = False

    def get_model_vars(self, action: str = ACTION_NAME) -> OrderedDict:
        """Retrieves all variables in the model. The variable that
        encodes the action is ignored. (Alternative way would be to
        use the flat hierarchy (pn.glob.flat_hierarchy())

        Returns an OrderedDict of pn.model.Identifiers as keys and
        pn.model.SimpleTypes as values.

        """
        _vars = copy.deepcopy(self.parsed_model.VAR)

        if pn.model.Identifier(action) in _vars.keys():
            del _vars[pn.model.Identifier(action)]

        return _vars

    def get_model_actions(self, action: str = ACTION_NAME) -> list[pn.model.Identifier]:
        """Retrieves the valuation of the model's variable that
        encodes the action. This variable should be a symbolic enum
        (of type pn.model.Scalar).

        Returns a list of pn.model.Identifiers, e.g., [a0, a1,
        unconstrain].

        """
        actions = []
        _vars = self.parsed_model.VAR

        if pn.model.Identifier(action) in _vars.keys():
            actions = list(_vars[pn.model.Identifier(action)].values)

        return actions

    @classmethod
    def evidence_type_to_func(cls, _type: EvidenceType) -> Callable:
        """Maps the EvidenceType (SE, NE, AE) to the corresponding
        calculation function.

        Returns the function needed to calculate the EvidenceType
        specified by the parameter _type.

        """
        if _type == EvidenceType.necessary:
            return cls.check_necessary_trace
        elif _type == EvidenceType.sufficient:
            return cls.check_sufficient_trace
        elif _type == EvidenceType.action_induced:
            return cls.check_action_induced_trace
        else:
            raise NotImplemented("{_type.value} is unknown.")

    def calc_set(
        self,
        _type: Union[EvidenceType, str],
        actions: Union[pn.model.Identifier, list[pn.model.Identifier]] = None,
    ) -> dict[str, dict[pn.model.Identifier, pn.model.Identifier]]:
        """Calucates the requested set of evidence.

        _type specifies which kind of evidence to calculate.

        actions might be a single action (specified as str or
        pn.model.Identifier or a list of those types). If it is [] or
        None, all actions are queried from the model

        Returns a dict of dicts where the respective action is used as key
        for the respective dict of evidence.

        """
        _type = EvidenceType.normalize(_type)

        actions = self.sanitize_actions(actions)

        check_func = self.evidence_type_to_func(_type)

        if _type == EvidenceType.action_induced:
            check_func = partial(check_func, actions)

        return self.calc_set_compound(check_func, actions)

    def calc_set_compound(
        self,
        check_func: Callable[
            [pn.model.Identifier, dict[pn.model.Identifier, pn.model.SimpleType], str],
            bool,
        ],
        actions: list[pn.model.Identifier],
    ):
        """Specialization of the calc_set()-method for the
        calculation of compound traces.

        The calculation itself is conducted as follows:

        1. Retrieve the model vars
        2. Form the powerdict
           (e.g., [{}, {x:[...]}, {y:[...]}, {x:[...], y:[...]},...])
        3. Take each element of the powerdict
        4. Form each possible combination of vars and values
           (e.g., [{x: 1, y: True}, {x:2, y=True},...}])
           Note: This includes unconstraint vars
        5. Pass the respective combination to the check-func,
           which constructs the LTL-specification and calls the MC
        6. Eventually, store the variable/value-combination, if
           the formula holds

        Returns a dict of dicts where the respective action is used as key
        for the respective dict of evidence.
        """
        results = {}
        _vars = self.get_model_vars()

        for action in actions:
            # Collect variable combos to avoid "checking to much"
            hits = []
            result = []
            for d in self.powerdict(_vars):

                # Check whether a subset of this variables were alread
                # sufficient (or necessary)
                if any([h.items() <= d.items() for h in hits]):
                    continue

                # Get valuation of each variable
                # e.g., [[1,2,3], [True, False],...
                a = [self.get_values(v) for v in d.values()]

                # Construct the combinations
                # e.g., [{x: 1, y: True}, {x:2, y=True},...}]
                combos = [
                    dict(zip(d.keys(), comb)) for comb in product(*a) if len(comb)
                ]

                # Pass the combinations to the check-functions,
                # which constructs the LTL-formula and queries the MC
                for c in combos:
                    if check_func(action, c):
                        hits.append(d)
                        result.append(c)

            results[str(action)] = result
        return results

    @staticmethod
    def check_necessary_trace(
        action: pn.model.Identifier,
        var_val_mapping: dict[pn.model.Identifier, pn.model.SimpleType],
        action_name: str = ACTION_NAME,
    ) -> bool:
        """Checks whether the variable/value-combination is part of
        the necessary evidence of the target action. This is
        accomplished by using the following LTL-formula:

        X (G(A -> (G E))

        For compound traces, we employ dualization, which means that
        in the case of a compound trace, we negate E and read the resulting
        set as big conjunction comprised of all set elements. To be
        specific:

        The first step is the negation of E:

        X (G ( (action = a1) -> G !(var1 = FALSE & var2 = FALSE) ) )

        which would lead to the inclusion of 'var1=TRUE \/ var2=TRUE' in
        the evidence set, whose elements are connected via
        conjunctions to form NE.

        To implement it more easily, we could distribute the negation
        and directly compute the following LTL specification

        X (G ( (action = a1) -> G (var1 = TRUE | var2 = TRUE) ) )

        which is actually done in this function.

        """
        phi = (
            f"X ( G ( {action_name} = {action} ->  G ("
            + " | ".join([f"{var} = {val}" for var, val in var_val_mapping.items()])
            + ")))"
        )

        spec = pn.prop.Spec(pn.parser.parse_ltl_spec(phi))
        res = pn.mc.check_ltl_spec(spec)

        return res

    @staticmethod
    def check_sufficient_trace(
        action: pn.model.Identifier,
        var_val_mapping: dict[pn.model.Identifier, pn.model.SimpleType],
        action_name: str = ACTION_NAME,
    ) -> bool:
        """Checks whether the variable/value-combination(s) is/are
        part of the necessary evidence of the target action. This is
        accomplished by using the following LTL-formula:

        (X action = a) V ({var1} != {val1})

        Based on DeMorgan's law, the following formula is used when
        there are multiple variables:

        (X action = a) V (({var1} !={val1}) | ({var} != {val}) | ...)

        """
        phi = (
            f"(X {action_name} = {action}) V ("
            + " | ".join([f"{var} != {val}" for var, val in var_val_mapping.items()])
            + ")"
        )
        spec = pn.prop.Spec(pn.parser.parse_ltl_spec(phi))

        releases = pn.mc.check_ltl_spec(spec)

        # Early exit since the trace is definitely not sufficient
        if not releases:
            return releases

        return releases and not NuSMVEvidenceProcessor.is_unreachable(var_val_mapping)

    @staticmethod
    def is_unreachable(
        var_val_mapping: dict[pn.model.Identifier, pn.model.SimpleType]
    ) -> bool:
        """Checks whether a variable's valuation (or a combination of
        variable valuations) is actually reachable.

        In the most simple case, you check if the model contains
        constants by using following formula as well

        G (var != TRUE)  <- this should yield False

        This ensures that the variable is actually set/changed
        somewhere.

        For combinations of variabls, the disjunction is checked
        (De-morgan since we use the negation here).

        """
        # Checks if this combination of variables is actually reachable
        phi = (
            "G("
            + " | ".join([f"({var} != {val})" for var, val in var_val_mapping.items()])
            + ")"
        )

        spec = pn.prop.Spec(pn.parser.parse_ltl_spec(phi))
        return pn.mc.check_ltl_spec(spec)

    @staticmethod
    def check_action_induced_trace(
        actions: list[pn.model.Identifier],
        action: pn.model.Identifier,
        var_val_mapping: dict[pn.model.Identifier, pn.model.SimpleType],
        action_name: str = "action",
    ) -> bool:
        """Checks whether the variable/value-combination is part of
        the action-induced evidence set by applying the following
        LTL-formula:

        ! AE &
        X G (sigma -> AE) &
        G ^_{sigma' in Sigma'} ! AE -> X (sigma' -> not EA)

        Here, the big conjunction symbol ^_ expresses a finite
        conjunction over all other actions sigma' other than the
        target action sigma

        If the a/m formula yields true, the evidence E is
        action-induced evidence meaning that it is direct effect of
        the target action sigma.

        *Note:* The current implementation is oversimplified.
        Assignments to a value of a another variable would lead to
        evidence formed by an implication, which cannot be handled by
        the current implementation.

        """
        ae = " & ".join([f"{var} = {val}" for var, val in var_val_mapping.items()])

        phi = (
            f"(!{ae}) & (X G (({action_name} = {action}) -> ({ae}))) & G ("
            + " & ".join(
                [
                    f"((!{ae}) -> X (({action_name} = {other}) -> (!{ae}))) "
                    for other in actions
                    if other != action
                ]
            )
            + ")"
        )
        spec = pn.prop.Spec(pn.parser.parse_ltl_spec(phi))
        res = pn.mc.check_ltl_spec(spec)

        # Early exit, since the trace is definitely not part of the evidence set

        if not res:
            return res

        return res and not NuSMVEvidenceProcessor.is_unreachable(var_val_mapping)

    def sanitize_actions(
        self, actions: Union[pn.model.Identifier, list[pn.model.Identifier]]
    ) -> list[pn.model.Identifier]:
        """Sanitizes the received action(s). If the passed parameter
        is an empty list or None, all possible actions from the model
        are used.

        """
        model_actions = self.get_model_actions()

        # Ensure actions is a list
        if isinstance(actions, str) or isinstance(actions, pn.model.Identifier):
            actions = [actions]

        # Either populate
        if isinstance(actions, list):
            if not len(actions) or not actions[0]:
                actions = self.get_model_actions()
            elif isinstance(actions[0], str):
                actions = [pn.model.Identifier(a) for a in actions]
                for a in actions:
                    if a not in model_actions:
                        raise ValueError(
                            f"Specified action {a} is not existing in the model."
                        )
        else:
            actions = self.get_model_actions()

        return actions

    @staticmethod
    def get_values(valuation: pn.model.SimpleType) -> list[pn.model.SimpleType]:
        """Retrieves the values from pn.model.Scalar or
        pn.model.Boolean-objects. This is necessary, since Booleans do
        not have a values-member.
        """
        if isinstance(valuation, pn.model.Boolean):
            return [pn.model.Trueexp(), pn.model.Falseexp()]
        return valuation.values

    @staticmethod
    def quantify_expressiveness(actions_to_evidence, ):
        """Calculates expressiveness by using the following formula

        E(p) = \frac{\big\vert\{\sigma \in \Sigma \mid \exists \rho \in
               SE(\sigma,M):\, \rho \sqsubseteq p\}\big\vert}{|\Sigma|}

        Note: This requires a _complete_ actions_to_evidence-dict that
        contains all actions in the model and the respective traces.
        """

        # Retrieve all unique facets
        facets = set(
            [
                frozenset(elem.items())
                for elem in reduce(iconcat, actions_to_evidence.values())
            ]
        )
        # Actions to consider
        actions = actions_to_evidence.keys()

        _expr = {}  # resulting expressiveness per facet

        # Calculate expressiveness of each facet:
        return {
            p: sum(
                map(
                    lambda k: any(
                        [
                            k
                            for rho in actions_to_evidence[k]
                            if all(e in p for e in rho.items())
                        ]
                    ),
                    actions,
                )
            )
            / len(actions)
            for p in facets
        }

    @staticmethod
    def powerset(_set):
        """Constructs a powerset

        E.g., powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)

        Inspired by
        http://jim-holmstroem.github.io/python/itertools/2014/09/28/powerset-powerdict.html

        """
        return chain.from_iterable(
            map(partial(combinations, _set), range(len(_set) + 1))
        )

    @staticmethod
    def powerdict(dict_):
        """Constructs a powerdict

        E.g., powerdict({"x":[], "y": []}) --> {"x": [], "y": [] } ->
        [{}, {'x': []}, {'y': []}, {'x': [], 'y': []}]

        """
        return map(dict, NuSMVEvidenceProcessor.powerset(dict_.items()))
