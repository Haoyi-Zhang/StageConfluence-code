# Fixed analysis, irreversible emission: mathematical arguments

These are handwritten proofs for the model defined here. They are not proof-assistant-checked theorems. The executable finite checks are separate evidence. In particular, the implementation is not an extraction from these proofs.

## 1. Definitions

Let `(L, <=, bottom, top)` be a finite lattice with `N` elements. Its height `h` is the maximum number of elements in a strict chain, so `1 <= h <= N`. Let `F = (f_0, ..., f_(m-1))` be a nonempty finite list of self-maps on L. For every i and every x,y:

- Inflationarity: `x <= f_i(x)`.
- Global monotonicity: `x <= y` implies `f_i(x) <= f_i(y)`.

The lattice and maps are fixed throughout a run. For an intended history/prophecy interpretation, the lattice may be a product, but monotonicity is required on the entire product, not just the coordinate a particular map writes.

Write `x ->_i y` when `y = f_i(x)` and `y != x`. Write `->*` for reflexive transitive closure of these strict updates, and `R = {x : bottom ->* x}`. A progress run uses only strict updates. A maximal finite progress run stops at a state with no strict successor. It cannot stop merely because the scheduler declines an enabled update.

Let A be a set of finite residual syntax trees. Let `E : L -> A` be a total deterministic emission function, and `g : L -> {false,true}` an emission guard. A compiler configuration is `(x,c)`, where x is in L and c is either the distinct empty-slot marker `empty` or an element of A. Its two kinds of steps are:

1. `(x,c) ->_i (f_i(x),c)` when `f_i(x) != x`.
2. `(x,empty) ->_emit (x,E(x))` when `g(x)`.

There is no overwrite, no code-dependent map selection, no code-dependent guard or emitter, no fresh slot allocation, and no modification of L or F. The initial configuration is `(bottom,empty)`.

A maximal compiler progress run is **complete** when its terminal slot is nonempty. **Unique output for all runs** means every maximal run is complete and all their residual syntax trees are equal. This definition deliberately excludes an incomplete run and a run that never emits from being a successful compilation.

## 2. Fixed-fact baseline

### Lemma A: upper-bound invariant

For every common fixed point z of F and every x in R, `x <= z`.

**Proof.** At the initial state, bottom <= z. If x <= z and x ->_i y, monotonicity gives `y = f_i(x) <= f_i(z) = z`. Induction over the path proves the claim. No emission property is used. QED.

### Theorem B: common least fixed point and progress bound

Every maximal fact progress run from bottom is finite and terminates at the same state mu. The state mu is the least common fixed point of F. Every such run has at most h-1 strict updates.

**Proof.** Every strict update satisfies `x < f_i(x)` by inflationarity and the progress condition. A progress run is therefore a strict ascending chain, with at most h elements and at most h-1 edges. At its endpoint x, maximality implies `f_i(x)=x` for every i. At least one maximal run exists because one may choose an enabled rule until none remains, and this choice can occur only finitely often. By Lemma A, that endpoint is below every common fixed point. It is itself common fixed, so it is the least one, denoted mu. The same reasoning applies to every maximal run. QED.

No distributivity, idempotence, or pairwise commutation of the maps is needed. The proof actually uses only a finite partial order with a bottom element, but the checker intentionally validates the declared lattice interface. This extension is not claimed as a new order-theoretic theorem.

### Lemma C: suffix convergence

For every reachable x, every maximal progress suffix beginning at x ends at mu.

**Proof.** The suffix is finite and ends at a common fixed point z. Since it extends a path from bottom, Lemma A gives z <= mu. Leastness of mu among common fixed points gives mu <= z. Antisymmetry gives equality. QED.

### Fair schedules with stuttering

For a schedule that may apply an unchanged rule, require that each rule is selected infinitely often in an infinite continuation. There can still be at most h-1 strict increases. The fact sequence is eventually constant, say at x. Fairness implies every rule is eventually applied while x is constant, so all rules fix x; the upper-bound argument again gives x=mu. Without bounded fairness this gives no bound on the number of no-op selections before convergence. The progress relation and its h-1 bound are not a bound on real staging runtime.

