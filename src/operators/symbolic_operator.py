"""
Symbolic Operator (Φ_s)

Handles rules, logic, and constraints.
Operates on the symbolic component of state.
"""

from typing import Dict, Any, List, Callable, Optional
from .base_operator import BaseOperator, OperatorType
from ..state.cognitive_state import CognitiveState


class SymbolicOperator(BaseOperator):
    """
    Symbolic operator for rule-based reasoning and constraint satisfaction.
    """
    
    def __init__(
        self,
        operator_id: str,
        rules: Optional[List[str]] = None,
        constraints: Optional[List[str]] = None,
        description: str = ""
    ):
        super().__init__(operator_id, OperatorType.SYMBOLIC, description)
        self.rules = rules or []
        self.constraints = constraints or []
    
    def _execute(self, state: CognitiveState, **kwargs) -> Dict[str, Any]:
        """
        Execute symbolic reasoning on state.
        
        Args:
            **kwargs:
                - operation: type of symbolic operation (deduce, constrain, validate)
                - new_facts: facts to add
                - new_rules: rules to add
                - new_constraints: constraints to add
        """
        operation = kwargs.get("operation", "deduce")
        
        if operation == "deduce":
            return self._deduce(state, **kwargs)
        elif operation == "constrain":
            return self._constrain(state, **kwargs)
        elif operation == "validate":
            return self._validate(state, **kwargs)
        elif operation == "add_fact":
            return self._add_facts(state, **kwargs)
        elif operation == "add_rule":
            return self._add_rules(state, **kwargs)
        else:
            return {"facts": ["error:unknown_operation"]}
    
    def _deduce(self, state: CognitiveState, **kwargs) -> Dict[str, Any]:
        """Apply deductive reasoning based on existing facts and rules"""
        facts = state.symbolic.facts.copy()
        rules = state.symbolic.rules.copy() + self.rules
        
        # Simple deduction simulation
        new_facts = []
        for rule in rules:
            # Parse rule format: "if FACT then FACT"
            if "if" in rule and "then" in rule:
                parts = rule.split("then")
                if len(parts) == 2:
                    condition = parts[0].replace("if", "").strip()
                    conclusion = parts[1].strip()
                    
                    if condition in facts and conclusion not in facts:
                        new_facts.append(conclusion)
                        new_facts.append(f"deduced_from:{rule}")
        
        return {
            "facts": new_facts,
            "dependencies": ["deductive_reasoning"],
            "effects": [f"derived:{f}" for f in new_facts]
        }
    
    def _constrain(self, state: CognitiveState, **kwargs) -> Dict[str, Any]:
        """Apply constraints to filter or validate state"""
        constraints = kwargs.get("new_constraints", []) + self.constraints
        facts = state.symbolic.facts.copy()
        
        violations = []
        for constraint in constraints:
            # Simple constraint checking
            if "must_have:" in constraint:
                required = constraint.replace("must_have:", "").strip()
                if required not in facts:
                    violations.append(f"missing:{required}")
            
            if "cannot_have:" in constraint:
                forbidden = constraint.replace("cannot_have:", "").strip()
                if forbidden in facts:
                    violations.append(f"violation:{forbidden}")
        
        result = {
            "dependencies": ["constraint_application"]
        }
        
        if violations:
            result["effects"] = ["constraint_violation"]
            result["facts"] = [f"violation:{v}" for v in violations]
        else:
            result["effects"] = ["constraints_satisfied"]
            result["facts"] = ["validation:passed"]
        
        return result
    
    def _validate(self, state: CognitiveState, **kwargs) -> Dict[str, Any]:
        """Validate current state against rules and constraints"""
        facts = state.symbolic.facts.copy()
        all_constraints = state.symbolic.constraints.copy() + self.constraints
        
        issues = []
        
        # Check for contradictions
        for i, fact1 in enumerate(facts):
            for fact2 in facts[i+1:]:
                if fact1.startswith("not_") and fact1[4:] == fact2:
                    issues.append(f"contradiction:{fact1} vs {fact2}")
                if fact2.startswith("not_") and fact2[4:] == fact1:
                    issues.append(f"contradiction:{fact1} vs {fact2}")
        
        return {
            "facts": issues if issues else ["validation:consistent"],
            "dependencies": ["validation"]
        }
    
    def _add_facts(self, state: CognitiveState, **kwargs) -> Dict[str, Any]:
        """Add new facts to state"""
        new_facts = kwargs.get("new_facts", [])
        return {
            "facts": new_facts,
            "dependencies": ["fact_addition"]
        }
    
    def _add_rules(self, state: CognitiveState, **kwargs) -> Dict[str, Any]:
        """Add new rules to state"""
        new_rules = kwargs.get("new_rules", [])
        return {
            "rules": new_rules,
            "dependencies": ["rule_addition"]
        }


class LogicOperator(SymbolicOperator):
    """
    Advanced symbolic operator for logical operations.
    """
    
    def _execute(self, state: CognitiveState, **kwargs) -> Dict[str, Any]:
        """
        Execute logical operations.
        
        Args:
            **kwargs:
                - logic_op: AND, OR, NOT, IMPLIES
                - operands: list of facts to operate on
        """
        logic_op = kwargs.get("logic_op", "AND")
        operands = kwargs.get("operands", [])
        facts = state.symbolic.facts.copy()
        
        if logic_op == "AND":
            all_present = all(op in facts for op in operands)
            result_fact = f"conjunction:{','.join(operands)}"
            return {
                "facts": [result_fact] if all_present else [],
                "dependencies": [f"logical_and:{','.join(operands)}"]
            }
        
        elif logic_op == "OR":
            any_present = any(op in facts for op in operands)
            result_fact = f"disjunction:{','.join(operands)}"
            return {
                "facts": [result_fact] if any_present else [],
                "dependencies": [f"logical_or:{','.join(operands)}"]
            }
        
        elif logic_op == "NOT":
            if operands:
                operand = operands[0]
                is_present = operand in facts
                result_fact = f"negation:{operand}"
                return {
                    "facts": [result_fact],
                    "dependencies": [f"logical_not:{operand}"],
                    "effects": [f"negated:{operand}" if is_present else f"confirmed_absence:{operand}"]
                }
        
        elif logic_op == "IMPLIES":
            if len(operands) >= 2:
                premise, conclusion = operands[0], operands[1]
                premise_present = premise in facts
                return {
                    "facts": [f"implication:{premise}->{conclusion}"] if premise_present else [],
                    "dependencies": [f"logical_implies:{premise}->{conclusion}"]
                }
        
        return {"facts": ["error:invalid_logic_operation"]}
