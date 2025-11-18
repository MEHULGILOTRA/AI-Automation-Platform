import os
import requests
import json
from typing import List, Dict, Tuple
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from google_workspace_tools import send_gmail

def generate_and_send_email_tool(to_email: str, subject: str, body_query: str, context: str) -> dict:
    """
    Generates email content using LLM and SENDS IT IMMEDIATELY via Gmail API.
    """

    print(f"---TOOL: Generating and SENDING email to: {to_email}---")
    
    # 1. Generate the content using the LLM
    prompt = f"""
    You are a professional automated email assistant.
    Generate the JSON content for an email based on the request.
    
    To: "{to_email}"
    Subject Request: "{subject}"
    Body Request: "{body_query}"
    Context: "{context}"
    
    Respond ONLY with a JSON object: {{"to": "...", "subject": "...", "body": "..."}}
    """
    
    try:
        #response = llm.invoke([HumanMessage(content=prompt)])
        content_json = """```json
            {
            "to": "mehulgilotra@gmail.com",
            "subject": "Summary of Document",
            "body": "This document outlines key accomplishments and projects in AI/ML and NLP. It details experience in integrating Oracle Digital Assistant with custom NLP for document processing, building vector database-backed RAG pipelines for semantic search, and engineering AI-driven automation with LangChain and FastAPI for LLMs. It also includes the creation of a conversational HR assistant using Oracle APEX and an LLM agent. Internship experience at Ernst & Young involved automating Python backend pipelines for insurance reporting, and research at IISc focused on multilingual NLP for low-resource languages. Key projects include a Customer Churn Prediction ML pipeline and a Sign Language Translator web service."
            }
        ```
        """
        print(f"Generated Email Content: {content_json}")

        # --- CLEANUP LOGIC START ---
        # Remove markdown code block markers if present
        cleaned_json = content_json.strip()
        if cleaned_json.startswith("```json"):
            cleaned_json = cleaned_json[7:]
        elif cleaned_json.startswith("```"):
            cleaned_json = cleaned_json[3:]
        
        if cleaned_json.endswith("```"):
            cleaned_json = cleaned_json[:-3]
            
        cleaned_json = cleaned_json.strip()
        # --- CLEANUP LOGIC END ---
        
        # 2. Parse the JSON
        email_data = json.loads(cleaned_json)
        final_to = email_data.get("to", to_email)
        final_subject = email_data.get("subject", subject)
        final_body = email_data.get("body", "")
        
        # 3. SEND THE EMAIL IMMEDIATELY
        print("---TOOL: Calling Gmail API...---")
        send_result = send_gmail(final_to, final_subject, final_body)
        
        if send_result.get("success"):
            success_msg = (
                f"✅ AUTOMATED ACTION: Email successfully sent to {final_to}.\n"
                f"Subject: {final_subject}\n"
                f"Message ID: {send_result.get('message_id')}"
            )
            return {"text": success_msg, "sources": ["Gmail API (Auto-Sent)"]}
        else:
            return {"text": f"❌ Failed to send email: {send_result.get('error')}", "sources": ["Gmail API Error"]}

    except Exception as e:
        print(f"Error in generate_and_send_email_tool: {e}")
        return {"text": f"Error processing email task: {e}", "sources": []}

if __name__ == "__main__":
    to_email = "mehulgilotra@gmail.com"
    subject = "This is a test email sent by AI Assistant"
    body_query = "Hello user"
    context = "This is the summary"

    generate_and_send_email_tool(to_email, subject, body_query, context)