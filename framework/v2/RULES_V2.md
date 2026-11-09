# Rules v2: a refined rule set (future work)

**Status:** v2 is proposed for future work. It is **not** the rule set of the paper.
- Version 1 (`--rules v1`, the default) implements the 54 rules of Appendix B exactly as published.
- Version 2 is switched on with `--rules v2` in the terminal or in **Settings → Rule set** on the web page.

## 1. Idea

The 54 rules decide the relationship separately for every combination of element types (term, triple, word,
sequence of words). Version 2 explores a more compact formulation for future work: the element types only decide
how the evidence is measured, one decision table maps the evidence to a relationship, and an explicit *unknown*
outcome is added for missing or weak evidence.

## 2. The v2 rule set

**C1. One decision table replaces 41 case-specific WHAT rules.** The element types only decide *how the evidence is measured* (Steps A and B). The decision itself depends only on the evidence levels.

**C2. WHAT evidence has four levels**, whatever the element types:

| Level | Meaning |
|---|---|
| SAME | equals or synonym (T-T: SRS + VR + ORS) |
| HIER | subclass or superclass (T-T: a hierarchical S or O with VR and no unlinked element) |
| RELATED | similar, or a partial T-T match |
| NONE | no link |

Two adjustments:
- A triple against a single term counts at most as HIER: the triple specialises the term (as in W01).
- A link involving a sequence of words counts at most as RELATED, because it is found by similarity only.

**C3. HOW evidence has three levels instead of two:**

| Level | Meaning |
|---|---|
| SAME | same action **and** same target |
| PARTIAL | same action **or** same target |
| DIFFERENT | neither |

The subject of a HOW triple is no longer used. It is the artefact itself, already compared in the WHAT, so in v1 (H01–H08) it counted twice.

**C4. Unknown outcome (abstain).** v1 returns *disjoint* when no rule applies (the default of Algorithm 1) and treats a missing HOW as "different". v2 can abstain instead:

| ID | When |
|---|---|
| U01 | WHAT missing or empty for at least one idea |
| U02 | HOW missing or empty for at least one idea |
| U03 | The link that moves the pair away from *disjoint* is weak: found only through a modifier word (e.g. "*structure* element"), between generic heads (system, device, structure, ...), or with a score within `rules_v2.margin` (0.03) of its threshold |
| U04 | The deciding elements could not be compared at all (no vector, no lexical entry) |

*Unknown* is reported separately: coverage, and accuracy on the decided pairs. When an *unknown* has to be compared with a label, it counts as not related.

**C5. The decision table**

| WHAT \ HOW | SAME | PARTIAL | DIFFERENT |
|---|---|---|---|
| **SAME** | R01 duplicate | R02 similar | R03 similar |
| **HIER** | R04 generalise/detail | R05 similar | R06 disjoint (*) |
| **RELATED** | R07 similar | R08 similar | R09 disjoint |
| **NONE** | R10 alternative-solution | R11 alternative-solution | R12 disjoint |

(*) Two artefacts of the same broad class that do different things share no functional evidence, so R06 is *disjoint* by default. `rules_v2.hier_different=similar` gives *similar*.

How each cell follows from the definitions:
- **Duplicate:** same artefact and same function.
- **Generalise/detail:** hierarchical artefacts with the same function. The more specific idea details the more general one.
- **Similar:** the ideas share the artefact or part of the function.
- **Alternative-solution:** a different artefact for the same, or partly the same, function.
- **Disjoint:** nothing functional in common.

## 3. Correspondence with the 54 rules

✔ = same output; ✎ = different output in v2.

### WHAT rules (41)

