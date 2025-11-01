from typing import Dict, Optional
import logging
from patient_data_manager import PatientDataManager

logger = logging.getLogger(__name__)


class ReceptionistAgent:
    """
    Handles initial patient interactions:
    - Greets patients
    - Retrieves patient data
    - Routes to clinical agent when needed
    """
    
    def __init__(self, patient_manager: PatientDataManager):
        self.patient_manager = patient_manager
        self.conversation_state = {}
    
    def greet(self) -> str:
        """Initial greeting"""
        return (
            "Hello! 👋 I'm your post-discharge care assistant. "
            "I'm here to help you with your recovery and answer any questions. "
            "What's your name?"
        )
    
    def identify_patient(self, name: str, session_id: str) -> Dict:
        """
        Identify patient and retrieve their data
        
        Returns:
            {
                "found": bool,
                "message": str,
                "patient_data": Optional[Dict]
            }
        """
        patient = self.patient_manager.find_patient(name)
        
        if patient:
            # Store in conversation state
            self.conversation_state[session_id] = {
                "patient_name": name,
                "patient_data": patient,
                "identified": True
            }
            
            message = (
                f"Hi {patient.get('patient_name')}! 😊\n\n"
                f"I found your discharge report from {patient.get('discharge_date')} "
                f"for **{patient.get('primary_diagnosis')}**.\n\n"
                f"How are you feeling today? Are you following your medication schedule?"
            )
            
            return {
                "found": True,
                "message": message,
                "patient_data": patient
            }
        else:
            message = (
                f"I couldn't find a discharge record for '{name}'. "
                f"Could you please verify your full name? "
                f"(First and Last name)"
            )
            
            return {
                "found": False,
                "message": message,
                "patient_data": None
            }
    
    def get_patient_info(self, session_id: str, info_type: str = "summary") -> str:
        """Get specific patient information"""
        state = self.conversation_state.get(session_id)
        
        if not state or not state.get("identified"):
            return "I don't have your information yet. Could you please tell me your name first?"
        
        patient_data = state.get("patient_data")
        
        if info_type == "summary":
            return self.patient_manager.get_patient_summary(patient_data)
        elif info_type == "medications":
            meds = patient_data.get('medications', [])
            return "**Your Medications:**\n" + "\n".join(f"• {med}" for med in meds)
        elif info_type == "diet":
            return f"**Dietary Restrictions:**\n{patient_data.get('dietary_restrictions')}"
        elif info_type == "follow_up":
            return f"**Follow-up Appointments:**\n{patient_data.get('follow_up')}"
        elif info_type == "warnings":
            return f"**Warning Signs:**\n{patient_data.get('warning_signs')}"
        else:
            return self.patient_manager.get_patient_summary(patient_data)
    
    def should_route_to_clinical(self, message: str, session_id: str) -> Dict:
        """
        Determine if message should be routed to clinical agent
        
        Returns:
            {
                "route": bool,
                "reason": str,
                "is_warning_sign": bool
            }
        """
        message_lower = message.lower()
        
        # Medical concern keywords
        medical_keywords = [
            'pain', 'swelling', 'fever', 'bleeding', 'dizzy', 
            'short of breath', 'chest pain', 'nausea', 'vomiting',
            'headache', 'rash', 'infection', 'weight gain',
            'difficulty breathing', 'confused', 'weak', 'tired'
        ]
        
        # Question keywords
        question_keywords = [
            'what is', 'why', 'how', 'when', 'should i',
            'can i', 'is it normal', 'treatment', 'side effect',
            'research', 'study', 'guideline', 'recommend'
        ]
        
        # Check for medical concerns
        has_medical_keyword = any(keyword in message_lower for keyword in medical_keywords)
        has_question = any(keyword in message_lower for keyword in question_keywords)
        
        # Check if it's a warning sign
        is_warning_sign = False
        state = self.conversation_state.get(session_id)
        if state and state.get("identified"):
            patient_data = state.get("patient_data")
            is_warning_sign = self.patient_manager.check_warning_signs(
                patient_data, message
            )
        
        if has_medical_keyword or has_question or is_warning_sign:
            reason = "medical concern" if has_medical_keyword else "medical question"
            if is_warning_sign:
                reason = "potential warning sign"
            
            return {
                "route": True,
                "reason": reason,
                "is_warning_sign": is_warning_sign
            }
        
        return {
            "route": False,
            "reason": "general inquiry",
            "is_warning_sign": False
        }
    
    def handle_general_query(self, message: str, session_id: str) -> str:
        """Handle non-medical queries"""
        message_lower = message.lower()
        
        # Check for common questions
        if any(word in message_lower for word in ['medication', 'medicine', 'pill']):
            return self.get_patient_info(session_id, "medications")
        
        elif any(word in message_lower for word in ['diet', 'food', 'eat', 'drink']):
            return self.get_patient_info(session_id, "diet")
        
        elif any(word in message_lower for word in ['appointment', 'follow-up', 'follow up']):
            return self.get_patient_info(session_id, "follow_up")
        
        elif any(word in message_lower for word in ['warning', 'signs', 'symptoms', 'watch']):
            return self.get_patient_info(session_id, "warnings")
        
        elif any(word in message_lower for word in ['discharge', 'summary', 'report', 'information']):
            return self.get_patient_info(session_id, "summary")
        
        else:
            return (
                "I can help you with:\n"
                "• Your medications and when to take them\n"
                "• Dietary restrictions and guidelines\n"
                "• Follow-up appointments\n"
                "• Warning signs to watch for\n"
                "• Your discharge summary\n\n"
                "What would you like to know?"
            )