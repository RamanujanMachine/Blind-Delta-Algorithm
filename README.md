Blind Delta Algorithm
======================
The Blind Delta Algorithm is a Python-based computational tool designed to explore and analyze Polynomial Continued Fractions (PCFs). PCFs are mathematical constructs related to continued fractions and have applications in number theory and mathematical research.

## Overview
The algorithm employs numerical and optimization libraries, including NumPy, SciPy, and GMPY2, to perform an exhaustive search over a specified search space of PCFs. The code calculates and analyzes various characteristics of PCFs, such as limits, convergence rates, and deltas. This README provides an overview of the key functions within the code.

## Functions
1. **format_with(var, precision, symbol)**
   - Format a variable with a specified precision and symbol ('e' or 'f').
   - Parameters:
      - var: The variable to be formatted.
      - precision (int): The precision for formatting.
      - symbol (str): The format symbol ('e' or 'f').
   - Returns:
      - str or list: The formatted variable.

2. **fit_Normalized_Qn(qn, GCD, depth)**
   - Fit the function of normalized qn.
   - Parameters:
      - qn (list): Qn values of the calculated PCF.
      - GCD (list): GCD values of the calculated PCF.
      - depth (int): Depth of calculation.
   - Returns:
      - list: Coefficients and covariances of the fit.

3. **fit_Convergence_Rate(pn, qn, depth, sample_depth)**
   - Fit the convergence rate of the PCF.
   - Parameters:
      - pn (list): Pn values of the calculated PCF.
      - qn (list): Qn values of the calculated PCF.
      - depth (int): Depth of the reference point- or the "limit".
      - sample_depth (int): The maximum depth to compare to the reference point.
   - Returns:
      - list: Parameters and covariances of the fit.

4. **delta2(L, p, q, gcd, rational_marker)**
   - Calculate unreduced and reduced (normalized) deltas.
   - Parameters:
      - L (mpfr): The "Limit" of the PCF.
      - p (mpz): The numerator of the fraction evaluating the number.
      - q (mpz): The denominator of the fraction evaluating the number.
      - gcd (mpz): The greatest common divisor.
      - rational_marker: Marker for rational values.
   - Returns:
      - list: [unreduced delta, reduced delta].

5. **delta3(eigenvalues_ratio, c, d, n)**
   - Calculate the conjectured delta formula.
   - Parameters:
      - eigenvalues_ratio (float): The eigenvalues ratio of the PCF matrix.
      - c (float): The c parameter from the normalized qn curve fit.
      - d (float): The d parameter from the normalized qn curve fit.
      - n (int): The depth at which the delta is calculated.
   - Returns:
      - mpfr: The resulting delta.

6. **getPCFMatrixEigenvaluesRatio(coefficients, coefficients_lengths, n)**
   - Calculate the eigenvalues ratio of the PCF matrix at a given depth.
   - Parameters:
      - coefficients (list): Coefficients of the PCF's polynomials a_n and b_n.
      - coefficients_lengths (list): Lengths (or the degree+1) of the polynomials a_n and b_n.
      - n (int): The depth at which the eigenvalues are calculated.
   - Returns:
      - tuple: Flag indicating complex eigenvalues and the eigenvalues ratio.

7. **calc_rec(coefficients_lengths, coefficients, initial_pn, initial_qn, depth)**
   - Calculate Pn, Qn, and GCD up to a specified depth.
   - Parameters:
      - coefficients_lengths (list): Lengths (or the degree+1) of the polynomials a_n and b_n.
      - coefficients (list): Coefficients of the PCF's polynomials a_n and b_n.
      - initial_pn (list): Initial Pn values.
      - initial_qn (list): Initial Qn values.
      - depth (int): Calculation depth.
   - Returns:
      - list: Resulting Pn, Qn, GCD lists, and a flag indicating divergence.

8. **normalized_qn_model_function(x, c, d)**
   - Model function for curve fitting the normalized Qn. This function defines the model function used in the curve fitting process.

9. **normalized_qn_FR_model_function(x, c)**
   - Model function for curve fitting the normalized Qn in the case of factorial reduction.

10. **convergence_rate_model_function(x, b, c, d)**
    - Model function for curve fitting of convergence rate. This function defines the model function used in the convergence rate curve fitting.

11. **calc_individual(coefficients, coefficients_lengths, depth, p, precision, not_calculated_marker, rational_marker, LIMIT_CONSTANT)**
    - Calculate an individual PCF. This function brings together various calculations and formats the results for a single PCF, including limits, deltas, and convergence rates.
    - Parameters:
       - coefficients (list): Coefficients of the PCF's polynomials a_n and b_n.
       - coefficients_lengths (list): Lengths (or the degree+1) of the polynomials a_n and b_n.
       - depth (int): Calculation depth.
       - p (int): The relation between the calculation depth and the point where the blind delta is sampled.
       - precision (int): The required precision for all calculations.
       - not_calculated_marker (int): A flag to mark data that was not calculated.
       - rational_marker (int): A flag to mark data as rational.
       - LIMIT_CONSTANT (int): A variable used as a numerical replacement for infinity.
    - Returns:
       - dict: Resulting PCF data.

12. **search(depth, p, coefficients_lengths, co_min, co_max, precision, not_calculated_marker, rational_marker, LIMIT_CONSTANT, n_cores)**
    - Explore all PCFs in a given search space. This function orchestrates the search process, distributing calculations across multiple cores for efficiency.
    - Parameters:
       - depth (int): Calculation depth.
       - p (int): The relation between the calculation depth and the point where the blind delta is sampled.
       - coefficients_lengths (list): Lengths (or the degree+1) of the polynomials a_n and b_n.
       - co_min (int): Minimum value for the coefficients of a_n and b_n.
       - co_max (int): Maximum value for the coefficients of a_n and b_n.
       - precision (int): The required precision for all calculations.
       - not_calculated_marker (int): A flag to mark data that was not calculated.
       - rational_marker (int): A flag to mark data as rational.
       - LIMIT_CONSTANT (int): A variable used as a numerical replacement for infinity.
       - n_cores (int): Number of CPU cores to use.
    
13. **main()**
    - The main function initializes the search with specific parameters. Users can customize these parameters based on their exploration needs.

## Usage
1. Set up Python 3.x and install required dependencies using pip install numpy scipy gmpy2.
2. Open blind_delta.py and adjust parameters in the main function.
3. Run the script with python blind_delta.py.
4. View the results in the generated CSV file that will have the name BlindDelta<coefficients_lengths>_<co_min>_<co_max>.csv
   where coefficients_lengths, co_min, and co_max are the parameters supplied to the search function to define the search space.
