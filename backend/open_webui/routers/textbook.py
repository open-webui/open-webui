import logging
import random
import time
from typing import List, Optional, Dict
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from open_webui.utils.auth import get_verified_user
from open_webui.env import SRC_LOG_LEVELS
from open_webui.internal.db import get_db
from open_webui.models.chats import Chat


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

router = APIRouter()


class Subsection(BaseModel):
    id: str
    title: str
    subtitle: str


class Section(BaseModel):
    id: str
    title: str
    subsections: List[Subsection]


class TextbookData(BaseModel):
    title: str
    author: str
    edition: str
    sections: List[Section]


TEXTBOOK_DATA = TextbookData(
    title="Advanced Engineering Mathematics",
    author="Erwin Kreyszig",
    edition="10th Edition",
    sections=[
        Section(
            id="part-a",
            title="Part A. 상미분방정식",
            subsections=[
                Subsection(
                    id="ode-1",
                    title="1. 1계 상미분방정식 (First-Order ODEs)",
                    subtitle="1계 미분방정식의 기본 개념과 해법을 학습합니다."
                ),
                Subsection(
                    id="ode-2",
                    title="2. 2계 선형 상미분방정식 (Second-Order Linear ODEs)",
                    subtitle="2계 선형 미분방정식의 해법과 응용을 다룹니다."
                ),
                Subsection(
                    id="ode-3",
                    title="3. 고계 선형 상미분방정식 (Higher Order Linear ODEs)",
                    subtitle="3계 이상의 선형 미분방정식을 학습합니다."
                )
            ]
        ),
        Section(
            id="part-b",
            title="Part B. 선형 대수, 벡터 미적분",
            subsections=[
                Subsection(
                    id="linear-1",
                    title="4. 선형 대수: 행렬, 벡터, 행렬식 (Linear Algebra: Matrices, Vectors, Determinants)",
                    subtitle="행렬과 벡터의 기본 개념을 이해합니다."
                ),
                Subsection(
                    id="linear-2",
                    title="5. 선형 대수: 행렬 고유값 문제 (Linear Algebra: Matrix Eigenvalue Problems)",
                    subtitle="고유값과 고유벡터의 개념과 응용을 학습합니다."
                ),
                Subsection(
                    id="vector-1",
                    title="6. 벡터 미적분: 그래디언트, 발산, 회전 (Vector Calculus: Gradient, Divergence, Curl)",
                    subtitle="벡터장의 미분 연산자를 이해합니다."
                )
            ]
        ),
        Section(
            id="part-c",
            title="Part C. 푸리에 해석, 편미분방정식",
            subsections=[
                Subsection(
                    id="fourier-1",
                    title="7. 푸리에 급수 (Fourier Series)",
                    subtitle="주기 함수의 푸리에 급수 전개를 학습합니다."
                ),
                Subsection(
                    id="fourier-2",
                    title="8. 푸리에 적분과 변환 (Fourier Integrals and Transforms)",
                    subtitle="푸리에 변환의 개념과 응용을 다룹니다."
                ),
                Subsection(
                    id="pde-1",
                    title="9. 편미분방정식 (Partial Differential Equations)",
                    subtitle="편미분방정식의 기본 개념과 해법을 학습합니다."
                )
            ]
        ),
        Section(
            id="part-d",
            title="Part D. 복소 해석",
            subsections=[
                Subsection(
                    id="complex-1",
                    title="10. 복소수와 복소 함수 (Complex Numbers and Functions)",
                    subtitle="복소수의 기본 개념과 복소 함수를 이해합니다."
                ),
                Subsection(
                    id="complex-2",
                    title="11. 복소 적분 (Complex Integration)",
                    subtitle="복소 평면에서의 적분을 학습합니다."
                )
            ]
        ),
        Section(
            id="general",
            title="일반 질문",
            subsections=[
                Subsection(
                    id="uncategorized",
                    title="기타 질문 (Uncategorized)",
                    subtitle="특정 챕터에 속하지 않는 일반적인 질문입니다."
                )
            ]
        )
    ]
)

# 모든 유효한 chapter_id 목록
VALID_CHAPTER_IDS = [
    "ode-1", "ode-2", "ode-3",
    "linear-1", "linear-2", "vector-1",
    "fourier-1", "fourier-2", "pde-1",
    "complex-1", "complex-2",
    "uncategorized"
]


@router.get("/", response_model=TextbookData)
async def get_textbook():
    """
    Get the complete textbook data including all sections and subsections.
    """
    return TEXTBOOK_DATA


@router.get("/sections", response_model=List[Section])
async def get_sections():
    """
    Get all sections of the textbook.
    """
    return TEXTBOOK_DATA.sections


