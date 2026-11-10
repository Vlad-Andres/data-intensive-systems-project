# Report changes, relative to your current version (main-2.pdf)

Your current state: the theory part has the figures and text from the previous round; `experimentation.tex` still has the placeholders and empty subsections. Section A says what to change in what you have; section B is new content for the experiments. All numbers come from the CSVs in `plots/` (redraw the figures with `uv run python -m plotting.report_figures`).

## 0. How figure placement works (why figures were far from their text)

- A wide figure (`figure*`) is **never** placed on the page where it is in the source: LaTeX puts it at the top of the **next** page or later. So every `figure*` below goes about one page **before** the text that cites it, at the spot named in the instructions.
- A one-column `figure` uses `[!htbp]`: it goes right where it is in the source if it fits, otherwise to the top or bottom of the same or next column. Do not use `[H]`: when an `[H]` figure does not fit, LaTeX leaves the rest of the column empty or stretches the gaps between equations.
- Code listings are wrapped in a `minipage` so a listing never breaks across a column or runs off the page (see section 3).
- At most two wide figures share the top of a page, in source order.
- `\newpage` pushes every waiting figure out at once and leaves half-empty columns: all of them go (listed below).
- All plots are drawn at the size they are printed (fonts match the text) and have no titles inside; the caption says what they show. The diagrams contain no formulas; formulas are LaTeX equations.
- After compiling: a wide figure one page late → move its block a paragraph or two earlier; one page early → later.

## 1. Files (Overleaf folder `figures/`)

**Upload, replacing files with the same name:**

| File | Width | Section |
|---|---|---|
| `diagram_match_importance.png` | page | Theory 2.1 |
| `measures_databasex3.png` | page | Theory 2.3 |
| `diagram_greedy_evaluation.png`, `diagram_toy_selection.png` | page | Theory 2.4.2 |
| `greedy_pick_order_databasex7.png` | column | Theory 2.4.2 |
| `diagram_graph_similarity_example.png` | page | Theory 2.4.3 |
| `qlog_distributions.png` | page | 4.3 Query logs |
| `baseline_query_log.png` | column | 4.3 Query logs |
| `worked_example_selection.png` | page | 4.4 Measurements |
| `worked_example_evaluation.png` | column | 4.4 Measurements |
| `comparison_keep_curve.png`, `similarity_budget.png` | page | 4.5 Findings |
| `comparison_databasex7_keep1.png`, `small_databases.png`, `comparison_timings.png`, `baseline_comparison.png`, `baseline_timings.png` | column | 4.5 Findings |

**Delete from Overleaf** if you uploaded them earlier (replaced by the files above): `qlog_1_popularity.png`, `qlog_2_shifting_interest.png`, `qlog_3_complex_variables.png`, `qlog_4_sub_queries.png`, `run_1_coverage_table.png`, `run_2_graph_scores.png`, `run_3_answered_queries.png`, `run_3_kept_graphs.png`, `run_4_evaluation.png`, `small_databases_keep_curve.png`.

## 2. main.tex

After the `\usepackage` lines, add (lets two wide figures share the top of a page):

```latex
\renewcommand{\dbltopfraction}{0.85}
\raggedbottom
```

`\raggedbottom` stops LaTeX from stretching the space between paragraphs and equations to fill a column.

## 3. implementation.tex

Wrap every `lstlisting` (five of them) in a minipage, so each listing stays in one piece:

```latex
\noindent\begin{minipage}{\columnwidth}
\begin{lstlisting}[language=Python]
...
\end{lstlisting}
\end{minipage}
```

---

# A. Changes to what you have now (theory.tex)

Your paragraphs stay as they are. Only figure blocks move or change, two `\newpage` go and one equation is added.

### A1. Delete both `\newpage` lines in `theory.tex`

One is right after the paragraph of `\subsection{Importance distributed full coverage}`, the other at the end of the file (after Design considerations).

### A2. Figure 1: column width

In the `data_example.png` figure, change `width=0.5\textwidth` to `width=\columnwidth` (`\textwidth` is the whole page in a two-column layout).

### A3. Match and measures figures: move to the start of the section

**Delete** your current `figure*` block with `diagram_match_importance.png` and your current figure block with `measures_databasex3.png`. **Insert** both right after the second paragraph of `theory.tex` (the one ending `... calculations.`), before the `\begin{figure}[htbp]` of `data_example.png`. They then land together at the top of page 2, next to 2.1–2.3. The measures figure is now a wide, short strip, so it is a `figure*`:

