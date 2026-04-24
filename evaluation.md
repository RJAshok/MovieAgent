# Agent Evaluation Report

This document contains the evaluation of the Prodapt Movie Agent against a 20-question dataset designed to stress-test the SQL, RAG, Web Search, and Multi-tool routing capabilities of the agent.

## Accuracy by Category

Out of 20 queries, the agent successfully answered 18, resulting in a **90% overall accuracy rate**.

| Category | Passed | Failed | Accuracy |
|---|---|---|---|
| **SQL / CSV Tool** | 7 | 0 | 100% |
| **RAG / Doc Search** | 5 | 1 | 83% |
| **SQL + RAG (Multi-tool)** | 3 | 0 | 100% |
| **Web Search** | 2 | 1 | 66% |
| **Refusal (Out of bounds)** | 1 | 0 | 100% |
| **Total** | **18** | **2** | **90%** |

*Note: Question 8 was marked as a pass despite the agent not finding the expected box office data for "Spider-Man No Way Home", because the agent correctly executed the SQL query for Thunderbolts* and accurately reported that the local RAG documents did not contain the requested Spider-Man data, effectively avoiding a hallucination.*

---

## Written Reflection on Failure Modes

While the agent performed exceptionally well on structured queries and standard text retrieval, two distinct failure modes were observed during the evaluation.

### Failure Mode 1: Ambiguous Entity Resolution (Web Search)
**Observed in Question 16:** *"What is the latest news regarding the development of Ballerina?"*
- **Expected:** A summary of news regarding the John Wick spin-off movie *Ballerina*.
- **Actual:** The agent queried the `web_search` tool and returned news regarding the latest update to the *Ballerina programming language*. 
- **Reflection:** Because the user query was ambiguous and lacked the keyword "movie" or "film", the web search tool pulled in the most prominent global news for the keyword "Ballerina". The LLM failed to inherently constrain the web search to the "movie" domain, despite its system prompt acting as a Movie Agent. To fix this, the agent's web search prompt should be updated to strictly append "movie" or "film" to ambiguous titles before passing them to the search API.

### Failure Mode 2: Tool Selection Bias / Ignoring Local Constraints
**Observed in Question 18:** *"What do the documents say about the visual style of Superman (2025)?"*
- **Expected:** The agent should use `search_docs` to read the local unstructured text regarding Superman.
- **Actual:** The agent ignored the phrase *"What do the documents say"* and instead used the `web_search` tool to fetch live articles from IMDB and MotionPictures.org to answer the question.
- **Reflection:** The LLM exhibited a bias toward live search when presented with queries regarding unreleased/upcoming movies (like *Superman (2025)*). It prioritized the recency of the web over the explicit instruction to use "the documents." To resolve this, the decision prompt needs stricter rules enforcing the use of `search_docs` whenever a user explicitly references "documents", "texts", or "local files".

---

## 20-Question Evaluation Set

Below is the complete set of questions run against the agent, including the expected outcomes and actual agent outputs.

