#.\.venv\Scripts\activate
# http://127.0.0.1:8000 
from fastapi import FastAPI, File, UploadFile
import os

app = FastAPI()

@app.post("/upload")
async def upload_audio(file: UploadFile = File(...)):
    upload_dir = "uploaded_audio"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    
    return {"filename": file.filename, "status": "uploaded"}