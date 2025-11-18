import os
import google.generativeai as genai
import time
import json
from config import cfg 

# API_KEY is now loaded from cfg
genai.configure(api_key=cfg.GOOGLE_API_KEY)

# --- 1. Prepare Your Data ---

def create_sample_dataset(file_name="tuning_dataset.jsonl"):
    """
    Creates a sample JSONL (JSON Lines) file required for fine-tuning.
    """
    dataset = [
        {"text_input": "What is the capital of France?", "output": "Paris is the capital of France."},
        {"text_input": "Who wrote 'Hamlet'?", "output": "William Shakespeare wrote 'Hamlet'."},
        {"text_input": "What is 2+2?", "output": "2+2 equals 4."},
        {"text_input": "Hi", "output": "Hello, I am a AI Chatbot. How can i help you today?"},
        {"text_input": "What can you do?", "output": """
            As a large language model, I can perform a wide range of tasks, including:

            Answering your questions and providing information on various topics.
            Summarizing information and distilling key points from texts.
            Generating different creative text formats such as poems, code, scripts, musical pieces, emails, and letters.
            Translating text between various languages.
            Assisting with creative writing tasks.
            Helping with coding by providing snippets, explaining concepts, and debugging simple programs.
            Assisting with research by helping you find and synthesize information.
            Engaging in conversational dialogue.
        """},
        

    ]
    
    with open(file_name, "w") as f:
        for entry in dataset:
            f.write(json.dumps(entry) + "\n")
    print(f"Sample dataset created at '{file_name}'")
    return file_name

# --- 2. Upload Data ---

def upload_file_for_tuning(file_path: str):
    """
    Uploads the dataset file to Google AI Studio.
    """
    print(f"Uploading '{file_path}'...")
    file = genai.upload_file(path=file_path)
    print(f"File uploaded: {file.name} (URI: {file.uri})")
    
    while file.state.name == "PROCESSING":
        print("Waiting for file to be processed...")
        time.sleep(10)
        file = genai.get_file(file.name)
        
    if file.state.name == "FAILED":
        raise Exception("File processing failed.")
        
    print(f"File '{file.name}' is ready for tuning.")
    return file

# --- 3. Start Fine-Tuning Job ---

def start_fine_tuning_job(model_display_name: str, training_file_uri: str):
    """
    Starts the fine-tuning job on the 'gemini-1.5-flash-tune-model' base model.
    """
    print(f"Starting fine-tuning job for '{model_display_name}'...")
    
    job = genai.GenerativeModel.create_tuned_model(
        source_model="models/gemini-1.5-flash-tune-model",
        training_data=training_file_uri,
        display_name=model_display_name,
        epoch_count=5, 
    )
    
    print(f"Tuning job started. Operation name: {job.operation.name}")
    print("This will take some time. You can monitor its status.")
    return job

# --- 4. Monitor Job & Use Model ---

def monitor_job(job: genai.models.Job):
    """
    Polls the tuning job until it's finished.
    """
    while job.state.name == "RUNNING":
        print(f"Job state: {job.state.name}. Waiting 30 seconds...")
        time.sleep(30)
        job = genai.get_tuned_model(job.tuned_model_name) 
    
    if job.state.name == "SUCCEEDED":
        print(f"Success! Your tuned model is ready: {job.name}")
        return genai.GenerativeModel(job.tuned_model_name)
    elif job.state.name == "FAILED":
        print(f"Job failed: {job.error}")
        return None
    
def list_my_tuned_models():
    """
    Lists all tuned models in your project.
    """
    print("\n--- Your Tuned Models ---")
    for model in genai.list_tuned_models():
        print(f"- {model.display_name} ({model.name}) - State: {model.state.name}")

# --- Main execution flow ---
if __name__ == "__main__":
    
    dataset_file = create_sample_dataset()
    
    try:
        uploaded_file = upload_file_for_tuning(dataset_file)
        
        model_name = "my-first-tuned-model"
        job = start_fine_tuning_job(
            model_display_name=model_name,
            training_file_uri=uploaded_file.uri
        )
        
        tuned_model = monitor_job(job)
        
        if tuned_model:
            print(f"\n--- Testing tuned model: '{model_name}' ---")
            response = tuned_model.generate_content("What is the capital of France?")
            print(f"Prompt: What is the capital of France?")
            print(f"Tuned Answer: {response.text}")

        list_my_tuned_models()
        
    except Exception as e:
        print(f"\n--- An error occurred ---")
        print(e)