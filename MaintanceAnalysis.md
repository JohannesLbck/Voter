## Maintenance Analysis

To evaluate maintenance effort, we qualitatively assess the amount of manual work $W$ required to ensure compliance when handling changes. We denote the $W$ needed when using VOTER as $W_v$, and the $W$ needed without outsourcing, i.e., when enforcing explicitly, as $W_e$. We differentiate between A) changes to the model and B) changes to constraints, and further differentiate B1) adding a constraint, B2) deleting a constraint, and B3) changing a constraint.

**A) Model changes:** An extensive analysis of $W_v$ and $W_e$ for each potential change type is beyond the scope of this paper. However, as long as we assume that $W$ is independent of the date at which it is performed, we can ensure that, in the worst case, $W_v = W_e$ holds, since the explicit process is never lost in the transformation. The assumption accounts for potential *tech debt* that can arise when constraints change between the model transformation and the model itself. When using VOTER, constraint changes automatically add, remove, or modify helper instances that are invoked at run time. Accordingly, the overall process behavior differs from that of the original pre-transformation process. As such, the amount of *tech debt* is equal to $W_e$, but required at the moment of the model change, rather than being spread out over time. An algorithm that transforms any $M'$ back to $M$ can prevent this problem.

Table: Effort comparison when constraint parameters change

| **Constraint** | **A** | **B** | **C** | **t** |
| --- | --- | --- | --- | --- |
| `event_between(A, B, C)` | = | = | = | --- |
| `max_exec_time(A, t)` | $\ll$ | --- | --- | $<$ |
| `recurring(A, B, t)` | $\ll$ | $<$ | --- | $<$ |
| `max_time_between(A, B, t)` | $<$ | $<$ | --- | $<$ |
| `min_exec_time(A, t)` | $\ll$ | --- | --- | $<$ |

**B1) Adding a constraint** leads to $W_v < W_e$, since only the endpoints have to be defined, without considering where they have to fit into the process model.

**B2) Deleting a constraint:** For the `exec_time` and `time_between` CP, deleting a CP leads to $W_v < W_e$, as the timeouts/parallels are automatically removed, such that the process model does not have to be manually adjusted to prevent overcompliance~\cite{DBLP:conf/coopis/LoebbeckeR25}. However, deleting a `event_between(A,B,C)` CP while using VOTER can lead to undesired behavior: `C` is automatically removed from the process, even if it should still be executed for compliance-unrelated reasons.

**B3) Changing Constraint Parameters:** For constraint parameter changes, $W$ depends on the constraint and which parameter is modified. A $\ll$ entry in Table~\ref{tab:changes} means that changing this parameter leads to $W_v \ll W_e$, with $\ll$ implying a larger difference than $<$.

Conclusively, our approach does not increase maintenance effort and, in most cases, reduces it. However, a transformation algorithm that transforms TCS-enabled processes back to explicit processes to prevent tech debt is still missing.