```latex
\begin{figure*}[t]
  \centering
  \includegraphics[width=\textwidth]{figures/diagram_match_importance.png}
  \caption{Match and importance on the running example. Left: log lines are reduced to distinct queries and every worker computes the coverage of each query on its graphs; only coverages above 0 are kept. Right: the distributed importance (Equation~\ref{eq:distributed}), where every query line gives one point that is split over the $|A(q)|$ graphs that fully answer it (in this diagram Q1 is asked six times).}
  \label{fig:diagram_match_importance}
\end{figure*}

\begin{figure*}[t]
  \centering
  \includegraphics[width=\textwidth]{figures/measures_databasex3.png}
  \caption{Score and rank (\#) of every graph of DatabaseX\_3 under the three measures, for the whole query log QLog3\_3. The colour is the score relative to the highest score of its row, because the measures use different scales.}
  \label{fig:measures}
\end{figure*}
```

### A4. Distributed importance as an equation

In `\subsection{Importance distributed full coverage}`, after the sentence `This functionality is implemented with the function \textit{measure\_graph\_importance\_based\_on\_current\_queries}.` and before `So with the example of ...`, **insert** (on its own lines):

```latex
\begin{equation}
\mathrm{importance}(g) = \sum_{q\,:\,\mathrm{cov}(g,q)=1} \frac{w(q)}{|A(q)|}
\label{eq:distributed}
\end{equation}
where $w(q)$ is the number of times query $q$ is asked and $|A(q)|$ the number of graphs that fully answer it.
```

### A5. Greedy and toy figures: move to the start of 2.4

**Delete** your current `figure*` blocks with `diagram_greedy_evaluation.png` and `diagram_toy_selection.png`. **Insert** them directly after `\subsection{Selection}` (before `Finally we have a overview ...`). They land at the top of the next page, beside the gain formula and its example. The greedy diagram no longer has the formula callout; its caption points to Equation 1 instead:

```latex
\begin{figure*}[t]
  \centering
  \includegraphics[width=0.9\textwidth]{figures/diagram_greedy_evaluation.png}
  \caption{Selection in rounds: the candidate with the highest gain (Equation~\ref{eq:gain}) is kept and the gains are recomputed until $B\cdot|D|$ graphs are kept. The reduced database is then evaluated on the past and the future query lines.}
  \label{fig:diagram_greedy}
\end{figure*}

\begin{figure*}[t]
  \centering
  \includegraphics[width=\textwidth]{figures/diagram_toy_selection.png}
  \caption{Toy example with seven query lines, four movie graphs and room for two graphs. Left: distributed importance. Right: selection once keeps two graphs with the same answers and loses two lines; the greedy answers all seven.}
  \label{fig:diagram_toy}
\end{figure*}
```

### A6. Pick-order plot: one column, right where it is cited

**Replace** your current block with `greedy_pick_order_databasex7.png` by this one, directly after your paragraph `Figure~\ref{fig:diagram_greedy} shows the loop ...` (the plot is now one column wide and about 7 cm high):

```latex
\begin{figure}[!htbp]
  \centering
  \includegraphics[width=\columnwidth]{figures/greedy_pick_order_databasex7.png}
  \caption{Greedy on DatabaseX\_7 with QLog7\_2 and $B=2\%$: the 14 highest distributed scores, all kept, with their pick order. Graph 915 ties for the third-highest score but is picked seventh, because graphs 373 and 753 already answer its query.}
  \label{fig:pick_order}
\end{figure}
```

### A7. Graph similarity figure: one page earlier

**Delete** your current `figure*` block with `diagram_graph_similarity_example.png`. **Insert** it directly before the paragraph `Thus, the harmonic normalization ensures ...` (after the last gain equation). It then lands at the top of the page where 2.4.3 is; your paragraph `In detail, with a similarity budget ...` stays where it is.

```latex
\begin{figure*}[t]
  \centering
  \includegraphics[width=0.8\textwidth]{figures/diagram_graph_similarity_example.png}
  \caption{Graph similarity with budget 0.5 on four kept slots. GF and TS1 stay; the two freed slots go to the graphs with the most facts not kept yet. TS2 repeats facts of TS1 and is dropped, so the query that TS2 answered loses its answer.}
  \label{fig:diagram_similarity}
\end{figure*}
```

