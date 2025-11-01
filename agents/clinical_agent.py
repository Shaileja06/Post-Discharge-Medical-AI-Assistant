from typing import Dict, Optional
import logging
from agent import RAGAgent
from patient_data_manager import PatientDataManager

logger = logging.getLogger(__name__)


class ClinicalAgent:
    """
    Handles medical queries using RAG + Web Search
    Provides clinical guidance with citations
    """
    
    def __init__(self, rag_agent: RAGAgent, patient_manager: PatientDataManager):
        self.rag_agent = rag_agent
        self.patient_manager = patient_manager
    
    def handle_query(
        self, 
        query: str, 
        patient_data: Optional[Dict] = None,
        is_warning_sign: bool = False
    ) -> Dict:
        """
        Handle clinical query with patient context
        
        Returns:
            {
                "answer": str,
                "citations": List[Dict],
                "urgency": str,  # "emergency", "urgent", "routine"
                "recommendation": str
            }
        """
        # Add patient context to query
        enhanced_query = self._enhance_query_with_context(query, patient_data)
        
        # Get RAG response
        rag_result = self.rag_agent.query(enhanced_query)
        
        # Assess urgency
        urgency = self._assess_urgency(query, is_warning_sign, patient_data)
        
        # Generate recommendation
        recommendation = self._generate_recommendation(urgency, patient_data)
        
        # Format clinical response
        response = self._format_clinical_response(
            query=query,
            answer=rag_result["answer"],
            urgency=urgency,
            recommendation=recommendation,
            is_warning_sign=is_warning_sign
        )
        
        return {
            "answer": response,
            "citations": rag_result["citations"],
            "used_web_search": rag_result["used_web_search"],
            "urgency": urgency,
            "recommendation": recommendation
        }
    
    def _enhance_query_with_context(
        self, 
        query: str, 
        patient_data: Optional[Dict]
    ) -> str:
        """Add patient context to improve RAG accuracy"""
        if not patient_data:
            return query
        
        context = f"""
Patient Context:
- Diagnosis: {patient_data.get('primary_diagnosis')}
- Current Medications: {', '.join(patient_data.get('medications', []))}

Patient Question: {query}
"""
        return context
    
    def _assess_urgency(
        self, 
        query: str, 
        is_warning_sign: bool,
        patient_data: Optional[Dict]
    ) -> str:
        """Assess urgency level of the query"""
        query_lower = query.lower()
        
        # Emergency keywords
        emergency_keywords = [
            'chest pain', 'can\'t breathe', 'severe pain', 
            'unconscious', 'bleeding heavily', 'stroke',
            'heart attack', 'seizure', 'suicidal'
        ]
        
        # Urgent keywords
        urgent_keywords = [
            'high fever', 'severe swelling', 'sudden weight gain',
            'difficulty breathing', 'confusion', 'severe headache',
            'blood in', 'can\'t urinate', 'extreme pain'
        ]
        
        if any(keyword in query_lower for keyword in emergency_keywords):
            return "emergency"
        
        if is_warning_sign or any(keyword in query_lower for keyword in urgent_keywords):
            return "urgent"
        
        return "routine"
    
    def _generate_recommendation(
        self, 
        urgency: str,
        patient_data: Optional[Dict]
    ) -> str:
        """Generate appropriate recommendation based on urgency"""
        if urgency == "emergency":
            return (
                "🚨 **EMERGENCY**: Please call 911 or go to the nearest emergency room immediately. "
                "This could be a life-threatening situation."
            )
        elif urgency == "urgent":
            follow_up = patient_data.get('follow_up', '') if patient_data else ''
            return (
                "⚠️ **URGENT**: Please contact your healthcare provider today. "
                f"Your follow-up: {follow_up}\n"
                "If symptoms worsen, go to the emergency room."
            )
        else:
            return (
                "📋 **Routine**: Continue monitoring your symptoms. "
                "If they persist or worsen, contact your healthcare provider."
            )
    
    def _format_clinical_response(
        self,
        query: str,
        answer: str,
        urgency: str,
        recommendation: str,
        is_warning_sign: bool
    ) -> str:
        """Format the clinical response with appropriate warnings"""
        response = ""
        
        # Add urgency header if needed
        if urgency in ["emergency", "urgent"]:
            response += f"{recommendation}\n\n---\n\n"
        
        # Add warning sign notice
        if is_warning_sign:
            response += (
                "⚠️ **Note**: This symptom is listed in your warning signs. "
                "Please pay close attention.\n\n"
            )
        
        # Add main answer
        response += f"**Clinical Information:**\n\n{answer}\n\n"
        
        # Add routine recommendation at the end
        if urgency == "routine":
            response += f"\n{recommendation}"
        
        # Add disclaimer
        response += (
            "\n\n---\n"
            "*Disclaimer: This information is for educational purposes only "
            "and does not replace professional medical advice.*"
        )
        
        return response