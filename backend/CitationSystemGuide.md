# Citation System Guide

This document explains how the citation system works in `backend/rag_engine.py`.

The goal is simple:

- Generate an answer from retrieved documents.
- Attach inline references like `[1]`, `[2]` to parts of that answer.
- Return structured citation metadata so the frontend can show source details.

If a developer wants to understand how citations are created, this should be the first file to read.

## Why This Citation System Exists

Large language models can answer questions correctly, but users also need to know:

- Which document supported the answer
- Which file the answer came from
- Which snippet in the source is the best evidence

This citation system improves trust. It tries to connect each answer sentence to one of the retrieved documents.

## High-Level Flow

The citation pipeline happens after retrieval and after answer generation.

End-to-end flow:

1. User asks a question.
2. The system retrieves relevant documents from Chroma and BM25 search.
3. The LLM generates an answer using those retrieved documents.
4. The answer text is split into smaller claims or sentence-like parts.
5. Each claim is compared against the retrieved documents.
6. If a supporting source is found, the code adds an inline citation marker like `[1]`.
7. A `citations` list is returned with metadata such as source name, snippet, page number, and sometimes a semantic score.

So the citation system is not part of retrieval itself. It is a post-processing step applied to the answer.

## Where The Main Logic Lives

The main citation logic is in these functions inside `backend/rag_engine.py`:

- `_normalize_match_text`
- `_tokenize_match_text`
- `_split_source_spans`
- `_cosine_similarity`
- `_find_claim_citation`
- `_annotate_line_with_citations`
- `_build_answer_citations`

The main answer flow that calls the citation system is inside `DeepContextEngine.get_answer`.

## Core Idea

Think of the citation system as a second pass over the answer.

The LLM writes the answer first.

Then the citation logic asks:

"For this sentence, which retrieved document most likely supports it?"

If it finds a good match, it adds a marker like `[1]` into the answer and stores citation details separately.

## Helper Functions

### 1. `_normalize_match_text`

Purpose:

- Clean text before matching

What it does:

- Converts text to lowercase
- Removes existing citation markers like `[1]`
- Removes punctuation
- Collapses repeated whitespace

Why this matters:

Matching becomes more reliable when formatting differences are removed.

Example:

- Original: `Objective: Ensure Control and Compliance [1]`
- Normalized: `objective ensure control and compliance`

### 2. `_tokenize_match_text`

Purpose:

- Convert cleaned text into useful tokens

What it does:

- Extracts words and alphanumeric tokens
- Removes very short tokens

Why this matters:

The fallback citation matching logic uses token overlap. It needs a token list, not raw text.

Example:

- Text: `The main objective is control and compliance.`
- Tokens: `main`, `objective`, `control`, `compliance`

### 3. `_split_source_spans`

Purpose:

- Break a document chunk into smaller readable spans

What it does:

- Splits the chunk on line breaks and sentence boundaries
- Keeps reasonably sized spans

Why this matters:

Retrieved document chunks can be large. When a citation is shown in the UI, a short proof snippet is more useful than a huge paragraph.

### 4. `_cosine_similarity`

Purpose:

- Compare semantic similarity between two embedding vectors

Why this matters:

This is how the system handles paraphrased answers. The LLM may not repeat the source text exactly, but the meaning may still be very close.

## Main Citation Matcher

### `_find_claim_citation`

This is the most important citation function.

Inputs:

- `claim_text`: one sentence or sentence-like part of the answer
- `docs`: the retrieved documents
- `citation_index`: the current citation number
- `chunk_embeddings`: precomputed embeddings for retrieved chunks
- `embed_fn`: embedding function used for the claim text

Output:

- A citation dictionary if a match is found
- `None` if no strong source is found

This function uses two levels of matching.

## Level 1: Semantic Matching

This is the stronger and smarter layer.

Process:

1. Convert the answer claim into an embedding.
2. Compare that embedding to the embeddings of the retrieved document chunks.
3. Find the document with the highest similarity score.
4. If the score passes the threshold, return that document as the citation source.

Why this is useful:

- The source and the answer may say the same thing using different words.
- Exact text matching would miss that.
- Embedding similarity can still connect them.

