#.\.venv\Scripts\activate
# uvicorn main:app --reload --host 127.0.0.1 --port 8000

import os
import subprocess
import json
import traceback
import requests
from fastapi import FastAPI, File, UploadFile, HTTPException, Header
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()

class TTSVector(BaseModel):
    token: str
    vector: list

@app.post("/upload")
async def upload_audio(file: UploadFile = File(...), authorization: str = Header(...)):
    """
    1. 음성 파일을 업로드하고 저장
    2. tts_vector.py를 실행하여 벡터를 생성
    3. 결과 벡터를 Spring 서버로 전송
    """
    
    upload_dir = "uploaded_audio"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)

    # 파일 저장
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    file_path = f'uploaded_audio/news.mp3'  # 일단 임시 파일로 변경경

    try:
        # tts_vector.py 실행
        result = run_tts_script(file_path)  
    except Exception as e:
        print(f"Error details: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error running tts.py: {str(e)}")

    try:
        # Spring 서버로 전송
        spring_response = send_vector_to_spring(authorization, result)
    except Exception as e:
        print(f"Error details: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error processing audio file: {str(e)}")

    # 최종 결과 반환
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

        # 타임아웃을 설정하고 출력 캡처
        stdout, stderr = process.communicate(timeout=120)
        print(f"Raw stdout: {stdout}")

        # 반환 코드 확인
        if process.returncode != 0:
            print(f"Error output: {stderr}")
            raise RuntimeError(f"tts.py 실행 중 오류: {stderr}")

        # JSON 형식 검사
        stdout_lines = stdout.strip().splitlines()
        for line in stdout_lines:
            try:
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


def send_vector_to_spring(token: str, target_se: list):
    """
    생성된 벡터를 Spring 서버로 전송
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
    
    
class VoiceRequest(BaseModel):
    text: str
    vector: str


@app.post("/convert")
async def convert_voice(request: VoiceRequest, authorization: str = Header(...)):
    """
    1. voice.py를 실행해 입력된 텍스트와 벡터로 음성을 생성
    2. 생성된 음성 파일을 Spring 서버로 전송
    """
    try:
        # 입력된 데이터
        text = request.text
        vector = request.vector
        
        output_file = run_voice_script(text, vector)  # voice.py 실행 후 음성 파일 생성

        # 생성된 파일 반환
        return FileResponse(
            path=output_file,
            filename=os.path.basename(output_file),
            media_type="audio/wav"
        )
        
    except Exception as e:
        print(f"Error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error processing voice conversion: {str(e)}")


def run_voice_script(text: str, vector: str) -> str:
    """
    voice.py를 subprocess로 실행하고 음성 파일 경로를 반환
    """
    script_path = "voice.py"
    venv_python_path = os.path.join(".venv", "Scripts", "python.exe")  # 가상환경 Python 실행 경로
    output_dir = "outputs_v2"
    os.makedirs(output_dir, exist_ok=True)

    output_path = f"{output_dir}/output_v2_news.wav"

    # voice.py 실행 명령어
    command = [
        venv_python_path,
        script_path,
        "--text", text,
        "--vector", vector,
        "--output", output_path
    ]

    print(f"Running command: {' '.join(command)}")

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        stdout, stderr = process.communicate(timeout=120)

        if process.returncode != 0:
            print(f"Error output: {stderr}")
            raise RuntimeError(f"voice.py 실행 중 오류: {stderr}")

        print(f"voice.py output: {stdout}")
        return output_path  # 성공적으로 생성된 음성 파일 경로 반환

    except subprocess.TimeoutExpired:
        process.kill()
        raise RuntimeError("voice.py 실행 시간 초과")
    except Exception as e:
        raise RuntimeError(f"voice.py 실행 중 예외 발생: {str(e)}")

