Group 15 - Data Intensive Systems 2026-2027 - Deliverable 1 Dataset and Query Log

FILES
Database15.txt  The graph database. One graph per line (3,370 graphs, about 92,000 edges and 74,000 attributes in total).

QLog15.txt      The query log. One query per line (5,963 queries, 1,726 distinct). Repeated lines are intentional: how often a
                query appears is how often it is asked.

README.txt      This file.

SOURCE
Built from the IBM Transactions for Anti-Money Laundering dataset, HI-Small version. 
Files used:
- HI-Small_Patterns.txt (the laundering attempts):
  https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml?select=HI-Small_Patterns.txt
- HI-Small_accounts.csv (banks, accounts and owner types):
  https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml?select=HI-Small_accounts.csv
- Paper: Altman et al., "Realistic Synthetic Financial Transactions for
  Anti-Money Laundering Models", NeurIPS 2023 Datasets and Benchmarks.
  https://arxiv.org/abs/2306.16424

THE GRAPHS
Two kinds of graph are mixed in Database15.txt:
- 370 laundering cases: one laundering attempt each, in 8 shapes
  (fan-out, fan-in, cycle, stack, scatter-gather, gather-scatter,
  bipartite, random).
- 3,000 normal flows: one account's payments on one day, plus the onward
  payments of each receiver (2 hops).
Graph sizes range from 16 to 418 triples (median 31).

Nodes (the same object has the same id in every graph):
- Banks keep their own id from the source data.
- Accounts are numbered from 1,000,000.
- Owners are numbered from 5,000,000.

Edges:
- Payments: label = payment type + currency, e.g. achUSD, wireGBP,
  chequeEUR, cashJPY (85 such labels).
- Account -> bank: heldAt;   bank -> account: holds.
- Account -> owner: ownedBy; owner -> account: owns.

Attributes:
- Bank:    name, group
- Owner:   type (e.g. "Corporation", "Partnership", "Sole Proprietorship")
- Account: currency, role ("source", "intermediate" or "sink": the
           account's position in the money flow of that graph)

THE QUERY LOG

Queries simulate a bank's anti-money-laundering team:
- Routine analysts (asked often, broad), e.g. 12.holds.creditCardINR
- Operations (asked a few times, one concrete payment),
  e.g. 1003900.chequeJPY.1009652
- Investigators (rare, narrow, multi-hop chains),
  e.g. 1002901.achUSD.1001307.achUSD.1001726
- Attribute checks, e.g. 1013905.heldAt.144225.group."Israel"
- Multi-path queries (2 or 3 paths separated by commas).
- Around 60 queries that no graph can answer (edge cases).
Query frequencies follow a Zipf-like distribution: popular queries appear up to about 60 times, investigator queries 1-3 times.

NOTE ON PATHS WITH TWO LABELS IN A ROW
Some paths have an edge label directly after another edge label, e.g. 12.holds.creditCardINR. The node in between is left open (any node): "node 12 has a holds edge to some node, and that node has an outgoing creditCardINR edge". All other paths alternate node and label as in the project description.
