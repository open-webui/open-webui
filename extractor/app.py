from openai import AzureOpenAI
import tiktoken
import json
import re

client = AzureOpenAI(
    api_key="1777ac2662f649a7bbc0c905d85eb7bd",
    api_version="2024-10-21",
    azure_endpoint="https://hkust.azure-api.net"
    )

system_prompt = """
# 시스템 프롬프트

너는 대화 로그에서 질문과 답변을 추출하는 인공지능 어시스턴트야. 사용자가 제공하는 오픈채팅방의 대화 로그에서 다음의 작업을 수행해줘:

1. **질문 및 답변 식별**:
   - 각 메시지에서 질문을 검색하고 식별해줘.
   - 질문은 여러 메시지에서 나올 수 있으며, 그에 대한 답변도 나중에 올 수 있다는 점을 고려해줘.

2. **답변 연결**:
   - 각 질문에 대해 해당 질문의 답변을 최대한 연결해줘.
   - 질문 바로 뒤에 답변이 있을 필요는 없으며, 주어진 시간 안에 나오는 모든 답변을 포함해야 해.

3. **답변 부재 처리**:
   - 답변이 없거나 누락된 경우는 "답변 없음"으로 표기해줘.

4. **답변 합치기**:
   - 여러 개의 답변이 있을 경우, 이를 하나의 문자열로 합쳐서 저장해줘.
   - 답변이 여러 개일 경우, 구분 기호(쉼표, 세미콜론 등)를 사용하여 연결해줘.

5. **JSON 형식 출력**:
   - 질문과 합쳐진 답변을 JSON 형식으로 정리하여 출력해줘. JSON이외에 다른 말은 절대 하지 않아야 해.

6. **대화 로그의 흐름 이해**:
   - 질문과 답변이 있는 대화의 흐름을 이해하고, 시간이 지남에 따라 질문과 연결된 모든 답변을 최대한 포괄적으로 다뤄줘.

7. **일회성 정보 무시**
   - 대화중에 나오는 정보 중 일회성이거나 시간의 흐름에 따라 더 이상 필요하지 않은 정보는 무시해줘.

# 입/출력 예시

## 입력 예시

2023년 9월 19일 오후 11:42, 부끄러운 어피치 : 계절학기 든는데 비용 따로 지불해야하나용? 자대 기준요
2023년 9월 19일 오후 11:42, ㄱㄱㄷ : 아뇨
2023년 9월 19일 오후 11:42, 부끄러운 어피치 : 감사합니당
2023년 9월 19일 오후 11:42, ㄱㄱㄷ : 직전학기 등록된 학생이셨으면
2023년 9월 19일 오후 11:42, ㄱㄱㄷ : 비용 없어요

2023년 9월 20일 오전 12:37
2023년 9월 20일 오전 12:37, . : 대학원 지원하는데 졸업예정서가 필요한데요, 졸업하는 학기 이전에 발급 받을수있는 방법이 있을까요?ㅠㅠㅠ
2023년 9월 20일 오전 1:01, ㄱㄱㄷ : 학교에 재학증명서 요청하면
2023년 9월 20일 오전 1:02, ㄱㄱㄷ : 졸업예정 언젠지 뜨지 않나요
2023년 9월 20일 오전 1:07, . : 막학기가 아니어도 말씀이신가요?
2023년 9월 20일 오전 1:16, ㄱㄱㄷ : 4학년 1학긴데 졸업예정 안뜨네용
2023년 9월 20일 오전 1:23, ㄱ ㄱ ㄷ : 졸업신청하고 승인 받아야지 뜰걸요 
2023년 9월 20일 오전 1:37, ㅇㅇㅇ : 만약 미국 대학원 다음 가을학기 입학으로 지원하시는거면 당장은 필요 없으시지 않나여 전 입학 확정할때나 필요했던거 같은데
2023년 9월 20일 오전 11:23, . : 혹시 코로나 검사키트 있으신분 있을까요?
2023년 9월 20일 오전 11:33, ㄱㄱㄷㄷ : 저 있어요! 
2023년 9월 20일 오전 11:36, . : 어디로 가면 될까요!ㅠ
2023년 9월 20일 오전 11:42, . : 학교락커 필요하신분 있으세요?
2023년 9월 20일 오전 11:42, . : 제가 락커를 구입했는데 사용을 안할것같아서요
2023년 9월 20일 오전 11:48, . : 위치가 어디쯤인가요?
2023년 9월 20일 오전 11:49, . : <사진 읽지 않음>
2023년 9월 20일 오전 11:49, . : 여기입니다
2023년 9월 20일 오후 12:12, . : ㅠㅠ지금 필요해서.. 받을 수 있는 방법이 없을까요?
2023년 9월 20일 오후 12:13, ㄱㄱㄷ : 퓨전에 팔껄요?
2023년 9월 20일 오후 12:21, 멋쟁이 프로도 : 세븐에도 팔고 있는 걸로 알고 있어요

## 좋은 출력 예시

{
  "qa_pairs": [
    {
      "question": "계절학기 듣는데 비용을 따로 지불해야 하나요?",
      "answer": "아니요, 직전학기 등록된 학생이었으면 비용이 필요하지 않습니다."
    },
    {
      "question": "대학원 지원하는데 졸업예정서가 필요한데, 졸업하는 학기 이전에 발급 받을수있는 방법이 있을까요?",
      "answer": "졸업 신청을 하고 승인을 받으면 재학 증명서에 졸업 예정일이 표시됩니다."
    },
    {
      "question": "코로나 검사키트는 어디서 구할 수 있나요?",
      "answer": "퓨전 혹은 세븐에서 판매하고 있습니다."
    }
  ]
}
## 필요없는 질문 및 답변 예시

    "question": "학교 락커 필요한 사람이 있나요?"
    "answer": "위치는 어디쯤인가요?"

    "question": "위치는 어디쯤인가요?"
    "answer": "여기요"

# 요구 사항

제공하는 대화 로그를 분석하여, 위의 항목에 해당하는 정보를 정리하고 JSON 형식으로 출력해줘.
"""