---

# B. New content (experimentation.tex)

### B0. Delete both `\newpage` lines in `experimentation.tex`

One is after Table 3 (database versions), the other after Table 4 (query log types).

### B1. Setup

**Replace** the placeholder line `For experiment we tested with X databases, Y query logs and Z different configuration settings (i think doing all of them would be to much time consuming)` **with:**

```latex
Every query log is split in two halves: the first half (the \emph{past}) is used to compute the importance and select the graphs, the second half (the \emph{future}) is only used to evaluate the reduced database, together with the other three query logs of the same database. We compare three methods: \emph{naive} (selection once with the full coverage measure), \emph{greedy} (selection in rounds with the distributed measure) and \emph{greedy + graph similarity} (greedy followed by graph similarity with budget $s=0.2$). We ran:
\begin{itemize}
  \item the four large databases (\texttt{5}--\texttt{8}) $\times$ four query logs $\times$ $B\in\{1,2,5,10\}\%$ $\times$ three methods: 192 reductions;
  \item the four small databases (\texttt{1}--\texttt{4}) with $B\in\{20,40\}\%$, i.e.\ 4 and 8 of 20 graphs (1--2\% would keep no graph): 96 reductions;
  \item greedy + graph similarity with budgets $s\in\{0.1,0.5,1\}$ on the large databases with $B\in\{1,2\}\%$: 96 reductions;
  \item the baseline dataset with $B\in\{1,2,5,10\}\%$ $\times$ three methods: 12 reductions.
\end{itemize}
```

**Then insert, directly after this `itemize`**, the wide query-log figure. It lands at the top of the next page, where the datasets and query logs are described:

```latex
\begin{figure*}[t]
  \centering
  \includegraphics[width=\textwidth]{figures/qlog_distributions.png}
  \caption{How often each distinct query is asked in the four query log types (DatabaseX\_7, most asked in the middle). The other databases give the same shapes.}
  \label{fig:qlog_distributions}
\end{figure*}
```

### B2. Query logs (IMDb): the text for the figure

After the paragraph `The query logs are stored in files following the naming convention ...`, **insert:**

```latex
Figure~\ref{fig:qlog_distributions} shows the four shapes: QLog\_1 and QLog\_2 are concentrated on a few queries, QLog\_3 and QLog\_4 are flat, every query is asked once. The type also decides how much of the future repeats the past: 92--98\% of the second-half lines of QLog\_1 were already asked in the first half, 24--28\% for QLog\_2 and none for QLog\_3 and QLog\_4.
```

**Then insert** the wide worked-example figure (it lands at the top of the next page, where 4.4 Measurements starts):

```latex
\begin{figure*}[t]
  \centering
  \includegraphics[width=\textwidth]{figures/worked_example_selection.png}
  \caption{One greedy reduction (DatabaseX\_4, QLog4\_4, $B=20\%$, i.e.\ 4 of 20 graphs). Rows: the 25 past queries. Columns: the eight graphs that fully answer at least one of them, with their distributed score; the kept graphs are left of the line, in pick order. A cell is the share of the query's paths the graph satisfies (1 = full answer). Right: whether a kept graph still fully answers the query.}
  \label{fig:worked_selection}
\end{figure*}
```

### B3. Query logs (baseline)

In `\subsubsection{Baseline}` under Query logs, after the paragraph ending `... around 60 queries that no graph can answer` (add the missing full stop), **insert:**

```latex
566 of its 1,726 distinct queries (3,528 of the 5,962 lines) put two edge labels directly after each other, e.g.\ \texttt{3.holds.chequeCNY}, which the path syntax of the project does not allow (Section~\ref{sec:baseline_commentary}). We removed these queries; the remaining log has 2,434 lines and 1,160 distinct queries (Figure~\ref{fig:baseline_qlog}), its most asked query is asked 40 times, and 57\% of its second-half lines were already asked in the first half.

\begin{figure}[!htbp]
  \centering
  \includegraphics[width=\columnwidth]{figures/baseline_query_log.png}
  \caption{How often each distinct query of the filtered baseline query log is asked. The distribution is Zipf-like: half of the lines come from 101 of the 1,160 queries.}
  \label{fig:baseline_qlog}
\end{figure}
```

### B4. Measurements (IMDb)

Under `\subsection{Measurements}` → `\subsubsection{IMBd}` (empty now), **insert:**

