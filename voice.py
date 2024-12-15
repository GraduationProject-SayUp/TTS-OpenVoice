from melo.api import TTS
import os
import json
import torch
import argparse
from openvoice.api import ToneColorConverter

# 명령어 인자 파싱
parser = argparse.ArgumentParser(description="Voice conversion using TTS and ToneColorConverter")
parser.add_argument("--text", type=str, required=True, help="Input text to be converted to speech")
parser.add_argument("--vector", type=str, required=True, help="Target tone vector for conversion (comma-separated)")
parser.add_argument("--output", type=str, required=True, help="Output file path to save the converted voice")
args = parser.parse_args()

# 입력 데이터 설정
text = args.text
vector_str = args.vector  # 문자열로 전달된 벡터
try:
    # JSON 문자열을 리스트로 변환
    vector_list = json.loads(vector_str)
    # torch.Tensor로 변환
    vector_tensor = torch.tensor(vector_list, device="cuda:0" if torch.cuda.is_available() else "cpu")
except json.JSONDecodeError:
    raise ValueError(f"Invalid vector format: {vector_str}")
output_path = args.output

output_dir = os.path.dirname(output_path)
os.makedirs(output_dir, exist_ok=True)  # 출력 폴더 생성

device = "cuda:0" if torch.cuda.is_available() else "cpu"

# 텍스트를 음성으로 변환한 결과를 저장하기 위한 임시 파일 경로
src_path = os.path.join(output_dir, 'tmp.wav')

ckpt_converter = 'checkpoints_v2/converter'

tone_color_converter = ToneColorConverter(f'{ckpt_converter}/config.json', device=device)
tone_color_converter.load_ckpt(f'{ckpt_converter}/checkpoint.pth')

# 속도 조정
speed = 1.0

model = TTS(language='KR', device=device)  
speaker_ids = model.hps.data.spk2id

for speaker_key in speaker_ids.keys():
    speaker_id = speaker_ids[speaker_key]
    speaker_key = speaker_key.lower().replace('_', '-')
    
    source_se = torch.load(f'checkpoints_v2/base_speakers/ses/{speaker_key}.pth', map_location=device)
    
    model.tts_to_file(text, speaker_id, src_path, speed=speed)
    save_path = f'{output_dir}/output_v2_news.wav'
    
    # Run the tone color converter (생성된 음성의 음색을 변환)
    encode_message = "@MyShell"
    tone_color_converter.convert(
        audio_src_path=src_path, 
        src_se=source_se, 
        tgt_se=vector_tensor, 
        output_path=output_path,
        message=encode_message)
    
    result = {"status": "success", "output_file": output_path}
    print(json.dumps(result)) 