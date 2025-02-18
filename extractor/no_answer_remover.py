import json

def filter_qa_pairs(input_file, output_file):
    # 기존 JSON 파일 읽기
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # "답변 없음" 항목 제거
    filtered_qa_pairs = [qa for qa in data.get("qa_pairs", []) if qa.get("answer") != ("답변 없음" or "답변 없음.")]

    # 최종 JSON 데이터 구조
    filtered_json = {
        "qa_pairs": filtered_qa_pairs
    }

    # 결과를 새로운 JSON 파일로 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(filtered_json, f, ensure_ascii=False, indent=4)

# 사용 예
input_file = 'merged_qa_pairs.json'  # 기존 병합된 JSON 파일 경로
output_file = 'filtered_qa_pairs.json'  # 필터링된 결과를 저장할 파일 이름

filter_qa_pairs(input_file, output_file)
print(f"Filtered QA pairs have been saved to {output_file}")