```latex
On every set of query lines we measure:
\begin{itemize}
  \item \textbf{Exact coverage}: the share of query lines that at least one kept graph fully answers. Repeated lines count every time, so popular queries weigh more.
  \item \textbf{Closeness}: for every query line the best coverage of a kept graph (the share of the query's paths it satisfies, as in the match table), averaged over the lines, so near answers count partly.
  \item \textbf{Random reference}: the expected value of both metrics when the same number of graphs is kept at random. A line answered by $n$ of the $N$ graphs keeps an answer with probability $1-\binom{N-n}{k}/\binom{N}{k}$ when $k$ graphs are kept; the expected closeness follows from the same formula for every closeness level.
  \item \textbf{Reduction time}: match, scores and selection, without the Spark start-up.
\end{itemize}

Figure~\ref{fig:worked_selection} follows one reduction through the phases. Many graphs partly answer each query, but only eight graphs fully answer at least one. The greedy keeps graphs 1, 4, 12 and 6, which answer 24 of the 25 past queries. Graphs 6 and 17 are each the only full answer to one query and have the same gain in the last round; the slot goes to graph 6, so the query that only graph 17 answers is lost. On the future half the reduced database still fully answers 64\% of the lines (74\% closeness), against 21\% (52\%) for a random selection of four graphs (Figure~\ref{fig:worked_evaluation}). On the other query logs of the database it falls below random (14\% against 20\% on QLog4\_1, 5\% against 20\% on QLog4\_2): a reduction made for one workload does not serve another.

\begin{figure}[!htbp]
  \centering
  \includegraphics[width=\columnwidth]{figures/worked_example_evaluation.png}
  \caption{Evaluation of the reduction of Figure~\ref{fig:worked_selection} on the past, the future and the other query logs of DatabaseX\_4. Black line: expected value of a random selection of four graphs.}
  \label{fig:worked_evaluation}
\end{figure}
```

### B5. Measurements (baseline)

Under `\subsubsection{Baseline}` of Measurements (empty now), **insert:**

```latex
We use the same metrics on the filtered baseline log. Because the baseline has a single query log, the future is only its second half. We reduced the baseline with $B\in\{1,2,5,10\}\%$ (33 to 337 of the 3,370 graphs).
```

**Then insert** the wide keep-curve figure here (it lands at the top of the next page, where the findings start):

```latex
\begin{figure*}[t]
  \centering
  \includegraphics[width=\textwidth]{figures/comparison_keep_curve.png}
  \caption{Future exact coverage (top) and closeness (bottom) against the keep share $B$, per query log type, averaged over DatabaseX\_5--8.}
  \label{fig:keep_curve}
\end{figure*}
```

### B6. Findings

Under `\subsection{Findings}` (empty now), **insert all of this, in this order:**

