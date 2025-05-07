import csv
from multiprocessing import Pool
from itertools import product
import time
import gmpy2
import numpy as np
from scipy.optimize import curve_fit
from gmpy2 import mpz, mpfr, log, gcd, sqrt

def format_with(var, precision, symbol):
    """
    Format a variable with the specified precision and symbol.

    Parameters:
    - var: The variable to be formatted.
    - precision (int): The precision for formatting.
    - symbol (str): The format symbol ('e' or 'f').

    Returns:
    str: The formatted variable.
    """
    formatted = []

    if isinstance(var, list) or isinstance(var, np.ndarray):
        for value in var:
            if symbol == 'e':
                formatted.append("{:.{}e}".format(value, precision))
            elif symbol == 'f':
                formatted.append("{:.{}f}".format(value, precision))
            else:
                raise(f"\"format_with\" can't handle with symbol {symbol}!\n")
        return formatted
    else:
        if symbol == 'e':
            return "{:.{}e}".format(var, precision)
        elif symbol == 'f':
            return "{:.{}f}".format(var, precision)
        else:
            raise(f"\"format_with\" can't handle with symbol {symbol}!\n")

def fit_Normalized_Qn(qn, GCD, depth):
    """
    Fit the function of normalized qn.

    Parameters:
    - qn (list): Qn values of the calculated PCF.
    - GCD (list): GCD values of the calculated PCF.
    - depth (int): Depth of calculation.

    Returns:
    list: Coefficients and covariances of the fit.
    """
    #Generate the locations of the data points
    depths = [6, int(depth/8), int(depth/4), int(depth/2), int(depth)]
    #Get a list of normalized qn values
    normalized_qn = [log(abs(mpfr(qn[z]) / mpfr(GCD[z]))) for z in depths]

    #preform curve fitting
    params, covariance = curve_fit(normalized_qn_model_function, depths, normalized_qn, maxfev=10000, xtol=1e-5)

    c_opt, d_opt = params
    c_covariance = covariance[0][0]
    d_covariance = covariance[1][1]

    """
    If d is less than a small threshold, it means we have FR. 
    This means d should be zero, and if not it will cause calculation errors later.
    For that reason we preform another fit this time with c*x as the function, and manually setting d to 0.
    """
    if abs(d_opt) < 0.05:
        params, covarianceFR = curve_fit(normalized_qn_FR_model_function, depths, normalized_qn, maxfev=10000, xtol=1e-5)
        d_opt = 0
        d_covariance = 0
        c_opt = params[0]
        c_covariance = covarianceFR[0][0]

    return [c_opt, d_opt, c_covariance, d_covariance]

def fit_Convergence_Rate(pn, qn, depth, sample_depth):
    """
    Fit the convergence rate of the PCF.

    Parameters:
    - pn (list): Pn values of the calculated PCF.
    - qn (list): Qn values of the calculated PCF.
    - depth (int): Depth of the reference point- or the "limit".
    - sample_depth (int): The maximum depth to compare to the reference point.

    Returns:
    list: Parameters and covariances of the fit.
    """

    #Generate the locations of the data points
    depths = [6, int(sample_depth/8), int(sample_depth/4), int(sample_depth/2), int(sample_depth)]

    #Calculate the convergence at each data point location
    difference = [log(abs(mpfr(pn[depth])/mpfr(qn[depth]) - mpfr(pn[n])/mpfr(qn[n])))  for n in depths]

    #Preform the fit
    params, covariance = curve_fit(convergence_rate_model_function, depths, difference, maxfev=10000, xtol=1e-15)

    return [params, [covariance[0][0], covariance[1][1], covariance[2][2]]]

def blind_delta(L, p, q, gcd, rational_marker):
    """
    Calculate the unreduced and reduced (divided by the GCD) deltas.

    Args:
    - L (mpfr): The "Limit" of the PCF.
    - p (mpz): The numerator of the fraction evaluating the number.
    - q (mpz): The denominator of the fraction evaluating the number.

    Returns:
    - list: [unreduced delta, reduced delta].
    """
    if q + p == 0 or p == 0:
        return [rational_marker, rational_marker]

    q = abs(q)
    p = abs(p)
    L = abs(L)

    numerator = -(log(abs(L - mpfr(p) / mpfr(q))))

    unreduced = (numerator / log(q)) - 1
    reduced = (numerator / log(q/gcd)) - 1
    return [unreduced, reduced]

