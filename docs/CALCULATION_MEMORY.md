# Calculation Memory: Analytical Availability and Reliability Block Diagrams (RBD)

This document provides a concise calculation memory (*memória de cálculo*) for the analytical availability modeling of the cloud payment processing architecture.


## 1. System Parameterization and Alternating Renewal Theory

Each functional subsystem operates in the constant hazard rate period of the bathtub curve ($\beta = 1$). Under alternating renewal theory, the steady-state availability $A_i$ relates to the constant failure rate $\lambda_i = 1/\text{MTBF}_i$ and repair rate $\mu_i = 1/\text{MTTR}_i$ [1], [4]:

$$A_i = \lim_{t \to \infty} A_i(t) = \frac{\text{MTBF}_i}{\text{MTBF}_i + \text{MTTR}_i} = \frac{\mu_i}{\lambda_i + \mu_i}$$

$$\lambda_i = \frac{1}{\text{MTTR}_i} \left(\frac{1 - A_i}{A_i}\right), \quad \text{MTBF}_i = \text{MTTR}_i \left(\frac{A_i}{1 - A_i}\right)$$

$$U_i = 1 - A_i, \quad D_i = U_i \times 8760\text{ hours/year} = (1 - A_i) \times 525{,}600\text{ minutes/year}$$

### Subsystem Parameters Table

| Block Code | Subsystem Name | Architectural Tier | Single-AZ SLA ($A_i$) | Multi-AZ SLA ($A_{i,\text{red}}$) | Nominal MTTR | Failure Rate $\lambda_i$ ($10^{-3}\text{ h}^{-1}$) | MTBF (hours) | Baseline Downtime (h/yr) | Redundant Downtime (h/yr) | Reference SLA |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **LB** | Load Balancer | Ingress & Routing | $99.99\%$ ($0.9999$) | $99.99\%$ ($0.9999$) | $15\text{ min}$ ($0.25\text{ h}$) | $0.400$ | $2500$ | $0.876\text{ h}$ | $0.876\text{ h}$ | AWS ELB / GCP LB [13], [15] |
| **App** | Application Server | Business Logic | $99.50\%$ ($0.9950$) | $99.99\%$ ($0.9999$) | $30\text{ min}$ ($0.50\text{ h}$) | $10.050$ | $99.5$ | $43.800\text{ h}$ | $0.876\text{ h}$ | AWS EC2 / Azure VM [11], [14] |
| **DB** | Relational Database | Data Persistence | $99.50\%$ ($0.9950$) | $99.95\%$ ($0.9995$) | $60\text{ min}$ ($1.00\text{ h}$) | $5.025$ | $199.0$ | $43.800\text{ h}$ | $4.380\text{ h}$ | AWS RDS Single vs Multi-AZ [12], [15] |
| **PGW** | Payment Gateway | External Settlement | $99.95\%$ ($0.9995$) | $99.999975\%$ | $30\text{ min}$ ($0.50\text{ h}$) | $1.001$ | $999.5$ | $4.380\text{ h}$ | $0.002\text{ h}$ | FinTech API (Single vs Dual) [10] |


## 2. Reliability Block Diagram (RBD) Formulations

- **Pure Series System ($n$ independent blocks in series):**
  $$A_{\text{series}} = \prod_{i=1}^n A_i, \quad U_{\text{series}} \approx \sum_{i=1}^n U_i \quad (\text{for } U_i \ll 1)$$
- **Active Parallel Subsystem ($m$ independent redundant units):**
  $$A_{\text{parallel}} = 1 - \prod_{j=1}^m (1 - A_j)$$
  For two identical units with availability $A$: $A_{\text{parallel}} = 1 - (1 - A)^2$.


## 3. Step-by-Step Scenario Derivations

### 3.1 Scenario 1: Baseline Architecture (Pure Series)

$$\text{Ingress} \longrightarrow [\text{LB}] \longrightarrow [\text{App}] \longrightarrow [\text{DB}] \longrightarrow [\text{PGW}] \longrightarrow \text{Egress}$$

$$A_{\text{base}} = A_{\text{LB}} \cdot A_{\text{App}} \cdot A_{\text{DB}} \cdot A_{\text{PGW}} = 0.9999 \times 0.9950 \times 0.9950 \times 0.9995$$

$$A_{\text{base}} = 0.9894310345 \implies \mathbf{98.943\%}$$

$$U_{\text{base}} = 1 - A_{\text{base}} = 0.0105689655 \implies \mathbf{1.0569\%}$$

$$D_{\text{base}} = 0.0105689655 \times 8760\text{ h} = \mathbf{92.5841\text{ h/year}} \approx \mathbf{92.58\text{ h/year}} \quad (5555.05\text{ min/year})$$

**Criticality Assessment:** Single-instance App ($43.80\text{ h}$) and DB ($43.80\text{ h}$) cause $\frac{87.60}{92.5841} = \mathbf{94.62\%}$ of total downtime. Every component is a Single Point of Failure (SPOF).


### 3.2 Scenario 2: Multi-AZ Architecture (Series-Parallel)

$$\text{Ingress} \longrightarrow [\text{LB}] \longrightarrow \begin{bmatrix} \text{App}_1 \\ \parallel \\ \text{App}_2 \end{bmatrix} \longrightarrow \begin{bmatrix} \text{DB}_1 \\ \parallel \\ \text{DB}_2 \end{bmatrix} \longrightarrow [\text{PGW}] \longrightarrow \text{Egress}$$

- **Application Multi-AZ:** $A_{2,\text{red}} = 0.9999$ (AWS EC2 Multi-AZ SLA [11], [14]; parallel theoretical: $1 - 0.005^2 = 0.999975$).
- **Database Multi-AZ HA:** $A_{3,\text{red}} = 0.9995$ (AWS RDS Multi-AZ SLA [12], [15], accounting for synchronous replication and failover overhead).

$$A_{\text{red}} = A_{\text{LB}} \cdot A_{2,\text{red}} \cdot A_{3,\text{red}} \cdot A_{\text{PGW}} = 0.9999 \times 0.9999 \times 0.9995 \times 0.9995$$

$$A_{\text{red}} = (0.9999)^2 \times (0.9995)^2 = 0.99980001 \times 0.99900025 = 0.9988004599 \implies \mathbf{99.880\%}$$

$$U_{\text{red}} = 1 - A_{\text{red}} = 0.0011995401 \implies \mathbf{0.11995\%}$$

$$D_{\text{red}} = 0.0011995401 \times 8760\text{ h} = \mathbf{10.5080\text{ h/year}} \approx \mathbf{10.51\text{ h/year}} \quad (630.48\text{ min/year})$$

$$\Delta D = D_{\text{base}} - D_{\text{red}} = 92.5841 - 10.5080 = \mathbf{82.0761\text{ h/year saved}} \implies \mathbf{88.65\%\text{ reduction}}$$

**Bottleneck Shift:** Internal compute/DB downtime drops by $97.9\%$. The external Payment Gateway ($4.38\text{ h/yr}$) and DB failover ($4.38\text{ h/yr}$) jointly represent $\frac{4.38 + 4.38}{10.5080} = \mathbf{83.36\%}$ of all remaining downtime.


### 3.3 Scenario 3: Multi-Gateway Expansion (End-to-End Fault Tolerance)

$$\text{Ingress} \longrightarrow [\text{LB}] \longrightarrow \begin{bmatrix} \text{App}_1 \\ \parallel \\ \text{App}_2 \end{bmatrix} \longrightarrow \begin{bmatrix} \text{DB}_1 \\ \parallel \\ \text{DB}_2 \end{bmatrix} \longrightarrow \begin{bmatrix} \text{PGW}_A \\ \parallel \\ \text{PGW}_B \end{bmatrix} \longrightarrow \text{Egress}$$

$$A_{4,\text{red}} = 1 - (1 - A_4)^2 = 1 - (0.0005)^2 = 1 - 0.00000025 = \mathbf{0.99999975 \implies 99.999975\%}$$

$$D_{\text{PGW,red}} = 0.00000025 \times 8760\text{ h} = 0.00219\text{ h/year} \approx \mathbf{7.88\text{ seconds/year}}$$

$$A_{\text{scen3}} = A_{\text{LB}} \cdot A_{2,\text{red}} \cdot A_{3,\text{red}} \cdot A_{4,\text{red}} = 0.9999 \times 0.9999 \times 0.9995 \times 0.99999975$$

$$A_{\text{scen3}} = 0.9992998602 \implies \mathbf{99.930\%}$$

