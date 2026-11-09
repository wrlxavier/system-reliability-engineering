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


## 7. References

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