## 3. Exact terminal configurations

### Theorem D: terminal factorization

The reachable terminal configurations of the compiler progress relation are exactly

`T = {(mu,E(x)) : x in R and g(x)} union U`,

where `U = {(mu,empty)}` when `g(mu)=false`, and `U` is empty otherwise.

**Proof, inclusion from actual terminals.** The sequence of fact updates in a compiler run is a fact path from bottom. Emission leaves facts unchanged. At a terminal configuration, no strict fact update remains; Theorem B and Lemma C imply that its fact component is mu. If code is present, it was committed once, at some reachable x with g(x), and its value is E(x). Immutability preserves that value until the terminal configuration. If code is absent, terminality requires that emission is disabled at mu, so g(mu)=false.

**Proof, inclusion toward actual terminals.** For any reachable enabled x, take a fact path from bottom to x while postponing all emissions. Emit E(x), then choose a maximal fact suffix. Lemma C gives final facts mu, and the occupied slot prevents another emission. This is a terminal configuration `(mu,E(x))`. When g(mu)=false, take a maximal fact path with no emission. At mu neither kind of step is enabled, yielding `(mu,empty)`. QED.

Postponing a temporarily enabled emission is legal under the nondeterministic progress semantics. It is not a violation of weak fairness, because a finitely enabled action need not be taken. If g(mu) is true, a run that stops at `(mu,empty)` is not maximal.

### Corollary E: completion and unique residual syntax

Every maximal compiler progress run is complete iff g(mu) is true. Complete unique output holds iff

`g(mu)` and `for every x in R, g(x) implies E(x)=E(mu)`.

**Proof.** The empty terminal is present exactly when g(mu) is false. If g(mu) is true, emission at mu is reachable, so E(mu) is among the outputs. By Theorem D all outputs equal this one exactly under the stated condition. QED.

### Corollary F: trace size

Every compiler progress trace has at most h events and hence at most N events: at most h-1 strict fact updates plus at most one emission. Its state graph is acyclic.

**Proof.** Delete the optional emission to obtain a strict fact chain. An emission cannot be repeated. Neither operation can return a compiler state to an earlier configuration. QED.

Thus the two-state early-emission counterexample is an acyclic nonjoinable fork, not a cycle. Searching only for cycles misses this failure.

## 4. Observation and preservation

For k Boolean inputs, let residual expressions be finite trees generated by constants 0 and 1, variables `u_i` for `0 <= i < k`, unary `not`, and binary `and`, `or`, and `xor`. Evaluation on an environment `rho in {0,1}^k` is structural, total, and side-effect free. Syntax equality is tree equality, without commutative or algebraic normalization. Let `[e]` denote the complete truth table of expression e in increasing binary environment order.

### Lemma G: Boolean observation equality

Two residual expressions have equal truth tables iff they evaluate to the same result under every allowed input environment.

**Proof.** A truth table has one entry for each of the finitely many environments. Equality is pointwise equality over exactly that complete domain. Evaluation is total by structural induction on the expression. QED.

### Theorem H: source preservation

For a fixed source expression S, every completed maximal run returns a residual program observationally equivalent to S iff

`for every x in R with g(x), [E(x)] = [S]`.

This assertion does not by itself require that a completed run exists. To claim a successful preserving compilation for every maximal run, additionally require g(mu).

**Proof.** Theorem D identifies the set of completed outputs exactly; Lemma G is the chosen observational semantics. Each enabled x gives an actual completed run, so the condition is also necessary. QED.

The implementation reports preservation as null when no output exists, instead of turning the vacuous universal statement into a success flag.

### Theorem I: projected-output criterion

For any deterministic observation function `q : A -> Q`, complete unique observed output holds iff

`g(mu)` and `for every x in R with g(x), q(E(x)) = q(E(mu))`.

**Proof.** Apply q to the nonempty output components in Theorem D. The empty marker remains separate and is never mapped into Q. The proof of Corollary E then applies. QED.

