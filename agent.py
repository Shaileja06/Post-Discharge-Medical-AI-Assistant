from typing import TypedDict, Annotated, Sequence, List, Dict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
import operator
from vector_store import VectorStore
from web_search import WebSearchTool
from config import settings
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    context: str
    query: str
    citations: List[Dict]
    web_results: List[Dict]
    needs_web_search: bool


class RAGAgent:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.web_search = WebSearchTool()
        
        # Initialize Gemini 2.5 Flash
        self.llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.1,
            convert_system_message_to_human=True
        )
        
        # Create the graph
        self.graph = self._create_graph()
    
    def retrieve_context(self, state: AgentState) -> AgentState:
        """Retrieve relevant context from vector store with citation tracking"""
        query = state["query"]
        
        logger.info(f"Retrieving context for query: {query}")
        results = self.vector_store.search(query, n_results=5)
        
        # Combine retrieved documents with citations
        context_parts = []
        citations = []
        
        for idx, (doc, metadata, distance) in enumerate(
            zip(results["documents"], results["metadatas"], results["distances"]), 
            start=1
        ):
            # Add citation marker to document
            citation_id = f"[{idx}]"
            context_parts.append(f"{citation_id} {doc}")
            
            # Store citation info
            citations.append({
                "id": idx,
                "content": doc[:200] + "..." if len(doc) > 200 else doc,
                "metadata": metadata,
                "relevance_score": 1 - distance  # Convert distance to similarity
            })
        
        context = "\n\n---\n\n".join(context_parts)
        
        # Check if context is sufficient
        needs_web_search = self._is_context_insufficient(context, query)
        
        logger.info(f"Retrieved {len(results['documents'])} relevant chunks")
        logger.info(f"Context sufficiency: {'INSUFFICIENT' if needs_web_search else 'SUFFICIENT'}")
        
        return {
            **state,
            "context": context,
            "citations": citations,
            "needs_web_search": needs_web_search,
            "messages": state["messages"] + [
                AIMessage(content=f"Retrieved {len(results['documents'])} relevant chunks from the knowledge base")
            ]
        }
    
    def _is_context_insufficient(self, context: str, query: str) -> bool:
        """
        Determine if retrieved context is insufficient
        
        Criteria:
        - Too short
        - Low relevance indicators
        - Generic content
        """
        # Empty or very short context
        if not context or len(context.strip()) < 100:
            return True
        
        # Check for common "not found" indicators
        insufficient_indicators = [
            "no information",
            "not available",
            "cannot find",
            "no data",
            "insufficient"
        ]
        
        context_lower = context.lower()
        if any(indicator in context_lower for indicator in insufficient_indicators):
            return True
        
        # Check if context is too generic (low keyword overlap)
        query_keywords = set(query.lower().split())
        context_keywords = set(context.lower().split())
        
        overlap = len(query_keywords & context_keywords)
        if overlap < len(query_keywords) * 0.3:  # Less than 30% keyword match
            return True
        
        return False
    
    def web_search_node(self, state: AgentState) -> AgentState:
        """Perform web search for additional context"""
        query = state["query"]
        
        logger.info(f"Performing web search for: {query}")
        
        # Search the web
        web_results = self.web_search.search(query, num_results=5)
        
        # Format web results
        web_context_parts = []
        for idx, result in enumerate(web_results, start=len(state["citations"]) + 1):
            citation_id = f"[{idx}]"
            content = f"{result.get('title', '')}\n{result.get('body', '')}"
            web_context_parts.append(f"{citation_id} {content}")
        
        web_context = "\n\n---\n\n".join(web_context_parts)
        
        # Combine with existing context
        combined_context = state["context"]
        if web_context:
            combined_context += f"\n\n=== WEB SEARCH RESULTS ===\n\n{web_context}"
        
        logger.info(f"Found {len(web_results)} web results")
        
        return {
            **state,
            "context": combined_context,
            "web_results": web_results,
            "messages": state["messages"] + [
                AIMessage(content=f"Performed web search and found {len(web_results)} additional sources")
            ]
        }
    
    def generate_response(self, state: AgentState) -> AgentState:
        """Generate response using Gemini with context and citations"""
        context = state["context"]
        query = state["query"]
        has_web_results = len(state.get("web_results", [])) > 0
        
        # Create a comprehensive prompt for Gemini
        system_prompt = """You are a helpful AI assistant with access to a knowledge base and web search results.
Your task is to answer questions based on the provided context.

Rules:
1. Answer the question using information from the provided context
2. **ALWAYS cite your sources using the citation markers [1], [2], [3], etc.**
3. Include citations inline after each claim or fact
4. If the context doesn't contain enough information, clearly state that
5. Be concise but comprehensive
6. If you're unsure, say so rather than making up information
7. Distinguish between knowledge base sources and web sources when relevant

Example of good citation:
"The company was founded in 2020 [1] and has over 500 employees [2]. According to recent reports, their revenue grew by 40% [3]."
"""

        user_prompt = f"""Context from knowledge base and web search:
{context}

---

Question: {query}

Please provide a detailed answer based on the context above. Remember to cite your sources using [1], [2], etc."""
        
        # Gemini API call
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        try:
            response = self.llm.invoke(messages)
            
            # Add source information notice if web search was used
            answer = response.content
            if has_web_results:
                answer += "\n\n*Note: This answer includes information from both your documents and web search results.*"
            
            response = AIMessage(content=answer)
            logger.info("Generated response successfully")
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            response = AIMessage(content=f"Error generating response: {str(e)}")
        
        return {
            **state,
            "messages": state["messages"] + [response]
        }
    
    def should_web_search(self, state: AgentState) -> str:
        """Decide if we need to perform web search"""
        if state.get("needs_web_search", False):
            return "web_search"
        return "generate"
    
    def _create_graph(self) -> StateGraph:
        """Create the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("retrieve", self.retrieve_context)
        workflow.add_node("web_search", self.web_search_node)
        workflow.add_node("generate", self.generate_response)
        
        # Add edges
        workflow.set_entry_point("retrieve")
        
        # Conditional edge: retrieve -> web_search or generate
        workflow.add_conditional_edges(
            "retrieve",
            self.should_web_search,
            {
                "web_search": "web_search",
                "generate": "generate"
            }
        )
        
        # web_search -> generate
        workflow.add_edge("web_search", "generate")
        workflow.add_edge("generate", END)
        
        return workflow.compile()
    
    def query(self, question: str) -> dict:
        """Query the RAG agent"""
        logger.info(f"Processing query: {question}")
        
        initial_state = {
            "messages": [HumanMessage(content=question)],
            "context": "",
            "query": question,
            "citations": [],
            "web_results": [],
            "needs_web_search": False
        }
        
        result = self.graph.invoke(initial_state)
        
        # Extract the final answer
        answer = ""
        for message in reversed(result["messages"]):
            if isinstance(message, AIMessage) and not message.content.startswith("Retrieved") and not message.content.startswith("Performed"):
                answer = message.content
                break
        
        # Build citations list
        all_citations = []
        
        # Add document citations
        for citation in result.get("citations", []):
            all_citations.append({
                "id": citation["id"],
                "source": "document",
                "content": citation["content"],
                "metadata": citation["metadata"],
                "relevance_score": citation["relevance_score"]
            })
        
        # Add web citations
        for idx, web_result in enumerate(result.get("web_results", []), start=len(result.get("citations", [])) + 1):
            all_citations.append({
                "id": idx,
                "source": "web",
                "title": web_result.get("title", ""),
                "url": web_result.get("href", ""),
                "content": web_result.get("body", "")[:200] + "..."
            })
        
        return {
            "answer": answer,
            "citations": all_citations,
            "context": result.get("context", ""),
            "used_web_search": len(result.get("web_results", [])) > 0,
            "chunks_used": len(result.get("citations", []))
        }