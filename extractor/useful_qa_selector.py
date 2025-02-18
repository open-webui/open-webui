import json
import requests
from openai import AzureOpenAI
system_prompt = '''
당신은 두 개의 문장으로 쌍을 이루는 QA들을 받게 됩니다: 하나는 질문, 다른 하나는 그 질문에 대한 답변입니다. 각 질문과 답변은 홍콩과기대 학생 정보 공유 커뮤니티에서 질의된 질문과 그에 대한 답변에 대한 쌍입니다. 질문과 답변이 주어진 상황에서 일반적인 홍콩과기대 학생들에게 유용한 정보가 포함되어 있는지를 판단하세요.  

유용한 정보란, 질문과 답변이 특정 개인을 넘어 다른 학생들에게도 도움이 되거나, 일반적인 상황에서 지속적으로 적용될 수 있는 정보를 의미합니다. 반면, 정보가 특정 시간이나 상황에만 유효하거나 개인적인 내용일 경우 유용하다고 볼 수 없습니다. 정보안에 시간적 요소가 포함되어 있으면 유용하지 않습니다.

아래의 기준을 사용하여 판단하십시오: 

    True : 질문과 답변이 일반적인 홍콩과기대 학생들에게도 유용한 정보가 제공되는 경우.
    False : 질문과 답변이 특정 개인이나 순간에만 유용하거나, 미래에 적용될 수 없는 경우. 시간적 요소가 포함되어 있는 경우

질문-답변 쌍의 순서에 따라 True False의 나열 하세요
예시 인풋:
[
    {
        "question": "기숙사 빠지는거 이제 끝인가요?! 아님 계속해서 빠지나요?",
        "answer": "계속 빠집니다."
    },
    {
        "question": "학교 의무실에서 항생제도 주나요? 감기가 심해서ㅠ",
        "answer": "네, 넵."
    },
    {
        "question": "기숙사 사시나요?",
        "answer": "많이 안 좋으시면 오늘치 약 드릴게요. 온캠 사시면 저도 약 있어서 드릴 수 있어요."
    },
    {
        "question": "비자 연장을 할려고 하는데, 학생 비자 연장 가능한 곳 중에서 과기대랑 가장 가까운 곳이 어디에 있나요?",
        "answer": "인터넷이요; 오프라인은 완차이 뿐인걸로 알고 있습니다."
    },
    {
        "question": "과기대에서 몽콕으로 가는 가장 빠른 방법이 뭔가요?",
        "answer": "/tp @p mongkok."
    },
    {
        "question": "여자 논로컬 홀 웨잇 몇명 빠진건가요?",
        "answer": "10명 이상 빠진 듯해요, 20명 정도 빠진 것 같아요."
    },
    {
        "question": "혹시 가격도 아시나요?",
        "answer": "코베에 커트가 400, 학교는 100입니다."
    },
    {
        "question": "한국으로 visitor program 가보신 분 혹시 돌아올때 credit transfer 문제없이 잘 되셨나요?",
        "answer": "네!"
    },
    {
        "question": "헬스장 프리웨이트 하려면 예약 해야하나요?",
        "answer": "4시에서 6시 사이는 사람 많아서 예약하시는게 좋아요, 예약이 안차있으면 워크인이 가능합니다."
    },
    {
        "question": "사이쿵에서 티코가는 792m을 타면되나요?",
        "answer": "굳이 사이쿵 종점역에서 내릴 필요는 없어요."
    }
]
예시 답변 [False, True, False, True, False, False, True, True, True, False]
'''

# JSON 파일 읽기
with open('filtered_qa_pairs.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

qa_pairs = data['qa_pairs']

client = AzureOpenAI(
    api_key="1777ac2662f649a7bbc0c905d85eb7bd",
    api_version="2024-10-21",
    azure_endpoint="https://hkust.azure-api.net"
    )

# QA 쌍을 나누는 함수
def chunk_qa_pairs(qa_pairs, chunk_size):
    for i in range(0, len(qa_pairs), chunk_size):
        yield qa_pairs[i:i + chunk_size]

# LLM에 요청을 보내는 함수
def get_usefulness_from_llm(prompt, qa_chunk):
    structured_input = [{'question': pair['question'], 'answer': pair['answer']} for pair in qa_chunk]
    structured_input_str = json.dumps(structured_input, ensure_ascii=False)

    # 예시로 OpenAI API에 요청을 보낸다고 가정 (실제 사용시 API 키 필요)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"system","content":system_prompt},{"role":"user","content":structured_input_str}],
        max_tokens=4096,
        stream=False,
    )

    return response.choices[0].message.content

def extract_json(response_text):
    start_index = response_text.find('{')
    end_index = response_text.rfind('}')+1
    if start_index != -1 and end_index != -1 and end_index > start_index:
        return response_text[start_index:end_index]
    else:
        return None

# QA 쌍의 유용성을 판단하고 결과를 기반으로 필터링
filtered_qa_pairs = []
chunk_size = 10  # 한 번에 보낼 QA 쌍의 수

chunk_index = 1
chunk_number = len(qa_pairs) // chunk_size + 1
for qa_chunk in chunk_qa_pairs(qa_pairs, chunk_size):
    print(f"Processing chunk {chunk_index}/{chunk_number}")
    try:
        usefulness_response = get_usefulness_from_llm(system_prompt, qa_chunk)
        print(usefulness_response)
        usefulness_list = eval(usefulness_response.strip())  # 응답을 평가
        print(usefulness_list)

        # 유용한 QA 쌍만 필터링
        for index, usefulness in enumerate(usefulness_list):
            if usefulness:  # True인 경우만 추가
                filtered_qa_pairs.append(qa_chunk[index])
    except:
        print("An error occurred while processing the chunk. Retrying(1)...")
        try:
            usefulness_response = get_usefulness_from_llm(system_prompt, qa_chunk)
            print(usefulness_response)
            usefulness_list = eval(usefulness_response.strip())  # 응답을 평가
            print(usefulness_list)

            # 유용한 QA 쌍만 필터링
            for index, usefulness in enumerate(usefulness_list):
                if usefulness:  # True인 경우만 추가
                    filtered_qa_pairs.append(qa_chunk[index])
        except:
            print("An error occurred while processing the chunk. Retrying(final)...")
            try:
                usefulness_response = get_usefulness_from_llm(system_prompt, qa_chunk)
                print(usefulness_response)
                usefulness_list = eval(usefulness_response.strip())  # 응답을 평가
                print(usefulness_list)

                # 유용한 QA 쌍만 필터링
                for index, usefulness in enumerate(usefulness_list):
                    if usefulness:  # True인 경우만 추가
                        filtered_qa_pairs.append(qa_chunk[index])
            except:
                print("An error occurred while processing the chunk. Skipping...")
                with open('failed_chunk_indice.txt', 'a', encoding='utf-8') as f:
                    f.write(f"Failed at chunk {chunk_index}\n")
                chunk_index += 1
                continue
    chunk_index += 1

# 결과를 JSON 형식으로 저장
result_data = {"qa_pairs": filtered_qa_pairs}
with open('filtered_qa_pairs_final.json', 'w', encoding='utf-8') as f:
    json.dump(result_data, f, ensure_ascii=False, indent=4)

print("유용한 QA 쌍이 성공적으로 필터링되어 저장되었습니다.")