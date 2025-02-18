import json
import os

# JSON 파일 경로
json_file_path = 'filtered_qa_pairs_final.json'  # 여기에 JSON 파일 경로 입력

# 출력할 디렉토리 생성
output_dir = 'qa_pairs_output'
os.makedirs(output_dir, exist_ok=True)

# JSON 파일 읽기
with open(json_file_path, 'r', encoding='utf-8') as json_file:
    data = json.load(json_file)

# 각 질문-답변 쌍을 파일로 저장
for index, qa_pair in enumerate(data['qa_pairs']):
    question = qa_pair['question']
    answer = qa_pair['answer']
    
    # 파일 이름 설정
    file_name = f'qa_pair_{index + 1}.txt'
    file_path = os.path.join(output_dir, file_name)
    
    # 질문과 답변을 파일에 쓰기
    with open(file_path, 'w', encoding='utf-8') as txt_file:
        txt_file.write(f'질문: {question}\n')
        txt_file.write(f'답변: {answer}\n')

print("모든 질문-답변 쌍이 각각의 txt 파일로 저장되었습니다.")