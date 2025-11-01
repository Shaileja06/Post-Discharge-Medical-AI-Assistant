from duckduckgo_search import DDGS
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class WebSearchTool:
    """Web search tool using DuckDuckGo"""
    
    def __init__(self, max_results: int = 5):
        self.max_results = max_results
    
    def search(self, query: str, num_results: int = None) -> List[Dict]:
        """
        Search the web using DuckDuckGo
        
        Returns:
            List of search results with title, body, and href
        """
        try:
            num_results = num_results or self.max_results
            logger.info(f"Performing web search for: {query}")
            
            with DDGS() as ddgs:
                results = list(ddgs.text(
                    query, 
                    max_results=num_results,
                    region='wt-wt',  # Worldwide
                    safesearch='moderate'
                ))
            
            logger.info(f"Found {len(results)} web results")
            return results
            
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return []
    
    def format_results(self, results: List[Dict]) -> str:
        """Format search results into readable text"""
        if not results:
            return ""
        
        formatted = []
        for idx, result in enumerate(results, 1):
            formatted.append(
                f"[{idx}] {result.get('title', 'No title')}\n"
                f"URL: {result.get('href', 'No URL')}\n"
                f"{result.get('body', 'No description')}\n"
            )
        
        return "\n---\n\n".join(formatted)