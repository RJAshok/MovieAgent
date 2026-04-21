import os
from typing import List, Dict, Any
from tavily import TavilyClient

def web_search(query: str) -> List[Dict[str, Any]]:
    """
    Perform a live web search using Tavily API to fetch recent or real-world information.
    
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
        return []
        
    try:
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            try:
                from dotenv import load_dotenv
                load_dotenv()
                api_key = os.environ.get("TAVILY_API_KEY")
            except ImportError:
                pass
                
        if not api_key:
            return [{"error": "TAVILY_API_KEY environment variable is not set."}]
            
        client = TavilyClient(api_key=api_key)
        response = client.search(query=query.strip(), max_results=3)
        
        results = response.get("results", [])
        if not results:
            return []
            
        formatted_results = []
        for r in results:
            formatted_results.append({
                "snippet": r.get("content", ""),
                "url": r.get("url", ""),
                "date": r.get("published_date", "N/A")
            })
            
        return formatted_results
    except Exception as e:
        return [{"error": str(e)}]