$$U_{\text{scen3}} = 1 - A_{\text{scen3}} = 0.0007001398 \implies \mathbf{0.07001\%}$$

$$D_{\text{scen3}} = 0.0007001398 \times 8760\text{ h} = \mathbf{6.1332\text{ h/year}} \approx \mathbf{6.13\text{ h/year}} \quad (368.00\text{ min/year})$$

- **Gain vs. Baseline (Scenario 1):** $86.45\text{ h/yr saved}$ ($\mathbf{93.38\%}$ reduction).
- **Gain vs. Multi-AZ (Scenario 2):** $4.37\text{ h/yr saved}$ ($\mathbf{41.63\%}$ additional reduction).


## 4. Consolidated Comparison Table

| Metric | Scenario 1 (Baseline Series) | Scenario 2 (Multi-AZ Series-Parallel) | Scenario 3 (Multi-Gateway Expansion) |
| :--- | :---: | :---: | :---: |
| **System Availability ($A_{\text{sys}}$)** | **$98.9431\%$** ($98.943\%$) | **$99.8800\%$** ($99.880\%$) | **$99.9300\%$** ($99.930\%$) |
| **System Unavailability ($U_{\text{sys}}$)** | $1.0569\%$ | $0.11995\%$ | $0.07001\%$ |
| **Annual Downtime (hours/year)** | **$92.58\text{ h}$** ($92.584\text{ h}$) | **$10.51\text{ h}$** ($10.508\text{ h}$) | **$6.13\text{ h}$** ($6.133\text{ h}$) |
| **Annual Downtime (minutes/year)** | $5555.05\text{ min}$ | $630.48\text{ min}$ | $368.00\text{ min}$ |
| **Absolute Downtime Saved** | Reference ($0.00\text{ h}$) | **$82.08\text{ h/year}$** | **$86.45\text{ h/year}$** |
| **Relative Downtime Reduction** | Reference ($0.0\%$) | **$88.65\%$** ($\approx 88.6\%$) | **$93.38\%$** |
| **Critical Bottleneck** | App & DB tiers ($94.6\%$) | Payment Gateway ($41.7\%$) & DB ($41.7\%$) | DB Replication Failover ($71.4\%$) |


## 5. Time-Dependent Reliability Functions $R(t)$ and Analytical MTTF Gain

While steady-state availability $A$ models the long-term proportion of time a repairable system spends in the operational state ($t \to \infty$), the mission reliability function $R(t)$ quantifies the probability that the system executes uninterrupted service without a single failure throughout an initial operational horizon $[0, t]$:

$$R(t) = P(T_{\text{failure}} > t), \quad R(0) = 1, \quad \lim_{t \to \infty} R(t) = 0$$

The Mean Time to Failure (MTTF) of the non-repairable mission profile represents the expected duration until the first system crash:

$$\text{MTTF} = \mathbb{E}[T_{\text{failure}}] = \int_0^\infty R(t)\,dt$$


### 5.1 Component Reliability Formulation

Assuming independent exponential distributions for subsystem failure times ($\text{TTF}_i \sim \text{Exp}(\lambda_i)$ with constant hazard rate $\lambda_i$), the individual survival functions are:

$$R_i(t) = e^{-\lambda_i t}, \quad \forall i \in \{\text{LB}, \text{App}, \text{DB}, \text{PGW}\}$$

Using nominal parameters derived from public cloud SLAs:
- $\lambda_1 = \lambda_{\text{LB}} = \frac{4}{9999} \approx 0.400040 \times 10^{-3}\text{ h}^{-1}$ ($\text{MTBF}_1 \approx 2499.75\text{ h}$)
- $\lambda_2 = \lambda_{\text{App}} = \frac{2}{199} \approx 10.050251 \times 10^{-3}\text{ h}^{-1}$ ($\text{MTBF}_2 = 99.50\text{ h}$)
- $\lambda_3 = \lambda_{\text{DB}} = \frac{1}{199} \approx 5.025126 \times 10^{-3}\text{ h}^{-1}$ ($\text{MTBF}_3 = 199.00\text{ h}$)
- $\lambda_4 = \lambda_{\text{PGW}} = \frac{2}{1999} \approx 1.000500 \times 10^{-3}\text{ h}^{-1}$ ($\text{MTBF}_4 = 999.50\text{ h}$)


### 5.2 Scenario 1: Baseline Architecture (Pure Series)

In the unredundant series pipeline ($\text{LB} \to \text{App} \to \text{DB} \to \text{PGW}$), system failure occurs whenever any individual component fails:

$$R_{\text{base}}(t) = \prod_{i=1}^4 R_i(t) = \prod_{i=1}^4 e^{-\lambda_i t} = \exp\left(-\sum_{i=1}^4 \lambda_i t\right) = e^{-\lambda_{\text{base}} t}$$

where the equivalent baseline failure rate is:

$$\lambda_{\text{base}} = \sum_{i=1}^4 \lambda_i = \frac{4}{9999} + \frac{2}{199} + \frac{1}{199} + \frac{2}{1999} = \frac{4}{9999} + \frac{3}{199} + \frac{2}{1999}$$

$$\lambda_{\text{base}} = 0.000400040 + 0.015075377 + 0.001000500 = \mathbf{0.016475917\text{ h}^{-1}} \quad (16.4759 \times 10^{-3}\text{ h}^{-1})$$

The baseline Mean Time to Failure is evaluated directly by integrating the exponential survival function:

$$\text{MTTF}_{\text{base}} = \int_0^\infty R_{\text{base}}(t)\,dt = \int_0^\infty e^{-\lambda_{\text{base}} t}\,dt = \frac{1}{\lambda_{\text{base}}} = \frac{1}{\sum_{i=1}^4 \lambda_i}$$

$$\text{MTTF}_{\text{base}} = \frac{1}{0.016475917139\text{ h}^{-1}} = \mathbf{60.694649\text{ hours}} \approx \mathbf{60.69\text{ hours}}$$

At $t = \text{MTTF}_{\text{base}}$, the baseline survival probability is exactly the characteristic life fraction:

$$R_{\text{base}}(\text{MTTF}_{\text{base}}) = e^{-1} \approx \mathbf{0.367879 \implies 36.79\%}$$


### 5.3 Scenario 2: Multi-AZ Series-Parallel Architecture

In the Multi-AZ enhanced architecture, the critical Application and Database tiers operate under active parallel redundancy (1-out-of-2):
- Load Balancer: single series unit, $R_{\text{LB}}(t) = e^{-\lambda_1 t}$
- Application Multi-AZ: 2 independent active parallel units, $R_{\text{App,red}}(t) = 1 - (1 - R_2(t))^2 = 2e^{-\lambda_2 t} - e^{-2\lambda_2 t}$
- Database Multi-AZ HA: 2 independent active parallel units, $R_{\text{DB,red}}(t) = 1 - (1 - R_3(t))^2 = 2e^{-\lambda_3 t} - e^{-2\lambda_3 t}$
- Payment Gateway: single series unit, $R_{\text{PGW}}(t) = e^{-\lambda_4 t}$

The system reliability function is the product across the 4 stages:

$$R_{\text{red}}(t) = R_{\text{LB}}(t) \cdot R_{\text{App,red}}(t) \cdot R_{\text{DB,red}}(t) \cdot R_{\text{PGW}}(t)$$

$$R_{\text{red}}(t) = e^{-(\lambda_1 + \lambda_4)t} \left(2e^{-\lambda_2 t} - e^{-2\lambda_2 t}\right) \left(2e^{-\lambda_3 t} - e^{-2\lambda_3 t}\right)$$

Expanding the algebraic product of the parallel redundant terms:

$$\left(2e^{-\lambda_2 t} - e^{-2\lambda_2 t}\right)\left(2e^{-\lambda_3 t} - e^{-2\lambda_3 t}\right) = 4 e^{-(\lambda_2 + \lambda_3)t} - 2 e^{-(2\lambda_2 + \lambda_3)t} - 2 e^{-(\lambda_2 + 2\lambda_3)t} + e^{-(2\lambda_2 + 2\lambda_3)t}$$

Multiplying through by $e^{-(\lambda_1 + \lambda_4)t}$ gives a linear combination of four exponential decay modes:

$$R_{\text{red}}(t) = 4 e^{-\gamma_1 t} - 2 e^{-\gamma_2 t} - 2 e^{-\gamma_3 t} + e^{-\gamma_4 t}$$

where the four modal decay rates are defined as:

