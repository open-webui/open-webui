import requests
import json
from datetime import datetime
from tqdm import tqdm
import time
import mergefeat_openwebui as mfowui

# API 설정
mfowui.api_key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjcxNDMzZGMxLTk5ZTQtNGQxYi04MjA5LWQyZGIwOTBiYmEwYiJ9.4zyGPO5zugK-lTPiXde26jprBhSn8Pu8t7i5HhZ1yss'
mfowui.host = 'http://localhost:8080'
mfowui.chat_completion_api_endpoint = '/api/chat/completions'

def process_question_safely(qa_pair, language, max_retries=5):
    question = qa_pair['question'][language]
    q_id = qa_pair['id']
    last_error = None
    
    for attempt in range(max_retries):
        try:
            response = mfowui.ChatCompletion.create(
                model='hkust-guide',
                messages=[{"role": "user", "content": question}],
                max_completion_tokens=512,
                temperature=0.5,
                num_ctx=2048
            )
            
            if response.status_code == 200:
                response_data = response.json()
                if 'choices' in response_data and len(response_data['choices']) > 0:
                    answer = response_data['choices'][0].get('message', {}).get('content', '')
                    return {
                        "id": q_id,
                        "language": language,
                        "asked_question": question,
                        "generated_answer": answer,
                        "timestamp": datetime.now().isoformat(),
                        "attempts": attempt + 1
                    }
                else:
                    raise ValueError("Invalid response format: 'choices' missing or empty")
            else:
                raise ValueError(f"API Error: {response.status_code} - {response.text}")
                
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries - 1:
                wait_time = min(2 ** attempt, 10)  # 지수 백오프 (최대 10초)
                time.sleep(wait_time)
    
    return {
        "id": q_id,
        "language": language,
        "asked_question": question,
        "generated_answer": f"Error after {max_retries} attempts: {last_error}",
        "timestamp": datetime.now().isoformat(),
        "attempts": max_retries
    }

def main():
    try:
        with open('./SHRLO_qa.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading QA file: {str(e)}")
        return

    # QA 쌍에 고유 ID 부여
    for idx, qa_pair in enumerate(data.get('housing_policies', [])):
        qa_pair['id'] = idx + 1

    results = []
    total_questions = len(data.get('housing_policies', [])) * 2
    
    with tqdm(total=total_questions, desc="Processing Questions") as pbar:
        for qa_pair in data.get('housing_policies', []):
            # 한국어 처리 (성공할 때까지 반복)
            korean_result = process_question_safely(qa_pair, 'korean')
            results.append(korean_result)
            pbar.update(1)
            
            # 영어 처리 (성공할 때까지 반복)
            english_result = process_question_safely(qa_pair, 'english')
            results.append(english_result)
            pbar.update(1)
            
            # 각 질문 처리 후 0.5초 대기 (서버 부하 방지)
            time.sleep(0.5)
    
    # 결과 처리 및 저장 (기존 코드와 동일)
    grouped_results = {}
    for result in results:
        q_id = result['id']
        if q_id not in grouped_results:
            qa_pair = next(q for q in data['housing_policies'] if q['id'] == q_id)
            grouped_results[q_id] = {
                "id": q_id,
                "original_question": qa_pair['question'],
                "original_answer": qa_pair['answer'],
                "responses": {
                    "korean": None,
                    "english": None
                },
                "timestamps": {
                    "korean": None,
                    "english": None
                },
                "attempts": {
                    "korean": 0,
                    "english": 0
                }
            }
        
        grouped_results[q_id]['responses'][result['language']] = result['generated_answer']
        grouped_results[q_id]['timestamps'][result['language']] = result['timestamp']
        grouped_results[q_id]['attempts'][result['language']] = result['attempts']
    
    sorted_results = [grouped_results[q_id] for q_id in sorted(grouped_results.keys())]
    
    output = {
        "metadata": {
            "model": "SHRLO",
            "generated_at": datetime.now().isoformat(),
            "total_questions": len(data.get('housing_policies', [])),
            "success_rate": f"{sum(1 for r in sorted_results if 'Error' not in r['responses']['korean'] and 'Error' not in r['responses']['english'])/len(sorted_results)*100:.1f}%"
        },
        "results": sorted_results
    }
    
    with open('output.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\nProcessing completed! Results saved to output.json")
    print(f"Success rate: {output['metadata']['success_rate']}")

if __name__ == "__main__":
    main()