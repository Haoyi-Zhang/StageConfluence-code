# Confluence and semantic preservation for finite bidirectional staged systems

This note states the mathematical model implemented by `src/staged_model.py`,
gives complete proofs of the general results used by the paper, and separates
those proofs from the executable finite checks.  The Python checker is not a
proof assistant.  Its certificates instantiate the definitions below for finite
JSON instances; the theorems in this note are handwritten arguments.

## 1. Model

Let \((L,\sqsubseteq,\bot,\top)\) be a nonempty finite lattice.  Only the
finite partial order is needed by most results; joins and meets are required by
the input format because the intended facts are abstract-domain elements.  Let
\(P\) be a nonempty finite set of residual programs and let
\(\rho:P\to\mathbb N\) be a program rank.

For every \(p\in P\), there is a nonempty finite family of analysis functions

\[
  A_{p,1},\ldots,A_{p,k_p}:L\to L.
\]

Every analysis function is:

1. **inflationary:** \(x\sqsubseteq A_{p,i}(x)\); and
2. **monotone:** \(x\sqsubseteq y\Rightarrow
   A_{p,i}(x)\sqsubseteq A_{p,i}(y)\).

The names “forward,” “prophecy,” and “history” are labels on functions.  The
mathematics deliberately does not infer operational meaning from a label.

A rewrite rule is a tuple

\[
  r=(p,q,g_r,\tau_r),
\]

where \(p\) is its source program, \(q\) its target program,
\(g_r:L\to\{\mathsf{false},\mathsf{true}\}\) is a guard, and
\(\tau_r:L\to L\) is a fact transfer.  Every transfer is monotone and
inflationary, and every rewrite strictly decreases rank:

\[
  \rho(q)<\rho(p).
\]

A state is a pair \((p,x)\in P\times L\).  The transition relation \(\to\)
has two forms.

* **Analysis:**
  \((p,x)\to_A(p,A_{p,i}(x))\) when \(A_{p,i}(x)\ne x\).
* **Rewrite:**
  \((p,x)\to_r(q,\tau_r(x))\) when \(r=(p,q,g_r,\tau_r)\) and \(g_r(x)\).

Analysis stutters are omitted.  A rewrite is a real code change even when its
fact transfer is the identity.  The rooted system starts at a declared
\((p_0,x_0)\), normally with \(x_0=\bot\).

A state is **normal** when it has no outgoing analysis or rewrite transition.
A rooted system is **confluent** when, for every reachable state \(s\) and all
\(u,v\) with \(s\to^*u\) and \(s\to^*v\), there exists \(w\) with
\(u\to^*w\) and \(v\to^*w\).  It has a **schedule-independent residual
program** when every normal state reachable from the root has the same program
component.  The latter is weaker than confluence because final facts may differ.

## 2. Termination

For \(x\in L\), define the remaining height (coheight)

\[
  h(x)=\max\{n\mid x=x_0\sqsubset x_1\sqsubset\cdots\sqsubset x_n\}.
\]

The maximum exists because \(L\) is finite.  Put
\(H=1+\max_{x\in L}h(x)\), and define

\[
  M(p,x)=H\rho(p)+h(x).
\]

### Lemma 2.1 (strict growth lowers coheight)

If \(x\sqsubset y\), then \(h(y)<h(x)\).

**Proof.**  Prepending \(x\) to any strict chain starting at \(y\) gives a
strict chain starting at \(x\) with one more edge.  Hence
\(h(x)\ge 1+h(y)\).  ∎

### Lemma 2.2 (the measure decreases)

For every transition \(s\to t\), \(M(t)<M(s)\).

**Proof.**  For a strict analysis transition, inflationarity gives
\(x\sqsubset A_{p,i}(x)\); Lemma 2.1 lowers \(h\) while the program rank is
unchanged.