For syntax, q is identity. For Boolean observations, q is the complete truth-table function. A syntax-safe guard is necessarily observation-safe, but the converse need not hold: `u xor 0` and u are the smallest running example of different syntax with the same observation.

### Corollary J: a guard cannot repair an incorrect final emitter

There exists a guard under which every maximal run is complete and source-preserving iff `[E(mu)]=[S]`.

**Proof.** Necessity follows because every complete guard enables emission at mu. For sufficiency enable emission only at mu. Every fact run reaches mu and emits its correct residual program. QED.

This also gives existence of a guard satisfying completeness, syntactic uniqueness, and source preservation simultaneously. It does not make a wrong final emitter correct.

## 5. Maximal guards

All maximality statements in this section concern enabling sets **on R**. Unreachable states cannot affect the rooted execution property and may be assigned arbitrary guard values.

### Theorem K: maximal safe enabling set

Let `G = {x in R : E(x)=E(mu)}`. Then G contains mu. Every enabling set H giving complete unique syntax satisfies `mu in H subseteq G`. Conversely every H with these inclusions gives complete unique syntax. In particular G is the unique largest such enabling set on R.

**Proof.** Substitute H for the set of true guard states in Corollary E. Determinism gives E(mu)=E(mu), so mu belongs to G. QED.

### Theorem L: maximal persistent safe enabling set

Call H persistent when every strict fact transition from an enabled state remains enabled: `x in H and x ->_i y` implies `y in H`. Let Bad be `R minus G`, and let `Pre*(Bad)` contain all states in R from which some Bad state is reachable, including Bad itself. Define

`P = R minus Pre*(Bad)`.

Then P is the largest persistent subset of G, contains mu, and yields complete unique output. It is computed by reverse reachability from Bad in the actual fact graph.

**Proof.** Zero-length reachability gives `Bad subseteq Pre*(Bad)`, so P subseteq G. If x is in P and x ->_i y but y were outside P, a path from y to Bad would extend to one from x, a contradiction. Hence P is persistent. The fixed point mu has no strict outgoing edge and is not bad, so mu is in P. Conversely, let H be any persistent subset of G. If x in H could reach a bad y, repeated persistence along that path would put y in H, contradicting H subseteq G. Thus H subseteq P. Completeness and uniqueness follow from Theorem K. QED.

The same construction works with equality after any projection q. The resulting guard is safe for q, not necessarily for residual syntax or for an unrelated source.

### Proposition M: order-upward safety can be stricter

Define `O = {x in R : no y in Bad satisfies x <= y}`. Then `O subseteq P`; strict inclusion is possible.

**Proof of inclusion.** Every actual fact path is ascending. If x can reach a bad y, then x <= y. Contrapositively, x in O cannot reach Bad and so belongs to P.

**Strictness witness.** Take the powerset of `{a,b,c}`, ordered by inclusion, with

`f(X) = X union {b} union ({c} if a in X else {})`,

`g(X) = X union {a}`.

Both are globally monotone and inflationary. From the empty set, the reachable states are `{}, {a}, {b}, {a,b}, {a,b,c}`. The strict transitions are

`{} -f-> {b}`, `{} -g-> {a}`, `{a} -f-> {a,b,c}`,

`{b} -g-> {a,b}`, `{a,b} -f-> {a,b,c}`.

Let the emitter equal u at all states except `{a,b}`, where it equals `u xor 0`. The least fixed point is `{a,b,c}`. The greatest persistent syntax-safe set is `{{a},{a,b,c}}`. The order-upward safe set is only `{{a,b,c}}`, because `{a} <= {a,b}` although `{a,b}` is not reachable *from* `{a}`. The distinction is between reachable supersets and actual continuations. QED.

Neither upward-closure computation nor backward reachability is presented as a new general algorithm.

## 6. Boundary and minimality arguments

### Minimal nonjoinable emission fork

