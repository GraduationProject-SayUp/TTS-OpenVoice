import os
import torch
from openvoice import se_extractor
from openvoice.api import ToneColorConverter
import json
import argparse
import sys
import logging
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.ERROR)

if __name__ == "__main__":
    # 명령줄 인자를 처리하기 위한 설정
    parser = argparse.ArgumentParser(description="TTS Vector Extractor")
    parser.add_argument("--audio", type=str, required=True, help="Path to the audio file")
    args = parser.parse_args()

    # 모델 경로 및 설정
    base_dir = Path(__file__).parent.resolve()  # 현재 파일의 디렉토리
    ckpt_converter = base_dir / "checkpoints_v2" / "converter"
    output_dir = base_dir / "outputs_v2"
    audio_path = Path(args.audio)
    
    device = "cuda:0" if torch.cuda.is_available() else "cpu"

    tone_color_converter = ToneColorConverter(
        str(ckpt_converter / "config.json"), device=device
    )
    tone_color_converter.load_ckpt(str(ckpt_converter / "checkpoint.pth"))

    os.makedirs(output_dir, exist_ok=True)

    # 음성에서 음색 특성과 관련 정보를 추출
    try:
        target_se, audio_name = se_extractor.get_se(str(audio_path), tone_color_converter, vad=True)
        
        if target_se is None:
            raise ValueError("Target SE extraction failed.")
        
        # JSON 형식으로 결과 반환
        result = {
            "target_se": target_se.tolist(),  # Tensor를 리스트로 변환
            "audio_name": audio_name
        }
        print(json.dumps(result))  # JSON 출력
    except Exception as e:
        print(json.dumps({"error": str(e)}))  # 에러를 JSON 형식으로 출력
        exit(1)
