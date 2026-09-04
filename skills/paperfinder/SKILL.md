---
name: paperfinder
description: Find papers from a topic or keyword description, expanding through the citation graph. Use when the user wants to discover work on a topic they have no anchor papers for, find a half-remembered paper, or check what exists before starting something.
---

# Paper Finder

Discovery from a cold start. The user gives a topic, a description, or a fuzzy
memory; you return a ranked, verified set of papers.

Boundary with the neighbouring skills: `/paperfinder` retrieves, `/lit-review`
argues. Use `/lit-review` when the user already has anchor papers and wants
related-work framing organized by axis. Use `/paper` to read one paper in depth.
Handing a finished search to `/lit-review` is the normal flow.

## Route the query first

Three intents, and they want different work. Decide which before searching.

- **Navigational** — a specific paper the user half-remembers. "The canary
  extraction one, maybe 2023, I think Carlini." Search on the distinctive
  fragment, filter by author and year, stop as soon as it resolves. Do not
  snowball; one paper is the whole answer.
- **Semantic** — papers about a topic or matching a description. The default,
  and the one the snowball loop below is for.
- **Metadata** — constraint-shaped. "Influential pre-2020 work on X", "everything
  from this group since 2024". Answer with filters and sorting, not expansion.

If the query mixes intents, say which you are treating as primary.

## Retrieval

OpenAlex and arXiv are the backbone: no key, no rate limit in practice, and
OpenAlex carries the citation graph. Web search is a lead generator only.

```bash
# Seed set. Add &filter=from_publication_date:2024-01-01 to constrain recency.
curl -s "https://api.openalex.org/works?search=membership+inference+attack&per-page=25" \
  | jq -r '.results[] | "\(.id)\t\(.publication_year)\t\(.cited_by_count)\t\(.primary_location.source.display_name // "?")\t\(.title)"'

# Forward hop: who cites this work
curl -s "https://api.openalex.org/works?filter=cites:W2535690855&per-page=50&sort=cited_by_count:desc"

# Backward hop: what it cites (already on the record, no extra call)
curl -s "https://api.openalex.org/works/W2535690855" | jq -r '.referenced_works[]'

# Fresh preprints the graph has not absorbed yet. https is required; http 301s.
curl -sG 'https://export.arxiv.org/api/query' \
  --data-urlencode 'search_query=all:"membership inference"' \
  --data-urlencode 'sortBy=submittedDate' --data-urlencode 'sortOrder=descending' \
  --data-urlencode 'max_results=20'
```

Notes that will otherwise cost you a debugging round:

- `primary_location.source.display_name` is null on some conference papers.
  Fall back to `.type` and the DOI prefix rather than reporting no venue.
- OpenAlex does not reliably expose arXiv ids, so dedup on normalized DOI first
  and normalized title second.
- Add `&mailto=<email>` to OpenAlex calls for their faster pool if the user wants
  it. Ask before putting their address in a URL; do not default it in.
- Semantic Scholar's keyless endpoint returns 429 essentially always. Use it only
  when `S2_API_KEY` is set, and then only to enrich — `tldr` summaries and venue
  strings. Never make the search depend on it.

**Web search is a lead generator, never a source of record.** It is for the two
things the APIs miss: workshop papers and blog-adjacent work without a DOI, and
things posted in the last few days. Anything it surfaces must be resolved back to
an OpenAlex or arXiv record before it enters the output. A lead that will not
resolve gets reported as an unresolved lead, not as a citation.

## The snowball loop

Keyword search finds the neighbourhood; the citation graph finds the field.

1. Seed with keyword search. Try the user's terms and the field's terms — they
   often differ, and the seed set is what everything downstream inherits.
2. Judge the seed on titles and abstracts. Keep the plausible ones.
3. Hop forward and backward one level from the keepers.
4. Dedup, re-rank, judge again.
5. Repeat until saturation.

**Stop on saturation, not on a result count.** When a hop returns mostly papers
already seen, the neighbourhood is closed and further hops buy nothing. Report it
as a completeness signal: "saturated after 3 hops, 87 unique papers" says
something real, where "here are 20 results" does not. If you stop before
saturation — the graph fans out too wide, the topic is too broad — say so
explicitly and say what was left unexplored.

Effort has two settings. **Fast**: seed plus one hop, top results only, for
orienting in an unfamiliar area. **Diligent**: hop to saturation, multiple seed
phrasings, venue sweeps. Default to fast and offer diligent; say which you ran.

## Ranking

Combine, in this order of weight: relevance to the actual query, then citation
count as an importance prior, then recency. Citation count is a signal about
influence, not quality, and it is biased against anything recent — never let it
bury a 2026 paper under a 2019 one. For a topic the user does not know yet, the
high-citation cluster is the canon and is worth surfacing explicitly as such.

## Output

For each paper: **claim in one sentence**, venue and year, citation count, and
why it matched. Sort into *directly on topic*, *adjacent, worth a look*, and
*surfaced but not relevant* — the last as bare titles, so the user can see what
was ruled out without reading summaries of papers they will not use.

Write the result to a markdown note so it survives the session and can be handed
to `/lit-review`. Put it where the user is working, or ask. Include the queries
run, the hop count, and whether it saturated — a search whose method is not
recorded cannot be resumed or trusted later.

## Rules

- **Only emit records that came back from an API call in this session.** Not from
  memory, not from a plausible-looking web result. This is the rule that makes
  fabricated citations mechanically impossible, and it is the one failure mode
  that would make the whole skill worse than useless.
- **Report counts honestly.** If OpenAlex says 4492 papers cite the anchor and you
  looked at 50, say that.
- **Anything within ~6 months is concurrent, not prior.** Flag it as such.
- **Distinguish what a paper proves from what it claims.** Abstracts overstate.
- **Prefer the peer-reviewed version** when both it and the preprint exist.
- **Exclude against an existing bib on request.** If the user points at a `.bib`,
  drop what they already have and report only what is new.
- **Say when the search was likely incomplete.** A topic that spans communities —
  ML and security, say — is easy to half-cover. Name the community you did not
  sweep rather than presenting the result as exhaustive.