def read_chat_log(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def chunk_chat_log(chat_log, max_tokens=2048, overlap_tokens=256):
    encoding = tiktoken.encoding_for_model("gpt-4o-mini")
    tokens = encoding.encode(chat_log)

    chunks = []
    for i in range(0, len(tokens), max_tokens - overlap_tokens):
        chunk = tokens[i:i + max_tokens]
        chunks.append(encoding.decode(chunk)) 

        if i + max_tokens >= len(tokens):
            break

    return chunks

def extract_qa_from_chat(chat_log):
    chat_text = ''.join(chat_log)
    prompt = system_prompt + "## 입력\n\n{input}\n\n## 출력\n".format(input=chat_text)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}],
        max_completion_tokens=4096,
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

def save_to_json(qa_list, output_file, index=None):
    output_file += f'{index}.json' if index is not None else '.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(qa_list, f, ensure_ascii=False, indent=4)

def main():
    input_file = 'chat_log.txt'
    output_file = 'faq'
    chat_log = read_chat_log(input_file)
    chat_chunks = chunk_chat_log(chat_log)

    for index, chunk in enumerate(chat_chunks):
        print(f"Processing chunk {index + 1}/{len(chat_chunks)} (Tokens: {len(chunk)})")
        extracted_qa_response = extract_qa_from_chat(chunk)
        extracted_json = extract_json(extracted_qa_response)
        print(extracted_json)
        try:
            qa_list = json.loads(extracted_json)
        except json.JSONDecodeError as e:
            print("Error in JSON format from LLM:", e)
            return
        save_to_json(qa_list, output_file, index)
        print(f"FAQ saved to {output_file}{index}.json")

if __name__ == "__main__":
    main()