For a rewrite \((p,x)\to(q,\tau_r(x))\), rank drops by at least one.  The
coheight term can increase by at most \(H-1\), regardless of transfer; under
the admitted inflationary transfer it in fact cannot increase.  Thus

\[
 M(q,\tau_r(x))-M(p,x)
 \le -H+(H-1)=-1.
\]

Therefore every transition strictly lowers the natural-number measure.  ∎

### Theorem 2.3 (termination)

Every admitted transition sequence is finite.  The reachable graph is acyclic,
and every reachable state reaches at least one normal state.

**Proof.**  An infinite sequence would induce an infinite strictly decreasing
sequence of natural numbers under \(M\), which is impossible.  A directed cycle
would produce the same contradiction.  Starting from any reachable state and
taking enabled transitions must stop at a normal state because the graph is
finite and acyclic.  ∎

The rank hypothesis is intentionally strong.  It excludes optimization cycles
that alternate between equally ranked residual programs.  The checker rejects
such inputs rather than trying to infer a more complicated well-founded order.

## 3. Analysis closure

Fix a program \(p\).  A fact \(z\) is **closed for \(p\)** when
\(A_{p,i}(z)=z\) for every \(i\).  Starting at \(x\), repeatedly apply any
strictly changing analysis function under a fair schedule.  Because facts grow
strictly and the lattice is finite, every such execution terminates.

### Lemma 3.1 (least common fixed point)

For every \(p\) and \(x\), all fair analysis-only executions from \(x\)
terminate at the same fact, denoted \(C_p(x)\).  It is the least fact
\(z\sqsupseteq x\) fixed by every \(A_{p,i}\).

**Proof.**  Termination follows from Lemma 2.1.  Let an execution end at \(z\).
Fairness together with termination means no rule changes \(z\), so \(z\) is a
common fixed point.  Let \(y\sqsupseteq x\) be any common fixed point.  By
induction over execution steps, every intermediate fact is below \(y\): the
base is \(x\sqsubseteq y\); and if \(u\sqsubseteq y\), monotonicity gives
\(A_{p,i}(u)\sqsubseteq A_{p,i}(y)=y\).  Hence \(z\sqsubseteq y\).  Thus every
terminating fair execution reaches the least common fixed point, which is
unique.  ∎

A cyclic scan of all analysis functions, repeated until a complete scan makes
no change, is fair.  This is the deterministic closure algorithm used by the
certificate generator.

### Lemma 3.2 (closure laws)

For each \(p\), \(C_p\) is extensive, monotone, and idempotent.  Moreover, if
\((p,x)\to_A(p,y)\), then \(C_p(x)=C_p(y)\).

**Proof.**  Extensivity is part of Lemma 3.1.  For monotonicity, suppose
\(x\sqsubseteq y\).  The fact \(C_p(y)\) is a common fixed point above \(x\),
so leastness gives \(C_p(x)\sqsubseteq C_p(y)\).  Idempotence follows because
\(C_p(x)\) is already common-fixed.

For the final claim, inflationarity gives \(x\sqsubseteq y\), hence
\(C_p(x)\sqsubseteq C_p(y)\).  Also
\(y=A_{p,i}(x)\sqsubseteq A_{p,i}(C_p(x))=C_p(x)\), so \(C_p(x)\) is a common
fixed point above \(y\), and leastness gives \(C_p(y)\sqsubseteq C_p(x)\).
The two inequalities imply equality.  ∎

### Corollary 3.3 (analysis peaks join)

Every local analysis/analysis peak
\((p,x)\to_A(p,y_1)\) and \((p,x)\to_A(p,y_2)\) joins at
\((p,C_p(x))\).

**Proof.**  By Lemma 3.2 both branch closures equal \(C_p(x)\), and Lemma 3.1
supplies finite strict analysis paths to the closure.  ∎

## 4. Exact finite confluence criterion

A **local peak** is a pair of one-step transitions
\(u\leftarrow s\to v\).  It is joinable when some \(w\) satisfies
\(u\to^*w\leftarrow^*v\).

