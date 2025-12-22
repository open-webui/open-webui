import logging
import time
from typing import List, Optional, Dict
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from open_webui.utils.auth import get_verified_user, get_admin_user
from open_webui.env import SRC_LOG_LEVELS
from open_webui.internal.db import get_db
from open_webui.models.chats import Chat
from open_webui.models.textbooks import (
    TextbookSections,
    TextbookChapters,
    TextbookQuestions,
    TextbookSectionModel,
    TextbookChapterModel,
    TextbookQuestionModel,
    TextbookSectionResponse,
    TextbookChapterResponse,
    TextbookDataResponse,
    TextbookQuestionResponse,
    TextbookSectionForm,
    TextbookSectionUpdateForm,
    TextbookChapterForm,
    TextbookChapterUpdateForm,
    TextbookQuestionForm,
    TextbookQuestionUpdateForm,
    get_textbook_metadata,
    seed_textbook_data,
    TextbookSection,
    TextbookChapter,
    TextbookQuestion,
)


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

router = APIRouter()


# ============================================================
# Legacy Response Models (for backward compatibility)
# ============================================================

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


# ============================================================
# Public Endpoints (User-facing)
# ============================================================

@router.get("/", response_model=TextbookData)
async def get_textbook():
    """
    Get the complete textbook data including all sections and subsections.
    Fetches from database, falls back to seeding if empty.
    """
    sections_data = TextbookSections.get_all_with_chapters()

    # If no data exists, seed the database
    if not sections_data:
        seed_textbook_data()
        sections_data = TextbookSections.get_all_with_chapters()

    metadata = get_textbook_metadata()

    # Convert to legacy format for backward compatibility
    sections = []
    for section in sections_data:
        subsections = [
            Subsection(
                id=chapter.id,
                title=chapter.title,
                subtitle=chapter.subtitle or ""
            )
            for chapter in section.chapters
        ]
        sections.append(Section(
            id=section.id,
            title=section.title,
            subsections=subsections
        ))

    return TextbookData(
        title=metadata["title"],
        author=metadata["author"],
        edition=metadata["edition"],
        sections=sections
    )


@router.get("/sections", response_model=List[Section])
async def get_sections():
    """
    Get all sections of the textbook.
    """
    sections_data = TextbookSections.get_all_with_chapters()

    if not sections_data:
        seed_textbook_data()
        sections_data = TextbookSections.get_all_with_chapters()

    sections = []
    for section in sections_data:
        subsections = [
            Subsection(
                id=chapter.id,
                title=chapter.title,
                subtitle=chapter.subtitle or ""
            )
            for chapter in section.chapters
        ]
        sections.append(Section(
            id=section.id,
            title=section.title,
            subsections=subsections
        ))

    return sections


@router.get("/sections/{section_id}", response_model=Section)
async def get_section(section_id: str):
    """
    Get a specific section by its ID.
    """
    section = TextbookSections.get_by_id(section_id)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    chapters = TextbookChapters.get_by_section(section_id)
    subsections = [
        Subsection(
            id=chapter.id,
            title=chapter.title,
            subtitle=chapter.subtitle or ""
        )
        for chapter in chapters
    ]

    return Section(
        id=section.id,
        title=section.title,
        subsections=subsections
    )


@router.get("/sections/{section_id}/subsections/{subsection_id}", response_model=Subsection)
async def get_subsection(section_id: str, subsection_id: str):
    """
    Get a specific subsection by section ID and subsection ID.
    """
    section = TextbookSections.get_by_id(section_id)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    chapter = TextbookChapters.get_by_id(subsection_id)
    if not chapter or chapter.section_id != section_id:
        raise HTTPException(status_code=404, detail="Subsection not found")

    return Subsection(
        id=chapter.id,
        title=chapter.title,
        subtitle=chapter.subtitle or ""
    )


@router.get("/chapters", response_model=List[TextbookChapterModel])
async def get_all_chapters():
    """
    Get all chapters (flat list).
    """
    chapters = TextbookChapters.get_all()
    if not chapters:
        seed_textbook_data()
        chapters = TextbookChapters.get_all()
    return chapters


@router.get("/valid-chapter-ids", response_model=List[str])
async def get_valid_chapter_ids():
    """
    Get list of all valid chapter IDs.
    """
    chapter_ids = TextbookChapters.get_valid_chapter_ids()
    if not chapter_ids:
        seed_textbook_data()
        chapter_ids = TextbookChapters.get_valid_chapter_ids()
    return chapter_ids


# ============================================================
# Recommendations Endpoints
# ============================================================

class RecommendedQuestion(BaseModel):
    id: str
    question: str
    section_id: str
    subsection_id: str
    section_title: str
    subsection_title: str