def delta3(eigenvalues_ratio, c, d, n):
    """
    Calculate the conjectured delta formula.

    Parameters:
    - c (float): the c parameter from the normalized qn curve fit.
    - d (float): the d parameter from the normalized qn curve fit.
    - n (int): the depth at which the delta is calculated.

    Returns:
    mpfr: The resulting delta.
    """
    return (n * mpfr(abs(log(abs(eigenvalues_ratio)))) / mpfr(normalized_qn_model_function(n, c, d)) - 1)

def getPCFMatrixEigenvaluesRatio(coefficients, coefficients_lengths, n):
    """
    Calculate the eigenvalues ratio of the PCF matrix.

    Parameters:
    - coefficients (list): Coefficients of the PCF's a_n and b_n.
    - coefficients_lengths (list): Lengths (or the degree+1) of a_n and b_n polynomials.
    - n (int): The depth at which the eigenvalues are calculated.

    Returns:
    tuple: Flag indicating complex eigenvalues and the eigenvalues ratio.
    """
    A = mpz(sum([mpz(coefficients[i]*pow(n, coefficients_lengths[0]-(i+1))) for i in range(coefficients_lengths[0])]))
    B = mpz(sum([mpz(coefficients[coefficients_lengths[0]+i]*pow(n, coefficients_lengths[1]-(i+1))) for i in range(coefficients_lengths[1])]))

    descriminant_in = mpz(mpz(pow(A, 2)) + 4 * B)

    complex_eigenvalueRatio_Flag = 1 if descriminant_in < 0 else 0

    eigenvalues_ratio = mpfr((A + sqrt(abs(descriminant_in)))) / mpfr(A - sqrt(abs(descriminant_in)))

    return (complex_eigenvalueRatio_Flag, eigenvalues_ratio)

def calc_rec(coefficients_lengths, coefficients, initial_pn, initial_qn, depth):
    """
    Calculate Pn, Qn, and GCD up to a specified depth.

    Parameters:
    - coefficients_lengths (list): Lengths (or the degree+1) of a_n and b_n polynomials.
    - coefficients (list): Coefficients of the PCF's a_n and b_n.
    - initial_pn (list): Initial Pn values.
    - initial_qn (list): Initial Qn values.
    - depth (int): Calculation depth.

    Returns:
    list: Resulting Pn, Qn, and GCD lists, and a flag indicating divergence.
    """
    pn = initial_pn
    qn = initial_qn
    GCD = [1, 1]

    qn_zeroes = []

    for n in range(1, depth):

        pn_coef_sum = 0
        qn_coef_sum = 0
        curr = 0

        for rc in range(len(coefficients_lengths)):
            coefficient_deg = coefficients_lengths[rc]
            Dn = 0
            for pc in range(coefficient_deg):
                Dn += mpz(coefficients[curr + pc]) * mpz(pow(n, coefficient_deg - pc - 1))
            if rc == 1 and Dn == 0:
                return [pn, qn, GCD, 1]
            curr += coefficient_deg
            pn_coef_sum += mpz(Dn) * mpz(pn[-(rc + 1)])
            qn_coef_sum += mpz(Dn) * mpz(qn[-(rc + 1)])

        if qn_coef_sum == 0:
            qn_zeroes.append(n+1)

        pn.append(mpz(pn_coef_sum))
        qn.append(mpz(qn_coef_sum))
        GCD.append(gcd(pn[-1], qn[-1]))

    #Though 0s in Qn are valid, they might cause calculation erros later, so they are removed.
    for z, i in zip(qn_zeroes, range(len(qn_zeroes))):
        pn.pop(z-i)
        qn.pop(z-i)
        GCD.pop(z-i)
    return [pn, qn, GCD, 0]

def normalized_qn_model_function(x, c, d):
    """
    Model function for curve fitting the normalized Qn.

    Parameters:
    - x (float): independent parameter.
    - c (float): Coefficient c.
    - d (float): Coefficient d.

    Returns:
    float: Result of the model function.
    """
    return c * x + d * x * np.log(x)

def normalized_qn_FR_model_function(x, c):
    """
    Model function for curve fitting the normalized Qn in the case of factorial reduction.

    Parameters:
    - x (float): independent parameter.
    - c (float): Coefficient c.

    Returns:
    float: Result of the model function.
    """
    return c * x

