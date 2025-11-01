from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import os
import tempfile
import logging

from pdf_processor import RobustPDFProcessor
from vector_store import VectorStore
from agent import RAGAgent
from patient_data_manager import PatientDataManager
from agents.receptionist_agent import ReceptionistAgent
from agents.clinical_agent import ClinicalAgent
from conversation_manager import ConversationManager
from config import settings

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Patient Care Chatbot with RAG",
    description="Multi-agent patient care system with RAG, citations, and web search",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/chat-ui")
async def chat_ui():
    """Serve the chat UI"""
    return FileResponse("static/index.html")

# Initialize components
pdf_processor = RobustPDFProcessor()
vector_store = VectorStore()
rag_agent = RAGAgent(vector_store)
patient_manager = PatientDataManager()

# Initialize agents
receptionist_agent = ReceptionistAgent(patient_manager)
clinical_agent = ClinicalAgent(rag_agent, patient_manager)

# Initialize conversation manager
conversation_manager = ConversationManager(receptionist_agent, clinical_agent)


# ============== Pydantic Models ==============

class ChatStartRequest(BaseModel):
    """Request to start a new chat session"""
    pass


class ChatMessageRequest(BaseModel):
    """Request to send a message in a chat session"""
    session_id: str
    message: str


class Citation(BaseModel):
    id: int
    source: str
    content: str
    metadata: Optional[Dict] = None
    relevance_score: Optional[float] = None
    title: Optional[str] = None
    url: Optional[str] = None


class ChatMessageResponse(BaseModel):
    """Response from chat message"""
    session_id: str
    message: str
    agent: str
    citations: Optional[List[Citation]] = None
    urgency: Optional[str] = None
    used_web_search: Optional[bool] = None
    patient_data: Optional[Dict] = None
    requires_input: bool = True


class ConversationHistoryResponse(BaseModel):
    """Conversation history response"""
    session_id: str
    messages: List[Dict]
    patient_identified: bool
    patient_name: Optional[str] = None


# ============== Chat Endpoints ==============

@app.post("/chat/start", response_model=ChatMessageResponse)
async def start_chat():
    """
    Start a new chat conversation
    
    Returns initial greeting from receptionist agent
    """
    try:
        session_id = conversation_manager.create_session()
        result = conversation_manager.start_conversation(session_id)
        
        return ChatMessageResponse(
            session_id=result["session_id"],
            message=result["message"],
            agent=result["agent"],
            requires_input=result["requires_input"]
        )
    except Exception as e:
        logger.error(f"Error starting chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/message", response_model=ChatMessageResponse)
async def send_message(request: ChatMessageRequest):
    """
    Send a message in an existing chat session
    
    Automatically routes to appropriate agent (receptionist or clinical)
    """
    try:
        logger.info(f"Processing message in session {request.session_id}: {request.message}")
        
        result = conversation_manager.process_message(
            session_id=request.session_id,
            user_message=request.message
        )
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        
        citations = None
        if result.get("citations"):
            citations = [Citation(**c) for c in result["citations"]]
        
        return ChatMessageResponse(
            session_id=request.session_id,
            message=result["message"],
            agent=result["agent"],
            citations=citations,
            urgency=result.get("urgency"),
            used_web_search=result.get("used_web_search"),
            patient_data=result.get("patient_data"),
            requires_input=result.get("requires_input", True)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chat/history/{session_id}", response_model=ConversationHistoryResponse)
async def get_conversation_history(session_id: str):
    """
    Get full conversation history for a session
    """
    try:
        session = conversation_manager.get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return ConversationHistoryResponse(
            session_id=session_id,
            messages=session["messages"],
            patient_identified=session["patient_identified"],
            patient_name=session.get("patient_data", {}).get("patient_name") if session.get("patient_data") else None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/chat/session/{session_id}")
async def end_chat_session(session_id: str):
    """
    End a chat session
    """
    try:
        conversation_manager.end_session(session_id)
        return {"status": "success", "message": "Session ended"}
    except Exception as e:
        logger.error(f"Error ending session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Patient Data Endpoints ==============

@app.get("/patients/list")
async def list_patients():
    """
    List all patients in the system
    """
    try:
        patients = patient_manager.get_all_patients()
        return {
            "total": len(patients),
            "patients": [
                {
                    "name": p.get("patient_name"),
                    "discharge_date": p.get("discharge_date"),
                    "diagnosis": p.get("primary_diagnosis")
                }
                for p in patients
            ]
        }
    except Exception as e:
        logger.error(f"Error listing patients: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/patients/{patient_name}")
async def get_patient_info(patient_name: str):
    """
    Get detailed information for a specific patient
    """
    try:
        patient = patient_manager.find_patient(patient_name)
        
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        return {
            "patient": patient,
            "summary": patient_manager.get_patient_summary(patient)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting patient info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Existing Endpoints (PDF Upload, Query, etc.) ==============

@app.post("/upload-pdf/")
async def upload_pdf(file: UploadFile = File(...), metadata: Optional[str] = None):
    """Upload and process medical guidelines/documents"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    try:
        logger.info(f"Processing PDF: {file.filename}")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        text = pdf_processor.extract_text(tmp_path)
        chunks = pdf_processor.chunk_text(
            text,
            chunk_size=settings.CHUNK_SIZE,
            overlap=settings.CHUNK_OVERLAP
        )
        
        file_metadata = {
            "filename": file.filename,
            "type": "medical_guideline"
        }
        if metadata:
            file_metadata["custom_metadata"] = metadata
        
        vector_store.add_documents(chunks, metadata=file_metadata)
        os.unlink(tmp_path)
        
        return {
            "status": "success",
            "filename": file.filename,
            "chunks_created": len(chunks)
        }
    
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        if 'tmp_path' in locals():
            try:
                os.unlink(tmp_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health/")
async def health_check():
    """Health check endpoint"""
    try:
        collection_count = vector_store.collection.count()
        patient_count = len(patient_manager.get_all_patients())
        
        return {
            "status": "healthy",
            "model": settings.GEMINI_MODEL,
            "document_count": collection_count,
            "patient_count": patient_count,
            "features": {
                "multi_agent": True,
                "receptionist_agent": True,
                "clinical_agent": True,
                "citations": True,
                "web_search_fallback": True,
                "patient_data_integration": True
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Patient Care Chatbot System",
        "version": "2.0.0",
        "description": "Multi-agent system for post-discharge patient care",
        "agents": {
            "receptionist": "Handles greetings, patient identification, and general queries",
            "clinical": "Handles medical questions with RAG + web search"
        },
        "endpoints": {
            "chat": {
                "start": "POST /chat/start - Start new conversation",
                "message": "POST /chat/message - Send message",
                "history": "GET /chat/history/{session_id} - Get conversation history",
                "end": "DELETE /chat/session/{session_id} - End session"
            },
            "patients": {
                "list": "GET /patients/list - List all patients",
                "get": "GET /patients/{name} - Get patient info"
            },
            "documents": {
                "upload": "POST /upload-pdf/ - Upload medical guidelines"
            }
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)