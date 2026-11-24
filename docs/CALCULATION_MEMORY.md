# Calculation Memory: Analytical Availability and Reliability Block Diagrams (RBD)

This document provides a concise calculation memory (*memória de cálculo*) for the analytical availability modeling of the cloud payment processing architecture.


## 1. System Parameterization and Constant Failure/Repair Rates

Each functional subsystem operates in the useful-life region of the bathtub curve (constant hazard rate, $\beta = 1$). Under constant failure rate $\lambda_i = 1/\text{MTBF}_i$ and constant repair rate $\mu_i = 1/\text{MTTR}_i$, the steady-state availability $A_i$ is given by [1], [4]:

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

> [!NOTE]
> **Technical Justification: Multi-AZ Database Modeling (`sla_subsystem` vs. Pure Parallel)**  
> In the analytical and simulation formulations, the redundant database tier is parameterized with $A_{3,\text{red}} = 0.9995$ ($D = 4.38\text{ h/year}$), corresponding to official cloud Service Level Agreements for managed Multi-AZ deployments (e.g., AWS RDS Multi-AZ SLA [12], Google Cloud Cloud SQL HA [15]).
>
> A naive combinatorial assumption of two purely independent parallel database instances would yield $A_{\text{DB,parallel}} = 1 - (1 - A_3)^2 = 1 - (0.005)^2 = 0.999975$ ($D \approx 1.33\text{ h/year}$). However, this assumption is physically and architecturally invalid for transactional relational database management systems (RDBMS) because:
> 1. **Synchronous State Replication:** Write transactions require synchronous commit protocols across Availability Zones, meaning instances share synchronous replication channels and state dependencies.
> 2. **Failure Detection and Heartbeat Latency:** When the primary DB node fails, automated health checks require 30 to 60 seconds to declare an unrecoverable failure and prevent split-brain conditions.
> 3. **Failover Promotion and DNS Propagation:** Promoting the standby replica to primary and repointing client connection pools (updating DNS CNAME records or cluster endpoints) introduces an unavoidable operational interruption of 60 to 120 seconds.
>
> Therefore, adopting the contractual SLA benchmark of $99.95\%$ (`sla_subsystem` mode) realistically incorporates the intrinsic switching and failover penalties of stateful transactional persistence, avoiding overly optimistic availability estimates.

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


### 5.5 Analytical MTTF Gain Quantification

The comparative gain achieved by migrating from Scenario 1 (Baseline Pure Series) to Scenario 2 (Multi-AZ Series-Parallel) is:

- **Absolute MTTF Gain:**
  $$\Delta\text{MTTF} = \text{MTTF}_{\text{red}} - \text{MTTF}_{\text{base}} = 106.057027 - 60.694649 = \mathbf{45.362378\text{ hours}} \approx \mathbf{45.36\text{ hours}}$$

- **Relative MTTF Improvement Percentage:**
  $$\text{Gain}_{\text{MTTF}} = \frac{\Delta\text{MTTF}}{\text{MTTF}_{\text{base}}} \times 100\% = \frac{45.362378}{60.694649} \times 100\% = \mathbf{74.7387\%} \approx \mathbf{74.74\%}$$

- **MTTF Multiplication Factor:**
  $$\frac{\text{MTTF}_{\text{red}}}{\text{MTTF}_{\text{base}}} = \frac{106.057027}{60.694649} = \mathbf{1.7474\times}$$

At $t = \text{MTTF}_{\text{base}} = 60.69\text{ h}$, the redundant system preserves a survival probability of $R_{\text{red}}(60.69) = \mathbf{61.20\%}$ (compared to only $36.79\%$ for the baseline series).

> [!IMPORTANT]
> **Boundary Premise: Mission Reliability $R(t)$ vs. Steady-State Availability $A$**  
> The analytical derivation of $R_{\text{red}}(t)$ and the resulting $\text{MTTF}_{\text{red}} = 106.06\text{ hours}$ model a non-repairable mission profile **without maintenance or component restoration during the mission interval $[0, t]$**. That is, $R(t)$ measures the probability that no single unrecovered system crash occurs up to time $t$.  
>  
> In continuous commercial cloud operations, automated self-healing, instance replacement, and online replica rebuilds occur continuously. Thus, $\text{MTTF}_{\text{red}}$ represents a **conservative lower bound** for uninterrupted mission capability (useful for uninterrupted transaction batch windows or peak shopping intervals like Black Friday), and must not be confused with steady-state operational availability ($A_{\text{red}} = 99.88\%$), which accounts for continuous failure and repair cycles and yields an expected annual uptime of $8749.49\text{ hours/year}$ in the presence of continuous automated repairs.


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


## 7. Subsystem Percentage Contribution to Unavailability and Bottleneck Identification

Quantifying the percentage contribution of each architectural tier to total downtime identifies the primary single points of failure (SPOFs) in the baseline design and reveals how bottlenecks shift when redundancy is introduced [1], [7].

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

#### 7.1.2 Percentage Downtime Contribution and Cumulative Ranking
Subsystems are sorted in descending order of individual downtime: $D_{(1)} \ge D_{(2)} \ge \dots \ge D_{(n)}$.