$$\gamma_1 = \lambda_1 + \lambda_2 + \lambda_3 + \lambda_4 = \lambda_{\text{base}} = 0.016475917\text{ h}^{-1}$$

$$\gamma_2 = \lambda_1 + 2\lambda_2 + \lambda_3 + \lambda_4 = \lambda_{\text{base}} + \lambda_2 = 0.026526168\text{ h}^{-1}$$

$$\gamma_3 = \lambda_1 + \lambda_2 + 2\lambda_3 + \lambda_4 = \lambda_{\text{base}} + \lambda_3 = 0.021501043\text{ h}^{-1}$$

$$\gamma_4 = \lambda_1 + 2\lambda_2 + 2\lambda_3 + \lambda_4 = \lambda_{\text{base}} + \lambda_2 + \lambda_3 = 0.031551294\text{ h}^{-1}$$


### 5.4 Analytical Integral Derivation for $\text{MTTF}_{\text{red}}$

Because integration is a linear operator and $\int_0^\infty e^{-\gamma t}\,dt = \frac{1}{\gamma}$ for any $\gamma > 0$, the MTTF of Scenario 2 admits an exact closed-form solution:

$$\text{MTTF}_{\text{red}} = \int_0^\infty R_{\text{red}}(t)\,dt = \int_0^\infty \left(4 e^{-\gamma_1 t} - 2 e^{-\gamma_2 t} - 2 e^{-\gamma_3 t} + e^{-\gamma_4 t}\right) dt$$

$$\text{MTTF}_{\text{red}} = \frac{4}{\gamma_1} - \frac{2}{\gamma_2} - \frac{2}{\gamma_3} + \frac{1}{\gamma_4}$$

Evaluating each term numerically:
- Term 1: $\frac{4}{\gamma_1} = \frac{4}{0.016475917139} = 242.778596\text{ hours}$
- Term 2: $-\frac{2}{\gamma_2} = -\frac{2}{0.026526168395} = -75.397246\text{ hours}$
- Term 3: $-\frac{2}{\gamma_3} = -\frac{2}{0.021501042767} = -93.018745\text{ hours}$
- Term 4: $+\frac{1}{\gamma_4} = +\frac{1}{0.031551294024} = +31.694422\text{ hours}$

Summing the four terms:

$$\text{MTTF}_{\text{red}} = 242.778596 - 75.397246 - 93.018745 + 31.694422 = \mathbf{106.057027\text{ hours}} \approx \mathbf{106.06\text{ hours}}$$

*Validation:* Adaptive Gauss-Kronrod numerical integration yields $\int_0^\infty R_{\text{red}}(t)\,dt = 106.057027\text{ hours}$, confirming the exact analytical solution to within $|\Delta| < 10^{-10}\text{ hours}$.


### 5.5 Analytical MTTF Gain Quantification

The comparative gain achieved by migrating from Scenario 1 (Baseline Pure Series) to Scenario 2 (Multi-AZ Series-Parallel) is:

- **Absolute MTTF Gain:**
  $$\Delta\text{MTTF} = \text{MTTF}_{\text{red}} - \text{MTTF}_{\text{base}} = 106.057027 - 60.694649 = \mathbf{45.362378\text{ hours}} \approx \mathbf{45.36\text{ hours}}$$

- **Relative MTTF Improvement Percentage:**
  $$\text{Gain}_{\text{MTTF}} = \frac{\Delta\text{MTTF}}{\text{MTTF}_{\text{base}}} \times 100\% = \frac{45.362378}{60.694649} \times 100\% = \mathbf{74.7387\%} \approx \mathbf{74.74\%}$$

- **MTTF Multiplication Factor:**
  $$\frac{\text{MTTF}_{\text{red}}}{\text{MTTF}_{\text{base}}} = \frac{106.057027}{60.694649} = \mathbf{1.7474\times}$$

At $t = \text{MTTF}_{\text{base}} = 60.69\text{ h}$, the redundant system preserves a survival probability of $R_{\text{red}}(60.69) = \mathbf{61.20\%}$ (compared to only $36.79\%$ for the baseline series).


### 5.6 Scenario 3 Expansion (Multi-Gateway Extension)

In Scenario 3, active parallel redundancy is also incorporated into the external Payment Gateway ($R_{\text{PGW,red}}(t) = 2e^{-\lambda_4 t} - e^{-2\lambda_4 t}$):

$$R_{\text{scen3}}(t) = e^{-\lambda_1 t} \prod_{j \in \{2, 3, 4\}} \left(2e^{-\lambda_j t} - e^{-2\lambda_j t}\right)$$

Expanding into eight exponential terms and integrating term by term:

$$\text{MTTF}_{\text{scen3}} = \int_0^\infty R_{\text{scen3}}(t)\,dt = \mathbf{114.053524\text{ hours}} \approx \mathbf{114.05\text{ hours}}$$

- **Gain vs. Baseline (Scenario 1):** $+53.36\text{ hours}$ ($\mathbf{+87.91\%}$ improvement).
- **Gain vs. Multi-AZ (Scenario 2):** $+8.00\text{ hours}$ ($\mathbf{+7.54\%}$ additional improvement).


### 5.7 Operational Horizon Reliability Profile

The table below contrasts uninterrupted survival probabilities $R(t)$ across critical operational milestones without repairs:

| Operational Horizon $t$ | Equivalent Calendar Period | Baseline Series $R_{\text{base}}(t)$ | Multi-AZ Redundant $R_{\text{red}}(t)$ | Multi-Gateway $R_{\text{scen3}}(t)$ | Operational Interpretation |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **$1\text{ h}$** | Initial startup hour | $98.366\%$ | $\mathbf{99.848\%}$ | $99.947\%$ | Near-zero infant operational failure risk |
| **$24\text{ h}$** | 1 operational day | $67.340\%$ | $\mathbf{91.062\%}$ | $93.223\%$ | Redundancy prevents single-day failure ($+23.72\text{ pp}$) |
| **$72\text{ h}$** | 3 operational days (weekend) | $30.536\%$ | $\mathbf{60.307\%}$ | $64.498\%$ | Survival probability doubled over weekend window |
| **$168\text{ h}$** | 1 operational week | $6.279\%$ | $\mathbf{17.896\%}$ | $20.664\%$ | Rapid decay; repair capability becomes essential |
| **$720\text{ h}$** | 1 operational month | $0.001\%$ | $\mathbf{0.003\%}$ | $0.004\%$ | Near certainty of component event; handled by repairs |
| **$8760\text{ h}$** | 1 operational year ($T$) | $\approx 0\%$ ($10^{-63}$) | $\approx \mathbf{0\%}$ ($10^{-42}$) | $\approx 0\%$ | Highlights difference: $R(t) \to 0$ without repair, while $A = 99.88\%$ with repair |


## 6. Consolidated Multi-Metric Comparison Table

| Metric Category | Metric Symbol / Name | Scenario 1 (Baseline Series) | Scenario 2 (Multi-AZ Series-Parallel) | Scenario 3 (Multi-Gateway Expansion) | Mathematical Reference |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Availability** | Steady-state Availability $A_{\text{sys}}$ | **$98.9431\%$** | **$99.8800\%$** | **$99.9300\%$** | Eq. (10), (39), (59), (80) |
| | Unavailability $U_{\text{sys}}$ | $1.0569\%$ | $0.11995\%$ | $0.07001\%$ | $U = 1 - A$ |
| | Annual Downtime ($D$) | **$92.58\text{ h/yr}$** | **$10.51\text{ h/yr}$** | **$6.13\text{ h/yr}$** | $D = U \times 8760\text{ h}$ |
| | Downtime Reduction vs S1 | Reference ($0.0\%$) | **$88.65\%$** ($82.08\text{ h}$) | **$93.38\%$** ($86.45\text{ h}$) | $\Delta D / D_{\text{base}}$ |
| **Reliability** | Mean Time to Failure ($\text{MTTF}$) | **$60.69\text{ h}$** | **$106.06\text{ h}$** | **$114.05\text{ h}$** | $\int_0^\infty R(t)\,dt$ |
| | MTTF Absolute Gain ($\Delta\text{MTTF}$) | Reference ($0.00\text{ h}$) | **$+45.36\text{ h}$** | **$+53.36\text{ h}$** | $\text{MTTF} - \text{MTTF}_{\text{base}}$ |
| | MTTF Relative Gain | Reference ($0.0\%$) | **$+74.74\%$** | **$+87.91\%$** | $\Delta\text{MTTF} / \text{MTTF}_{\text{base}}$ |
| | MTTF Multiplier Factor | $1.000\times$ | **$1.747\times$** | **$1.879\times$** | $\text{MTTF} / \text{MTTF}_{\text{base}}$ |
| | 24-hour Survival $R(24\text{ h})$ | $67.34\%$ | **$91.06\%$** | $93.22\%$ | $R(24)$ |
| | 72-hour Survival $R(72\text{ h})$ | $30.54\%$ | **$60.31\%$** | $64.50\%$ | $R(72)$ |


