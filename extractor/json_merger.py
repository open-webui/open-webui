import json
import os

def merge_json_files(input_folder, output_file):
    merged_qa_pairs = []

    # 입력 폴더의 모든 JSON 파일을 순회
    for i in range(335):
        file_path = os.path.join(input_folder, f"faq{i}.json")

            # JSON 파일 읽기
        print(f"Merging {file_path}...")
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # qa_pairs 리스트를 추출하여 병합
            merged_qa_pairs.extend(data.get("qa_pairs", []))

    # 최종 JSON 데이터 구조
    merged_json = {
        "qa_pairs": merged_qa_pairs
    }

    # 결과를 새로운 JSON 파일로 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(merged_json, f, ensure_ascii=False, indent=4)

# 사용 예
input_folder = '.'  # JSON 파일들이 있는 폴더 경로
output_file = 'merged_qa_pairs.json'       # 저장할 출력 파일 이름

merge_json_files(input_folder, output_file)
print(f"All JSON files merged into {output_file}")