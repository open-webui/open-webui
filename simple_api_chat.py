import requests
import uuid
import time
import json

# API 엔드포인트와 인증 토큰 설정
BASE_URL = "http://localhost:8080"  # Open WebUI 서버 URL
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjRiNzcwYTY0LWRjZGYtNDU3OS1iMzM2LTEyMzBhZTA2NzQ2OSJ9.3J-OdxTfDqYTCYa5j0sGOw2p6khS2Zav-U5Qm3KapNw"  # 실제 토큰으로 대체

def simple_chat_with_log():
    """
    채팅을 생성하고 API를 호출하여 응답을 생성하고 채팅 로그를 저장하는 간단한 예제
    """
    # Step 1: 채팅 ID 및 메시지 ID 생성
    chat_id = None
    user_message_id = str(uuid.uuid4())
    assistant_message_id = str(uuid.uuid4())
    model_id = "gpt-4o-mini"  # 사용할 모델
    prompt = "안녕하세요, 간단한 채팅 API 테스트입니다."
    
    # Step 2: 새 채팅 생성
    chat_response = requests.post(
        f"{BASE_URL}/api/v1/chats/new",
        json={"chat": {"title": "Simple API Chat Test"}},
        headers={"Authorization": f"Bearer {TOKEN}"}
    )
    
    if chat_response.status_code != 200:
        print(f"채팅 생성 오류: {chat_response.text}")
        return
    
    chat_data = chat_response.json()
    chat_id = chat_data["id"]
    print(f"새 채팅이 생성되었습니다. ID: {chat_id}")
    
    # Step 3: 채팅 완성 API 호출
    completion_data = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "chat_id": chat_id,
        "id": assistant_message_id,
        "stream": False,
        "model_item": {
            "id": model_id,
            "name": "GPT-4o-mini"
        }
    }
    
    completion_response = requests.post(
        f"{BASE_URL}/api/chat/completions", 
        json=completion_data,
        headers={"Authorization": f"Bearer {TOKEN}"}
    )
    
    if completion_response.status_code != 200:
        print(f"채팅 완성 오류: {completion_response.text}")
        return
    
    completion_result = completion_response.json()
    print("응답이 생성되었습니다.")
    
    # Step 4: 콘텐츠 추출 및 채팅 업데이트
    content = None
    if "choices" in completion_result and completion_result["choices"]:
        if "message" in completion_result["choices"][0]:
            content = completion_result["choices"][0]["message"]["content"]
    
    if not content:
        print("응답 콘텐츠를 찾을 수 없습니다.")
        return
    
    # Step 5: 채팅 업데이트
    # 현재 채팅 정보 가져오기
    chat_get_response = requests.get(
        f"{BASE_URL}/api/v1/chats/{chat_id}",
        headers={"Authorization": f"Bearer {TOKEN}"}
    )
    
    if chat_get_response.status_code != 200:
        print(f"채팅 정보 조회 오류: {chat_get_response.text}")
        return
    
    chat_info = chat_get_response.json()
    
    # 채팅 기록에 메시지 추가
    current_time = int(time.time())
    
    # 채팅 기록이 없으면 초기화
    if "history" not in chat_info["chat"]:
        chat_info["chat"]["history"] = {
            "messages": {},
            "currentId": assistant_message_id
        }
    
    # 사용자 메시지 추가
    chat_info["chat"]["history"]["messages"][user_message_id] = {
        "id": user_message_id,
        "parentId": None,
        "childrenIds": [assistant_message_id],
        "role": "user",
        "content": prompt,
        "timestamp": current_time,
        "models": [model_id]
    }
    
    # 응답 메시지 추가
    chat_info["chat"]["history"]["messages"][assistant_message_id] = {
        "id": assistant_message_id,
        "parentId": user_message_id,
        "childrenIds": [],
        "role": "assistant",
        "content": content,
        "model": model_id,
        "modelName": "GPT-4o-mini",
        "done": True,
        "timestamp": current_time
    }
    
    chat_info["chat"]["history"]["currentId"] = assistant_message_id
    
    # 채팅 업데이트
    update_response = requests.post(
        f"{BASE_URL}/api/v1/chats/{chat_id}",
        json={"chat": chat_info["chat"]},
        headers={"Authorization": f"Bearer {TOKEN}"}
    )
    
    if update_response.status_code != 200:
        print(f"채팅 업데이트 오류: {update_response.text}")
        return
    
    print(f"채팅이 성공적으로 업데이트되었습니다.")
    
    # Step 6: 검증: 저장된 채팅 확인
    verification_response = requests.get(
        f"{BASE_URL}/api/v1/chats/{chat_id}",
        headers={"Authorization": f"Bearer {TOKEN}"}
    )
    
    if verification_response.status_code == 200:
        verification_data = verification_response.json()
        if assistant_message_id in verification_data["chat"]["history"]["messages"]:
            saved_content = verification_data["chat"]["history"]["messages"][assistant_message_id]["content"]
            print(f"\n저장된 응답 확인: {saved_content[:100]}...")
        else:
            print(f"저장된 메시지를 찾을 수 없습니다.")
    else:
        print(f"저장된 채팅 확인 실패: {verification_response.text}")

if __name__ == "__main__":
    simple_chat_with_log() 