The individual percentage share of total subsystem downtime is:

$$p_i = \frac{D_i}{\sum_{j=1}^n D_j} \times 100\% = \frac{U_i}{\sum_{j=1}^n U_j} \times 100\%$$

The cumulative percentage share $C_k$ for the top $k$ contributors is:

$$C_k = \sum_{j=1}^k p_{(j)} = \frac{\sum_{j=1}^k D_{(j)}}{\sum_{j=1}^n D_j} \times 100\%, \quad C_n = 100\%$$

The proportionally allocated share of exact system downtime is:

$$D_{i, \text{alloc}} = \frac{D_i}{D_{\text{sum}}} \times D_{\text{sys}} = \frac{p_i}{100} \times D_{\text{sys}}$$


### 7.2 Scenario 1 Subsystem Contribution (Baseline Pure Series)

In Scenario 1, every subsystem is an unredundant Single Point of Failure (SPOF):

| Rank | Block Code | Subsystem Name | Architectural Tier | Availability ($A_i$) | Unavailability ($U_i$) | Standalone Downtime ($D_i$) | Share ($p_i$) | Cumulative Share ($C_k$) | Allocated Downtime ($D_{i,\text{alloc}}$) |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | **App** | Application Server | Business Logic | $99.5000\%$ | $5000\text{ ppm}$ | $43.8000\text{ h/yr}$ | $\mathbf{47.17\%}$ | $47.17\%$ | $43.6718\text{ h/yr}$ |
| **2** | **DB** | Relational Database | Data Persistence | $99.5000\%$ | $5000\text{ ppm}$ | $43.8000\text{ h/yr}$ | $\mathbf{47.17\%}$ | $\mathbf{94.34\%}$ | $43.6718\text{ h/yr}$ |
| **3** | **PGW** | Payment Gateway | External Settlement | $99.9500\%$ | $500\text{ ppm}$ | $4.3800\text{ h/yr}$ | $4.72\%$ | $99.06\%$ | $4.3672\text{ h/yr}$ |
| **4** | **LB** | Load Balancer | Ingress Routing | $99.9900\%$ | $100\text{ ppm}$ | $0.8760\text{ h/yr}$ | $0.94\%$ | $100.00\%$ | $0.8734\text{ h/yr}$ |
| **Total** | — | **Full System (Pure Series)** | — | **$98.9431\%$** | **$10569\text{ ppm}$** | **$92.8560\text{ h/yr}$** | **$100.00\%$** | — | **$92.5841\text{ h/yr}$** |

**Core Analytical Insight (S1):**
- **App and DB combined represent $94.34\%$** of all system downtime ($87.60\text{ hours/year}$ out of $92.86\text{ hours}$).
- Mitigating solely these top two internal tiers eliminates $>94\%$ of the reliability penalty.


### 7.3 Scenario 2 Subsystem Contribution (Multi-AZ Series-Parallel)

With active Multi-AZ redundancy deployed across Application instances ($A_{2,\text{red}} = 99.99\%$) and Database synchronous replication ($A_{3,\text{red}} = 99.95\%$):

| Rank | Block Code | Subsystem Name | Architectural Tier | Availability ($A_i$) | Unavailability ($U_i$) | Standalone Downtime ($D_i$) | Share ($p_i$) | Cumulative Share ($C_k$) | Allocated Downtime ($D_{i,\text{alloc}}$) |
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


### 7.4 Scenario 3 Subsystem Contribution (Multi-Gateway Expansion)

Incorporating active parallel redundancy on the external Payment Gateway ($A_{4,\text{red}} = 99.999975\%$):

| Rank | Block Code | Subsystem Name | Architectural Tier | Availability ($A_i$) | Unavailability ($U_i$) | Standalone Downtime ($D_i$) | Share ($p_i$) | Cumulative Share ($C_k$) | Allocated Downtime ($D_{i,\text{alloc}}$) |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | **DB** | Relational Database | Multi-AZ Failover | $99.9500\%$ | $500\text{ ppm}$ | $4.3800\text{ h/yr}$ | $\mathbf{71.41\%}$ | $\mathbf{71.41\%}$ | $4.3793\text{ h/yr}$ |
| **2** | **LB** | Load Balancer | Ingress Routing | $99.9900\%$ | $100\text{ ppm}$ | $0.8760\text{ h/yr}$ | $14.28\%$ | $85.69\%$ | $0.8759\text{ h/yr}$ |
| **3** | **App** | Application Server | Multi-AZ Active-Active | $99.9900\%$ | $100\text{ ppm}$ | $0.8760\text{ h/yr}$ | $14.28\%$ | $99.96\%$ | $0.8759\text{ h/yr}$ |
| **4** | **PGW** | Payment Gateway | Dual Active-Active Gateways | $99.999975\%$ | $0.25\text{ ppm}$ | $0.00219\text{ h/yr}$ ($7.88\text{ s}$) | $\mathbf{0.04\%}$ | $100.00\%$ | $0.00219\text{ h/yr}$ |
| **Total** | — | **Full System (Multi-Gateway)** | — | **$99.9300\%$** | **$700\text{ ppm}$** | **$6.1342\text{ h/yr}$** | **$100.00\%$** | — | **$6.1332\text{ h/yr}$** |