Example:

- Source says: `ensure control and compliance`
- Answer says: `support better authorization control and compliance`

The words are not identical, but the meaning is very similar. Semantic matching helps here.

The current similarity threshold is `0.50`.

That value is a tradeoff:

- Lower threshold means more citations, but also more risk of wrong citations
- Higher threshold means safer citations, but more missing citations

## Level 2: Text Matching Fallback

If semantic matching does not succeed, the code falls back to more direct matching.

It tries three things:

1. Exact substring match
2. Normalized text match
3. Token overlap match on smaller spans

### Exact substring match

If the exact answer claim appears in a retrieved document chunk, the function returns it immediately.

### Normalized text match

If formatting differences are the only issue, normalized matching may still find the claim.

### Token overlap match

If exact matching fails, the function compares the answer tokens against token sets from source spans.

This is a weaker fallback than semantic matching, but it is still useful for near-exact wording.

The current token-overlap threshold is intentionally a little loose so the system can recover citations more often.

## What A Citation Object Contains

A citation usually contains:

- `index`: number used in the answer, like `1`
- `sourceName`: file name or source label
- `page`: page number if available
- `snippet`: short source excerpt

Sometimes it may also contain:

- `semanticScore`: similarity score from embedding matching
- `charStart`
- `charEnd`
- `isFallback`

The answer text and the citation metadata are kept separate.

Example:

Answer:

`The main objective is to ensure control and compliance. [1]`

Citation metadata:

```json
{
  "index": 1,
  "sourceName": "cbdcindus-651_dispute_maker_checker_flow.md",
  "page": null,
  "snippet": "To implement functionality for dispute resolution with support for a maker-checker authorization process to ensure control and compliance."
}
```

## How Inline Citations Are Added

### `_annotate_line_with_citations`

This function takes one line of answer text and tries to attach citations to that line.

What it does:

- Skips lines that should not be modified
- Preserves list bullets and numbering
- Splits the line into smaller claim-like parts using punctuation
- Calls `_find_claim_citation` for each part
- Appends ` [1]`, ` [2]`, and so on when a match is found

Important behavior:

- It avoids touching code fences and markdown separators
- It keeps the original line structure as much as possible

This matters because the answer may contain:

- plain paragraphs
- bullet points
- numbered lists
- code blocks

The citation logic should not break that formatting.

## How Full Answer Citation Assembly Works

### `_build_answer_citations`

This function processes the full answer, not just one line.

What it does:

- Splits the answer into segments
- Preserves fenced code blocks exactly
- Processes normal text lines through `_annotate_line_with_citations`
- Builds the final annotated answer text
- Builds the final `citations` list

### Fallback Citation Behavior

If no sentence-level citations are found, the code still returns fallback citations based on the retrieved documents.

Why this was added:

- Without fallback citations, the frontend may show no sources even when valid documents were retrieved.
- That makes the result look weaker than it actually is.

What fallback means:

- It does not prove that a specific sentence matched a specific span
- It only says these documents were part of the retrieved evidence

This is useful for user experience, but it is weaker than true claim-level grounding.

## How The Citation System Is Called In `get_answer`

Inside `DeepContextEngine.get_answer`, the flow is:

1. Reload the vector database if needed.
2. Retrieve relevant documents using `_hybrid_search`.
3. Generate the answer from those documents using the LLM.
4. Precompute embeddings for the retrieved chunks.
5. Pass the answer and the retrieved docs into `_build_answer_citations`.
6. Return the annotated answer and the citation list.

Important detail:

The code precomputes embeddings for retrieved chunks before calling the citation builder.

That is done for speed.

Instead of computing chunk embeddings repeatedly for every claim, the code computes them once and reuses them.

## Why Hybrid Search Matters For Citations

The citation system only works with the documents it receives from retrieval.

That means citation quality depends heavily on retrieval quality.

If the correct document is not in `valid_docs`, then citations cannot be correct.

In other words:

- Good retrieval leads to good citations
- Weak retrieval leads to weak citations

This is why the code uses hybrid retrieval:

- semantic similarity from Chroma
- lexical matching from BM25
- rank fusion to combine both

