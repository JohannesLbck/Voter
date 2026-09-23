\subsection{Maintenance Analysis}
To evaluate maintenance effort, we qualitatively assess the amount of manual work $W$ required to ensure compliance when handling changes. We denote the $W$ needed when using VOTER as $W_v$, and the $W$ needed without outsourcing, i.e., when enforcing explicitly, as $W_e$. We differentiate between A) changes to the model and B) changes to constraints, and further differentiate B1) adding a constraint, B2) deleting a constraint, and B3) changing a constraint.

\noindent\textbf{A) Model changes:} An extensive analysis of $W_v$ and $W_e$ for each potential change type is beyond the scope of this paper. However, as long as we assume that $W$ is independent of the date at which it is performed, we can ensure that, in the worst case, $W_v = W_e$ holds, since the explicit process is never lost in the transformation. The assumption accounts for potential \emph{tech debt} that can arise when constraints change between the model transformation and the model itself. When using VOTER, constraint changes automatically add, remove, or modify helper instances that are invoked at run time. Accordingly, the overall process behavior differs from that of the original pre-transformation process. As such, the amount of \emph{tech debt} is equal to $W_e$, but required at the moment of the model change, rather than being spread out over time. An algorithm that transforms any $M'$ back to $M$ can prevent this problem. 

\begin{wraptable}{r}{0.5\textwidth} % {r} places it right, {0.5\textwidth} sets width
\centering
\scriptsize
\caption{Effort comparison when constraint parameters change}
\label{tab:changes}
\begin{tabular}{@{}lcccc@{}}
\textbf{Constraint} & \textbf{A} & \textbf{B} & \textbf{C} & \textbf{t} \\
\midrule
\texttt{event\_between(A, B, C)}      & = & = & = & --- \\
\texttt{max\_exec\_time(A, t)}        & $\ll$ & --- & --- & $<$  \\
\texttt{recurring(A, B, t)}           & $\ll$ & $<$  & --- & $<$  \\
\texttt{max\_time\_between(A, B, t)}  & $<$  & $<$  & --- & $<$  \\
\texttt{min\_exec\_time(A, t)}        & $\ll$ & --- & --- & $<$  \\
\end{tabular}
\end{wraptable}


\noindent\textbf{B1) Adding a constraint} leads to $W_v < W_e$, since only the endpoints have to be defined, without considering where they have to fit into the process model.

\noindent\textbf{B2) Deleting a constraint:} For the \texttt{exec\_time} and \texttt{time\_between} CP, deleting a CP leads to $W_v < W_e$, as the timeouts/parallels are automatically removed, such that the process model does not have to be manually adjusted to prevent overcompliance~\cite{DBLP:conf/coopis/LoebbeckeR25}. However, deleting a \texttt{event\_between(A,B,C)} CP while using VOTER can lead to undesired behavior: \texttt{C} is automatically removed from the process, even if it should still be executed for compliance-unrelated reasons.

\noindent\textbf{B3) Changing Constraint Parameters:} For constraint parameter changes, $W$ depends on the constraint and which parameter is modified. A $\ll$ entry in Table~\ref{tab:changes} means that changing this parameter leads to $W_v \ll W_e$, with $\ll$ implying a larger difference than $<$. 

Conclusively, our approach does not increase maintenance effort and, in most cases, reduces it. However, a transformation algorithm that transforms TCS-enabled processes back to explicit processes to prevent tech debt is still missing.