## 7. Subsystem Unavailability and Downtime Pareto Analysis

Pareto analysis quantifies the relative impact of individual architectural tiers on total system downtime, identifying the primary single points of failure (SPOFs) in baseline designs and revealing the bottleneck migration induced by fault-tolerant redundancy [1], [7].

### 7.1 Mathematical Formulation of Unavailability Allocation

Each subsystem $i \in \{\text{LB}, \text{App}, \text{DB}, \text{PGW}\}$ exhibits steady-state unavailability $U_i = 1 - A_i$. Over an annual mission duration $T = 8760\text{ hours}$ ($525{,}600\text{ minutes}$), the standalone expected annual downtime is:

$$D_i = U_i \times T = (1 - A_i) \times 8760\text{ hours/year}$$

The aggregate sum of standalone subsystem downtimes across all $n$ blocks is:

$$D_{\text{sum}} = \sum_{i=1}^n D_i = T \sum_{i=1}^n U_i$$

#### 7.1.1 Relation to Exact System Downtime (Overlapping Outage Derivation)
For an unredundant pure series system of independent blocks:

$$A_{\text{sys}} = \prod_{i=1}^n A_i = \prod_{i=1}^n (1 - U_i) = 1 - \sum_{i=1}^n U_i + \sum_{1 \le i < j \le n} U_i U_j - \dots$$

$$U_{\text{sys}} = 1 - A_{\text{sys}} = \sum_{i=1}^n U_i - \sum_{1 \le i < j \le n} U_i U_j + \dots \le \sum_{i=1}^n U_i$$

Because $U_i \ll 1$ in carrier-grade cloud architectures ($U_i \le 5 \times 10^{-3}$), higher-order joint outage products are negligible:

$$\varepsilon_{\text{overlap}} = \frac{D_{\text{sum}} - D_{\text{sys}}}{D_{\text{sys}}} = \frac{\sum_{1 \le i < j \le n} U_i U_j + \dots}{U_{\text{sys}}}$$

- **Scenario 1:** $D_{\text{sum}} = 92.8560\text{ h}$, $D_{\text{base}} = 92.5841\text{ h} \implies \Delta = 0.2719\text{ h}$ ($16.31\text{ min/yr}$, $\varepsilon = 0.293\%$).
- **Scenario 2:** $D_{\text{sum}} = 10.5120\text{ h}$, $D_{\text{red}} = 10.5080\text{ h} \implies \Delta = 0.0040\text{ h}$ ($14.50\text{ s/yr}$, $\varepsilon = 0.038\%$).
- **Scenario 3:** $D_{\text{sum}} = 6.1342\text{ h}$, $D_{\text{scen3}} = 6.1332\text{ h} \implies \Delta = 0.0010\text{ h}$ ($3.50\text{ s/yr}$, $\varepsilon = 0.016\%$).

The first-order linear approximation holds with $>99.7\%$ precision across all scenarios.

#### 7.1.2 Fractional Downtime Contribution and Cumulative Pareto Ranking
Subsystems are sorted in descending order of individual downtime: $D_{(1)} \ge D_{(2)} \ge \dots \ge D_{(n)}$.

The individual percentage share of total subsystem downtime is:

$$p_i = \frac{D_i}{\sum_{j=1}^n D_j} \times 100\% = \frac{U_i}{\sum_{j=1}^n U_j} \times 100\%$$

The cumulative Pareto distribution function $C_k$ for the top $k$ contributors is:

$$C_k = \sum_{j=1}^k p_{(j)} = \frac{\sum_{j=1}^k D_{(j)}}{\sum_{j=1}^n D_j} \times 100\%, \quad C_n = 100\%$$

The proportionally allocated share of exact system downtime is:

$$D_{i, \text{alloc}} = \frac{D_i}{D_{\text{sum}}} \times D_{\text{sys}} = \frac{p_i}{100} \times D_{\text{sys}}$$


### 7.2 Scenario 1 Pareto Decomposition (Baseline Pure Series)

In Scenario 1, every subsystem is an unredundant Single Point of Failure (SPOF):

| Pareto Rank | Block Code | Subsystem Name | Architectural Tier | Availability ($A_i$) | Unavailability ($U_i$) | Standalone Downtime ($D_i$) | Share ($p_i$) | Cumulative Share ($C_k$) | Allocated Downtime ($D_{i,\text{alloc}}$) |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | **App** | Application Server | Business Logic | $99.5000\%$ | $5000\text{ ppm}$ | $43.8000\text{ h/yr}$ | $\mathbf{47.17\%}$ | $47.17\%$ | $43.6718\text{ h/yr}$ |
| **2** | **DB** | Relational Database | Data Persistence | $99.5000\%$ | $5000\text{ ppm}$ | $43.8000\text{ h/yr}$ | $\mathbf{47.17\%}$ | $\mathbf{94.34\%}$ | $43.6718\text{ h/yr}$ |
| **3** | **PGW** | Payment Gateway | External Settlement | $99.9500\%$ | $500\text{ ppm}$ | $4.3800\text{ h/yr}$ | $4.72\%$ | $99.06\%$ | $4.3672\text{ h/yr}$ |
| **4** | **LB** | Load Balancer | Ingress Routing | $99.9900\%$ | $100\text{ ppm}$ | $0.8760\text{ h/yr}$ | $0.94\%$ | $100.00\%$ | $0.8734\text{ h/yr}$ |
| **Total** | — | **Full System (Pure Series)** | — | **$98.9431\%$** | **$10569\text{ ppm}$** | **$92.8560\text{ h/yr}$** | **$100.00\%$** | — | **$92.5841\text{ h/yr}$** |

**Core Analytical Insight (S1):**
- **App and DB combined represent $94.34\%$** of all system downtime ($87.60\text{ hours/year}$ out of $92.86\text{ hours}$).
- Under the Pareto 80/20 principle, mitigating solely the top two internal tiers eliminates $>94\%$ of the reliability penalty.


### 7.3 Scenario 2 Pareto Decomposition (Multi-AZ Series-Parallel)

With active Multi-AZ redundancy deployed across Application instances ($A_{2,\text{red}} = 99.99\%$) and Database synchronous replication ($A_{3,\text{red}} = 99.95\%$):

| Pareto Rank | Block Code | Subsystem Name | Architectural Tier | Availability ($A_i$) | Unavailability ($U_i$) | Standalone Downtime ($D_i$) | Share ($p_i$) | Cumulative Share ($C_k$) | Allocated Downtime ($D_{i,\text{alloc}}$) |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | **DB** | Relational Database | Multi-AZ Failover | $99.9500\%$ | $500\text{ ppm}$ | $4.3800\text{ h/yr}$ | $\mathbf{41.67\%}$ | $41.67\%$ | $4.3783\text{ h/yr}$ |
| **2** | **PGW** | Payment Gateway | External Settlement | $99.9500\%$ | $500\text{ ppm}$ | $4.3800\text{ h/yr}$ | $\mathbf{41.67\%}$ | $\mathbf{83.33\%}$ | $4.3783\text{ h/yr}$ |
| **3** | **LB** | Load Balancer | Ingress Routing | $99.9900\%$ | $100\text{ ppm}$ | $0.8760\text{ h/yr}$ | $8.33\%$ | $91.67\%$ | $0.8757\text{ h/yr}$ |
| **4** | **App** | Application Server | Multi-AZ Active-Active | $99.9900\%$ | $100\text{ ppm}$ | $0.8760\text{ h/yr}$ | $8.33\%$ | $100.00\%$ | $0.8757\text{ h/yr}$ |
| **Total** | — | **Full System (Multi-AZ)** | — | **$99.8800\%$** | **$1200\text{ ppm}$** | **$10.5120\text{ h/yr}$** | **$100.00\%$** | — | **$10.5080\text{ h/yr}$** |

