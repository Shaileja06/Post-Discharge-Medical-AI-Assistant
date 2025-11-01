import json
from typing import Optional, Dict, List
from datetime import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class PatientDataManager:
    """Manages patient discharge data"""
    
    def __init__(self, data_file: str = "patients_data.json"):
        self.data_file = data_file
        self.patients = self._load_patients()
        logger.info(f"Loaded {len(self.patients)} patient records")
    
    def _load_patients(self) -> List[Dict]:
        """Load patient data from JSON file"""
        try:
            if not Path(self.data_file).exists():
                logger.warning(f"Patient data file not found: {self.data_file}")
                return []
            
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Error loading patient data: {e}")
            return []
    
    def find_patient(self, name: str) -> Optional[Dict]:
        """
        Find patient by name (fuzzy matching)
        """
        name_lower = name.lower().strip()
        
        # Exact match first
        for patient in self.patients:
            if patient.get("patient_name", "").lower() == name_lower:
                return patient
        
        # Partial match (first name or last name)
        for patient in self.patients:
            patient_name = patient.get("patient_name", "").lower()
            if name_lower in patient_name or any(part in name_lower for part in patient_name.split()):
                return patient
        
        return None
    
    def get_patient_summary(self, patient_data: Dict) -> str:
        """Generate a human-readable summary of patient data"""
        summary = f"""
**Patient Information**
Name: {patient_data.get('patient_name')}
Discharge Date: {patient_data.get('discharge_date')}
Primary Diagnosis: {patient_data.get('primary_diagnosis')}

**Medications:**
{self._format_list(patient_data.get('medications', []))}

**Dietary Restrictions:**
{patient_data.get('dietary_restrictions', 'None specified')}

**Follow-up Appointments:**
{patient_data.get('follow_up', 'None scheduled')}

**Warning Signs to Watch For:**
{patient_data.get('warning_signs', 'None specified')}

**Discharge Instructions:**
{patient_data.get('discharge_instructions', 'None provided')}
        """
        return summary.strip()
    
    def _format_list(self, items: List[str]) -> str:
        """Format list items with bullet points"""
        return "\n".join(f"• {item}" for item in items) if items else "None"
    
    def check_warning_signs(self, patient_data: Dict, symptom: str) -> bool:
        """Check if symptom matches warning signs"""
        warning_signs = patient_data.get('warning_signs', '').lower()
        symptom_lower = symptom.lower()
        
        # Common symptom keywords
        warning_keywords = [
            'swelling', 'shortness of breath', 'chest pain', 
            'weight gain', 'fever', 'bleeding', 'pain',
            'difficulty breathing', 'dizziness', 'confusion'
        ]
        
        # Check if symptom is in warning signs
        if any(keyword in symptom_lower for keyword in warning_keywords):
            return True
        
        if symptom_lower in warning_signs:
            return True
        
        return False
    
    def get_all_patients(self) -> List[Dict]:
        """Return all patient records"""
        return self.patients