@router.get("/recommendations", response_model=List[RecommendedQuestion])
async def get_recommendations(
    k: int = Query(default=5, ge=1, le=20, description="Number of recommendations to return"),
    section_id: Optional[str] = Query(default=None, description="Filter by section ID"),
    subsection_id: Optional[str] = Query(default=None, description="Filter by subsection ID (chapter ID)"),
    shuffle: bool = Query(default=True, description="Randomly shuffle the results")
):
    """
    Get k recommended questions with their related textbook section info.

    - **k**: Number of recommendations to return (1-20, default: 5)
    - **section_id**: Optional filter by section (e.g., 'part-a')
    - **subsection_id**: Optional filter by chapter (e.g., 'ch-1')
    - **shuffle**: Whether to randomly shuffle results (default: True)
    """
    questions = TextbookQuestions.get_recommendations(
        k=k,
        section_id=section_id,
        chapter_id=subsection_id,
        shuffle=shuffle
    )

    if not questions:
        seed_textbook_data()
        questions = TextbookQuestions.get_recommendations(
            k=k,
            section_id=section_id,
            chapter_id=subsection_id,
            shuffle=shuffle
        )

    return [
        RecommendedQuestion(
            id=q.id,
            question=q.question,
            section_id=q.section_id,
            subsection_id=q.chapter_id,
            section_title=q.section_title,
            subsection_title=q.chapter_title
        )
        for q in questions
    ]


@router.get("/recommendations/all", response_model=List[RecommendedQuestion])
async def get_all_recommendations():
    """
    Get all recommended questions.
    """
    questions = TextbookQuestions.get_recommendations(k=1000, shuffle=False)

    if not questions:
        seed_textbook_data()
        questions = TextbookQuestions.get_recommendations(k=1000, shuffle=False)

    return [
        RecommendedQuestion(
            id=q.id,
            question=q.question,
            section_id=q.section_id,
            subsection_id=q.chapter_id,
            section_title=q.section_title,
            subsection_title=q.chapter_title
        )
        for q in questions
    ]