@router.get("/sections/{section_id}", response_model=Section)
async def get_section(section_id: str):
    """
    Get a specific section by its ID.
    """
    for section in TEXTBOOK_DATA.sections:
        if section.id == section_id:
            return section
    raise HTTPException(status_code=404, detail="Section not found")


@router.get("/sections/{section_id}/subsections/{subsection_id}", response_model=Subsection)
async def get_subsection(section_id: str, subsection_id: str):
    """
    Get a specific subsection by section ID and subsection ID.
    """
    for section in TEXTBOOK_DATA.sections:
        if section.id == section_id:
            for subsection in section.subsections:
                if subsection.id == subsection_id:
                    return subsection
            raise HTTPException(status_code=404, detail="Subsection not found")
    raise HTTPException(status_code=404, detail="Section not found")


# ============================================================
# 추천 질문 (Recommended Questions)
# ============================================================

class RecommendedQuestion(BaseModel):
    id: str
    question: str
    section_id: str
    subsection_id: str
    section_title: str
    subsection_title: str


RECOMMENDED_QUESTIONS: List[RecommendedQuestion] = [
    # Part A: 상미분방정식
    RecommendedQuestion(
        id="q1",
        question="1계 미분방정식에서 변수분리법은 어떻게 사용하나요?",
        section_id="part-a",
        subsection_id="ode-1",
        section_title="Part A. 상미분방정식",
        subsection_title="1. 1계 상미분방정식 (First-Order ODEs)"
    ),
    RecommendedQuestion(
        id="q2",
        question="완전미분방정식의 판별 조건은 무엇인가요?",
        section_id="part-a",
        subsection_id="ode-1",
        section_title="Part A. 상미분방정식",
        subsection_title="1. 1계 상미분방정식 (First-Order ODEs)"
    ),
    RecommendedQuestion(
        id="q3",
        question="2계 선형 상미분방정식의 일반해 구조를 설명해주세요.",
        section_id="part-a",
        subsection_id="ode-2",
        section_title="Part A. 상미분방정식",
        subsection_title="2. 2계 선형 상미분방정식 (Second-Order Linear ODEs)"
    ),
    RecommendedQuestion(
        id="q4",
        question="특성방정식을 이용한 2계 제차 미분방정식 풀이법은?",
        section_id="part-a",
        subsection_id="ode-2",
        section_title="Part A. 상미분방정식",
        subsection_title="2. 2계 선형 상미분방정식 (Second-Order Linear ODEs)"
    ),
    RecommendedQuestion(
        id="q5",
        question="고계 미분방정식을 1계 연립방정식으로 변환하는 방법은?",
        section_id="part-a",
        subsection_id="ode-3",
        section_title="Part A. 상미분방정식",
        subsection_title="3. 고계 선형 상미분방정식 (Higher Order Linear ODEs)"
    ),

    # Part B: 선형 대수, 벡터 미적분
    RecommendedQuestion(
        id="q6",
        question="행렬의 역행렬이 존재할 조건은 무엇인가요?",
        section_id="part-b",
        subsection_id="linear-1",
        section_title="Part B. 선형 대수, 벡터 미적분",
        subsection_title="4. 선형 대수: 행렬, 벡터, 행렬식"
    ),
    RecommendedQuestion(
        id="q7",
        question="크래머 공식(Cramer's Rule)을 설명해주세요.",
        section_id="part-b",
        subsection_id="linear-1",
        section_title="Part B. 선형 대수, 벡터 미적분",
        subsection_title="4. 선형 대수: 행렬, 벡터, 행렬식"
    ),
    RecommendedQuestion(
        id="q8",
        question="고유값과 고유벡터의 물리적 의미는 무엇인가요?",
        section_id="part-b",
        subsection_id="linear-2",
        section_title="Part B. 선형 대수, 벡터 미적분",
        subsection_title="5. 선형 대수: 행렬 고유값 문제"
    ),
    RecommendedQuestion(
        id="q9",
        question="대각화 가능한 행렬의 조건은 무엇인가요?",
        section_id="part-b",
        subsection_id="linear-2",
        section_title="Part B. 선형 대수, 벡터 미적분",
        subsection_title="5. 선형 대수: 행렬 고유값 문제"
    ),
    RecommendedQuestion(
        id="q10",
        question="그래디언트(gradient)의 기하학적 의미를 설명해주세요.",
        section_id="part-b",
        subsection_id="vector-1",
        section_title="Part B. 선형 대수, 벡터 미적분",
        subsection_title="6. 벡터 미적분: 그래디언트, 발산, 회전"
    ),
    RecommendedQuestion(
        id="q11",
        question="발산(divergence)과 회전(curl)의 차이점은?",
        section_id="part-b",
        subsection_id="vector-1",
        section_title="Part B. 선형 대수, 벡터 미적분",
        subsection_title="6. 벡터 미적분: 그래디언트, 발산, 회전"
    ),

    # Part C: 푸리에 해석, 편미분방정식
    RecommendedQuestion(
        id="q12",
        question="푸리에 급수의 수렴 조건은 무엇인가요?",
        section_id="part-c",
        subsection_id="fourier-1",
        section_title="Part C. 푸리에 해석, 편미분방정식",
        subsection_title="7. 푸리에 급수 (Fourier Series)"
    ),
    RecommendedQuestion(
        id="q13",
        question="짝함수와 홀함수의 푸리에 급수는 어떻게 다른가요?",
        section_id="part-c",
        subsection_id="fourier-1",
        section_title="Part C. 푸리에 해석, 편미분방정식",
        subsection_title="7. 푸리에 급수 (Fourier Series)"
    ),
    RecommendedQuestion(
        id="q14",
        question="푸리에 변환과 라플라스 변환의 차이점은?",
        section_id="part-c",
        subsection_id="fourier-2",
        section_title="Part C. 푸리에 해석, 편미분방정식",
        subsection_title="8. 푸리에 적분과 변환"
    ),
    RecommendedQuestion(
        id="q15",
        question="열방정식(Heat Equation)의 해법을 설명해주세요.",
        section_id="part-c",
        subsection_id="pde-1",
        section_title="Part C. 푸리에 해석, 편미분방정식",
        subsection_title="9. 편미분방정식 (PDEs)"
    ),
    RecommendedQuestion(
        id="q16",
        question="파동방정식과 열방정식의 차이점은 무엇인가요?",
        section_id="part-c",
        subsection_id="pde-1",
        section_title="Part C. 푸리에 해석, 편미분방정식",
        subsection_title="9. 편미분방정식 (PDEs)"
    ),

    # Part D: 복소 해석
    RecommendedQuestion(
        id="q17",
        question="복소수의 극형식(polar form)은 어떻게 표현하나요?",
        section_id="part-d",
        subsection_id="complex-1",
        section_title="Part D. 복소 해석",
        subsection_title="10. 복소수와 복소 함수"
    ),
    RecommendedQuestion(
        id="q18",
        question="해석함수(analytic function)의 정의와 조건은?",
        section_id="part-d",
        subsection_id="complex-1",
        section_title="Part D. 복소 해석",
        subsection_title="10. 복소수와 복소 함수"
    ),
    RecommendedQuestion(
        id="q19",
        question="코시 적분 공식(Cauchy's Integral Formula)을 설명해주세요.",
        section_id="part-d",
        subsection_id="complex-2",
        section_title="Part D. 복소 해석",
        subsection_title="11. 복소 적분"
    ),
    RecommendedQuestion(
        id="q20",
        question="유수 정리(Residue Theorem)의 응용 예시는?",
        section_id="part-d",
        subsection_id="complex-2",
        section_title="Part D. 복소 해석",
        subsection_title="11. 복소 적분"
    ),
]