```latex
\subsubsection{Comparison of the methods}

The greedy is the best method (Figure~\ref{fig:keep_curve}, Table~\ref{tab:future_exact}). Averaged over the large databases, the four query logs and the four keep shares, it fully answers 63.4\% of the future lines, against 52.1\% for naive and 14.0\% for random. It never answers fewer past lines than naive (better in 32 of the 64 cases, equal in the others) and answers more future lines in 27 cases, the same in 31 and fewer in 6. The advantage is largest when space is tight: at $B=1\%$ the greedy answers 60.4\% of the future lines and naive 36.5\%; at $B=10\%$ both keep almost every useful graph (67.2\% and 65.9\%).

\begin{table}[!htbp]
  \centering
  \caption{Future exact coverage (\%), averaged over DatabaseX\_5--8 and $B\in\{1,2,5,10\}\%$.}
  \label{tab:future_exact}
  \small
  \setlength{\tabcolsep}{4pt}
  \begin{tabular}{lrrrrr}
    \toprule
    & \multicolumn{4}{c}{query log type} & \\
    \cmidrule(lr){2-5}
    Method & 1 & 2 & 3 & 4 & all \\
    \midrule
    random & 8.0 & 8.8 & 28.5 & 10.5 & 14.0 \\
    naive & 89.8 & 30.1 & 21.2 & 67.2 & 52.1 \\
    greedy & 96.2 & 31.9 & 25.6 & 100.0 & 63.4 \\
    greedy + graph sim. & 96.5 & 28.4 & 27.5 & 100.0 & 63.1 \\
    \bottomrule
  \end{tabular}
\end{table}

How much the past helps depends on the query log (Figure~\ref{fig:comparison_db7}). On QLog\_4 the greedy answers every future line because the future sub-queries are parts of the big past queries, which the kept graphs answer; naive reaches 67\%. On QLog\_1 the future repeats the past, and both methods answer almost everything once the budget allows. On QLog\_2 only about 30\% of the future is answerable from the past, because the new popular queries of the second half concern graphs that no past query pointed to.

\begin{figure}[!htbp]
  \centering
  \includegraphics[width=\columnwidth]{figures/comparison_databasex7_keep1.png}
  \caption{DatabaseX\_7 with $B=1\%$: future (bars) and past (black lines) exact coverage and closeness per method and query log.}
  \label{fig:comparison_db7}
\end{figure}

\begin{figure*}[t]
  \centering
  \includegraphics[width=\textwidth]{figures/similarity_budget.png}
  \caption{Past (dashed) and future (solid) exact coverage of greedy + graph similarity against the graph similarity budget $s$, for $B=1\%$ and $2\%$, averaged over DatabaseX\_5--8. Budget 0 is the greedy alone.}
  \label{fig:similarity_budget}
\end{figure*}

\subsubsection{Selecting by the past overfits when the future is new}

On QLog\_3 a random selection answers more future lines than every method (28.5\% against 25.6\% for the greedy and 21.2\% for naive). For example, on DatabaseX\_6 with $B=5\%$ the greedy answers 100\% of the past lines but only 10\% of the future lines, while random answers 40\% and 35\%. Three reasons explain this. First, none of the future queries of QLog\_3 were asked in the past, so every slot spent on a past query is useless for the future. Second, the greedy gain and the distributed measure reward a graph most when it is the only answer to a query; in QLog\_3 these are atypical graphs with rare combinations of genre and year. Third, the future queries are generic (e.g.\ a drama from 2009) and about twenty graphs answer each of them, so a random selection, which resembles the database as a whole, contains such common graphs more often. The second half of QLog\_3 has only ten lines, so every line changes the score by ten points. Selecting by past queries is therefore only useful when future queries repeat or contain past ones; for new queries a method needs to score graphs by the patterns that queries use (genres, years, people) instead of by exact past answers.

\subsubsection{Graph similarity}

Graph similarity gives no§ measurable gain: with budget 0.2 it changes the future exact coverage by less than one point on average (63.1\% against 63.4\%), and it loses past answers when slots are scarce (Figure~\ref{fig:similarity_budget}). With $B=1\%$, a budget of 0.5 lowers the future coverage from 60.4\% to 49.2\%, and a budget of 1, which ignores the query log completely, leaves 11.5\%. The step maximises the number of facts that no kept graph has yet, but a query is answered by a single graph, so facts spread over different graphs do not answer more queries. Moreover, facts contain node identifiers and only 8--15\% of them occur in more than one graph, so the graphs with the most new facts are simply the largest graphs.

\subsubsection{Small databases}

On the 20-graph databases almost every query has a single answering graph, so the methods differ little (Figure~\ref{fig:small_databases}). With $B=20\%$ the greedy answers 29.3\% of the future lines, naive 24.8\% and random 21.7\%; with $B=40\%$ the greedy answers 62.0\%, naive 60.9\% and random 42.3\%. As on the large databases, random is better on QLog\_3.

\begin{figure}[!htbp]
  \centering
  \includegraphics[width=\columnwidth]{figures/small_databases.png}
  \caption{Small databases DatabaseX\_1--4: future (bars) and past (black lines) exact coverage per query log, averaged over the four databases, with $B=20\%$ and $40\%$.}
  \label{fig:small_databases}
\end{figure}

\subsubsection{Reduction time}

With $B=2\%$ a reduction takes 3--5\,s on DatabaseX\_5--7 and 5--9\,s on DatabaseX\_8, whose file is about twice as large (Figure~\ref{fig:timings}). The time hardly depends on $B$: averaged over the large databases the greedy takes 4.6--5.3\,s for every $B$ from 1\% to 10\%. The greedy costs about one second more than naive (three seconds on DatabaseX\_8), and graph similarity another 0.5--0.8\,s.

\begin{figure}[!htbp]
  \centering
  \includegraphics[width=\columnwidth]{figures/comparison_timings.png}
  \caption{Reduction time with $B=2\%$ (match, scores and selection; without Spark start-up), mean over the four query logs.}
  \label{fig:timings}
\end{figure}

\subsubsection{Baseline dataset}

On the baseline the greedy is clearly better than naive, more than on our databases (Figure~\ref{fig:baseline}): it answers 43.9\% of the future lines with $B=1\%$ (naive 26.0\%, random 5.4\%) and 52.0\% with $B=2\%$ (naive 28.8\%, random 10.2\%). The baseline log asks many different queries (663 distinct queries in the first half), so even 2\% of the graphs answers only 55\% of the past lines and the order of the picks matters. The future coverage is close to the past coverage for small budgets (52.0\% against 54.7\% with $B=2\%$) because popular queries recur; with $B=10\%$ the extra graphs answer rare past queries that do not come back (82.9\% past, 67.9\% future). Graph similarity is again within about one point of the greedy. A reduction takes 16--19\,s with naive and 36--47\,s with the greedy, because the baseline has 3.4 times more graphs and 1,160 distinct queries (Figure~\ref{fig:baseline_timings}).

\begin{figure}[!htbp]
  \centering
  \includegraphics[width=\columnwidth]{figures/baseline_comparison.png}
  \caption{Baseline dataset (group 15, filtered): future (bars) and past (black lines) exact coverage and closeness per keep share $B$.}
  \label{fig:baseline}
\end{figure}

\begin{figure}[!htbp]
  \centering
  \includegraphics[width=\columnwidth]{figures/baseline_timings.png}
  \caption{Reduction time on the baseline dataset (3,370 graphs).}
  \label{fig:baseline_timings}
\end{figure}
```