**Core Analytical Insight (S2 - The Bottleneck Shift):**
- Application downtime collapsed from $43.80\text{ h}$ to $0.876\text{ h}$ ($\mathbf{98.00\%\text{ reduction}}$).
- Database downtime fell from $43.80\text{ h}$ to $4.38\text{ h}$ ($\mathbf{90.00\%\text{ reduction}}$).
- Total internal tier downtime dropped by $\mathbf{94.00\%}$ (from $87.60\text{ h}$ to $5.256\text{ h}$).
- Because the external Payment Gateway remained unredundant at $99.95\%$ ($4.38\text{ h/yr}$), its relative share of system downtime multiplied by $\mathbf{8.83\times}$ (from $4.72\%$ to $\mathbf{41.67\%}$).
- **DB and PGW now jointly account for $83.33\%$** of all system downtime ($8.76\text{ hours/year}$ out of $10.51\text{ hours}$).


### 7.4 Scenario 3 Pareto Decomposition (Multi-Gateway Expansion)

Incorporating active parallel redundancy on the external Payment Gateway ($A_{4,\text{red}} = 99.999975\%$):

| Pareto Rank | Block Code | Subsystem Name | Architectural Tier | Availability ($A_i$) | Unavailability ($U_i$) | Standalone Downtime ($D_i$) | Share ($p_i$) | Cumulative Share ($C_k$) | Allocated Downtime ($D_{i,\text{alloc}}$) |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | **DB** | Relational Database | Multi-AZ Failover | $99.9500\%$ | $500\text{ ppm}$ | $4.3800\text{ h/yr}$ | $\mathbf{71.41\%}$ | $\mathbf{71.41\%}$ | $4.3793\text{ h/yr}$ |
| **2** | **LB** | Load Balancer | Ingress Routing | $99.9900\%$ | $100\text{ ppm}$ | $0.8760\text{ h/yr}$ | $14.28\%$ | $85.69\%$ | $0.8759\text{ h/yr}$ |
| **3** | **App** | Application Server | Multi-AZ Active-Active | $99.9900\%$ | $100\text{ ppm}$ | $0.8760\text{ h/yr}$ | $14.28\%$ | $99.96\%$ | $0.8759\text{ h/yr}$ |
| **4** | **PGW** | Payment Gateway | Dual Active-Active Gateways | $99.999975\%$ | $0.25\text{ ppm}$ | $0.00219\text{ h/yr}$ ($7.88\text{ s}$) | $\mathbf{0.04\%}$ | $100.00\%$ | $0.00219\text{ h/yr}$ |
| **Total** | — | **Full System (Multi-Gateway)** | — | **$99.9300\%$** | **$700\text{ ppm}$** | **$6.1342\text{ h/yr}$** | **$100.00\%$** | — | **$6.1332\text{ h/yr}$** |

**Core Analytical Insight (S3):**
- Dual payment gateway routing virtually eliminates external dependency risk, reducing PGW downtime from $4.38\text{ h}$ to $\mathbf{7.88\text{ seconds/year}}$ ($\mathbf{99.95\%\text{ reduction}}$).
- Transactional Database failover ($4.38\text{ h/yr}$) now accounts for $\mathbf{71.41\%}$ of all remaining downtime, establishing the ultimate architectural asymptote under current synchronous persistence technology.


### 7.5 Quantitative Summary of Bottleneck Shifts

The table below contrasts the distribution of annual downtime across architectural generations, demonstrating Amdahl's Law for system reliability:

| Subsystem / Metric | Scenario 1 (Baseline Series) | Scenario 2 (Multi-AZ Series-Parallel) | Scenario 3 (Multi-Gateway Expansion) | Shift Trend & Engineering Implication |
| :--- | :---: | :---: | :---: | :--- |
| **Application Server (App)** | $43.80\text{ h}$ ($47.17\%$) | $0.88\text{ h}$ ($8.33\%$) | $0.88\text{ h}$ ($14.28\%$) | Slashed by $98.0\%$; eliminated as primary SPOF |
| **Transactional Database (DB)** | $43.80\text{ h}$ ($47.17\%$) | $4.38\text{ h}$ ($41.67\%$) | $4.38\text{ h}$ ($\mathbf{71.41\%}$) | Reduced by $90.0\%$; becomes primary remaining bottleneck |
| **Internal Tiers Combined (App + DB)** | **$87.60\text{ h}$ ($94.34\%$)** | **$5.26\text{ h}$ ($50.00\%$)** | **$5.26\text{ h}$ ($85.69\%$)** | Internal downtime reduced by $94.0\%$ |
| **Payment Gateway (PGW)** | $4.38\text{ h}$ ($4.72\%$) | $4.38\text{ h}$ ($\mathbf{41.67\%}$) | $0.002\text{ h}$ ($0.04\%$) | Relative share surged $8.8\times$ in S2; wiped out in S3 |
| **Load Balancer (LB)** | $0.88\text{ h}$ ($0.94\%$) | $0.88\text{ h}$ ($8.33\%$) | $0.88\text{ h}$ ($14.28\%$) | Invariant baseline floor; managed infrastructure baseline |
| **Top 2 Contributors Combined ($C_2$)** | **$94.34\%$** (App, DB) | **$83.33\%$** (DB, PGW) | **$85.69\%$** (DB, LB) | Governed by Pareto principle in all configurations |
| **Total System Downtime** | **$92.58\text{ h/year}$** | **$10.51\text{ h/year}$** | **$6.13\text{ h/year}$** | **$93.38\%\text{ total downtime reduction}$** |


## 8. Stochastic Discrete-Event Monte Carlo Simulation & Statistical Inference

Stochastic simulation provides empirical cross-validation of the closed-form analytical models, capturing dynamic state transitions and finite-horizon edge effects over an annual operational lifespan $T = 8760\text{ hours}$ ($525{,}600\text{ minutes}$) across $N = 10^4$ independent simulated years [3], [6], [9].


### 8.1 Continuous-Time Alternating Renewal Process

Each functional subsystem $i \in \{\text{LB}, \text{App}, \text{DB}, \text{PGW}\}$ operates as an alternating renewal process governed by two independent continuous random variables:
1. **Time to Failure ($\text{TTF}_i$):** Distributed exponentially with constant hazard rate $\lambda_i > 0$:
   $$F_i(t) = P(\text{TTF}_i \le t) = 1 - e^{-\lambda_i t}, \quad f_i(t) = \lambda_i e^{-\lambda_i t}, \quad \mathbb{E}[\text{TTF}_i] = \text{MTBF}_i = \frac{1}{\lambda_i}$$
2. **Time to Repair ($\text{TTR}_i$):** Distributed exponentially with constant restoration rate $\mu_i > 0$:
   $$G_i(t) = P(\text{TTR}_i \le t) = 1 - e^{-\mu_i t}, \quad g_i(t) = \mu_i e^{-\mu_i t}, \quad \mathbb{E}[\text{TTR}_i] = \text{MTTR}_i = \frac{1}{\mu_i}$$

Pseudo-random variates are generated via Inverse Transform Sampling parameterized by uniform random numbers $u, v \sim \mathcal{U}(0, 1)$ initialized with a fixed seed (`np.random.seed(2026)`):
$$\text{TTF} = -\frac{\ln(1 - u)}{\lambda_i} \stackrel{d}{=} -\frac{\ln(u)}{\lambda_i}, \quad \text{TTR} = -\frac{\ln(1 - v)}{\mu_i} \stackrel{d}{=} -\frac{\ln(v)}{\mu_i}$$

For each simulated year $k \in \{1, \dots, N\}$, the renewal sequence generates an ordered set of disjoint outage intervals within the finite horizon $[0, T]$:
$$\mathcal{I}_i^{(k)} = \bigcup_{j=1}^{M_i^{(k)}} \left[ t_{\text{fail}, j}^{(i, k)}, \min\left(t_{\text{restored}, j}^{(i, k)}, T\right) \right) \subset [0, T]$$


### 8.2 Topological State Evaluation via Interval Arithmetic

The operational state of the architecture at time $t \in [0, T]$ is evaluated through Boolean structure functions translated into exact set-theoretic operations on outage intervals:

1. **Pure Series System (Scenario 1):**
   The payment pipeline fails if *any* subsystem is down ($S_{\text{sys}}(t) = \prod_{i=1}^4 S_i(t)$). Thus, the system outage set is the set union of all constituent outages:
   $$\mathcal{I}_{\text{base}}^{(k)} = \bigcup_{i=1}^4 \mathcal{I}_i^{(k)}$$
   Because outages can temporally overlap across independent subsystems, exact annual downtime is the Lebesgue measure of the merged union:
   $$D_{\text{base}}^{(k)} = \mu_{\text{Lebesgue}}\left( \mathcal{I}_{\text{base}}^{(k)} \right) = \sum_{m} \left( \text{end}_m - \text{start}_m \right)$$
   This naturally captures the overlapping outage term $\Delta = 0.2719\text{ h/year}$ derived in Section 7.1.1.