@router.get("/recommendations", response_model=List[RecommendedQuestion])
async def get_recommendations(
    k: int = Query(default=5, ge=1, le=20, description="Number of recommendations to return"),
    section_id: Optional[str] = Query(default=None, description="Filter by section ID"),
    subsection_id: Optional[str] = Query(default=None, description="Filter by subsection ID"),
    shuffle: bool = Query(default=True, description="Randomly shuffle the results")
):
    """
    Get k recommended questions with their related textbook section info.

    - **k**: Number of recommendations to return (1-20, default: 5)
    - **section_id**: Optional filter by section (e.g., 'part-a')
    - **subsection_id**: Optional filter by subsection (e.g., 'ode-1')
    - **shuffle**: Whether to randomly shuffle results (default: True)
    """
    filtered = RECOMMENDED_QUESTIONS

    if section_id:
        filtered = [q for q in filtered if q.section_id == section_id]

    if subsection_id:
        filtered = [q for q in filtered if q.subsection_id == subsection_id]

    if shuffle:
        filtered = random.sample(filtered, min(k, len(filtered)))
    else:
        filtered = filtered[:k]

    return filtered


@router.get("/recommendations/all", response_model=List[RecommendedQuestion])
async def get_all_recommendations():
    """
    Get all recommended questions.
    """
    return RECOMMENDED_QUESTIONS


# ============================================================
# 통계 (Statistics)
# ============================================================