## Recent Important Changes Around The Citation System

These are the key improvements currently present in the implementation.

### 1. Semantic citation matching was added

Before this, citations depended mostly on direct text overlap.

Now the system can handle paraphrased claims much better.

This is the most important improvement.

### 2. Chunk embeddings are precomputed

Retrieved chunk embeddings are computed once and reused while matching claims.

This improves efficiency.

### 3. Fallback citations were added

Even if no claim-level match is found, the response still returns source references for the retrieved documents.

This helps the frontend and improves the user experience.

### 4. Matching thresholds were made slightly looser

The fallback token overlap logic is more forgiving than before.

This helps avoid empty citation results, especially for imperfect LLM wording.

## Related Changes That Are Not Citation Logic

Two separate changes exist in the same file but are not really part of citation generation.

### Embedding initialization change

The embedding model now loads from the local Hugging Face cache using:

- `sentence-transformers/all-MiniLM-L6-v2`
- `local_files_only=True`

Why this was done:

- To stop Celery workers from making network calls to Hugging Face
- To avoid noisy retry warnings in offline environments

### Chroma telemetry change

The file also contains a no-op telemetry class and config for Chroma.

Why this was done:

- To stop noisy Chroma telemetry errors during startup and runtime

These changes support stability, but they are not part of the citation algorithm itself.

## Strengths Of The Current Design

- Works with markdown answers
- Preserves code blocks
- Can match paraphrased content
- Still returns sources even when exact sentence-level grounding fails
- Returns structured metadata that is easy for the frontend to render

## Limitations Of The Current Design

### 1. Citation quality depends on retrieval quality

If the correct source document is not retrieved, the citation system cannot fix that.

### 2. Claim splitting is simple

The code splits claims mostly based on punctuation.

That works reasonably well, but it is not full linguistic parsing.

### 3. Fallback citations are weaker than true grounding

A fallback citation means:

"This document was retrieved"

not necessarily:

"This exact sentence is proven by this exact span"

### 4. Threshold tuning is heuristic

The semantic threshold and overlap threshold are practical values, not mathematically guaranteed values.

They may need tuning for different document sets.

### 5. Claim embeddings are still computed claim by claim

The system precomputes chunk embeddings, which is good.

But claim embeddings are still created one at a time. For very long answers, batching claims would be more efficient.

## Recommended Future Improvements

If the team wants to improve this further, these would be sensible next steps.

### 1. Batch claim embeddings

Instead of embedding each answer claim one by one, batch all claims together.

This would improve performance.

### 2. Distinguish citation types in the response

Return a field like:

- `semantic`
- `exact`
- `token_overlap`
- `fallback`

This would make the frontend and debugging better.

### 3. Deduplicate similar citations

Many answer lines may point to the same source snippet.

Those duplicates could be merged more cleanly.

### 4. Add confidence rules

Very weak semantic matches should be rejected rather than shown as confident citations.

### 5. Improve snippet selection

Right now snippet selection is practical but simple.

It could be made smarter by choosing the most precise sentence window around the matched claim.

## Simple Example

Suppose the retrieved source says:

`To implement functionality for dispute resolution with support for a maker-checker authorization process to ensure control and compliance.`

The LLM answer says:

`The main objective is to ensure control and compliance through a maker-checker authorization flow.`

What happens:

1. The answer is generated.
2. The sentence is treated as one claim.
3. `_find_claim_citation` compares that claim to the retrieved docs.
4. Semantic matching finds the dispute document as the best source.
5. The answer becomes:

`The main objective is to ensure control and compliance through a maker-checker authorization flow. [1]`

6. The citation list stores the source name and snippet.

## Summary

The citation system is a post-processing layer over the LLM answer.

It does not create the answer itself.

Its job is to connect answer claims back to retrieved evidence and make the response easier to trust.

The most important parts are:

- retrieval quality
- claim splitting
- semantic claim-to-document matching
- fallback source handling

If you are debugging citations, always inspect these four things first:

1. Were the right documents retrieved?
2. Did the LLM answer stay close to the source?
3. Did `_find_claim_citation` find a match?
4. Did the response fall back to doc-level citations instead of claim-level citations?
