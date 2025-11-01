import requests
import json

BASE_URL = "http://localhost:8000"

def test_full_conversation():
    """Test complete conversation flow"""
    
    # 1. Start conversation
    print("=== Starting Conversation ===")
    response = requests.post(f"{BASE_URL}/chat/start")
    data = response.json()
    session_id = data["session_id"]
    print(f"Bot: {data['message']}\n")
    
    # 2. Provide name
    print("=== Patient Identification ===")
    response = requests.post(
        f"{BASE_URL}/chat/message",
        json={
            "session_id": session_id,
            "message": "John Smith"
        }
    )
    data = response.json()
    print(f"Bot: {data['message']}\n")
    
    # 3. General query
    print("=== General Query ===")
    response = requests.post(
        f"{BASE_URL}/chat/message",
        json={
            "session_id": session_id,
            "message": "What are my medications?"
        }
    )
    data = response.json()
    print(f"Bot ({data['agent']}): {data['message']}\n")
    
    # 4. Medical concern (warning sign)
    print("=== Medical Concern (Warning Sign) ===")
    response = requests.post(
        f"{BASE_URL}/chat/message",
        json={
            "session_id": session_id,
            "message": "I'm having swelling in my legs. Should I be worried?"
        }
    )
    data = response.json()
    print(f"Bot ({data['agent']}): {data['message']}")
    print(f"Urgency: {data.get('urgency')}")
    if data.get('citations'):
        print(f"\nCitations ({len(data['citations'])}):")
        for citation in data['citations']:
            print(f"  [{citation['id']}] {citation['source']}: {citation['content'][:100]}...")
    print()
    
    # 5. Research question (likely triggers web search)
    print("=== Research Question ===")
    response = requests.post(
        f"{BASE_URL}/chat/message",
        json={
            "session_id": session_id,
            "message": "What's the latest research on SGLT2 inhibitors for kidney disease?"
        }
    )
    data = response.json()
    print(f"Bot ({data['agent']}): {data['message']}")
    print(f"Used web search: {data.get('used_web_search')}")
    print()
    
    # 6. Get conversation history
    print("=== Conversation History ===")
    response = requests.get(f"{BASE_URL}/chat/history/{session_id}")
    history = response.json()
    print(f"Total messages: {len(history['messages'])}")
    print(f"Patient identified: {history['patient_identified']}")
    print(f"Patient name: {history.get('patient_name')}")

if __name__ == "__main__":
    test_full_conversation()