**Core Analytical Insight (S3):**
- Dual payment gateway routing virtually eliminates external dependency risk, reducing PGW downtime from $4.38\text{ h}$ to $\mathbf{7.88\text{ seconds/year}}$ ($\mathbf{99.95\%\text{ reduction}}$).
- Transactional Database failover ($4.38\text{ h/yr}$) now accounts for $\mathbf{71.41\%}$ of all remaining downtime, becoming the primary bottleneck of the architecture.


### 7.5 Quantitative Summary of Bottleneck Shifts

The table below contrasts the distribution of annual downtime across the three architectural configurations:

| Subsystem / Metric | Scenario 1 (Baseline Series) | Scenario 2 (Multi-AZ Series-Parallel) | Scenario 3 (Multi-Gateway Expansion) | Shift Trend & Engineering Implication |
| :--- | :---: | :---: | :---: | :--- |
| **Application Server (App)** | $43.80\text{ h}$ ($47.17\%$) | $0.88\text{ h}$ ($8.33\%$) | $0.88\text{ h}$ ($14.28\%$) | Slashed by $98.0\%$; eliminated as primary SPOF |
| **Transactional Database (DB)** | $43.80\text{ h}$ ($47.17\%$) | $4.38\text{ h}$ ($41.67\%$) | $4.38\text{ h}$ ($\mathbf{71.41\%}$) | Reduced by $90.0\%$; becomes primary remaining bottleneck |
| **Internal Tiers Combined (App + DB)** | **$87.60\text{ h}$ ($94.34\%$)** | **$5.26\text{ h}$ ($50.00\%$)** | **$5.26\text{ h}$ ($85.69\%$)** | Internal downtime reduced by $94.0\%$ |
| **Payment Gateway (PGW)** | $4.38\text{ h}$ ($4.72\%$) | $4.38\text{ h}$ ($\mathbf{41.67\%}$) | $0.002\text{ h}$ ($0.04\%$) | Relative share surged $8.8\times$ in S2; eliminated in S3 |
| **Load Balancer (LB)** | $0.88\text{ h}$ ($0.94\%$) | $0.88\text{ h}$ ($8.33\%$) | $0.88\text{ h}$ ($14.28\%$) | Constant managed infrastructure baseline |
| **Top 2 Contributors Combined ($C_2$)** | **$94.34\%$** (App, DB) | **$83.33\%$** (DB, PGW) | **$85.69\%$** (DB, LB) | Concentration of downtime shifts across layers |
| **Total System Downtime** | **$92.58\text{ h/year}$** | **$10.51\text{ h/year}$** | **$6.13\text{ h/year}$** | **$93.38\%\text{ total downtime reduction}$** |


## 8. Monte Carlo Simulation and Statistical Estimation

Monte Carlo simulation cross-validates the closed-form analytical models over an annual operational horizon $T = 8760\text{ hours}$ ($525{,}600\text{ minutes}$) across $N = 10^4$ independent simulated years [3], [6], [9].


### 8.1 Continuous-Time Failure and Repair Cycle Modeling

Each functional subsystem $i \in \{\text{LB}, \text{App}, \text{DB}, \text{PGW}\}$ alternates between operational and repair periods governed by two independent exponential random variables:
1. **Time to Failure ($\text{TTF}_i$):** Distributed exponentially with constant failure rate $\lambda_i > 0$:
   $$F_i(t) = P(\text{TTF}_i \le t) = 1 - e^{-\lambda_i t}, \quad f_i(t) = \lambda_i e^{-\lambda_i t}, \quad \mathbb{E}[\text{TTF}_i] = \text{MTBF}_i = \frac{1}{\lambda_i}$$
2. **Time to Repair ($\text{TTR}_i$):** Distributed exponentially with constant repair rate $\mu_i > 0$:
   $$G_i(t) = P(\text{TTR}_i \le t) = 1 - e^{-\mu_i t}, \quad g_i(t) = \mu_i e^{-\mu_i t}, \quad \mathbb{E}[\text{TTR}_i] = \text{MTTR}_i = \frac{1}{\mu_i}$$

Pseudo-random durations are generated via Inverse Transform Sampling parameterized by uniform random numbers $u, v \sim \mathcal{U}(0, 1)$ initialized with a fixed seed (`seed = 2026`):
$$\text{TTF} = -\frac{\ln(1 - u)}{\lambda_i}, \quad \text{TTR} = -\frac{\ln(1 - v)}{\mu_i}$$

For each simulated year $k \in \{1, \dots, N\}$, the sequence of failure and repair cycles produces an ordered set of disjoint outage intervals within $[0, T]$:
$$\mathcal{I}_i^{(k)} = \bigcup_{j=1}^{M_i^{(k)}} \left[ t_{\text{fail}, j}^{(i, k)}, \min\left(t_{\text{restored}, j}^{(i, k)}, T\right) \right) \subset [0, T]$$