def convergence_rate_model_function(x, b, c, d):
    """
    Model function for curve fitting of convergence rate.

    Parameters:
    - x (float): independent parameter.
    - b (float): Coefficient b.
    - c (float): Coefficient c.
    - d (float): Coefficient d.

    Returns:
    float: Result of the model function.
    """
    return b * np.log(x) + c * x + d * x * np.log(x)

def calc_individual(coefficients, coefficients_lengths, depth, p, precision, not_calculated_marker, rational_marker, LIMIT_CONSTANT):
    """
    Calculate an individual PCF.

    Parameters:
    - coefficients (list): Coefficients of the PCF.
    - coefficients_lengths (list): Lengths (or the degree+1) of a_n and b_n polynomials.
    - depth (int): Calculation depth.
    - p (int): The relation between the calculation depth and the point where the blind delta is sampled.
    - precision (int): Precision for calculations.
    - not_calculated_marker: Marker for not calculated values.
    - rational_marker: Marker for rational values.
    - LIMIT_CONSTANT: A constant mimicing infinity.

    Returns:
    dict: Resulting PCF data.
    """

    PCFdata = {
        "Coefficients": coefficients,
        "Limit": not_calculated_marker,
        "Convergence_Cycle_Length": not_calculated_marker,
        "Infinite_CCL_Flag": not_calculated_marker,
        "Naive_Delta": not_calculated_marker,
        "FR_Delta": not_calculated_marker,
        "Predicted_Delta": not_calculated_marker,
        "c": not_calculated_marker,
        "d": not_calculated_marker,
        "c_SDS": not_calculated_marker,
        "d_SDS": not_calculated_marker,
        "Eigenvalues_ratio": not_calculated_marker,
        "complex_Eigenvalues": not_calculated_marker,
        "convergence_b": not_calculated_marker,
        "convergence_c": not_calculated_marker,
        "convergence_d": not_calculated_marker,
        "convergence_b_SDS": not_calculated_marker,
        "convergence_c_SDS": not_calculated_marker,
        "convergence_d_SDS": not_calculated_marker
    }

    #Set the precision of the calculations
    gmpy2.get_context().precision = precision

    #Get the basic data on the PCF- the pairs of rationals evaluating it at every step up to a given depth, and their GCD.
    recurrence_relations_data = calc_rec(coefficients_lengths, coefficients, [1, coefficients[coefficients_lengths[0] - 1]], [0, 1], depth)

    #Evaluate the PCF's limit
    limit_evaluation = mpfr(recurrence_relations_data[0][-1]) / mpfr(recurrence_relations_data[1][-1])

    #Check roughly if the PCF converges, if it does- format the limit and store in the data.
    PCFdata["Limit"] = format_with(limit_evaluation, 60, "f") if abs(limit_evaluation) < 1000 else rational_marker

    #If it diverges - terminate here since nothing of value can be extracted
    if PCFdata["Limit"] == rational_marker or recurrence_relations_data[3] == 1:
        return PCFdata

    #Calculate the depth that will be used in the curve fits
    depth = len(recurrence_relations_data[1])-1
    sample_depth = int(depth/p)

    #Fit the curve of the normalized qn. Format all resulting coefficients and store them in the data
    PCFdata["c"], PCFdata["d"], PCFdata["c_SDS"], PCFdata["d_SDS"] = format_with(fit_Normalized_Qn(recurrence_relations_data[1], recurrence_relations_data[2], sample_depth), 10, "f")

    #Check for complex eigenvalues and calculate the eigenvalues ratio.
    complex_eigenvalueRatio_Flag, eigenvalues_ratio = getPCFMatrixEigenvaluesRatio(coefficients, coefficients_lengths, LIMIT_CONSTANT)

    PCFdata["complex_Eigenvalues"] = complex_eigenvalueRatio_Flag

    #If we do have complex eigenvalue- terminate the proccess since nothing usefull can be calculated from this point
    if complex_eigenvalueRatio_Flag == 1:
        return PCFdata

    #If we do not have complex eigenvalues, save the eigenvalues ratio to the data
    PCFdata["Eigenvalues_ratio"] = format_with(log(abs(eigenvalues_ratio)), 15, "e")

    #Prepare and calculate the naive and normalized deltas using the blind delta formula.
    p = mpz(recurrence_relations_data[0][sample_depth])
    q = mpz(recurrence_relations_data[1][sample_depth])
    gcd = mpz(recurrence_relations_data[2][sample_depth])

    PCFdata["Naive_Delta"], PCFdata["FR_Delta"] = format_with(blind_delta(limit_evaluation, p, q, gcd, rational_marker), 10, "f")

    #Calculate the numerical delta using delta3
    PCFdata["Predicted_Delta"] = format_with(delta3(mpfr(eigenvalues_ratio), mpfr(PCFdata["c"]), mpfr(PCFdata["d"]), LIMIT_CONSTANT), 10, "f")

    #Fit the convergence rate of the PCF
    convergence_params, convergence_covariance = fit_Convergence_Rate(recurrence_relations_data[0], recurrence_relations_data[1], depth, sample_depth)

    #Format and save to the data the fit's coefficients and covariances
    PCFdata["convergence_b"], PCFdata["convergence_c"], PCFdata["convergence_d"] = format_with(convergence_params,10,"f")
    PCFdata["convergence_b_SDS"], PCFdata["convergence_c_SDS"], PCFdata["convergence_d_SDS"] = format_with(convergence_covariance,10,"f")

    return PCFdata