If space is tight, drop `small_databases.png` and `baseline_timings.png` (keep their paragraphs, but remove the `(Figure~\ref{...})` reference in them; the numbers are in the text).

### B7. Baseline commentary

**Replace** the line `\subsection{Baseline commentary}` with the following (adds the label that B3 cites, then the text):

```latex
\subsection{Baseline commentary}
\label{sec:baseline_commentary}

The baseline is a realistic and well documented dataset: 3,370 graphs of an anti-money-laundering scenario (16--418 triples, median 31) with a Zipf-like query log that mixes broad, repeated queries with rare, narrow ones, multi-path queries and attribute checks. Its database follows the triple format exactly: all 166,387 triples have a numeric first element, labels with only letters and digits, and quoted attribute values.

Its query log, however, does not follow the path syntax of the project. 566 of the 1,726 distinct queries (3,528 of the 5,962 lines, 59\%) put two edge labels directly after each other, e.g.\ \texttt{3.holds.chequeCNY}, meaning that node 3 has a \texttt{holds} edge to some node with a \texttt{chequeCNY} edge. The project description writes such an unknown node as a variable (\texttt{5.married.X.city.Y}), so in the specified syntax the query is \texttt{3.holds.X.chequeCNY.Y}. The README of group 15 documents this extension, but a parser that follows the specification reads \texttt{chequeCNY} as a node and misreads these queries. Because these were mostly the frequently asked routine queries, removing them changed the workload: the most asked query drops from 60 to 40 lines and the share of the second half that repeats the first half from 77\% to 57\%.

Compared with our dataset, the baseline is larger (3,370 against at most 1,000 graphs) and its single query log is more varied (1,160 against at most 50 distinct queries per log). Its queries use only node identifiers and no variables, and 81\% of its distinct queries have exactly one answering graph (10\% have none), so it tests the memory of the reduction (keeping the answers of popular queries) rather than its ability to generalise to new queries, which our QLog\_3 and QLog\_4 test.
```

### B8. Future experiments

Under `\subsection{Future experiments}` (empty now), **insert:**

```latex
\begin{itemize}
  \item \textbf{Pattern-based importance for new queries.} Score graphs by how often the attribute values and edge labels they contain (genres, years, people) occur in the past queries, combined with the greedy gain through a weight $\lambda$, and test it on QLog\_3, where selecting by past answers is worse than random.
  \item \textbf{Several splits.} Repeat every experiment with random past/future splits and report mean and spread, since the second half of QLog\_3 has only ten lines.
  \item \textbf{Budget in bytes.} Measure $B$ as a share of the triples instead of the graphs, because graph similarity favours large graphs.
  \item \textbf{Scaling.} Run the reduction on a cluster with the 3,370-graph baseline and larger databases to measure how the match phase scales with the number of graphs and distinct queries.
\end{itemize}
```