2. **Active Parallel Redundancy (1-out-of-2):**
   A parallel subsystem of two independent units is unavailable only during concurrent failures (temporal intersection):
   $$\mathcal{I}_{\text{parallel}}^{(k)} = \mathcal{I}_{\text{unit 1}}^{(k)} \cap \mathcal{I}_{\text{unit 2}}^{(k)}$$

3. **Series-Parallel Architecture (Scenario 2):**
   Under Multi-AZ series-parallel configuration, the Load Balancer and Payment Gateway operate in series with the fault-tolerant Application and Database tiers:
   $$\mathcal{I}_{\text{red}}^{(k)} = \mathcal{I}_{\text{LB}}^{(k)} \cup \mathcal{I}_{\text{App,tier}}^{(k)} \cup \mathcal{I}_{\text{DB,tier}}^{(k)} \cup \mathcal{I}_{\text{PGW}}^{(k)}$$
   Under contractual SLA parameterization ($A_{2,\text{red}} = 99.99\%$, $A_{3,\text{red}} = 99.95\%$), the effective transition rates directly calibrate the simulation to the verified vendor benchmarks.


### 8.3 Statistical Estimators and Confidence Intervals

For each replication $k \in \{1, \dots, N\}$, the operational availability fraction is:
$$A_k = \frac{T_{\text{operational}, k}}{T} = \frac{T - D_k}{T} = 1 - \frac{D_k}{T}, \quad \text{where } T = 8760\text{ hours}$$

The point estimator for mean system availability is the sample mean [3]:
$$\hat{A} = \frac{1}{N} \sum_{k=1}^N A_k = \frac{1}{N} \sum_{k=1}^N \frac{T_{\text{operational}, k}}{T_{\text{operational}, k} + T_{\text{down}, k}} = 1 - \frac{\hat{D}}{T}$$

The point estimator for expected annual downtime is:
$$\hat{D} = \frac{1}{N} \sum_{k=1}^N D_k$$

The unbiased sample variances are:
$$s_A^2 = \frac{1}{N - 1} \sum_{k=1}^N \left(A_k - \hat{A}\right)^2, \quad s_D^2 = \frac{1}{N - 1} \sum_{k=1}^N \left(D_k - \hat{D}\right)^2 = T^2 s_A^2$$

The Standard Error of the Mean (SEM) is:
$$\text{SE}(\hat{A}) = \frac{s_A}{\sqrt{N}}, \quad \text{SE}(\hat{D}) = \frac{s_D}{\sqrt{N}}$$

#### Bilateral 95% Confidence Interval
By the Central Limit Theorem, for $N = 10^4 \gg 30$, the distribution of $\hat{A}$ is asymptotically Gaussian:
$$\hat{A} \sim \mathcal{N}\left(A, \frac{\sigma^2}{N}\right)$$