Take `L={0<1}`, one map f(0)=f(1)=1, guard true at both states, E(0)=`u xor 0`, E(1)=u. Emitting then learning ends at `(1,u xor 0)`. Learning then emitting ends at `(1,u)`. Both outputs equal u on every Boolean input. The fact state and observation converge; syntax does not. A one-element lattice has only one possible emitter value under the deterministic single-slot model, so it cannot produce two different completed syntactic outputs. The example is minimal in fact-state count within this precisely declared class. This is not a minimality claim over arbitrary staged languages or nondeterministic emitters.

### Local monotonicity is insufficient

On two bits `(h,p)`, define `F(h,p)=(h or not p,p)` and `B(h,p)=(h,p or not h)`. Both are inflationary. Holding the foreign coordinate fixed, the written-coordinate update is monotone. From `(0,0)`, choosing F first reaches the joint fixed point `(1,0)`; choosing B first reaches `(0,1)`. F is not globally monotone because `(0,0) <= (0,1)` but `(1,0)` is not below `(0,1)`. This counterexample is rejected by the checker, which checks the full product order.

### Reanalysis after code replacement

Let `E(0)=u and 0`, `E(1)=0`, and let D(e) be one if e contains a syntactic read of u and zero otherwise. Each analysis `x |-> D(e)` is constant, hence monotone, for a fixed e. But reanalysis through emission gives `D(E(0))=1` and `D(E(1))=0`: exact recomputation cycles. Both ASTs denote constant zero. Replacing recomputation by a join gives `p := p or D(E(p))`, which stabilizes at one from zero. The stabilized one is an accrued upper bound, not the exact syntactic-read property of E(1), which is zero. The example changes the global operator through code and is outside the fixed-family theorem.

### Monotonicity without inflationarity

On the two-bit powerset lattice, swapping the bits is monotone but not inflationary. From `(1,0)` it alternates with `(0,1)`. This example is not a bottom-start counterexample to Theorem B: bottom is fixed by swapping. It shows why arbitrary-state iteration must not borrow the strict-progress bound when inflationarity is absent.

## 7. Finite checker and witness soundness

The checker validates the explicit order and every map before applying the preceding formulas. It explores the fact graph and, separately, the full product graph `(fact,optional syntax)`; their terminal sets must agree. A full product graph has at most `N(K+1)` states for K distinct emitter values, and at most `mN(K+1)+N` labeled edges. In this one-slot model K<=N. This bound counts graph states, not the number of schedules; the latter can be much larger.

The witness verifier receives an instance and one or two event lists. It checks each applied map index, requires strict change, permits emission only into an empty slot under the actual guard, and checks terminality at the end. It then checks the claimed defect: an empty terminal, different completed syntax on two runs, or a completed residual whose truth table differs from the source. It never calls the graph explorer or fixed-point synthesizer.

An accepted witness is sound for the supplied instance: induction on the replayed events shows that its configurations form legal paths from the specified initial state. The final scan establishes that those paths are maximal. The final defect check is exactly the indicated failed property. The N-event bound follows from Corollary F. This is a mathematical explanation of the replay algorithm, not a machine-checked theorem about Python or its parser.

The construction also produces a witness for every failure of complete unique syntax. If g(mu) is false, a fact-only path to mu is an incomplete witness. Otherwise Corollary E supplies an enabled reachable x with E(x) different from E(mu); emit at x on one run and at mu on another, extending both to terminality. If syntax is unique but source preservation fails, emitting at mu witnesses the semantic error. When several defects coexist, the implementation returns one witness with priority incomplete, different syntax, then wrong semantics; the analysis report still describes all terminal observations.

## 8. Evidence scope

The retained campaign enumerates all ordered pairs of admitted maps, binary emitters, and guards for eight named lattices with at most five states. Its 2,560,900 cases check the formulas, not all finite lattices and not real compiler workloads. The general statements rest on the proofs above. The 56-expression, 3,136-pair Boolean check uses all four input environments, and therefore decides its stated semantic comparisons exactly. Neither experiment establishes a new general convergence theorem for BuildIt, Nexis, changing intermediate representations, or an unrestricted staged language.