### 8.2 System State Evaluation via Outage Interval Union and Intersection

System outages over $[0, T]$ are obtained directly from the component outage intervals:

1. **Pure Series System (Scenario 1):**
   The payment pipeline fails whenever *any* subsystem is down. Thus, the system outage set is the union of all constituent outage intervals:
   $$\mathcal{I}_{\text{base}}^{(k)} = \bigcup_{i=1}^4 \mathcal{I}_i^{(k)}$$
   Because outages can temporally overlap across independent subsystems, merging overlapping intervals avoids double counting, and total annual downtime is the sum of the disjoint merged interval durations:
   $$D_{\text{base}}^{(k)} = \sum_{m} \left( \text{end}_m - \text{start}_m \right)$$
   This naturally captures the overlapping outage term $\Delta = 0.2719\text{ h/year}$ derived in Section 7.1.1.

2. **Active Parallel Redundancy (1-out-of-2):**
   A parallel subsystem of two independent units is unavailable only when both units are simultaneously down (temporal intersection):
   $$\mathcal{I}_{\text{parallel}}^{(k)} = \mathcal{I}_{\text{unit 1}}^{(k)} \cap \mathcal{I}_{\text{unit 2}}^{(k)}$$

3. **Series-Parallel Architecture (Scenario 2 and Scenario 3):**
   The overall system outage set is the union of the stage outage sets across the pipeline:
   $$\mathcal{I}_{\text{sys}}^{(k)} = \mathcal{I}_{\text{LB}}^{(k)} \cup \mathcal{I}_{\text{App,tier}}^{(k)} \cup \mathcal{I}_{\text{DB,tier}}^{(k)} \cup \mathcal{I}_{\text{PGW,tier}}^{(k)}$$
   Under contractual SLA parameterization ($A_{2,\text{red}} = 99.99\%$, $A_{3,\text{red}} = 99.95\%$, $A_{4,\text{red}} = 99.999975\%$), the effective transition rates directly calibrate the simulation to the analytical benchmarks.


### 8.3 Statistical Estimators and Student's $t$ Confidence Intervals

For each simulated year $k \in \{1, \dots, N\}$, the operational availability fraction is:
$$A_k = \frac{T_{\text{operational}, k}}{T} = \frac{T - D_k}{T} = 1 - \frac{D_k}{T}, \quad \text{where } T = 8760\text{ hours}$$

The point estimator for mean system availability is the sample mean [3]:
$$\hat{A} = \frac{1}{N} \sum_{k=1}^N A_k = \frac{1}{N} \sum_{k=1}^N \frac{T_{\text{operational}, k}}{T_{\text{operational}, k} + T_{\text{down}, k}} = 1 - \frac{\hat{D}}{T}$$

The point estimator for expected annual downtime is:
$$\hat{D} = \frac{1}{N} \sum_{k=1}^N D_k$$

The unbiased sample variances are:
$$s_A^2 = \frac{1}{N - 1} \sum_{k=1}^N \left(A_k - \hat{A}\right)^2, \quad s_D^2 = \frac{1}{N - 1} \sum_{k=1}^N \left(D_k - \hat{D}\right)^2 = T^2 s_A^2$$

The Standard Error of the Mean (SEM) is:
$$\text{SE}(\hat{A}) = \frac{s_A}{\sqrt{N}}, \quad \text{SE}(\hat{D}) = \frac{s_D}{\sqrt{N}}$$

#### Bilateral 95% Confidence Interval (Student's $t$-Distribution)
For a bilateral confidence level $1 - \alpha = 0.95$ ($\alpha = 0.05$) and $N - 1 = 9{,}999$ degrees of freedom, the two-tailed Student's $t$ critical value is $t_{9999, 0.975} = 1.960204$:
$$\text{CI}_{95\%}(\hat{A}) = \left[ \hat{A} - t_{N-1, 0.975} \frac{s_A}{\sqrt{N}}, \quad \hat{A} + t_{N-1, 0.975} \frac{s_A}{\sqrt{N}} \right]$$
$$\text{CI}_{95\%}(\hat{D}) = \left[ \hat{D} - t_{N-1, 0.975} \frac{s_D}{\sqrt{N}}, \quad \hat{D} + t_{N-1, 0.975} \frac{s_D}{\sqrt{N}} \right]$$


### 8.4 Relative Percentage Error Formulation

The accuracy of the Monte Carlo estimator against the exact closed-form analytical availability $A$ is quantified through the relative percentage error:
$$\varepsilon_{\text{rel}}(\hat{A}) = \frac{|\hat{A} - A|}{A} \times 100\%$$
$$\varepsilon_{\text{rel}}(\hat{D}) = \frac{|\hat{D} - D|}{D} \times 100\%$$

The acceptance threshold for numerical validation is $\varepsilon_{\text{rel}}(\hat{A}) < 0.05\%$.


### 8.5 Simulation Validation Results Table ($N = 10^4$, Seed = 2026)