class UsageStats(BaseModel):
    period_days: int
    active_users: int
    total_conversations: int
    total_qa_pairs: int
    start_timestamp: int
    end_timestamp: int


class QuestionItem(BaseModel):
    question: str
    chapter_id: Optional[str] = None
    timestamp: int
    chat_id: str


class ChapterStats(BaseModel):
    chapter_id: str
    chapter_title: str
    question_count: int
    questions: List[QuestionItem]


class ChapterStatsResponse(BaseModel):
    period_days: int
    total_questions: int
    chapters: List[ChapterStats]


@router.get("/stats/usage", response_model=UsageStats)
async def get_usage_stats(
    days: int = Query(default=7, ge=1, le=365, description="Number of days to look back")
):
    """
    최근 k일간의 사용 통계를 반환합니다.

    - **days**: 조회 기간 (일) - 기본값 7일

    반환값:
    - active_users: 활성 사용자 수
    - total_conversations: 총 대화 수
    - total_qa_pairs: 총 질문-응답 쌍 수
    """
    current_time = int(time.time())
    start_time = current_time - (days * 24 * 60 * 60)

    with get_db() as db:
        # 해당 기간의 채팅 조회
        chats = db.query(Chat).filter(Chat.created_at >= start_time).all()

        # 활성 사용자 수 (중복 제거)
        active_users = len(set(chat.user_id for chat in chats))

        # 총 대화 수
        total_conversations = len(chats)

        # 총 질문-응답 쌍 수
        total_qa_pairs = 0
        for chat in chats:
            if chat.chat and isinstance(chat.chat, dict):
                messages = chat.chat.get("messages", [])
                # user 메시지 수 = Q&A 쌍 수
                total_qa_pairs += sum(1 for msg in messages if msg.get("role") == "user")

    return UsageStats(
        period_days=days,
        active_users=active_users,
        total_conversations=total_conversations,
        total_qa_pairs=total_qa_pairs,
        start_timestamp=start_time,
        end_timestamp=current_time
    )


@router.get("/stats/by-chapter", response_model=ChapterStatsResponse)
async def get_stats_by_chapter(
    days: int = Query(default=7, ge=1, le=365, description="Number of days to look back"),
    include_questions: bool = Query(default=True, description="Include question list in response"),
    max_questions_per_chapter: int = Query(default=10, ge=1, le=100, description="Max questions per chapter")
):
    """
    최근 k일간의 질문을 챕터별로 분류하여 반환합니다.

    - **days**: 조회 기간 (일) - 기본값 7일
    - **include_questions**: 질문 목록 포함 여부
    - **max_questions_per_chapter**: 챕터당 최대 질문 수
    """
    current_time = int(time.time())
    start_time = current_time - (days * 24 * 60 * 60)

    # 챕터별 질문 수집
    chapter_questions: Dict[str, List[QuestionItem]] = defaultdict(list)
    total_questions = 0

    with get_db() as db:
        chats = db.query(Chat).filter(Chat.created_at >= start_time).all()

        for chat in chats:
            if chat.chat and isinstance(chat.chat, dict):
                messages = chat.chat.get("messages", [])
                # chat의 chapter_id 컬럼에서 직접 가져오기
                chapter_id = chat.chapter_id

                for msg in messages:
                    if msg.get("role") == "user":
                        question = msg.get("content", "")
                        if not question or len(question.strip()) < 3:
                            continue

                        total_questions += 1

                        question_item = QuestionItem(
                            question=question[:200],  # 200자로 제한
                            chapter_id=chapter_id,
                            timestamp=chat.created_at or 0,
                            chat_id=chat.id
                        )

                        if chapter_id:
                            chapter_questions[chapter_id].append(question_item)

    # 결과 구성
    chapters: List[ChapterStats] = []

    for chapter_id, questions in chapter_questions.items():
        # 챕터 제목 찾기
        chapter_title = "Unknown"
        for section in TEXTBOOK_DATA.sections:
            for subsection in section.subsections:
                if subsection.id == chapter_id:
                    chapter_title = subsection.title
                    break

        # 최신순 정렬 후 제한
        sorted_questions = sorted(questions, key=lambda x: x.timestamp, reverse=True)
        limited_questions = sorted_questions[:max_questions_per_chapter] if include_questions else []

        chapters.append(ChapterStats(
            chapter_id=chapter_id,
            chapter_title=chapter_title,
            question_count=len(questions),
            questions=limited_questions
        ))

    # 질문 수 기준 내림차순 정렬
    chapters.sort(key=lambda x: x.question_count, reverse=True)

    return ChapterStatsResponse(
        period_days=days,
        total_questions=total_questions,
        chapters=chapters
    )