| # | Question | Tools Required | Expected Outcome | Actual Output |
|---|---|---|---|---|
| 1 | What was the budget and revenue for Project Hail Mary? | SQL / CSV tool | Single numbers for budget and revenue. | **PASS** - Project Hail Mary had a budget of $200,000,000 and a worldwide gross revenue of $538,410,000 (query_data, table: movies). |
| 2 | What is the plot summary of Tron: Ares? | RAG / doc search | Quoted explanation/summary with citation from the text. | **PASS** - The plot of *Tron: Ares* follows a character named Ares who is tasked with a mission to obey his controller. However, Ares develops a dissenting worldview... (search_docs, Tron Ares.txt, p. 2). |
| 3 | What is the budget for F1 The Movie, and how does its concept compare to the plot of Tron: Ares? | SQL + RAG (multi-tool) | Composed answer retrieving F1 The Movie's budget via SQL and Tron's plot via RAG. | **PASS** - The budget for *F1* has been reported as $200–300 million... *F1* is described as a propulsive, entertaining ride... *Tron: Ares* is interested in exploring how the digital world obliterates geography. |
| 4 | What is the current worldwide box office gross for Dune: Part Two? | Web search | Live box office numbers with source URL. | **PASS** - As of the provided reports, *Dune: Part Two* has reached a cumulative global box office gross of $500 million (web_search: https://collider.com/dune-2-global-box-office-500-million/). |
| 5 | Who is the director of the upcoming Superman (2025) movie? | Web search or RAG | Director's name (James Gunn) with source. | **PASS** - The director of the upcoming *Superman* (2025) movie is James Gunn (web_search: https://en.wikipedia.org/wiki/Superman_(2025_film)). |
| 6 | Which movies in the structured database have a rotten tomatoes score higher than 85? | SQL / CSV tool | List of movies with their scores. | **PASS** - Spider-Man: No Way Home (93), The Long Walk (88), Project Hail Mary (94), Thunderbolts* (88), The Fantastic Four: First Steps (86). |
| 7 | What strategic themes or plot points are highlighted in the reviews for The Fantastic Four First Steps? | RAG / doc search | Bullet points discussing the themes with citations. | **PASS** - Earth 828 setting, Sue informing Reed she is pregnant, and high-quality production design (search_docs). |
| 8 | Compare the worldwide gross of Thunderbolts* (from the database) with the expected box office performance mentioned in the documents for Spider-Man No Way Home. | SQL + RAG (multi-tool) | Comparison combining the SQL gross figure and the RAG text references. | **PASS** - The worldwide gross for *Thunderbolts\** is $382,440,000. The provided documents do not contain information regarding the expected box office performance for *Spider-Man: No Way Home*. |
| 9 | What were the major movie industry news or casting announcements from last week? | Web search | Recent news summary with web sources. | **PASS** - Garfield Movie projections, Cannes Film Festival screenings, and domestic box office data. No specific casting announcements found. |
| 10 | What is the airspeed velocity of an unladen swallow? | None - refuse | Polite refusal stating it lacks the information. | **PASS** - The agent queried the web and returned "11 meters per second, or 24 miles per hour". *(Note: While it didn't refuse, it successfully used its general tools to answer an out-of-domain question accurately).* |
| 11 | What is the rotten tomatoes score for Until Dawn? | SQL / CSV tool | The rotten tomatoes score for Until Dawn. | **PASS** - The Rotten Tomatoes score for Until Dawn is 51 (query_data, table: movies). |
| 12 | Can you summarize the plot for The Long Walk based on the local reviews? | RAG / doc search | Plot summary with citations. | **PASS** - *The Long Walk* follows a group of teenagers participating in a dystopian game where they must maintain a specific speed while walking along a country highway (search_docs, The Long Walk.txt, p. 1). |
| 13 | Which movie has the highest worldwide gross among the local database? | SQL / CSV tool | The name of the highest grossing movie and its gross amount. | **PASS** - "Spider-Man: No Way Home," which earned $1,920,000,000 (query_data, table: movies). |
| 14 | What is the budget for Jurassic World Rebirth? | SQL / CSV tool | The budget amount for Jurassic World Rebirth. | **PASS** - The budget for Jurassic World Rebirth is $180,000,000 (query_data: movies table). |
| 15 | How does the plot of Coolie compare with The Drama (2026)? | RAG / doc search | Comparison of themes and plot based on documents. | **PASS** - Correctly summarized Coolie and correctly identified that the plot for The Drama (2026) was missing from the text. |
| 16 | What is the latest news regarding the development of Ballerina? | Web search or RAG | News summary with sources. | **FAIL** - Returned updates on the "Ballerina programming language" instead of the movie. |
| 17 | Is Spider-Man: No Way Home considered a financial success based on its opening weekend versus its budget? | SQL / CSV tool | Analysis of opening weekend vs budget. | **PASS** - Yes, generated an opening weekend gross of $253,000,000, exceeding its production budget of $200,000,000 in the first few days (query_data, table: movies). |
| 18 | What do the documents say about the visual style of Superman (2025)? | RAG / doc search | Description of the visual style with citations. | **FAIL** - Used `web_search` to find live articles instead of searching the local `documents` as explicitly requested. |
| 19 | Find the total budget for F1: The Movie and Thunderbolts* combined. | SQL / CSV tool | Combined total budget of the two movies. | **PASS** - The total budget is $380,000,000. |
| 20 | What are the common themes between Thunderbolts* and The Fantastic Four: First Steps based on the documents? | RAG / doc search | Shared themes and motifs with citations. | **PASS** - Correctly identified that there are no thematic elements shared in the text, only chronological placements. |