The table below contrasts the exact analytical solutions against the Monte Carlo estimates obtained from `src/simulation/monte_carlo.py` (exported to `data/processed/simulation_metrics.csv`):

| Evaluation Metric | Scenario 1 (Baseline Series) | Scenario 2 (Multi-AZ Series-Parallel) | Scenario 3 (Multi-Gateway Expansion) | Acceptance Criterion |
| :--- | :---: | :---: | :---: | :---: |
| **Analytical Availability ($A$)** | **$98.9431\%$** ($0.98943103$) | **$99.8800\%$** ($0.99880046$) | **$99.9300\%$** ($0.99929986$) | Theoretical Benchmark |
| **Simulated Availability ($\hat{A}$)** | **$98.9425\%$** ($0.98942474$) | **$99.8802\%$** ($0.99880240$) | **$99.9293\%$** ($0.99929328$) | Point Estimator |
| **Availability 95% Confidence Interval** | **$[98.9399\%, 98.9451\%]$** | **$[99.8794\%, 99.8811\%]$** | **$[99.9286\%, 99.9300\%]$** | $A \in \text{CI}_{95\%}$ (Contains Theoretical) |
| **Availability Relative Error ($\varepsilon_{\text{rel}}$)** | **$0.00064\%$** | **$0.00019\%$** | **$0.000659\%$** | **$< 0.05\%$ (Passed)** |
| **Analytical Downtime ($D$)** | **$92.58\text{ h/year}$** | **$10.51\text{ h/year}$** | **$6.13\text{ h/year}$** | Theoretical Benchmark |
| **Simulated Downtime ($\hat{D}$)** | **$92.64\text{ h/year}$** | **$10.49\text{ h/year}$** | **$6.19\text{ h/year}$** ($6.1909\text{ h}$) | Point Estimator |
| **Downtime 95% Confidence Interval** | **$[92.41\text{ h}, 92.87\text{ h}]$** | **$[10.42\text{ h}, 10.56\text{ h}]$** | **$[6.13\text{ h}, 6.25\text{ h}]$** | $D \in \text{CI}_{95\%}$ (Contains Theoretical) |
| **Downtime Sample Std Dev ($s_D$)** | $11.55\text{ h}$ | $3.74\text{ h}$ | $3.20\text{ h}$ | Sample Standard Deviation |
| **Standard Error of Mean ($\text{SE}$)** | $0.115\text{ h}$ ($6.93\text{ min}$) | $0.037\text{ h}$ ($2.24\text{ min}$) | $0.032\text{ h}$ ($1.92\text{ min}$) | $\text{SE} = s / \sqrt{10^4}$ |
| **Average Failure Events / Year** | $142.93\text{ events}$ | $18.43\text{ events}$ | $9.71\text{ events}$ | Mean annual failure count |
| **Execution Wall-Clock Time** | **$< 2\text{ seconds}$** | **$< 1\text{ second}$** | **$< 1\text{ second}$** | **$< 60\text{ seconds (Passed)}$** |

*Validation Conclusion:* For all three architectural scenarios, the analytical benchmark lies strictly within the simulated 95% Student's $t$ confidence interval, and the availability relative error is well below the $0.05\%$ threshold ($\le 0.000659\%$), confirming consistency between the analytical formulas and the Monte Carlo simulation.


### 8.6 Monte Carlo Convergence Analysis

Let $A_1, A_2, \dots, A_N$ denote the sequence of independent annual availability values generated across Monte Carlo iterations. The cumulative sample mean sequence is defined as [3]:

$$\hat{A}(n) = \frac{1}{n} \sum_{k=1}^n A_k, \quad \text{for } n \in \{1, 2, \dots, N\}$$

As the number of simulated years $n$ increases, the cumulative sample mean $\hat{A}(n)$ stabilizes around the analytical availability $A_{\text{theo}}$, while the 95% Student's $t$ confidence interval half-width narrows proportionally to $1/\sqrt{n}$:

$$\Delta_n = t_{n-1, 0.975} \frac{s_A(n)}{\sqrt{n}}$$

$$\text{CI}_{95\%}(n) = \left[ \hat{A}(n) - \Delta_n, \quad \hat{A}(n) + \Delta_n \right]$$

where $s_A(n) = \sqrt{\frac{1}{n-1}\sum_{k=1}^n (A_k - \hat{A}(n))^2}$ is the running sample standard deviation.

#### Convergence Milestones ($N = 10^4$, Seed = 2026)

The table below traces the convergence progression at key iteration checkpoints across all three architectural scenarios:

| Checkpoint ($n$) | Metric | Scenario 1 (Baseline Series) | Scenario 2 (Multi-AZ Series-Parallel) | Scenario 3 (Multi-Gateway Expansion) |
| :---: | :--- | :---: | :---: | :---: |
| **$n = 10$** | Cumulative Mean $\hat{A}(n)$<br>95% Margin of Error $\Delta_n$<br>Relative Error $\varepsilon_{\text{rel}}$ | $99.00506\%$<br>$\pm 0.09704\%$<br>$0.06262\%$ | $99.87120\%$<br>$\pm 0.03461\%$<br>$0.00886\%$ | $99.93427\%$<br>$\pm 0.02920\%$<br>$0.00429\%$ |
| **$n = 50$** | Cumulative Mean $\hat{A}(n)$<br>95% Margin of Error $\Delta_n$<br>Relative Error $\varepsilon_{\text{rel}}$ | $98.94312\%$<br>$\pm 0.03340\%$<br>$0.00002\%$ | $99.88591\%$<br>$\pm 0.01135\%$<br>$0.00587\%$ | $99.93756\%$<br>$\pm 0.00856\%$<br>$0.00758\%$ |
| **$n = 100$** | Cumulative Mean $\hat{A}(n)$<br>95% Margin of Error $\Delta_n$<br>Relative Error $\varepsilon_{\text{rel}}$ | $98.93972\%$<br>$\pm 0.02641\%$<br>$0.00342\%$ | $99.88182\%$<br>$\pm 0.00780\%$<br>$0.00178\%$ | $99.93055\%$<br>$\pm 0.00713\%$<br>$0.00056\%$ |
| **$n = 500$** | Cumulative Mean $\hat{A}(n)$<br>95% Margin of Error $\Delta_n$<br>Relative Error $\varepsilon_{\text{rel}}$ | $98.95172\%$<br>$\pm 0.01160\%$<br>$0.00871\%$ | $99.88008\%$<br>$\pm 0.00390\%$<br>$0.00003\%$ | $99.92905\%$<br>$\pm 0.00335\%$<br>$0.00094\%$ |
| **$n = 1{,}000$** | Cumulative Mean $\hat{A}(n)$<br>95% Margin of Error $\Delta_n$<br>Relative Error $\varepsilon_{\text{rel}}$ | $98.95095\%$<br>$\pm 0.00847\%$<br>$0.00793\%$ | $99.88027\%$<br>$\pm 0.00266\%$<br>$0.00023\%$ | $99.92988\%$<br>$\pm 0.00229\%$<br>$0.00011\%$ |
| **$n = 5{,}000$** | Cumulative Mean $\hat{A}(n)$<br>95% Margin of Error $\Delta_n$<br>Relative Error $\varepsilon_{\text{rel}}$ | $98.94412\%$<br>$\pm 0.00367\%$<br>$0.00103\%$ | $99.87979\%$<br>$\pm 0.00120\%$<br>$0.00026\%$ | $99.92923\%$<br>$\pm 0.00102\%$<br>$0.00076\%$ |
| **$n = 10{,}000$** | Cumulative Mean $\hat{A}(n)$<br>95% Margin of Error $\Delta_n$<br>Relative Error $\varepsilon_{\text{rel}}$ | **$98.94247\%$**<br>**$\pm 0.00258\%$**<br>**$0.00064\%$** | **$99.88024\%$**<br>**$\pm 0.00084\%$**<br>**$0.00019\%$** | **$99.92933\%$**<br>**$\pm 0.00072\%$**<br>**$0.00066\%$** |
| **Benchmark ($A_{\text{theo}}$)** | Analytical Availability | **$98.94310\%$** | **$99.88005\%$** | **$99.92999\%$** |

*Convergence Conclusion:* For all configurations, relative error falls below $0.01\%$ for $n \ge 500$ iterations and achieves sub-$0.001\%$ precision at $N = 10^4$, confirming numerical stability of the $N = 10^4$ sample size.


### 8.7 Simulated Annual Downtime Distribution

Annual downtime $D_k = \sum_m (\text{end}_m - \text{start}_m)$ varies from year to year across the $N = 10^4$ simulated horizons:

1. **Scenario 1 (Baseline Pure Series):**
   Outages occur across all four unredundant blocks ($\Lambda = \sum_{i=1}^4 \lambda_i = 16.476 \times 10^{-3}\text{ h}^{-1}$), producing an average of $142.93$ failure events per year with simulated mean $\hat{D} = 92.64\text{ h/year}$ and standard deviation $s_D = 11.55\text{ h/year}$.
2. **Scenario 2 (Multi-AZ Series-Parallel):**
   Active redundancy reduces internal outages substantially, leaving an average of $18.43$ failure events per year with simulated mean $\hat{D} = 10.49\text{ h/year}$ and standard deviation $s_D = 3.74\text{ h/year}$.
3. **Scenario 3 (Multi-Gateway Expansion):**
   With dual external payment gateways, third-party outages become negligible ($\approx 0.003\text{ h/yr}$), leaving an average of $9.71$ failure events per year (driven mainly by database failovers) with simulated mean $\hat{D} = 6.19\text{ h/year}$ and standard deviation $s_D = 3.20\text{ h/year}$.

#### Annual Downtime Descriptive Summary and Percentiles Table