### Theorem 4.1 (reachable Newman criterion)

For an admitted rooted system, the following are equivalent:

1. every reachable local peak is joinable;
2. the reachable transition relation is confluent;
3. every reachable state has exactly one reachable normal form.

**Proof.**  The reachable relation terminates by Theorem 2.3.  Newman's lemma
therefore gives (1) iff (2).  Confluence implies unique normal forms because two
normal forms reachable from one state can join only if they are equal.  For the
converse, take \(s\to^*u\) and \(s\to^*v\).  Termination extends both branches
to normal forms.  By assumption both normal forms are the unique normal form of
\(s\), so the branches join there.  ∎

This theorem is exact but may require exploring the entire rooted state graph.
The next section gives a compositional sufficient condition that separates
analysis/rewrite interaction from rewrite/rewrite critical peaks.

## 5. Saturated rewrite relation

A state \((p,z)\) is **saturated** when \(z=C_p(z)\).  Define the saturated
rewrite relation \(\Rightarrow\) by

\[
 (p,z)\Rightarrow_r
 \bigl(q,C_q(\tau_r(z))\bigr)
\]

when \(z\) is saturated, \(r=(p,q,g_r,\tau_r)\), and \(g_r(z)\).  The rooted
saturated system begins at \((p_0,C_{p_0}(x_0))\).  Every saturated step is
realizable in the full system by one rewrite followed by an analysis-only path
to closure.

The following three obligations form the modular criterion.

**Guard persistence (GP).**  For every rewrite \(r\) out of \(p\), every fact
\(x\), and every analysis function \(A_{p,i}\),

\[
  g_r(x)\Longrightarrow g_r(A_{p,i}(x)).
\]

**Closure commutation (CC).**  For every rewrite
\(r=(p,q,g_r,\tau_r)\) and every fact with \(g_r(x)\),

\[
 C_q(\tau_r(x))=C_q(\tau_r(C_p(x))).
\]

**Saturated local confluence (SLC).**  Every local rewrite/rewrite peak reachable
in the rooted saturated relation \(\Rightarrow\) is joinable under
\(\Rightarrow^*\).

GP is only persistence under the declared source analyses; it need not be
upward closure over every order edge in the lattice.  CC compares the normalized
result of rewriting now with the normalized result of first closing the source.
SLC is a critical-peak obligation on a smaller graph that has no analysis edges.

### Lemma 5.1 (persistence to closure)

Under GP, \(g_r(x)\) implies \(g_r(y)\) for every analysis-only descendant
\((p,x)\to_A^*(p,y)\), in particular for \(y=C_p(x)\).

**Proof.**  Induction over the analysis path, applying GP at each step.  ∎

### Lemma 5.2 (one analysis step commutes after normalization)

Assume GP and CC.  If \((p,x)\to_A(p,y)\), and rewrite \(r\) is enabled at
\(x\), then it is enabled at \(y\) and

\[
 C_q(\tau_r(x))=C_q(\tau_r(y)).
\]

**Proof.**  Enablement at \(y\) is GP.  By Lemma 3.2,
\(C_p(x)=C_p(y)\).  Applying CC at \(x\) and at \(y\) (permitted by GP) gives

\[
 C_q(\tau_r(x))=C_q(\tau_r(C_p(x)))
 =C_q(\tau_r(C_p(y)))=C_q(\tau_r(y)).
\]

∎

### Lemma 5.3 (normalization simulation)

Assume GP and CC.  If a full-system state \((p,x)\) is reachable, then its
normalization \((p,C_p(x))\) is reachable in the rooted saturated system.  More
generally, every full execution projects to a saturated execution after deleting
analysis steps and normalizing after each rewrite.

