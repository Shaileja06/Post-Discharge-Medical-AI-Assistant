from typing import Dict, List, Optional
import logging
from datetime import datetime
import uuid
from agents.receptionist_agent import ReceptionistAgent
from agents.clinical_agent import ClinicalAgent

logger = logging.getLogger(__name__)


class ConversationManager:
    """
    Orchestrates multi-turn conversations between receptionist and clinical agents
    """
    
    def __init__(
        self, 
        receptionist_agent: ReceptionistAgent,
        clinical_agent: ClinicalAgent
    ):
        self.receptionist = receptionist_agent
        self.clinical = clinical_agent
        self.sessions = {}  # session_id -> conversation history
    
    def create_session(self) -> str:
        """Create a new conversation session"""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "created_at": datetime.now().isoformat(),
            "messages": [],
            "patient_identified": False,
            "patient_data": None,
            "current_agent": "receptionist"
        }
        logger.info(f"Created new session: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session data"""
        return self.sessions.get(session_id)
    
    def start_conversation(self, session_id: str) -> Dict:
        """Start a new conversation"""
        greeting = self.receptionist.greet()
        
        self._add_message(session_id, "assistant", greeting, "receptionist")
        
        return {
            "session_id": session_id,
            "message": greeting,
            "agent": "receptionist",
            "requires_input": True
        }
    
    def process_message(self, session_id: str, user_message: str) -> Dict:
        """
        Process user message and route to appropriate agent
        
        Returns:
            {
                "message": str,
                "agent": str,
                "citations": Optional[List],
                "urgency": Optional[str],
                "patient_data": Optional[Dict]
            }
        """
        session = self.sessions.get(session_id)
        if not session:
            return {
                "error": "Session not found. Please start a new conversation.",
                "message": "Session expired. Let's start over!",
                "agent": "system"
            }
        
        # Add user message to history
        self._add_message(session_id, "user", user_message)
        
        # Check if patient is identified
        if not session["patient_identified"]:
            return self._handle_patient_identification(session_id, user_message)
        
        # Check if should route to clinical agent
        routing = self.receptionist.should_route_to_clinical(user_message, session_id)
        
        if routing["route"]:
            return self._handle_clinical_query(
                session_id, 
                user_message, 
                routing["is_warning_sign"]
            )
        else:
            return self._handle_general_query(session_id, user_message)
    
    def _handle_patient_identification(self, session_id: str, name: str) -> Dict:
        """Handle patient name and identification"""
        result = self.receptionist.identify_patient(name, session_id)
        
        session = self.sessions[session_id]
        
        if result["found"]:
            session["patient_identified"] = True
            session["patient_data"] = result["patient_data"]
            
            self._add_message(
                session_id, 
                "assistant", 
                result["message"], 
                "receptionist"
            )
            
            return {
                "message": result["message"],
                "agent": "receptionist",
                "patient_data": result["patient_data"],
                "requires_input": True
            }
        else:
            self._add_message(
                session_id, 
                "assistant", 
                result["message"], 
                "receptionist"
            )
            
            return {
                "message": result["message"],
                "agent": "receptionist",
                "requires_input": True
            }
    
    def _handle_clinical_query(
        self, 
        session_id: str, 
        query: str,
        is_warning_sign: bool
    ) -> Dict:
        """Route to clinical agent"""
        session = self.sessions[session_id]
        patient_data = session.get("patient_data")
        
        # Transition message
        if session["current_agent"] != "clinical":
            transition = (
                "This sounds like a medical concern. "
                "Let me connect you with our Clinical AI Agent... 🏥"
            )
            self._add_message(session_id, "assistant", transition, "receptionist")
            session["current_agent"] = "clinical"
        
        # Get clinical response
        clinical_result = self.clinical.handle_query(
            query=query,
            patient_data=patient_data,
            is_warning_sign=is_warning_sign
        )
        
        self._add_message(
            session_id, 
            "assistant", 
            clinical_result["answer"], 
            "clinical",
            citations=clinical_result.get("citations", [])
        )
        
        response = {
            "message": clinical_result["answer"],
            "agent": "clinical",
            "citations": clinical_result.get("citations", []),
            "used_web_search": clinical_result.get("used_web_search", False),
            "urgency": clinical_result.get("urgency"),
            "requires_input": True
        }
        
        # Add transition back message for routine queries
        if clinical_result.get("urgency") == "routine":
            response["follow_up"] = (
                "\nIs there anything else I can help you with regarding your care plan?"
            )
        
        return response
    
    def _handle_general_query(self, session_id: str, query: str) -> Dict:
        """Handle general queries with receptionist"""
        session = self.sessions[session_id]
        
        # Transition back from clinical if needed
        if session["current_agent"] == "clinical":
            session["current_agent"] = "receptionist"
        
        response = self.receptionist.handle_general_query(query, session_id)
        
        self._add_message(session_id, "assistant", response, "receptionist")
        
        return {
            "message": response,
            "agent": "receptionist",
            "requires_input": True
        }
    
    def _add_message(
        self, 
        session_id: str, 
        role: str, 
        content: str,
        agent: str = None,
        citations: List = None
    ):
        """Add message to conversation history"""
        session = self.sessions.get(session_id)
        if session:
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "agent": agent
            }
            if citations:
                message["citations"] = citations
            
            session["messages"].append(message)
    
    def get_conversation_history(self, session_id: str) -> List[Dict]:
        """Get full conversation history"""
        session = self.sessions.get(session_id)
        if session:
            return session["messages"]
        return []
    
    def end_session(self, session_id: str):
        """End conversation session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Ended session: {session_id}")