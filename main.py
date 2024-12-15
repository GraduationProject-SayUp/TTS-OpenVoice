#.\.venv\Scripts\activate
# uvicorn main:app --reload --host 127.0.0.1 --port 8000

import os
import subprocess
import json
import traceback
import requests
from fastapi import FastAPI, File, UploadFile, HTTPException, Header
from pydantic import BaseModel

app = FastAPI()

class TTSVector(BaseModel):
    token: str
    vector: list

@app.post("/upload")
async def upload_audio(file: UploadFile = File(...), authorization: str = Header(...)):
    upload_dir = "uploaded_audio"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)

    # 파일 저장
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    file_path = f'uploaded_audio/news.mp3'  # 일단 임시 파일로 변경경

    try:
        result = run_tts_script(file_path)
    except Exception as e:
        print(f"Error details: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error running tts.py: {str(e)}")

    try:
        spring_response = send_to_spring_server(authorization, result)
    except Exception as e:
        print(f"Error details: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error processing audio file: {str(e)}")

    return {
        "filename": file.filename,
        "status": "uploaded",
        "tts_vector": result,
        "spring_response": spring_response
    }

def run_tts_script(audio_path: str):
    """
    tts.py를 subprocess로 실행하고 결과 벡터를 반환
    """

    script_path = "tts_vector.py"
    venv_python_path = os.path.join('.venv', 'Scripts', 'python.exe') # 가상환경 Python 경로에 대한 동적 탐색

    command = [
        venv_python_path,
        script_path,
        "--audio",
        audio_path
    ]

    print(f"Running command: {' '.join(command)}")

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        # 타임아웃과 함께 출력 캡처
        stdout, stderr = process.communicate(timeout=120)
        print(f"Raw stdout: {stdout}")

        # 반환 코드 확인
        if process.returncode != 0:
            print(f"Error output: {stderr}")
            raise RuntimeError(f"tts.py 실행 중 오류: {stderr}")

        stdout_lines = stdout.strip().splitlines()
        for line in stdout_lines:
            try:
                # JSON 형식인 경우 반환
                json_data = json.loads(line)
                if "target_se" in json_data:  # JSON 데이터가 target_se 키를 포함하는지 확인
                    return json_data.get("target_se")
            except json.JSONDecodeError:
                continue  # JSON 형식이 아닌 라인은 무시
        
        # JSON 데이터가 없을 경우 예외 처리
        raise ValueError(f"No valid JSON found in tts.py output: {process.stdout}")

    except subprocess.TimeoutExpired:
        process.kill()
        raise RuntimeError("tts.py 실행 시간 초과")
    except Exception as e:
        print(f"예기치 않은 오류: {traceback.format_exc()}")
        raise


def send_to_spring_server(token: str, target_se: list):
    """
    Spring 서버로 데이터를 전송
    """
    print("Spring 서버로 데이터 전송 중")

    url = "http://127.0.0.1:8080/api/users/tts"
    headers = {
        "Content-Type": "application/json",
        "Authorization": token
    }
    payload = {
        "ttsVector": json.dumps(target_se)
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        
        # 응답 상태 코드와 본문 출력 (디버깅용)
        print(f"Response status code: {response.status_code}")
        print(f"Response body: {response.text}")
    
        response.raise_for_status()  # HTTP 오류 발생 시 예외 발생
        
        # JSON 파싱 시도
        if response.status_code == 200:
            try:
                return response.json()
            except json.JSONDecodeError:
                raise ValueError(f"Spring 서버 응답이 JSON 형식이 아닙니다: {response.text}")
        
        return response.json()
    
    except requests.RequestException as e:
        print(f"Spring 서버 전송 중 오류: {e}")
        raise