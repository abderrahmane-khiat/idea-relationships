# SPARQL queries of the structure-based matcher

The four queries of Appendix A of the paper, as used by the original prototype. All knowledge sources were
deployed locally (no public endpoint was queried):

- DBpedia Spotlight 1.1 (local service) to find the DBpedia resource of a term;
- DBpedia release 2022-12 in a local Blazegraph 2.1.5 store;
- Wikidata RDF dump 20230607 in a local Wikidata Query RDF 0.3.137 instance.

| File | Query | Used for |
|---|---|---|
| `1_dbpedia_concept_lookup.rq` | DBpedia resource with a given label | linking a term to DBpedia |
| `2_dbpedia_to_wikidata.rq` | `owl:sameAs` link from DBpedia to Wikidata | moving from DBpedia to Wikidata |
| `3_wikidata_subclass.rq` | `wdt:P279*` path in either direction between two labels | subclass / superclass of subjects and objects |
| `4_wikidata_predicate_synonym.rq` | Wikidata property whose label or alias matches both predicates | synonym predicates |

The example values (`"facade"`, `"emergency TV"`, `"composed of"`, `"display"`) are the ones printed in the paper;
the prototype replaced them with the terms being compared. Each query was logged with its parameters. The
`PREFIX` lines for `wikibase:` and `skos:` in query 4 are added here; the paper's listing leaves them implicit
(they are predefined on Wikidata Query endpoints).

The framework in `framework/v1` offers the subclass check of query 3 as its `sparql` structure backend
(`--set structure.backend=sparql`; endpoint `structure.sparql_endpoint`, default
`http://localhost:9999/blazegraph/namespace/wdq/sparql`): one query
per term pair, a `wdt:P279+` path in either direction between the two labels (see
`framework/v1/src/idearel/matching/matchers.py`, `_sparql`). Its default backend is WordNet, which needs no
endpoint.