def search(depth, p,coefficients_lengths, co_min, co_max, precision, not_calculated_marker, rational_marker, LIMIT_CONSTANT, n_cores):

    """
    Explore all PCFs in a given search space.

    Args:
    - depth (int): Calculation depth.
    - p (int): The relation between the calculation depth and the point where the blind delta is sampled.
    - coefficients_lengths (list): Lengths (or the degree+1) of a_n and b_n polynomials.
    - co_min (int): Minimum value for the coefficients of a_n and b_n.
    - co_max (int): Maximum value for the coefficients of a_n and b_n.
    - n_cores (int): Number of CPU cores to use.
    """

    filename = f"BlindDelta{coefficients_lengths}_{co_min}_{co_max}.csv"

    combinations_creation_S = time.time()

    #Get all combinations of a pair of polynomials up to a given degree and given minimum and maximum coefficients
    combinations = product(range(co_min, co_max + 1), repeat=sum(coefficients_lengths))

    combinations = list(combinations)

    #Remove all combinations were one of the polynomials is strictly 0
    f = 0
    for i in range(len(combinations)):

        if([x for x in list(combinations[i-f])[:coefficients_lengths[0]] if x != 0] == [] or [z for z in list(combinations[i-f])[coefficients_lengths[0]:] if z != 0] == []):
            
            combinations.remove(combinations[i-f])
            f+=1

    #Assign each pair of polynomials - now a PCF, data relevant for the calculation
    all_combinations = [
        (list(combo), coefficients_lengths, int(depth), p, precision, not_calculated_marker, rational_marker, LIMIT_CONSTANT) for combo in combinations
    ]
    

    combinations_creation_time = time.time() - combinations_creation_S

    pcf_calculation_S = time.time()

    #Split to different cores and explore all given PCFs
    with Pool(n_cores) as mp_pool:
        result = mp_pool.starmap(calc_individual, all_combinations)

    pcf_calculation_time = time.time() - pcf_calculation_S

    file_writing_S = time.time()

    #Write the results into a file
    with open(filename, "w") as csvfile:
        csvwriter = csv.writer(csvfile)
        fields = result[0].keys()
        csvwriter.writerow(fields)

        for i in range(len(result)):
            csvwriter.writerow(result[i].values())

    file_writing_time = time.time() - file_writing_S

    #Print the time calculations took 
    print(combinations_creation_time, pcf_calculation_time, file_writing_time)
    #Print some the settings of the calculations
    print (
        f"==================================================\n"
        f"Depth: {depth}\n"
        f"P: {p}"
        f"Maximum degree of a_n: {coefficients_lengths[0]-1}\n"
        f"Maximum degree of b_n: {coefficients_lengths[1]-1}\n"
        f"Minimum coefficient value: {co_min}\n"
        f"Maximum coefficient value: {co_max}\n"
        f"Precision: {precision}\n"
        f"Not calculated marker: {not_calculated_marker}\n"
        f"Rational marker: {rational_marker}\n"
        f"Limit constant: {LIMIT_CONSTANT}\n"
        f"==================================================\n"
    )


def main():
    search(2000, 2,[3, 3], -1, 1, 100000, -1010, -2020, 1000000000,3)


if __name__ == "__main__":
    main()