# ============================================================
# Statistics Endpoints
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
        chats = db.query(Chat).filter(Chat.created_at >= start_time).all()
        active_users = len(set(chat.user_id for chat in chats))
        total_conversations = len(chats)

        total_qa_pairs = 0
        for chat in chats:
            if chat.chat and isinstance(chat.chat, dict):
                messages = chat.chat.get("messages", [])
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
    """
    current_time = int(time.time())
    start_time = current_time - (days * 24 * 60 * 60)

    chapter_questions: Dict[str, List[QuestionItem]] = defaultdict(list)
    total_questions = 0

    # Get chapter titles from DB
    all_chapters = TextbookChapters.get_all()
    chapter_titles = {c.id: c.title for c in all_chapters}

    with get_db() as db:
        chats = db.query(Chat).filter(Chat.created_at >= start_time).all()

        for chat in chats:
            if chat.chat and isinstance(chat.chat, dict):
                messages = chat.chat.get("messages", [])
                chapter_id = chat.chapter_id

                for msg in messages:
                    if msg.get("role") == "user":
                        question = msg.get("content", "")
                        if not question or len(question.strip()) < 3:
                            continue

                        total_questions += 1

                        question_item = QuestionItem(
                            question=question[:200],
                            chapter_id=chapter_id,
                            timestamp=chat.created_at or 0,
                            chat_id=chat.id
                        )

                        if chapter_id:
                            chapter_questions[chapter_id].append(question_item)

    chapters: List[ChapterStats] = []

    for chapter_id, questions in chapter_questions.items():
        chapter_title = chapter_titles.get(chapter_id, "Unknown")
        sorted_questions = sorted(questions, key=lambda x: x.timestamp, reverse=True)
        limited_questions = sorted_questions[:max_questions_per_chapter] if include_questions else []

        chapters.append(ChapterStats(
            chapter_id=chapter_id,
            chapter_title=chapter_title,
            question_count=len(questions),
            questions=limited_questions
        ))

    chapters.sort(key=lambda x: x.question_count, reverse=True)

    return ChapterStatsResponse(
        period_days=days,
        total_questions=total_questions,
        chapters=chapters
    )


# ============================================================
# Admin Endpoints (CRUD Operations)
# ============================================================

# --- Section Admin ---

@router.get("/admin/sections", response_model=List[TextbookSectionModel])
async def admin_get_all_sections(user=Depends(get_admin_user)):
    """
    [Admin] Get all sections including inactive ones.
    """
    with get_db() as db:
        sections = db.query(TextbookSection).order_by(TextbookSection.order).all()
        return [TextbookSectionModel.model_validate(s) for s in sections]


@router.post("/admin/sections", response_model=TextbookSectionModel)
async def admin_create_section(
    form: TextbookSectionForm,
    user=Depends(get_admin_user)
):
    """
    [Admin] Create a new section.
    """
    existing = TextbookSections.get_by_id(form.id)
    if existing:
        raise HTTPException(status_code=400, detail="Section ID already exists")

    return TextbookSections.create(form)


@router.put("/admin/sections/{section_id}", response_model=TextbookSectionModel)
async def admin_update_section(
    section_id: str,
    form: TextbookSectionUpdateForm,
    user=Depends(get_admin_user)
):
    """
    [Admin] Update a section.
    """
    section = TextbookSections.update(section_id, form)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    return section


@router.delete("/admin/sections/{section_id}")
async def admin_delete_section(
    section_id: str,
    user=Depends(get_admin_user)
):
    """
    [Admin] Delete a section and all its chapters.
    """
    success = TextbookSections.delete(section_id)
    if not success:
        raise HTTPException(status_code=404, detail="Section not found")
    return {"success": True, "message": f"Section {section_id} deleted"}


# --- Chapter Admin ---

@router.get("/admin/chapters", response_model=List[TextbookChapterModel])
async def admin_get_all_chapters(user=Depends(get_admin_user)):
    """
    [Admin] Get all chapters including inactive ones.
    """
    with get_db() as db:
        chapters = db.query(TextbookChapter).order_by(TextbookChapter.order).all()
        return [TextbookChapterModel.model_validate(c) for c in chapters]


@router.post("/admin/chapters", response_model=TextbookChapterModel)
async def admin_create_chapter(
    form: TextbookChapterForm,
    user=Depends(get_admin_user)
):
    """
    [Admin] Create a new chapter.
    """
    existing = TextbookChapters.get_by_id(form.id)
    if existing:
        raise HTTPException(status_code=400, detail="Chapter ID already exists")

    section = TextbookSections.get_by_id(form.section_id)
    if not section:
        raise HTTPException(status_code=400, detail="Section not found")

    return TextbookChapters.create(form)


@router.put("/admin/chapters/{chapter_id}", response_model=TextbookChapterModel)
async def admin_update_chapter(
    chapter_id: str,
    form: TextbookChapterUpdateForm,
    user=Depends(get_admin_user)
):
    """
    [Admin] Update a chapter.
    """
    if form.section_id:
        section = TextbookSections.get_by_id(form.section_id)
        if not section:
            raise HTTPException(status_code=400, detail="Section not found")

    chapter = TextbookChapters.update(chapter_id, form)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter


@router.delete("/admin/chapters/{chapter_id}")
async def admin_delete_chapter(
    chapter_id: str,
    user=Depends(get_admin_user)
):
    """
    [Admin] Delete a chapter and all its questions.
    """
    success = TextbookChapters.delete(chapter_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return {"success": True, "message": f"Chapter {chapter_id} deleted"}


# --- Question Admin ---

@router.get("/admin/questions", response_model=List[TextbookQuestionModel])
async def admin_get_all_questions(
    chapter_id: Optional[str] = Query(default=None, description="Filter by chapter ID"),
    user=Depends(get_admin_user)
):
    """
    [Admin] Get all questions including inactive ones.
    """
    with get_db() as db:
        query = db.query(TextbookQuestion)
        if chapter_id:
            query = query.filter(TextbookQuestion.chapter_id == chapter_id)
        questions = query.order_by(TextbookQuestion.order).all()
        return [TextbookQuestionModel.model_validate(q) for q in questions]


@router.post("/admin/questions", response_model=TextbookQuestionModel)
async def admin_create_question(
    form: TextbookQuestionForm,
    user=Depends(get_admin_user)
):
    """
    [Admin] Create a new question.
    """
    chapter = TextbookChapters.get_by_id(form.chapter_id)
    if not chapter:
        raise HTTPException(status_code=400, detail="Chapter not found")

    if form.id:
        existing = TextbookQuestions.get_by_id(form.id)
        if existing:
            raise HTTPException(status_code=400, detail="Question ID already exists")

    return TextbookQuestions.create(form)


@router.put("/admin/questions/{question_id}", response_model=TextbookQuestionModel)
async def admin_update_question(
    question_id: str,
    form: TextbookQuestionUpdateForm,
    user=Depends(get_admin_user)
):
    """
    [Admin] Update a question.
    """
    if form.chapter_id:
        chapter = TextbookChapters.get_by_id(form.chapter_id)
        if not chapter:
            raise HTTPException(status_code=400, detail="Chapter not found")

    question = TextbookQuestions.update(question_id, form)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


@router.delete("/admin/questions/{question_id}")
async def admin_delete_question(
    question_id: str,
    user=Depends(get_admin_user)
):
    """
    [Admin] Delete a question.
    """
    success = TextbookQuestions.delete(question_id)
    if not success:
        raise HTTPException(status_code=404, detail="Question not found")
    return {"success": True, "message": f"Question {question_id} deleted"}


# --- Seed Data ---

@router.post("/admin/seed")
async def admin_seed_data(user=Depends(get_admin_user)):
    """
    [Admin] Seed initial textbook data if not exists.
    """
    success = seed_textbook_data()
    if success:
        return {"success": True, "message": "Textbook data seeded successfully"}
    else:
        return {"success": False, "message": "Textbook data already exists"}