| Statistical Metric | Scenario 1 (Baseline Series) | Scenario 2 (Multi-AZ Series-Parallel) | Scenario 3 (Multi-Gateway Expansion) | Interpretation |
| :--- | :---: | :---: | :---: | :--- |
| **Analytical Mean ($D$)** | **$92.58\text{ h/year}$** | **$10.51\text{ h/year}$** | **$6.13\text{ h/year}$** | Analytical expectation |
| **Simulated Mean ($\hat{D}$)** | **$92.64\text{ h/year}$** | **$10.49\text{ h/year}$** | **$6.19\text{ h/year}$** | Sample average over $10^4$ years |
| **Standard Deviation ($s_D$)** | $11.55\text{ h/year}$ | $3.74\text{ h/year}$ | $3.20\text{ h/year}$ | Sample dispersion |
| **Median ($p_{50}$)** | $92.16\text{ h/year}$ | $10.12\text{ h/year}$ | $5.73\text{ h/year}$ | 50% of simulated years |
| **90th Percentile ($p_{90}$)** | $107.72\text{ h/year}$ | $15.53\text{ h/year}$ | $10.51\text{ h/year}$ | 90% of simulated years |
| **95th Percentile ($D_{0.95}$)** | **$112.21\text{ h/year}$** | **$17.17\text{ h/year}$** | **$12.07\text{ h/year}$** | 95% of simulated years |
| **99th Percentile ($D_{0.99}$)** | **$121.15\text{ h/year}$** | **$20.85\text{ h/year}$** | **$15.45\text{ h/year}$** | 99% of simulated years |
| **Minimum Observed** | $53.52\text{ h/year}$ | $1.14\text{ h/year}$ | $0.06\text{ h/year}$ | Best-case simulated year |
| **Maximum Observed** | $138.15\text{ h/year}$ | $29.04\text{ h/year}$ | $23.24\text{ h/year}$ | Worst-case simulated year |

*Distribution Finding:* Multi-AZ redundancy reduces the 95th percentile annual downtime from $112.21\text{ h}$ to $17.17\text{ h}$ ($-84.7\%$), and Multi-Gateway expansion lowers it further to $12.07\text{ h}$.


### 8.8 Simulated Subsystem Downtime Breakdown and Cross-Validation

The simulation records individual outage intervals $\mathcal{I}_i^{(k)}$ per subsystem $i \in \{\text{LB}, \text{App}, \text{DB}, \text{PGW}\}$. The simulated mean subsystem downtime is:

$$\hat{D}_i = \frac{1}{N} \sum_{k=1}^N D_{i, k}$$

The table below contrasts the analytical downtime contributions against the simulated Monte Carlo subsystem averages:

| Architectural Tier | Subsystem Code | Scenario 1 Analytical ($D_i$) | Scenario 1 Simulated ($\hat{D}_i$) | Scenario 2 Analytical ($D_i$) | Scenario 2 Simulated ($\hat{D}_i$) | Scenario 3 Analytical ($D_i$) | Scenario 3 Simulated ($\hat{D}_i$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Load Balancer** | **LB** | $0.876\text{ h}$ ($0.94\%$) | $0.867\text{ h}$ ($0.94\%$) | $0.876\text{ h}$ ($8.33\%$) | $0.882\text{ h}$ ($8.40\%$) | $0.876\text{ h}$ ($14.28\%$) | $0.878\text{ h}$ ($14.18\%$) |
| **Application Server** | **App** | $43.800\text{ h}$ ($47.17\%$) | $43.849\text{ h}$ ($47.33\%$) | $0.876\text{ h}$ ($8.33\%$) | $0.874\text{ h}$ ($8.33\%$) | $0.876\text{ h}$ ($14.28\%$) | $0.882\text{ h}$ ($14.25\%$) |
| **Database Engine** | **DB** | $43.800\text{ h}$ ($47.17\%$) | $43.783\text{ h}$ ($47.26\%$) | $4.380\text{ h}$ ($41.67\%$) | $4.355\text{ h}$ ($41.51\%$) | $4.380\text{ h}$ ($71.41\%$) | $4.429\text{ h}$ ($71.54\%$) |
| **Payment Gateway** | **PGW** | $4.380\text{ h}$ ($4.72\%$) | $4.412\text{ h}$ ($4.76\%$) | $4.380\text{ h}$ ($41.67\%$) | $4.386\text{ h}$ ($41.80\%$) | $0.002\text{ h}$ ($0.03\%$) | $0.003\text{ h}$ ($0.05\%$) |
| **System Downtime** | **Total** | **$92.584\text{ h}$** | **$92.639\text{ h}$** | **$10.508\text{ h}$** | **$10.491\text{ h}$** | **$6.133\text{ h}$** | **$6.191\text{ h}$** |

#### Cross-Validation Conclusions
1. **Subsystem Contribution & Bottleneck Replication:** The simulation reproduces the analytical subsystem contributions and bottleneck shifts across all scenarios:
   - In Scenario 1, App ($43.85\text{ h}$) and DB ($43.78\text{ h}$) cause $94.59\%$ of all outages.
   - In Scenario 2, compute downtime drops by $98.01\%$, shifting the main bottlenecks to DB ($41.51\%$) and PGW ($41.80\%$).
   - In Scenario 3, redundant gateways eliminate the external bottleneck ($0.003\text{ h}$), leaving the database tier as the primary bottleneck ($71.54\%$).
2. **Non-Double-Counting of Overlapping Outages:** Total system downtime is slightly smaller than the sum of individual subsystem downtimes because overlapping outage intervals are merged into a union without double counting, matching the analytical overlap term $\Delta = 0.272\text{ h/year}$ in Scenario 1.


## 9. Scenario 3: Multi-Gateway Active Parallel Architecture

Scenario 3 expands the fault-tolerant architecture by addressing the external dependency bottleneck identified in Scenario 2. In Scenario 2, while internal compute and database tiers achieved high availability via Multi-AZ clustering, the external Payment Gateway (PGW) was left unredundant with SLA $A_4 = 99.95\%$. Consequently, PGW became co-dominant with the database tier, accounting for $41.67\%$ of all residual downtime ($4.38\text{ h/year}$).

Scenario 3 introduces active parallel redundancy across two independent external payment service providers (e.g., Stripe and Adyen) [10].


### 9.1 Multi-Gateway Parallel Availability Formulation

Let $A_4$ represent the steady-state availability of a single third-party payment gateway. Under active-active parallel operation, a payment transaction can be successfully processed if at least one gateway is operational.

Assuming independent failures between distinct payment service providers:

$$A_{4,\text{red}} = 1 - (1 - A_4)^2$$

For nominal commercial FinTech API SLAs ($A_4 = 0.9995$, $U_4 = 0.0005$):

$$A_{4,\text{red}} = 1 - (0.0005)^2 = 1 - 0.00000025 = \mathbf{0.99999975 \implies 99.999975\%}$$

$$U_{4,\text{red}} = 1 - A_{4,\text{red}} = 2.5 \times 10^{-7} \implies \mathbf{0.25\text{ ppm}}$$

The standalone expected annual downtime for the redundant payment gateway subsystem drops to:

$$D_{4,\text{red}} = U_{4,\text{red}} \times 8760\text{ h/year} = 2.5 \times 10^{-7} \times 8760 = 0.00219\text{ h/year} = \mathbf{7.884\text{ seconds/year}}$$

Compared to the single-gateway downtime of $4.380\text{ h/year}$, active parallel redundancy eliminates:

$$\Delta D_4 = 4.380 - 0.00219 = \mathbf{4.3778\text{ h/year saved}} \quad (\mathbf{99.95\%\text{ reduction}})$$


### 9.2 End-to-End System Availability and Downtime Evaluation

In Scenario 3, the complete payment pipeline topology is:

$$\text{Ingress} \longrightarrow [\text{LB}] \longrightarrow \begin{bmatrix} \text{App}_1 \\ \parallel \\ \text{App}_2 \end{bmatrix} \longrightarrow \begin{bmatrix} \text{DB}_1 \\ \parallel \\ \text{DB}_2 \end{bmatrix} \longrightarrow \begin{bmatrix} \text{PGW}_A \\ \parallel \\ \text{PGW}_B \end{bmatrix} \longrightarrow \text{Egress}$$

$$A_{\text{scen3}} = A_1 \cdot A_{2,\text{red}} \cdot A_{3,\text{red}} \cdot A_{4,\text{red}}$$

Substituting nominal values:
- $A_1 = 0.9999$ (Load Balancer)
- $A_{2,\text{red}} = 0.9999$ (Application Tier Multi-AZ)
- $A_{3,\text{red}} = 0.9995$ (Database Multi-AZ HA)
- $A_{4,\text{red}} = 0.99999975$ (Dual Active Gateways)

$$A_{\text{internal}} = A_1 \cdot A_{2,\text{red}} \cdot A_{3,\text{red}} = 0.9999 \times 0.9999 \times 0.9995 = 0.99930014995$$

$$A_{\text{scen3}} = 0.99930014995 \times 0.99999975 = \mathbf{0.9992998602 \implies 99.930\%}$$

$$U_{\text{scen3}} = 1 - A_{\text{scen3}} = 0.0007001398 \implies \mathbf{0.07001\%}$$

$$D_{\text{scen3}} = 0.0007001398 \times 8760\text{ h} = \mathbf{6.1332\text{ h/year}} \approx \mathbf{6.13\text{ h/year}} \quad (368.00\text{ min/year})$$

#### Comparative Gains Summary
- **Versus Scenario 1 (Baseline Series, $92.58\text{ h/year}$):**
  $$\Delta D = 92.5841 - 6.1332 = \mathbf{86.4509\text{ h/year saved}} \implies \mathbf{93.38\%\text{ overall downtime reduction}}$$
- **Versus Scenario 2 (Multi-AZ Core, $10.5080\text{ h/year}$):**
  $$\Delta D = 10.5080 - 6.1332 = \mathbf{4.3748\text{ h/year saved}} \implies \mathbf{41.63\%\text{ additional downtime reduction}}$$

After introducing dual-gateway redundancy, the external payment gateway contribution drops to $0.00219\text{ h/year}$ ($0.04\%$), leaving the Multi-AZ database ($4.38\text{ h/year}$, $71.41\%$ of total downtime) as the primary remaining bottleneck.


## 10. References

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