| v1 rule | v1 condition | v1 output | v2 cell | v2 output | |
|---|---|---|---|---|---|
| W01 | T-W linked, same HOW | generalise | R04 (R07 if the link is only *similar*) | generalise (similar) | ✎ partly |
| W02 | T-W linked, different HOW | alternative | R06 / R09 | disjoint | ✎ |
| W03 | T-W no link, same HOW | similar | R10 | alternative | ✎ |
| W04 | T-W no link, different HOW | disjoint | R12 (R11 if PARTIAL) | disjoint | ✔ |
| W05 | T-SW linked, same HOW | similar | R07 | similar | ✔ |
| W06 | T-SW linked, different HOW | alternative | R09 | disjoint | ✎ |
| W07 | T-SW no link, same HOW | alternative | R10 | alternative | ✔ |
| W08 | T-SW no link, different HOW | disjoint | R12 | disjoint | ✔ |
| W09 | SRS VR ORS, same HOW | duplicate | R01 | duplicate | ✔ |
| W10 | SRS VR ORS, different HOW | alternative | R03 | similar | ✎ |
| W11 | (SR\|SRS) VR (OR\|ORS), same HOW | generalise | R04 (R07 without hierarchy) | generalise (similar) | ✎ partly |
| W12 | idem, different HOW | alternative | R06 / R09 | disjoint | ✎ |
| W13 | (SR\|SRS) VR OD, same HOW | alternative | R07 | similar | ✎ |
| W14 | idem, different HOW | disjoint | R09 | disjoint | ✔ |
| W15 | (SR\|SRS) VD (OR\|ORS), same HOW | alternative | R07 | similar | ✎ |
| W16 | idem, different HOW | disjoint | R09 | disjoint | ✔ |
| W17 | (SR\|SRS) VD OD, any HOW | disjoint | R07 / R08 / R09 | similar if the HOW is same or partial | ✎ |
| W18 | SD VR (OR\|ORS), same HOW | alternative | R07 | similar | ✎ |
| W19 | idem, different HOW | disjoint | R09 | disjoint | ✔ |
| W20 | SD VR OD, different HOW | disjoint | R12 | disjoint | ✔ |
| W21 | SD VR OD, same HOW | alternative | R10 | alternative | ✔ |
| W22 | SD VD OD, same HOW | alternative | R10 | alternative | ✔ |
| W23 | SD VD OD, different HOW | disjoint | R12 | disjoint | ✔ |
| W24 | SD VD (OR\|ORS), same HOW | alternative | R07 | similar | ✎ |
| W25 | idem, different HOW | disjoint | R09 | disjoint | ✔ |
| W26 | W-W hierarchical, same HOW | generalise | R04 | generalise | ✔ |
| W27 | W-W hierarchical, different HOW | alternative | R06 | disjoint | ✎ |
| W28 | W-W same, same HOW | duplicate | R01 | duplicate | ✔ |
| W29 | W-W same, different HOW | alternative | R03 | similar | ✎ |
| W30 | W-W similar, same HOW | alternative | R07 | similar | ✎ |
| W31 | W-W similar, different HOW | disjoint | R09 | disjoint | ✔ |
| W32 | W-W no link, same HOW | alternative | R10 | alternative | ✔ |
| W33 | W-W no link, different HOW | disjoint | R12 (R11 if PARTIAL) | disjoint | ✔ |
| W34 | W-SW linked, same HOW | similar | R07 | similar | ✔ |
| W35 | W-SW linked, different HOW | disjoint | R09 | disjoint | ✔ |
| W36 | W-SW no link, same HOW | alternative | R10 | alternative | ✔ |
| W37 | W-SW no link, different HOW | disjoint | R12 | disjoint | ✔ |
| W38 | SW-SW linked, same HOW | similar | R07 | similar | ✔ |
| W39 | SW-SW linked, different HOW | disjoint | R09 | disjoint | ✔ |
| W40 | SW-SW no link, same HOW | alternative | R10 | alternative | ✔ |
| W41 | SW-SW no link, different HOW | disjoint | R12 | disjoint | ✔ |

In total, 15 WHAT rules change fully or partly (13 fully, W01 and W11 partly) and 26 are kept. A new PARTIAL HOW column adds four outcomes (R02, R05, R08, R11).

### HOW rules (13)

| v1 rule | v1 | v2 |
|---|---|---|
| H01 SR VR OR | same | SAME (V and O related) ✔ |
| H02 SR VR OD | different | PARTIAL (same action) ✎ |
| H03 SR VD OR | same | PARTIAL (same target only) ✎ |
| H04 SR VD OD | different | DIFFERENT ✔ |
| H05 SD VR OR | same | SAME ✔ |
| H06 SD VR OD | different | PARTIAL ✎ |
| H07 SD VD OD | different | DIFFERENT ✔ |
| H08 SD VD OR | different | PARTIAL ✎ |
| H09 T-W | same if linked | PARTIAL if the term is linked to the object or the action ✎ |
| H10 T-SW | same if linked | PARTIAL if linked ✎ |
| H11 W-W | same if linked | SAME if equal, synonym or hierarchical; PARTIAL if only similar ✎ |
| H12 W-SW | same if linked | PARTIAL if linked ✎ |
| H13 SW-SW | same if linked | PARTIAL if linked ✎ |
| (missing HOW) | different | U02 unknown ✎ |

## 4. Evaluating v2

- `idearel evaluate --rules v2` runs v2 on the 240 annotated pairs; `scripts/tune.py --rules v2` evaluates it with
  nested cross-validation (20 x 5 folds, seed 2026; outputs in `results/tuning/`).
- The v2 table was derived from the definitions of the relationship types; R06 and the generic-term check were
  added after an error analysis on these same 240 pairs. A fair evaluation of v2 needs annotated pairs that were
  not used here (future work).
