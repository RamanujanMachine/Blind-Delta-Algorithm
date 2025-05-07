from functools import reduce
from operator import mul, add
from LIReC.lib.pcf import PCF
from sympy import Symbol, Float, sympify
from DF_Manager import Mathematical_Constant
from LIReC.lib.pslq_utils import get_exponents

from LIReC.lib.pcf import PCF

from utils import pcf_to_key

def relation_to_expr(relation):
    """
    Converts a PolyPSLQRelation object into a symbolic expression.
    """
    exponents = get_exponents(relation.degree, relation.order, len(relation.constants))
    
    # Ensure each constant has a proper sympy Symbol
    for i, const in enumerate(relation.constants):
        if not getattr(const, "symbol", None):
            const.symbol = Symbol(f'c{i}')
        elif not isinstance(const.symbol, Symbol):
            const.symbol = Symbol(const.symbol)
    
    # Build the polynomial expression from the coefficients and exponents
    monoms = [
        reduce(mul, (const.symbol**exp[i] for i, const in enumerate(relation.constants)), relation.coeffs[j])
        for j, exp in enumerate(exponents)
    ]
    # Sum up all monomials to form the full expression
    return sympify(reduce(add, monoms, 0))

def get_calculation_depth(pcf, precision, fallback_depth, precision_buffer=1.3):
    """
    Returns the calculation depth required to achieve the given precision.
    """

    required_depth = None

    try:
        required_depth = pcf.predict_depth(precision)
    except Exception:
        pass

    if required_depth is None:
        return fallback_depth

    return int(precision_buffer * required_depth)


def verify_relation(relation, values):
    """
    Substitutes numerical values into the relation and evaluates it.
    'values' should be a list of high-precision numbers corresponding to each constant.
    """

    expr = relation_to_expr(relation)
    if any(val is None for val in values):
        return None, expr
    
    # Create a substitution dictionary mapping each symbol to its evaluated value
    substitutions = {const.symbol: Float(str(val))
                 for const, val in zip(relation.constants, values)}
    
    # Substitute and evaluate the expression numerically
    result = expr.subs(substitutions).evalf()
    return result, expr

def evaluate_expression(expr,precision,max_depth, precision_buffer=1.3):
    if isinstance(expr,PCF):
        try:
            pcf, symbol = expr, str(pcf_to_key(expr))
            eval_depth = min(precision_buffer*get_calculation_depth(pcf, precision, max_depth),max_depth)
            pcf.eval(depth=eval_depth)
            value = pcf.value
            precision = pcf.predict_precision(eval_depth)
        except Exception:
            return None
    elif isinstance(expr,Mathematical_Constant):
        value, symbol, precision = expr.value, expr.name, expr.precision
    else:
        print(f"Could not identify the expression type: {expr}, {type(expr)}")
        return None
    
    return [value, symbol, precision]