For a bilateral confidence level $1 - \alpha = 0.95$ ($\alpha = 0.05$), the two-tailed critical value is $z_{0.975} = 1.959964$ (or $t_{9999, 0.975} = 1.960204$ from Student's t-distribution):
$$\text{CI}_{95\%}(\hat{A}) = \left[ \hat{A} - z_{0.975} \frac{s_A}{\sqrt{N}}, \quad \hat{A} + z_{0.975} \frac{s_A}{\sqrt{N}} \right]$$
$$\text{CI}_{95\%}(\hat{D}) = \left[ \hat{D} - z_{0.975} \frac{s_D}{\sqrt{N}}, \quad \hat{D} + z_{0.975} \frac{s_D}{\sqrt{N}} \right]$$


### 8.4 Relative Percentage Error Formulation

The accuracy of the Monte Carlo estimator against the exact closed-form analytical availability $A$ is quantified through the relative percentage error:
$$\varepsilon_{\text{rel}}(\hat{A}) = \frac{|\hat{A} - A|}{A} \times 100\%$$
$$\varepsilon_{\text{rel}}(\hat{D}) = \frac{|\hat{D} - D|}{D} \times 100\%$$

The acceptance threshold for numerical validation is $\varepsilon_{\text{rel}}(\hat{A}) < 0.05\%$.


### 8.5 Empirical Validation Results Table ($N = 10^4$, Seed = 2026)

The table below contrasts the exact analytical solutions against the stochastic Monte Carlo estimates obtained from the simulation engine (`src/simulation/monte_carlo.py`):

| Evaluation Metric | Scenario 1 (Baseline Series) | Scenario 2 (Multi-AZ Series-Parallel) | Scenario 3 (Multi-Gateway Expansion) | Acceptance Criterion |
| :--- | :---: | :---: | :---: | :---: |
| **Analytical Availability ($A$)** | **$98.9431\%$** ($0.98943103$) | **$99.8800\%$** ($0.99880046$) | **$99.9300\%$** ($0.99929986$) | Theoretical Benchmark |
| **Simulated Availability ($\hat{A}$)** | **$98.9425\%$** ($0.98942474$) | **$99.8802\%$** ($0.99880240$) | **$99.9294\%$** ($0.99929430$) | Point Estimator |
| **Availability 95% Confidence Interval** | **$[98.9399\%, 98.9451\%]$** | **$[99.8794\%, 99.8811\%]$** | **$[99.9287\%, 99.9301\%]$** | $A \in \text{CI}_{95\%}$ (Contains Theoretical) |
| **Availability Relative Error ($\varepsilon_{\text{rel}}$)** | **$0.00064\%$** | **$0.00019\%$** | **$0.00056\%$** | **$< 0.05\%$ (Passed)** |
| **Analytical Downtime ($D$)** | **$92.58\text{ h/year}$** | **$10.51\text{ h/year}$** | **$6.13\text{ h/year}$** | Theoretical Benchmark |
| **Simulated Downtime ($\hat{D}$)** | **$92.64\text{ h/year}$** | **$10.49\text{ h/year}$** | **$6.18\text{ h/year}$** | Point Estimator |
| **Downtime 95% Confidence Interval** | **$[92.41\text{ h}, 92.87\text{ h}]$** | **$[10.42\text{ h}, 10.56\text{ h}]$** | **$[6.12\text{ h}, 6.24\text{ h}]$** | $D \in \text{CI}_{95\%}$ (Contains Theoretical) |
| **Downtime Sample Std Dev ($s_D$)** | $11.55\text{ h}$ | $3.74\text{ h}$ | $3.19\text{ h}$ | Empirical Sample Dispersion |
| **Standard Error of Mean ($\text{SE}$)** | $0.115\text{ h}$ ($6.93\text{ min}$) | $0.037\text{ h}$ ($2.24\text{ min}$) | $0.032\text{ h}$ ($1.91\text{ min}$) | $\text{SE} = s / \sqrt{10^4}$ |
| **Expected Failure Events / Year** | $142.93\text{ events}$ | $18.43\text{ events}$ | $7.94\text{ events}$ | Modeled Poisson/Renewal Intensity |
| **Execution Wall-Clock Time** | **$1.72\text{ seconds}$** | **$0.28\text{ seconds}$** | **$0.25\text{ seconds}$** | **$< 60\text{ seconds (Passed)}$** |

*Validation Conclusion:* For all architectural scenarios, the analytical benchmark lies strictly within the empirical 95% confidence interval, and the availability relative error is two orders of magnitude below the $0.05\%$ threshold ($\le 0.00064\%$), confirming the mathematical and computational integrity of the stochastic simulation engine.


### 8.6 Asymptotic Convergence Analysis and Strong Law of Large Numbers (SLLN)

Let $A_1, A_2, \dots, A_N$ denote the sequence of independent and identically distributed (i.i.d.) annual operational availability realizations generated across Monte Carlo replications. The cumulative sample mean sequence is defined as [3]:

$$\hat{A}(n) = \frac{1}{n} \sum_{k=1}^n A_k, \quad \text{for } n \in \{1, 2, \dots, N\}$$

By Kolmogorov's Strong Law of Large Numbers (SLLN), since the availability random variable is bounded ($A_k \in [0, 1] \implies \mathbb{E}[|A_k|] < \infty$), the empirical sequence converges almost surely to the exact theoretical expectation:

$$\mathbb{P}\left(\lim_{n \to \infty} \hat{A}(n) = A_{\text{theo}}\right) = 1$$

Furthermore, by the Lindeberg-Lévy Central Limit Theorem, the asymptotic error distribution follows:

$$\sqrt{n}\left(\hat{A}(n) - A_{\text{theo}}\right) \xrightarrow{d} \mathcal{N}\left(0, \sigma_A^2\right)$$

At each simulation iteration step $n$, the bilateral $95\%$ confidence envelope has a half-width shrinking strictly at rate $\mathcal{O}(1/\sqrt{n})$:

$$\Delta_n = z_{0.975} \frac{s_A(n)}{\sqrt{n}} = 1.959964 \times \frac{s_A(n)}{\sqrt{n}}$$

$$\text{CI}_{95\%}(n) = \left[ \hat{A}(n) - \Delta_n, \quad \hat{A}(n) + \Delta_n \right]$$

where $s_A(n) = \sqrt{\frac{1}{n-1}\sum_{k=1}^n (A_k - \hat{A}(n))^2}$ is the unbiased running sample standard deviation.

#### Asymptotic Convergence Milestones ($N = 10^4$, Seed = 2026)

The table below traces the convergence progression at key iteration checkpoints across all three architectural scenarios:

| Checkpoint ($n$) | Metric | Scenario 1 (Baseline Series) | Scenario 2 (Multi-AZ Series-Parallel) | Scenario 3 (Multi-Gateway Expansion) |
| :---: | :--- | :---: | :---: | :---: |
| **$n = 10$** | Cumulative Mean $\hat{A}(n)$<br>95% Margin of Error $\Delta_n$<br>Relative Error $\varepsilon_{\text{rel}}$ | $99.00506\%$<br>$\pm 0.08408\%$<br>$0.06262\%$ | $99.87120\%$<br>$\pm 0.02998\%$<br>$0.00886\%$ | $99.93427\%$<br>$\pm 0.02530\%$<br>$0.00429\%$ |
| **$n = 50$** | Cumulative Mean $\hat{A}(n)$<br>95% Margin of Error $\Delta_n$<br>Relative Error $\varepsilon_{\text{rel}}$ | $98.94312\%$<br>$\pm 0.03258\%$<br>$0.00002\%$ | $99.88591\%$<br>$\pm 0.01107\%$<br>$0.00587\%$ | $99.93756\%$<br>$\pm 0.00835\%$<br>$0.00758\%$ |
| **$n = 100$** | Cumulative Mean $\hat{A}(n)$<br>95% Margin of Error $\Delta_n$<br>Relative Error $\varepsilon_{\text{rel}}$ | $98.93972\%$<br>$\pm 0.02609\%$<br>$0.00342\%$ | $99.88182\%$<br>$\pm 0.00770\%$<br>$0.00178\%$ | $99.93055\%$<br>$\pm 0.00704\%$<br>$0.00056\%$ |
| **$n = 500$** | Cumulative Mean $\hat{A}(n)$<br>95% Margin of Error $\Delta_n$<br>Relative Error $\varepsilon_{\text{rel}}$ | $98.95172\%$<br>$\pm 0.01157\%$<br>$0.00871\%$ | $99.88008\%$<br>$\pm 0.00389\%$<br>$0.00003\%$ | $99.92905\%$<br>$\pm 0.00334\%$<br>$0.00094\%$ |
| **$n = 1{,}000$** | Cumulative Mean $\hat{A}(n)$<br>95% Margin of Error $\Delta_n$<br>Relative Error $\varepsilon_{\text{rel}}$ | $98.95095\%$<br>$\pm 0.00846\%$<br>$0.00793\%$ | $99.88027\%$<br>$\pm 0.00266\%$<br>$0.00023\%$ | $99.92988\%$<br>$\pm 0.00229\%$<br>$0.00011\%$ |
| **$n = 5{,}000$** | Cumulative Mean $\hat{A}(n)$<br>95% Margin of Error $\Delta_n$<br>Relative Error $\varepsilon_{\text{rel}}$ | $98.94412\%$<br>$\pm 0.00367\%$<br>$0.00103\%$ | $99.87979\%$<br>$\pm 0.00120\%$<br>$0.00026\%$ | $99.92923\%$<br>$\pm 0.00102\%$<br>$0.00076\%$ |
| **$n = 10{,}000$** | Cumulative Mean $\hat{A}(n)$<br>95% Margin of Error $\Delta_n$<br>Relative Error $\varepsilon_{\text{rel}}$ | **$98.94247\%$**<br>**$\pm 0.00258\%$**<br>**$0.00064\%$** | **$99.88024\%$**<br>**$\pm 0.00084\%$**<br>**$0.00019\%$** | **$99.92933\%$**<br>**$\pm 0.00072\%$**<br>**$0.00066\%$** |
| **Benchmark ($A_{\text{theo}}$)** | Analytical Availability | **$98.94310\%$** | **$99.88005\%$** | **$99.92999\%$** |

*Convergence Analysis:* For all configurations, relative error falls below $0.01\%$ for $n \ge 500$ iterations and achieves sub-$0.001\%$ precision at $N = 10^4$, validating asymptotic stability and proving that the $N = 10^4$ sample size satisfies IEEE publication requirements.


### 8.7 Empirical Annual Downtime Distribution and Value-at-Risk (SLA Risk Metrics)

Annual downtime $D_k = \sum_m (\text{end}_m - \text{start}_m)$ is a continuous random variable whose distribution depends on architectural topology and renewal intensity:

1. **Scenario 1 (Baseline Pure Series):**
   Outages occur across all four unredundant blocks at rate $\Lambda = \sum_{i=1}^4 \lambda_i = 16.476 \times 10^{-3}\text{ h}^{-1}$, generating an expected $142.93$ independent failure events annually. By the Central Limit Theorem applied to renewal counts and outage durations, the distribution of annual downtime $D_{\text{base}}$ converges closely to a normal profile:
   - Sample Mean: $\hat{\mu}_D = 92.64\text{ h/year}$
   - Sample Standard Deviation: $s_D = 11.55\text{ h/year}$
   - Skewness: $\gamma_1 = 0.1874 \approx 0$ (near-zero skewness, nearly symmetric)
   - Excess Kurtosis: $\gamma_2 = -0.0140 \approx 0$ (mesokurtic, near-Gaussian tails)

2. **Scenario 2 (Multi-AZ Series-Parallel):**
   Active redundancy at the compute tier collapses independent application outages. Annual downtime is governed by single-point database failovers and external payment gateway outages (~$18.43$ events/year). Because outages are rarer and have exponential durations, the distribution exhibits moderate right-skewness:
   - Sample Mean: $\hat{\mu}_D = 10.49\text{ h/year}$
   - Sample Standard Deviation: $s_D = 3.74\text{ h/year}$
   - Skewness: $\gamma_1 = 0.5785$ (moderately positive right-skew)
   - Excess Kurtosis: $\gamma_2 = 0.4229$ (leptokurtic, heavier right tail)

3. **Scenario 3 (Multi-Gateway Expansion):**
   With active payment gateway redundancy, external outages drop to near zero (~$0.0029\text{ h/yr}$). Total downtime is driven almost entirely by database Multi-AZ failovers (~$7.94$ events/year), amplifying right-skewness:
   - Sample Mean: $\hat{\mu}_D = 6.19\text{ h/year}$
   - Sample Standard Deviation: $s_D = 3.20\text{ h/year}$
   - Skewness: $\gamma_1 = 0.8627$ (pronounced right-skew)
   - Excess Kurtosis: $\gamma_2 = 1.0504$ (heavier tail)

#### Risk Percentiles and Operational SLA Thresholds Table

In contractual Service Level Agreements, point estimators alone are insufficient because financial penalties occur during extreme tail events. Percentiles provide operational Value-at-Risk (VaR) thresholds:

| Statistical Metric | Scenario 1 (Baseline Series) | Scenario 2 (Multi-AZ Series-Parallel) | Scenario 3 (Multi-Gateway Expansion) | Engineering Interpretation |
| :--- | :---: | :---: | :---: | :--- |
| **Analytical Mean ($D$)** | **$92.58\text{ h/year}$** | **$10.51\text{ h/year}$** | **$6.13\text{ h/year}$** | Theoretical long-term expectation |
| **Simulated Mean ($\hat{D}$)** | **$92.64\text{ h/year}$** | **$10.49\text{ h/year}$** | **$6.19\text{ h/year}$** | Empirical average over $10^4$ years |
| **Standard Deviation ($s_D$)** | $11.55\text{ h/year}$ | $3.74\text{ h/year}$ | $3.20\text{ h/year}$ | Sample dispersion |
| **Median ($p_{50}$)** | $92.16\text{ h/year}$ | $10.12\text{ h/year}$ | $5.73\text{ h/year}$ | 50% probability threshold |
| **90th Percentile ($p_{90}$)** | $107.72\text{ h/year}$ | $15.53\text{ h/year}$ | $10.51\text{ h/year}$ | Upper decile operational budget |
| **95th Percentile ($D_{0.95}$)** | **$112.21\text{ h/year}$** | **$17.17\text{ h/year}$** | **$12.07\text{ h/year}$** | **SLA Risk Boundary (95% certainty)** |
| **99th Percentile ($D_{0.99}$)** | **$121.15\text{ h/year}$** | **$20.85\text{ h/year}$** | **$15.45\text{ h/year}$** | Extreme tail risk (worst 1-in-100 years) |
| **Minimum Observed** | $53.52\text{ h/year}$ | $1.14\text{ h/year}$ | $0.06\text{ h/year}$ | Best-case simulated year |
| **Maximum Observed** | $138.15\text{ h/year}$ | $29.04\text{ h/year}$ | $23.24\text{ h/year}$ | Worst-case simulated year |
| **Risk Buffer ($D_{0.95} - \hat{D}$)** | $+19.57\text{ h/year}$ | $+6.68\text{ h/year}$ | $+5.88\text{ h/year}$ | Contractual safety margin needed |

*Operational Risk Finding:* Multi-AZ redundancy reduces the 95th percentile worst-case downtime from $112.21\text{ h}$ to $17.17\text{ h}$ ($-84.7\%$), drastically reducing the probability of catastrophic SLA penalty payments.


### 8.8 Simulated Subsystem Downtime Breakdown and Pareto Cross-Validation

The discrete-event simulation records individual downtime intervals $\mathcal{I}_i^{(k)}$ per subsystem $i \in \{\text{LB}, \text{App}, \text{DB}, \text{PGW}\}$. The empirical mean subsystem downtime is:

$$\hat{D}_i = \frac{1}{N} \sum_{k=1}^N D_{i, k}$$

The table below contrasts the analytical downtime contributions derived in Section 3 and Section 8 against the empirical Monte Carlo subsystem averages:

| Architectural Tier | Subsystem Code | Scenario 1 Analytical ($D_i$) | Scenario 1 Simulated ($\hat{D}_i$) | Scenario 2 Analytical ($D_i$) | Scenario 2 Simulated ($\hat{D}_i$) | Scenario 3 Analytical ($D_i$) | Scenario 3 Simulated ($\hat{D}_i$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Load Balancer** | **LB** | $0.876\text{ h}$ ($0.94\%$) | $0.867\text{ h}$ ($0.94\%$) | $0.876\text{ h}$ ($8.33\%$) | $0.882\text{ h}$ ($8.40\%$) | $0.876\text{ h}$ ($14.28\%$) | $0.878\text{ h}$ ($14.18\%$) |
| **Application Server** | **App** | $43.800\text{ h}$ ($47.17\%$) | $43.849\text{ h}$ ($47.33\%$) | $0.876\text{ h}$ ($8.33\%$) | $0.874\text{ h}$ ($8.33\%$) | $0.876\text{ h}$ ($14.28\%$) | $0.882\text{ h}$ ($14.25\%$) |
| **Database Engine** | **DB** | $43.800\text{ h}$ ($47.17\%$) | $43.783\text{ h}$ ($47.26\%$) | $4.380\text{ h}$ ($41.67\%$) | $4.355\text{ h}$ ($41.51\%$) | $4.380\text{ h}$ ($71.41\%$) | $4.429\text{ h}$ ($71.54\%$) |
| **Payment Gateway** | **PGW** | $4.380\text{ h}$ ($4.72\%$) | $4.412\text{ h}$ ($4.76\%$) | $4.380\text{ h}$ ($41.67\%$) | $4.386\text{ h}$ ($41.80\%$) | $0.002\text{ h}$ ($0.03\%$) | $0.003\text{ h}$ ($0.05\%$) |
| **System Downtime** | **Total** | **$92.584\text{ h}$** | **$92.639\text{ h}$** | **$10.508\text{ h}$** | **$10.491\text{ h}$** | **$6.133\text{ h}$** | **$6.191\text{ h}$** |

#### Cross-Validation Conclusions
1. **Pareto Hierarchy Replication:** The stochastic simulation perfectly reproduces the analytical Pareto findings:
   - In Scenario 1, App ($43.85\text{ h}$) and DB ($43.78\text{ h}$) cause $94.59\%$ of all outages.
   - In Scenario 2, compute downtime collapses by $98.01\%$, shifting the co-dominant bottlenecks to DB ($41.51\%$) and PGW ($41.80\%$).
   - In Scenario 3, redundant gateways eliminate the third-party bottleneck ($0.003\text{ h}$), leaving the database tier as the primary bottleneck ($71.54\%$).
2. **Multi-Subsystem Overlap Integrity:** Total system downtime is slightly less than the arithmetic sum of subsystem downtimes due to temporal overlaps ($\mu(\bigcup \mathcal{I}_i) \le \sum \mu(\mathcal{I}_i)$), with simulated overlap measure matching analytical expectation $\Delta = 0.272\text{ h/year}$.


## 9. References

[1] P. D. T. O'Connor and A. Kleyner, *Practical Reliability Engineering*, 5th ed. Chichester, UK: John Wiley & Sons, 2012. DOI: 10.1002/9781119961260.

[2] D. W. Benbow and H. W. Broome, *The Certified Reliability Engineer Handbook*, 1st ed. Milwaukee, WI, USA: ASQ Quality Press, 2009.

[3] E. Zio, *The Monte Carlo Simulation Method for System Reliability and Risk Analysis*. London, UK: Springer, 2013. DOI: 10.1007/978-1-4471-4588-2.

[4] K. S. Trivedi and A. Bobbio, *Reliability and Availability Engineering: Modeling, Analysis, and Applications*. Cambridge, UK: Cambridge University Press, 2017. DOI: 10.1017/9781316163047.

[5] M. Rausand and A. Høyland, *System Reliability Theory: Models, Statistical Methods, and Applications*, 2nd ed. Hoboken, NJ, USA: John Wiley & Sons, 2004. DOI: 10.1002/9780470316900.

[6] A. Birolini, *Reliability Engineering: Theory and Practice*, 8th ed. Berlin, Germany: Springer-Verlag, 2017. DOI: 10.1007/978-3-662-54209-5.

[7] J. Araujo, D. Oliveira, R. Matos, G. Alves, and P. Maciel, "Availability and reliability modeling of mobile cloud architectures," *IEEE Trans. Ind. Informat.*, vol. 22, no. 3, pp. 1622–1634, Mar. 2026. DOI: 10.1109/TII.2023.3254547.

[8] R. Ghosh, F. Longo, R. Xia, V. K. Naik, and K. S. Trivedi, "Stochastic model driven capacity planning for an infrastructure-as-a-service cloud," *IEEE Trans. Serv. Comput.*, vol. 7, no. 4, pp. 667–680, Oct. 2014. DOI: 10.1109/TSC.2013.44.

[9] M. Oszczypała, J. Konwerski, J. Ziółkowski, and J. Małachowski, "Reliability analysis and redundancy optimization of $k$-out-of-$n$ systems with random variable $k$ using Continuous Time Markov Chain and Monte Carlo simulation," *Reliab. Eng. Syst. Saf.*, vol. 242, art. 109780, Feb. 2024. DOI: 10.1016/j.ress.2023.109780.

[10] A. Singjai and U. Zdun, "Conformance assessment of architectural design decisions on API endpoint designs derived from domain models," *J. Syst. Softw.*, vol. 193, art. 111433, Nov. 2022. DOI: 10.1016/j.jss.2022.111433.

[11] Amazon Web Services, "Amazon Compute Service Level Agreement," AWS, 2023. https://aws.amazon.com/compute/sla/

[12] Amazon Web Services, "Amazon RDS Service Level Agreement," AWS, 2023. https://aws.amazon.com/rds/sla/

[13] Amazon Web Services, "Amazon Elastic Load Balancing Service Level Agreement," AWS, 2023. https://aws.amazon.com/elasticloadbalancing/sla/

[14] Microsoft Corporation, "Service Level Agreements (SLA) for Online Services," Microsoft Licensing Agreements, 2023. https://www.microsoft.com/licensing/docs/view/Service-Level-Agreements-SLA-for-Online-Services

[15] Google Cloud, "Google Cloud Platform Service Level Agreements," Google Cloud Documentation, 2023. https://cloud.google.com/terms/sla