**Proof.**  Induct over a full execution.  The normalized initial state is the
saturated root.  An analysis step does not change normalization by Lemma 3.2.
For a rewrite \(r:(p,x)\to(q,\tau_r(x))\), the induction hypothesis reaches
\((p,C_p(x))\).  Lemma 5.1 enables \(r\) there.  Its saturated target is
\((q,C_q(\tau_r(C_p(x))))\), which equals the normalization of the full target
by CC.  ∎

### Lemma 5.4 (termination and confluence of the saturated system)

The saturated relation terminates.  Under SLC, it is confluent on its reachable
states.

**Proof.**  Every saturated transition includes one rank-decreasing rewrite, so
\(\rho\) itself is a termination measure.  SLC is local confluence.  Newman's
lemma yields confluence.  ∎

### Theorem 5.5 (modular saturation theorem)

If GP, CC, and SLC hold, then the full rooted transition system is confluent.

**Proof.**  By Theorem 2.3, it suffices under Theorem 4.1 to join every reachable
local peak.  There are three cases.

* **Analysis/analysis.**  Corollary 3.3 joins both branches at the source
  closure.
* **Analysis/rewrite.**  Suppose the source is \((p,x)\), the analysis branch
  reaches \((p,y)\), and rewrite \(r\) reaches \((q,\tau_r(x))\).  Lemma 5.2
  enables the same rewrite after the analysis and equates the closures of the
  two rewrite targets.  Both branches therefore reach
  \((q,C_q(\tau_r(x)))\).
* **Rewrite/rewrite.**  Normalize the source to \((p,C_p(x))\).  By Lemma 5.1,
  both rewrites remain enabled.  By CC, the normalized immediate targets of the
  two full branches are exactly the two successors of this saturated state.
  Lemma 5.3 says the saturated source is reachable.  SLC and Lemma 5.4 join its
  two saturated successors.  Every saturated step expands to a full rewrite
  followed by analyses, so the original full branches join as well.

All reachable local peaks are joinable; Theorem 4.1 concludes confluence.  ∎

### Corollary 5.6 (modular criterion is sound, not complete)

GP+CC+SLC is sufficient but not necessary for confluence.

**Proof.**  Sufficiency is Theorem 5.5.  Non-necessity is witnessed by retained
case S08: its exact reachable graph has joinable local peaks and one normal form,
but a declared guard is not persistent.  The nonpersistent branch does not
prevent the concrete peak from joining by another route.  The certificate for
S08 checks the exact graph; the counterexample is finite evidence for
non-necessity, not a general theorem about how often the criterion is incomplete.
∎

## 6. Program uniqueness versus state confluence

For a state \(s\), write \(\mathsf{NF}(s)\) for its set of reachable normal
states and \(\pi_P(p,x)=p\).

### Proposition 6.1 (exact program-schedule criterion)

The root has a schedule-independent residual program iff

\[
  \left|\{\pi_P(t)\mid t\in\mathsf{NF}(p_0,x_0)\}\right|=1.
\]

**Proof.**  This is exactly the definition after termination guarantees that all
maximal executions end in normal states.  ∎

Confluence implies this condition, but the converse fails.  Case S10 has two
normal states with different final facts and the same program component.  It is
therefore program-schedule-independent but not state-confluent.  The distinction
matters when facts are proof artifacts or diagnostics that are erased before
execution.

## 7. Residual semantics

Let \(D\) be a finite input domain and let each program \(p\) denote a total
function \(\llbracket p\rrbracket:D\to O\).  The executable model uses Boolean
expressions and exhaustively enumerates \(D=\{0,1\}^k\).  Analysis transitions
do not change the program component.

A rewrite \(r:p\to q\) is **observationally preserving** when
\(\llbracket p\rrbracket=\llbracket q\rrbracket\).  This condition is fact
independent in the current model; a richer language could index semantics by a
fact invariant, but no such theorem is claimed here.

### Theorem 7.1 (pathwise preservation)

If every rewrite used by a rooted execution is observationally preserving, then
the program at every state on that execution has the same observation as the
initial program.

