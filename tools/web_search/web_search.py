from typing import List, Dict, Any
from duckduckgo_search import DDGS

def web_search(query: str) -> List[Dict[str, Any]]:
    """
    Perform a live web search using DuckDuckGo to fetch recent or real-world information.
    
    WHEN TO USE:
    - Use this tool to find current events, recent news, or information that is not present in local datasets.
    - Use this tool when the user specifically asks to "search the web" or "look up online".
    
    WHEN NOT TO USE:
    - Do NOT use this tool for information that can be found in the local movie reviews (use search_docs).
    - Do NOT use this tool for numerical/structured data about the sample movies (use query_data).
    
    The input should be a concise search query (under 10 words).
    Returns the top 3 search results.
    """
    if not query or not query.strip():
        return [{"error": "Empty query provided."}]
        
    try:
        ddgs = DDGS()
        results = ddgs.text(query.strip(), max_results=3)
        
        if not results:
            return []
            
        formatted_results = []
        for r in results:
            formatted_results.append({
                "snippet": r.get("body", ""),
                "url": r.get("href", ""),
                "date": "N/A"  # DDG text search doesn't consistently provide publish date
            })
            
        return formatted_results
    except Exception as e:
        return [{"error": f"Search API error: {str(e)}"}]
