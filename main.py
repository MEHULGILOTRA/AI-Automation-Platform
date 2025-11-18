import os
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil
from typing import List, Dict
from config import cfg 
import document_ingestion 
from graph.workflow import app as agent_workflow_app
from google_workspace_tools import send_gmail
from langchain_core.messages import BaseMessage

app = FastAPI(title="AI Multi-Agent Backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

chat_history_store: Dict[str, List[BaseMessage]] = {}

class ChatQuery(BaseModel):
    query: str
    session_id: str

class IngestionResponse(BaseModel):
    message: str
    filename: str

class ChatResponse(BaseModel):
    final_answer: str
    sources: list
    chat_history: List[Dict] 

class EmailRequest(BaseModel):
    to: str
    subject: str
    body: str

@app.post("/upload-document/", response_model=IngestionResponse)
async def upload_document(file: UploadFile = File(...)):
    temp_dir = "temp_docs"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, file.filename)
    try:
        with open(temp_path, "wb") as buffer: shutil.copyfileobj(file.file, buffer)
        document_ingestion.ingest_document(temp_path)
        return IngestionResponse(message="Document ingested.", filename=file.filename)
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_path): os.remove(temp_path)
        if file.file: file.file.close()

@app.post("/send-email/")
async def send_email(email: EmailRequest):
    try:
        res = send_gmail(email.to, email.subject, email.body)
        if not res.get("success"): raise HTTPException(status_code=500, detail=res.get("error"))
        return {"message": "Sent!", "message_id": res.get("message_id")}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/", response_model=ChatResponse)
async def chat_workflow(query: ChatQuery):
    current_history = chat_history_store.get(query.session_id, [])
    try:
        final_state = agent_workflow_app.invoke({"query": query.query, "chat_history": current_history})
        print("Final state is : ", final_state)
        new_history = final_state.get("chat_history", [])
        chat_history_store[query.session_id] = new_history
        
        # chat_history_json = [{"type": msg.type, "content": msg.content} for msg in new_history]
        # return ChatResponse(
        #     final_answer=final_state.get("final_answer", ""),
        #     sources=final_state.get("sources", []),
        #     chat_history=chat_history_json
        # )
        chat_history_json = []
        for msg in new_history:
            # Case 1: It is a LangChain Message Object (has .type attribute)
            if hasattr(msg, 'type'):
                chat_history_json.append({
                    "type": msg.type, 
                    "content": msg.content
                })
            # Case 2: It is a Dictionary (The error source)
            elif isinstance(msg, dict):
                chat_history_json.append({
                    "type": msg.get("type", "assistant"), # Default to assistant if type missing
                    "content": msg.get("content") or msg.get("text", "") # Handle 'text' key from tool
                })

        return ChatResponse(
            final_answer=final_state.get("final_answer", ""),
            sources=final_state.get("sources", []),
            chat_history=chat_history_json
        )
    except Exception as e: 
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)