**Proof.**  Induction over the execution.  Analysis steps leave the program
unchanged.  Rewrite steps preserve its denotation by hypothesis.  ∎

### Corollary 7.2 (unique source-equivalent residual program)

If all reachable rewrites preserve observation and the root has a
schedule-independent residual program, then that unique residual program is
observationally equivalent to the source program.  In particular, the
conclusion holds under Theorem 5.5 plus reachable rulewise preservation.

**Proof.**  Every maximal execution reaches the unique program, and Theorem 7.1
preserves the initial observation along each execution.  ∎

Confluence and semantic preservation are logically independent.  Case S07 is
confluent but rewrites \(u\) to \(\neg u\).  Conversely, two distinct Boolean
syntax trees can be observationally equivalent while violating syntactic
schedule independence.  The checker therefore reports exact terminal-program
identity, truth-table equivalence, reachable-rule preservation, and the stronger
global audit of every declared rewrite as separate fields.

An unreachable bad rewrite does not falsify rooted source equivalence; case S11
makes this distinction explicit.  It does, however, fail the stronger claim that
every declared rewrite rule is semantics preserving.

## 8. Certificate soundness argument

A positive certificate contains:

1. a finite list of states with their ranking measure;
2. a list of edges, each named by an analysis or rewrite rule;
3. for every state, the complete ordered list of outgoing edge identifiers;
4. an acyclic parent edge for every noninitial state;
5. all terminal-state identifiers;
6. one analysis-closure trace for every program/fact pair;
7. one join state and two edge paths for every unordered pair of outgoing edges;
8. source and residual-program truth tables; and
9. the claimed summary flags.

The verifier reconstructs each edge directly from the JSON instance.  It
reconstructs the complete successor list of every listed state and requires
exact equality with the certificate's list.  Parent edges prove every listed
state reachable; exact successor coverage proves the listed reachable set is
closed.  Consequently the state list is exactly the rooted reachable graph:
reachability gives one inclusion, and closure from the initial state gives the
other.

For each edge, the verifier checks strict decrease of \(M\).  For every local
peak induced by the exact outgoing lists, it replays both supplied paths and
checks a common endpoint.  Thus the certificate establishes termination and
local confluence of the exact rooted graph; Theorem 4.1 yields confluence.  The
verifier does not search for a path, a normal form, a join, or a fixed point.
It does recompute rule applications, outgoing transitions, the lattice
coheight, and Boolean truth tables, because those are the predicates being
checked.

A closure trace is accepted only if each listed analysis application is strict
and the endpoint is fixed by every analysis function.  Lemma 3.1 then implies
that endpoint is the least common fixed point above the trace's start.  The
closure traces are not needed for the exact local-peak proof, but they expose the
normalization evidence used by the modular criterion.

A negative witness contains two event sequences from the root and their claimed
endpoints.  The verifier replays every event from the input rules, checks that
both endpoints are normal, and checks that the endpoints differ.  Different
program components prove failure of program schedule independence; equal
program components with different facts prove only failure of state confluence.

The generator and verifier share the validated instance representation and
Boolean evaluator but not graph exploration or join search.  This is useful
separation, not an independent mechanized proof of the general metatheory.

## 9. Scope boundaries

The theorems depend on all of the following:

* finite facts and finitely many residual programs;
* globally monotone, inflationary analysis functions;
* monotone, inflationary rewrite transfers;
* a declared natural-number rank that strictly decreases at every rewrite;
* pure total residual expressions for the executable semantic check; and
* no rule generation, deletion, or mutation outside the finite instance.

The results do not cover unrestricted recursion, infinite-height abstract
domains without widening, code-expanding cycles, dynamically generated rewrite
rules, side-effecting residual programs, or production compiler performance.
They also do not assert that GP+CC+SLC is a maximal confluent fragment.  Exact
confluence remains decidable for every admitted finite instance by exhaustive
exploration; the modular theorem is a scalable proof decomposition within the
finite rank-decreasing model.
