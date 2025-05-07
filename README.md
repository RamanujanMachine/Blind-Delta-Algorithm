
# README

This repository contains code for the collection and analysis of data on Polynomial Continued Fractions (PCFs), with the aim of generating new conjectures for formulas involving mathematical constants.

## Links

Arxiv Paper [https://arxiv.org/pdf/2412.16818](url)

NeurIPS Poster and 5-minute video: [https://neurips.cc/virtual/2024/poster/95491](url)

Group Publication Page: [https://www.ramanujanmachine.com/publications/](url)

## Running the data collection algorithm using the `search` Function

The `search` function is designed for exploring a range of Polynomial Continued Fractions (PCFs) by enumerating all possible polynomial coefficient combinations within a defined search space. For each combination, the function estimates a variety of parameters—such as the convergence rate and the irrationality measure—and writes the results to a CSV file.

### Function Signature

```python
search(
    depth, 
    p, 
    coefficients_lengths, 
    co_min, 
    co_max, 
    precision, 
    not_calculated_marker, 
    rational_marker, 
    LIMIT_CONSTANT, 
    n_cores
)
```

### Parameters

- **depth (int)**  
  Maximum depth of calculation for each PCF. This determines how many terms of the polynomial continued fraction are computed.

- **p (int)**  
  Specifies the fraction of `depth` at which sampling is performed. For instance, if `depth = 2000` and `p = 2`, data sampling occurs at `depth / p = 1000`.

- **coefficients_lengths (list of int)**  
  A two-element list indicating the degrees (plus 1) of the polynomials generating $a_n$ and $b_n$. For example, `[3, 2]` means $a_n$ can be up to degree 2, and $b_n$ up to degree 1.

- **co_min (int), co_max (int)**  
  The inclusive range of integer coefficients for the polynomials. For example, if `co_min = -2` and `co_max = 2`, the coefficients will be sampled from the set $\{-2, -1, 0, 1, 2\}$.

- **precision (int)**  
  The bit precision used by `gmpy2` for arithmetic operations. A higher precision may be necessary for numerically sensitive calculations.

- **not_calculated_marker (any)**  
  A sentinel value (e.g., `"N/A"` or `None`) indicating that a particular result was not computed.

- **rational_marker (any)**  
  A sentinel value (e.g., `"RATIONAL"`) signifying that the PCF was deemed rational, diverged, or could not be further analyzed.

- **LIMIT_CONSTANT (int)**  
  A large integer used as a practical stand-in for infinity in certain eigenvalue-based calculations.

- **n_cores (int)**  
  The number of CPU cores utilized by the `multiprocessing.Pool` for parallel processing.

### Overview of the Process

1. **Generate Polynomial Combinations**  
   The function uses `itertools.product` to create every possible set of polynomial coefficients in the specified range (`co_min` to `co_max`).  
   - It excludes any combination where one of the polynomials would be entirely zero (all coefficients set to zero).

2. **Parallel Computation**  
   Each combination of coefficients is passed to the `calc_individual` helper function, which:
   - Recursively computes partial sums ($p_n$, $q_n$) up to the specified `depth`.
   - Checks for divergence or rational values.
   - Calculates a variety of measures (e.g., the irrationality measure, convergence rates, eigenvalue ratios).

3. **CSV Output**  
   The aggregated results are written to a CSV file, named according to a pattern such as:
   ```
   BlindDelta{coefficients_lengths}_{co_min}_{co_max}.csv
   ```
   Each row corresponds to a PCF, and is of the form:
   
   ```Coefficients``` - The "key" of the PCF.
   
   ```Limit``` - The approximated limit of the PCF.
   
   ```Convergence_Cycle_Length``` - At this moment "NotCalculatedMarker".
   
   ```Infinite_CCL_Flag``` - At this moment "NotCalculatedMarker".
   
   ```Naive_Delta``` - The irrationality measure* which **was not** normalized by the gcd of p_n and q_n.
   
   ```FR_Delta``` - The irrationality measure which which **was** normalized by the gcd of p_n and q_n.
   
   ```Predicted_Delta``` - See our paper [paper](https://arxiv.org/abs/2412.16818) section 3.2.
   
   ```c```,```d```, - the growth rate parameters of $\tilde{q_n}$: $\gamma'$, $\eta'$.
   
   ```c_SDS```,```d_SDS```,
   
   ```Eigenvalues_ratio``` - The approximated limit of the ratio of the eigenvalues of the matrix representing a PCF.
   
   ```complex_Eigenvalues``` - A flag enabling a quick debug and filtration of PCF which are estimated not to converge. 
   
   ```convergence_b```,```convergence_c```,```convergence_d``` - The dynamics of the convergence rate of the PCF: $\beta$, $\gamma$, $\eta$.
   
   ```convergence_b_SDS```,```convergence_c_SDS```,```convergence_d_SDS```

   *For a more detailed explenation about the irrationality measure, section 3.1 in our [paper](https://arxiv.org/abs/2412.16818).
   
5. **Performance Metrics**  
   The function reports timing information for:
   - Generating the combinations,
   - Performing the calculations,
   - Writing the CSV file.

### Example Usage

```python
if __name__ == "__main__":
    # Define search parameters
    depth = 2000
    p = 2
    coefficients_lengths = [3, 3]   # E.g., polynomials up to degree 2 for a_n and b_n
    co_min, co_max = -5, 5         # Coefficients range from -5 to 5
    precision = 100000                # Bits of precision for gmpy2
    not_calculated_marker = "N/A"
    rational_marker = "RATIONAL"
    LIMIT_CONSTANT = 10**6         # Used as a stand-in for infinity
    n_cores = 64                    # Number of CPU cores to use

    # Invoke the search
    search(
        depth,
        p,
        coefficients_lengths,
        co_min,
        co_max,
        precision,
        not_calculated_marker,
        rational_marker,
        LIMIT_CONSTANT,
        n_cores
    )
```

### Interpreting the Output

- **CSV File**: A CSV file such as `BlindDelta[3,3]_-5_5.csv` is generated. Each row in the file corresponds to a PCF.
- **Columns**:  
  - **`Limit`**: Approximate limit of the PCF if it converges (or a sentinel if it diverges).  
  - **`Naive_Delta`, `FR_Delta`, `Predicted_Delta`**: Different .  
  - **`Eigenvalues_ratio`**: A ratio derived from the eigenvalues of a relevant matrix, indicative of convergence properties.  
  - **`complex_Eigenvalues`**: A flag indicating whether the eigenvalues are complex, which can affect the validity of further computations.  
  - **Additional fields** may include convergence coefficients (`b, c, d`) and their variances, as well as other diagnostic information.

Any columns marked with the `not_calculated_marker` or `rational_marker` indicate that the function either could not compute a given quantity or deemed the PCF to be unsuitable for further analysis (e.g., due to divergence).

## Overview of Integral Functions
1. **Polynomial Continued Fractions and the** ```calc_rec``` **function**

    A PCF at depth $n$ is defined as:
    <p align="center">$$\huge a_0 + \cfrac{b_1}{a_1 + \cfrac{b_2}{\ddots + \cfrac{b_n}{a_n}}} = \frac{p_n}{q_n}$$</p>
    
    where $a_n=a(n)$ and $b_n=b(n)$ are evaluations of polynomials with integer  coefficients. 
    The PCF value is the limit $$L=\lim_{n\to\infty}{\frac{p_n}{q_n}}$$ (when it exists). The converging sequence of rational numbers $\frac{p_n}{q_n}$ provides an approximation of $L$, which is known as a Diophantine approximation. 

   Given $d_a$, $d_b$, $[A_0,A_1,...,A_{d_a}]$, $[B_0,B_1,...,B_{d_b}]$

    we define

   <p align="center">$$\large a_n \;=\; \sum_{k=0}^{d_a} A_{d_a-k}\,n^{\,d_a - k}\quad\text{and}\quad b_n \;=\; \sum_{k=0}^{d_b} B_{d_b-k}\,n^{\,d_b - k}$$</p>
   
   and the recurrence relations will look like:

   <p align="center">$$p_{n} \;=\; a_n\,p_{n-1} \;+\; b_n\,p_{n-2}\text{, }q_{n} \;=\; a_n\,q_{n-1} \;+\; b_n\,q_{n-2}$$</p>

   where

   <p align="center">$$p_{-1} = 1\text{, }p_0 = a_0\text{, }q_{-1} = 0\text{, }q_0 = 1$$</p>

   The function ```calc_rec``` is tasked with calculating $p_n$, $q_n$ and $gcd_n = \gcd(p_n,q_n)$ for each integer n, up to a given depth.


    #### Function Signature
    
    ```python
    calc_rec(
        coefficients_lengths,
        coefficients,
        initial_pn,
        initial_qn,
        depth
    )    
    ```
    
    #### Parameters
    
    - **coefficients_lengths (list of int)**  
      A k-element list specifying how many coefficients belong to each polynomial. In our case k=2 for $a_n$ and $b_n$. For example, `[3, 2]` indicates:
      - The first `3` coefficients in `coefficients` define $a_n$.
      - The next `2` coefficients define $b_n$.
    
    - **coefficients (list of int)**  
      The actual integer coefficients for the polynomials. Must match the sum of all elements in `coefficients_lengths`.  
      For instance, if `coefficients_lengths = [3, 2]`, you might have a total of 5 coefficients like `[1, 0, 1, -1, 2]`.
    
    - **initial_pn (list of int)**  
      P initial values for the reccurence relation $p_n$. In our case, `initial_pn = [1, a_0]`.
    
    - **initial_qn (list of int)**  
      Q initial values for the reccurence relation $q_n$. In our case, `initial_qn = [0, 1]`.
    
    - **depth (int)**
      The maximum depth to compute $p_n$, $q_n$. The function loops from `n = 1` through `n = depth - 1`, updating sequences.
    
    #### Process Overview
    
    1. **Initialize Sequences**  
       - `pn` and `qn` start as the lists `initial_pn` and `initial_qn`.  
       - A list `GCD` begins with `[1, 1]`.
    
    2. **Compute Recurrence Terms**  
       For each `n` from `1` up to (but not including) `depth`:
       - Evaluate the polynomial coefficients of $a_n$ or $b_n$ at $n$.  
       - Use $a_n$, $b_n$ to compute $p_n$ and $q_n$.
       - Compute the gcd of the new $pn$ and $qn$ elements and append to `GCD`.
    
    3. **Check for Divergence**  
       - If $b_n$ evaluates to `0` for some `n`, the function returns immediately with a divergence flag `1`.  
       - If `qn_coef_sum` is `0`, its index is recorded in `qn_zeroes`. After the loop, any entries where `Q_n = 0` are removed from `pn`, `qn`, and `GCD` so as not to break subsequent calculations.
    
    4. **Return Values**  
       - The final lists `pn`, `qn`, and `GCD`, along with a **divergence flag** which is `1` if the code ended early due to a zero denominator polynomial, and `0` otherwise.

    #### Example Usage
    
    ```python
    import gmpy2
    from gmpy2 import mpz
    from main import calc_rec  # or from your_module import calc_rec
    
    # 1. Define the polynomials' degrees and coefficients
    coefficients_lengths = [3, 3]    # e.g., a_n and b_n each have 3 coefficients
    coefficients = [1, 0, 1, 2, -1, 1]  #   a_n = 1*n^2 + 0*n + 1, b_n = 2*n^2 - 1*n + 1

    # 2. Provide initial Pn and Qn
    initial_pn = [mpz(1), mpz(coefficients[coefficients_lengths[0]-1)]  # e.g., [1, 1]
    initial_qn = [mpz(0), mpz(1)]
    
    # 3. Specify the depth
    depth = 1000
    
    # 4. Call the function
    pn, qn, gcd_list, divergence_flag = calc_rec(
        coefficients_lengths,
        coefficients,
        initial_pn,
        initial_qn,
        depth
    )
    
    # 5. Examine the results
    print("Partial numerators (Pn):", pn)
    print("Partial denominators (Qn):", qn)
    print("GCD list:", gcd_list)
    print("Divergence flag:", divergence_flag)
    ```
    
    **Interpretation**:
    
    - **`pn`**: Contains the sequence of numerators $p_0, p_1, \ldots$.  
    - **`qn`**: Contains the sequence of denominators $q_0, q_1, \ldots$.  
    - **`gcd_list`**: For each step, `gcd_list[i] = gcd(pn[i], qn[i])`.  
    - **`divergence_flag`**:  
      - `0` means the function finished the loop normally.  
      - `1` indicates that $b_n = 0$ for some $n$.
    
    #### Practical Notes
    
    - **Zero-Denominator Removal**:  
      Any steps that produce `Q_n = 0` are removed from the final lists (plural) to prevent further calculations from failing.
    
    - **Performance**:  
      For large `depth` or large-degree polynomials, these lists can grow very quickly. Ensure you have sufficient memory and that your `gmpy2` precision settings are appropriate.

2. **The ```calc_individual``` function**
   
Given $a_n$ and $b_n$ in the form of coefficients (list) and coefficients_lengths (list) in addition of other parameters as described [above](#parameters), the function ```calc_individual``` is tasked with claculating the dynamical metrics (see our [paper](https://arxiv.org/abs/2412.16818) section 3.3)of the resulting PCF.

#### Function Signature

```python
def calc_individual(
    coefficients,
    coefficients_lengths,
    depth,
    p,
    precision,
    not_calculated_marker,
    rational_marker,
    LIMIT_CONSTANT
):
    ...
```

#### Process Overview

1. **Initialize Precision**  
   The gmpy2 context precision is set to the specified precision to ensure that all subsequent mpfr operations adhere to the desired level of numerical accuracy. This precision setting is applied at this stage since the function is distributed across multiple cores via a multiprocessing pool, making it necessary to establish a consistent computational environment before execution.

3. **Compute Partial Numerators and Denominators**  
   Calls the [`calc_rec` function](#polynomial-continued-fractions-and-the-calc_rec-function) 

4. **Evaluate the PCF Limit**  
   The function takes the last partial numerator and denominator and attempts a floating-point division to estimate the limit of the PCF.

5. **Check for Divergence**  
   If the PCF is deemed divergent (or if the limit is excessively large), the function returns the data immidiately.  

6. **Curve Fitting of Normalized \(q_n\)**  
   If the PCF converges, a subset of the \(q_n\) values is normalized and fitted to a curve to extract parameters \(\{c, d\}\). These are stored, along with their standard deviations (`c_SDS`, `d_SDS`).

7. **Eigenvalue Analysis**  
   The function checks if the underlying matrix of the PCF has complex eigenvalues. If so, it flags this (`complex_Eigenvalues=1`) and returns early, since most PCFs of that kind diverge.

8. **Delta Computations**  
   - **Naive_Delta** and **FR_Delta** are computed using a “blind delta” formula based on the partial fraction limit, a specific partial numerator `p`, denominator `q`, and their gcd.  
   - **Predicted_Delta** is calculated via a custom function (`delta3`) that uses the eigenvalue ratio and fitted parameters \(\{c, d\}\).

9. **Convergence Rate Fitting**  
   A final fit is done to estimate how quickly the partial fractions converge to the limit. Parameters \(\{b, c, d\}\) are retrieved, along with their covariance estimates (`b_SDS, c_SDS, d_SDS`).

10. **Result Assembly**  
   All of the above computations are gathered in a dictionary (`PCFdata`) with keys like `"Limit"`, `"Naive_Delta"`, `"Eigenvalues_ratio"`, etc. This dictionary is returned to the caller.

---

#### Return Value

See [here](#csv_output)

#### Example Usage

```python
import gmpy2
from gmpy2 import mpz, mpfr
# from your_module import calc_individual

# Example coefficients for polynomials a_n, b_n
coefficients_lengths = [3, 2]    # Suppose a_n has 3 coefficients, b_n has 2
coefficients = [1, 0, 1,  2, -1] # e.g., a_n = n^2 + 1, b_n = 2*n - 1

# Calculation parameters
depth = 500
p = 10
precision = 128
not_calculated_marker = None
rational_marker = "DivergentOrRational"
LIMIT_CONSTANT = mpfr("1e20")

# Call the function
result_data = calc_individual(
    coefficients,
    coefficients_lengths,
    depth,
    p,
    precision,
    not_calculated_marker,
    rational_marker,
    LIMIT_CONSTANT
)

# Inspect results
print("======= PCF Data =======")
for key, val in result_data.items():
    print(f"{key}: {val}")
```

**Interpretation**:

- If `"Limit"` is a numeric string (e.g., `'1.4142135623'`), the PCF likely converged to that value.  
- If `"Limit" == "DivergentOrRational"`, the PCF either diverged (e.g., denominator polynomials going to zero) or produced a value out of the acceptable range.  
- If `"complex_Eigenvalues" == 1`, the function won’t calculate further data reliant on real-eigenvalue approximations.  

Use the fields `"Naive_Delta"`, `"FR_Delta"`, and `"Predicted_Delta"` to inspect how various error measures behave. The convergence parameters `"convergence_b"`, `"convergence_c"`, `"convergence_d"` and their standard deviations can guide how quickly the continued fraction converges to `"Limit"`.
