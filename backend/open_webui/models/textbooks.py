import logging
import time
import uuid
from typing import Optional, List

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, String, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship

####################
# Textbook DB Schema
####################

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


class TextbookSection(Base):
    """Part A, B, C, ... G 및 일반 질문 섹션"""
    __tablename__ = "textbook_section"

    id = Column(String, primary_key=True)  # e.g., "part-a", "part-b", "general"
    title = Column(Text, nullable=False)  # e.g., "Part A. 상미분방정식 (Ordinary Differential Equations)"
    order = Column(Integer, default=0)  # 정렬 순서
    is_active = Column(Boolean, default=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

    # Relationship
    chapters = relationship("TextbookChapter", back_populates="section", cascade="all, delete-orphan")


class TextbookChapter(Base):
    """각 챕터 (ch-1, ch-2, ... ch-25, uncategorized)"""
    __tablename__ = "textbook_chapter"

    id = Column(String, primary_key=True)  # e.g., "ch-1", "ch-2", "uncategorized"
    section_id = Column(String, ForeignKey("textbook_section.id", ondelete="CASCADE"), nullable=False)
    title = Column(Text, nullable=False)  # e.g., "1. 1계 상미분방정식 (First-Order ODEs)"
    subtitle = Column(Text, nullable=True)  # e.g., "1계 미분방정식의 기본 개념과 해법을 학습합니다."
    order = Column(Integer, default=0)  # 정렬 순서
    is_active = Column(Boolean, default=True)

    # RAG Store 매핑
    rag_store_name = Column(String, nullable=True)  # e.g., "fileSearchStores/xxx"

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

    # Relationship
    section = relationship("TextbookSection", back_populates="chapters")
    questions = relationship("TextbookQuestion", back_populates="chapter", cascade="all, delete-orphan")


class TextbookQuestion(Base):
    """추천 질문"""
    __tablename__ = "textbook_question"

    id = Column(String, primary_key=True)  # e.g., "q1", "q2", ...
    chapter_id = Column(String, ForeignKey("textbook_chapter.id", ondelete="CASCADE"), nullable=False)
    question = Column(Text, nullable=False)  # 질문 내용
    order = Column(Integer, default=0)  # 정렬 순서
    is_active = Column(Boolean, default=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

    # Relationship
    chapter = relationship("TextbookChapter", back_populates="questions")


####################
# Pydantic Models
####################

class TextbookSectionModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    order: int = 0
    is_active: bool = True
    created_at: Optional[int] = None
    updated_at: Optional[int] = None


class TextbookChapterModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    section_id: str
    title: str
    subtitle: Optional[str] = None
    order: int = 0
    is_active: bool = True
    rag_store_name: Optional[str] = None  # RAG Store 매핑
    created_at: Optional[int] = None
    updated_at: Optional[int] = None


class TextbookQuestionModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    chapter_id: str
    question: str
    order: int = 0
    is_active: bool = True
    created_at: Optional[int] = None
    updated_at: Optional[int] = None


####################
# Response Models (with nested data)
####################

class TextbookQuestionResponse(BaseModel):
    id: str
    question: str
    chapter_id: str
    chapter_title: str
    section_id: str
    section_title: str


class TextbookChapterResponse(BaseModel):
    id: str
    title: str
    subtitle: Optional[str] = None
    rag_store_name: Optional[str] = None
    questions: List[TextbookQuestionModel] = []


class TextbookSectionResponse(BaseModel):
    id: str
    title: str
    chapters: List[TextbookChapterResponse] = []


class TextbookDataResponse(BaseModel):
    title: str
    author: str
    edition: str
    sections: List[TextbookSectionResponse]


####################
# Form Models
####################

class TextbookSectionForm(BaseModel):
    id: str
    title: str
    order: Optional[int] = 0


class TextbookSectionUpdateForm(BaseModel):
    title: Optional[str] = None
    order: Optional[int] = None
    is_active: Optional[bool] = None


class TextbookChapterForm(BaseModel):
    id: str
    section_id: str
    title: str
    subtitle: Optional[str] = None
    order: Optional[int] = 0
    rag_store_name: Optional[str] = None  # RAG Store 매핑


class TextbookChapterUpdateForm(BaseModel):
    section_id: Optional[str] = None
    title: Optional[str] = None
    subtitle: Optional[str] = None
    order: Optional[int] = None
    is_active: Optional[bool] = None
    rag_store_name: Optional[str] = None  # RAG Store 매핑


class TextbookQuestionForm(BaseModel):
    id: Optional[str] = None  # Auto-generate if not provided
    chapter_id: str
    question: str
    order: Optional[int] = 0


class TextbookQuestionUpdateForm(BaseModel):
    chapter_id: Optional[str] = None
    question: Optional[str] = None
    order: Optional[int] = None
    is_active: Optional[bool] = None


####################
# CRUD Operations
####################

class TextbookSections:
    @staticmethod
    def get_all() -> List[TextbookSectionModel]:
        with get_db() as db:
            sections = db.query(TextbookSection).filter(
                TextbookSection.is_active == True
            ).order_by(TextbookSection.order).all()
            return [TextbookSectionModel.model_validate(s) for s in sections]

    @staticmethod
    def get_all_with_chapters() -> List[TextbookSectionResponse]:
        with get_db() as db:
            sections = db.query(TextbookSection).filter(
                TextbookSection.is_active == True
            ).order_by(TextbookSection.order).all()

            result = []
            for section in sections:
                chapters = db.query(TextbookChapter).filter(
                    TextbookChapter.section_id == section.id,
                    TextbookChapter.is_active == True
                ).order_by(TextbookChapter.order).all()

                chapter_responses = []
                for chapter in chapters:
                    questions = db.query(TextbookQuestion).filter(
                        TextbookQuestion.chapter_id == chapter.id,
                        TextbookQuestion.is_active == True
                    ).order_by(TextbookQuestion.order).all()

                    chapter_responses.append(TextbookChapterResponse(
                        id=chapter.id,
                        title=chapter.title,
                        subtitle=chapter.subtitle,
                        questions=[TextbookQuestionModel.model_validate(q) for q in questions]
                    ))

                result.append(TextbookSectionResponse(
                    id=section.id,
                    title=section.title,
                    chapters=chapter_responses
                ))

            return result

    @staticmethod
    def get_by_id(section_id: str) -> Optional[TextbookSectionModel]:
        with get_db() as db:
            section = db.query(TextbookSection).filter(
                TextbookSection.id == section_id
            ).first()
            return TextbookSectionModel.model_validate(section) if section else None

    @staticmethod
    def create(form: TextbookSectionForm) -> TextbookSectionModel:
        with get_db() as db:
            now = int(time.time())
            section = TextbookSection(
                id=form.id,
                title=form.title,
                order=form.order or 0,
                is_active=True,
                created_at=now,
                updated_at=now
            )
            db.add(section)
            db.commit()
            db.refresh(section)
            return TextbookSectionModel.model_validate(section)

    @staticmethod
    def update(section_id: str, form: TextbookSectionUpdateForm) -> Optional[TextbookSectionModel]:
        with get_db() as db:
            section = db.query(TextbookSection).filter(
                TextbookSection.id == section_id
            ).first()
            if not section:
                return None

            if form.title is not None:
                section.title = form.title
            if form.order is not None:
                section.order = form.order
            if form.is_active is not None:
                section.is_active = form.is_active
            section.updated_at = int(time.time())

            db.commit()
            db.refresh(section)
            return TextbookSectionModel.model_validate(section)

    @staticmethod
    def delete(section_id: str) -> bool:
        with get_db() as db:
            section = db.query(TextbookSection).filter(
                TextbookSection.id == section_id
            ).first()
            if not section:
                return False
            db.delete(section)
            db.commit()
            return True


class TextbookChapters:
    @staticmethod
    def get_all() -> List[TextbookChapterModel]:
        with get_db() as db:
            chapters = db.query(TextbookChapter).filter(
                TextbookChapter.is_active == True
            ).order_by(TextbookChapter.order).all()
            return [TextbookChapterModel.model_validate(c) for c in chapters]

    @staticmethod
    def get_by_section(section_id: str) -> List[TextbookChapterModel]:
        with get_db() as db:
            chapters = db.query(TextbookChapter).filter(
                TextbookChapter.section_id == section_id,
                TextbookChapter.is_active == True
            ).order_by(TextbookChapter.order).all()
            return [TextbookChapterModel.model_validate(c) for c in chapters]

    @staticmethod
    def get_by_id(chapter_id: str) -> Optional[TextbookChapterModel]:
        with get_db() as db:
            chapter = db.query(TextbookChapter).filter(
                TextbookChapter.id == chapter_id
            ).first()
            return TextbookChapterModel.model_validate(chapter) if chapter else None

    @staticmethod
    def get_valid_chapter_ids() -> List[str]:
        with get_db() as db:
            chapters = db.query(TextbookChapter.id).filter(
                TextbookChapter.is_active == True
            ).all()
            return [c.id for c in chapters]

    @staticmethod
    def create(form: TextbookChapterForm) -> TextbookChapterModel:
        with get_db() as db:
            now = int(time.time())
            chapter = TextbookChapter(
                id=form.id,
                section_id=form.section_id,
                title=form.title,
                subtitle=form.subtitle,
                order=form.order or 0,
                rag_store_name=form.rag_store_name,
                is_active=True,
                created_at=now,
                updated_at=now
            )
            db.add(chapter)
            db.commit()
            db.refresh(chapter)
            return TextbookChapterModel.model_validate(chapter)

    @staticmethod
    def update(chapter_id: str, form: TextbookChapterUpdateForm) -> Optional[TextbookChapterModel]:
        with get_db() as db:
            chapter = db.query(TextbookChapter).filter(
                TextbookChapter.id == chapter_id
            ).first()
            if not chapter:
                return None

            if form.section_id is not None:
                chapter.section_id = form.section_id
            if form.title is not None:
                chapter.title = form.title
            if form.subtitle is not None:
                chapter.subtitle = form.subtitle
            if form.order is not None:
                chapter.order = form.order
            if form.is_active is not None:
                chapter.is_active = form.is_active
            if form.rag_store_name is not None:
                chapter.rag_store_name = form.rag_store_name
            chapter.updated_at = int(time.time())

            db.commit()
            db.refresh(chapter)
            return TextbookChapterModel.model_validate(chapter)

    @staticmethod
    def get_rag_store(chapter_id: str) -> Optional[str]:
        """챕터 ID로 RAG Store 이름 조회"""
        with get_db() as db:
            chapter = db.query(TextbookChapter).filter(
                TextbookChapter.id == chapter_id,
                TextbookChapter.is_active == True
            ).first()
            return chapter.rag_store_name if chapter else None

    @staticmethod
    def get_all_rag_store_mappings() -> dict:
        """모든 챕터-Store 매핑 조회 (store가 설정된 챕터만)"""
        with get_db() as db:
            chapters = db.query(TextbookChapter).filter(
                TextbookChapter.rag_store_name.isnot(None),
                TextbookChapter.is_active == True
            ).all()
            return {
                c.id: {
                    "store_name": c.rag_store_name,
                    "display_name": c.title
                }
                for c in chapters
            }

    @staticmethod
    def set_rag_store(chapter_id: str, store_name: Optional[str]) -> Optional[TextbookChapterModel]:
        """챕터에 RAG Store 설정/해제"""
        with get_db() as db:
            chapter = db.query(TextbookChapter).filter(
                TextbookChapter.id == chapter_id
            ).first()
            if not chapter:
                return None

            chapter.rag_store_name = store_name
            chapter.updated_at = int(time.time())
            db.commit()
            db.refresh(chapter)
            return TextbookChapterModel.model_validate(chapter)

    @staticmethod
    def clear_rag_store_by_name(store_name: str) -> List[str]:
        """특정 Store를 사용하는 모든 챕터의 매핑 해제"""
        with get_db() as db:
            chapters = db.query(TextbookChapter).filter(
                TextbookChapter.rag_store_name == store_name
            ).all()

            cleared_chapter_ids = []
            now = int(time.time())
            for chapter in chapters:
                chapter.rag_store_name = None
                chapter.updated_at = now
                cleared_chapter_ids.append(chapter.id)

            db.commit()
            return cleared_chapter_ids

    @staticmethod
    def delete(chapter_id: str) -> bool:
        with get_db() as db:
            chapter = db.query(TextbookChapter).filter(
                TextbookChapter.id == chapter_id
            ).first()
            if not chapter:
                return False
            db.delete(chapter)
            db.commit()
            return True


class TextbookQuestions:
    @staticmethod
    def get_all() -> List[TextbookQuestionModel]:
        with get_db() as db:
            questions = db.query(TextbookQuestion).filter(
                TextbookQuestion.is_active == True
            ).order_by(TextbookQuestion.order).all()
            return [TextbookQuestionModel.model_validate(q) for q in questions]

    @staticmethod
    def get_by_chapter(chapter_id: str) -> List[TextbookQuestionModel]:
        with get_db() as db:
            questions = db.query(TextbookQuestion).filter(
                TextbookQuestion.chapter_id == chapter_id,
                TextbookQuestion.is_active == True
            ).order_by(TextbookQuestion.order).all()
            return [TextbookQuestionModel.model_validate(q) for q in questions]

    @staticmethod
    def get_by_id(question_id: str) -> Optional[TextbookQuestionModel]:
        with get_db() as db:
            question = db.query(TextbookQuestion).filter(
                TextbookQuestion.id == question_id
            ).first()
            return TextbookQuestionModel.model_validate(question) if question else None

    @staticmethod
    def get_recommendations(
        k: int = 5,
        section_id: Optional[str] = None,
        chapter_id: Optional[str] = None,
        shuffle: bool = True
    ) -> List[TextbookQuestionResponse]:
        """추천 질문 조회 (섹션/챕터 정보 포함)"""
        with get_db() as db:
            query = db.query(
                TextbookQuestion,
                TextbookChapter,
                TextbookSection
            ).join(
                TextbookChapter, TextbookQuestion.chapter_id == TextbookChapter.id
            ).join(
                TextbookSection, TextbookChapter.section_id == TextbookSection.id
            ).filter(
                TextbookQuestion.is_active == True,
                TextbookChapter.is_active == True,
                TextbookSection.is_active == True
            )

            if section_id:
                query = query.filter(TextbookSection.id == section_id)
            if chapter_id:
                query = query.filter(TextbookChapter.id == chapter_id)

            if shuffle:
                from sqlalchemy.sql.expression import func
                query = query.order_by(func.random())
            else:
                query = query.order_by(TextbookQuestion.order)

            results = query.limit(k).all()

            return [
                TextbookQuestionResponse(
                    id=q.id,
                    question=q.question,
                    chapter_id=c.id,
                    chapter_title=c.title,
                    section_id=s.id,
                    section_title=s.title
                )
                for q, c, s in results
            ]

    @staticmethod
    def create(form: TextbookQuestionForm) -> TextbookQuestionModel:
        with get_db() as db:
            now = int(time.time())
            question_id = form.id or f"q-{uuid.uuid4().hex[:8]}"
            question = TextbookQuestion(
                id=question_id,
                chapter_id=form.chapter_id,
                question=form.question,
                order=form.order or 0,
                is_active=True,
                created_at=now,
                updated_at=now
            )
            db.add(question)
            db.commit()
            db.refresh(question)
            return TextbookQuestionModel.model_validate(question)

    @staticmethod
    def update(question_id: str, form: TextbookQuestionUpdateForm) -> Optional[TextbookQuestionModel]:
        with get_db() as db:
            question = db.query(TextbookQuestion).filter(
                TextbookQuestion.id == question_id
            ).first()
            if not question:
                return None

            if form.chapter_id is not None:
                question.chapter_id = form.chapter_id
            if form.question is not None:
                question.question = form.question
            if form.order is not None:
                question.order = form.order
            if form.is_active is not None:
                question.is_active = form.is_active
            question.updated_at = int(time.time())

            db.commit()
            db.refresh(question)
            return TextbookQuestionModel.model_validate(question)

    @staticmethod
    def delete(question_id: str) -> bool:
        with get_db() as db:
            question = db.query(TextbookQuestion).filter(
                TextbookQuestion.id == question_id
            ).first()
            if not question:
                return False
            db.delete(question)
            db.commit()
            return True


####################
# Initial Data Seeding
####################

# Default textbook metadata
TEXTBOOK_METADATA = {
    "title": "Advanced Engineering Mathematics",
    "author": "Erwin Kreyszig",
    "edition": "10th Edition"
}

# Initial sections data
INITIAL_SECTIONS = [
    {"id": "part-a", "title": "Part A. 상미분방정식 (Ordinary Differential Equations)", "order": 1},
    {"id": "part-b", "title": "Part B. 선형대수, 벡터 미적분 (Linear Algebra, Vector Calculus)", "order": 2},
    {"id": "part-c", "title": "Part C. 푸리에 해석, 편미분방정식 (Fourier Analysis, PDEs)", "order": 3},
    {"id": "part-d", "title": "Part D. 복소해석 (Complex Analysis)", "order": 4},
    {"id": "part-e", "title": "Part E. 수치해석 (Numeric Analysis)", "order": 5},
    {"id": "part-f", "title": "Part F. 최적화, 그래프 (Optimization, Graphs)", "order": 6},
    {"id": "part-g", "title": "Part G. 확률, 통계 (Probability, Statistics)", "order": 7},
    {"id": "general", "title": "일반 질문", "order": 99},
]

# Initial chapters data
INITIAL_CHAPTERS = [
    # Part A: ODEs (Chapters 1-6)
    {"id": "ch-1", "section_id": "part-a", "title": "1. 1계 상미분방정식 (First-Order ODEs)", "subtitle": "1계 미분방정식의 기본 개념과 해법을 학습합니다.", "order": 1},
    {"id": "ch-2", "section_id": "part-a", "title": "2. 2계 선형 상미분방정식 (Second-Order Linear ODEs)", "subtitle": "2계 선형 미분방정식의 해법과 응용을 다룹니다.", "order": 2},
    {"id": "ch-3", "section_id": "part-a", "title": "3. 고계 선형 상미분방정식 (Higher-Order Linear ODEs)", "subtitle": "3계 이상의 선형 미분방정식을 학습합니다.", "order": 3},
    {"id": "ch-4", "section_id": "part-a", "title": "4. 상미분방정식의 연립계, 위상평면, 정성적 방법 (Systems of ODEs, Phase Plane, Qualitative Methods)", "subtitle": "연립 미분방정식과 위상평면 분석을 학습합니다.", "order": 4},
    {"id": "ch-5", "section_id": "part-a", "title": "5. 급수해법, 특수함수 (Series Solutions of ODEs, Special Functions)", "subtitle": "급수를 이용한 미분방정식의 해법과 특수함수를 다룹니다.", "order": 5},
    {"id": "ch-6", "section_id": "part-a", "title": "6. 라플라스 변환 (Laplace Transforms)", "subtitle": "라플라스 변환을 이용한 미분방정식 해법을 학습합니다.", "order": 6},
    # Part B: Linear Algebra, Vector Calculus (Chapters 7-10)
    {"id": "ch-7", "section_id": "part-b", "title": "7. 선형대수: 행렬, 벡터, 선형시스템 (Linear Algebra: Matrices, Vectors, Linear Systems)", "subtitle": "행렬과 벡터의 기본 개념, 선형시스템을 이해합니다.", "order": 7},
    {"id": "ch-8", "section_id": "part-b", "title": "8. 행렬 고유값 문제 (Matrix Eigenvalue Problems)", "subtitle": "고유값과 고유벡터의 개념과 응용을 학습합니다.", "order": 8},
    {"id": "ch-9", "section_id": "part-b", "title": "9. 벡터 미분학: 기울기, 발산, 회전 (Vector Differential Calculus: Grad, Div, Curl)", "subtitle": "벡터장의 미분 연산자를 이해합니다.", "order": 9},
    {"id": "ch-10", "section_id": "part-b", "title": "10. 벡터 적분학, 적분정리 (Vector Integral Calculus, Integral Theorems)", "subtitle": "선적분, 면적분과 적분정리를 학습합니다.", "order": 10},
    # Part C: Fourier Analysis, PDEs (Chapters 11-12)
    {"id": "ch-11", "section_id": "part-c", "title": "11. 푸리에 해석 (Fourier Analysis)", "subtitle": "푸리에 급수와 푸리에 변환을 학습합니다.", "order": 11},
    {"id": "ch-12", "section_id": "part-c", "title": "12. 편미분방정식 (Partial Differential Equations)", "subtitle": "편미분방정식의 기본 개념과 해법을 학습합니다.", "order": 12},
    # Part D: Complex Analysis (Chapters 13-18)
    {"id": "ch-13", "section_id": "part-d", "title": "13. 복소수와 복소함수 (Complex Numbers and Functions)", "subtitle": "복소수의 기본 개념과 복소함수를 이해합니다.", "order": 13},
    {"id": "ch-14", "section_id": "part-d", "title": "14. 복소적분 (Complex Integration)", "subtitle": "복소평면에서의 적분을 학습합니다.", "order": 14},
    {"id": "ch-15", "section_id": "part-d", "title": "15. 거듭제곱급수, 테일러급수 (Power Series, Taylor Series)", "subtitle": "복소함수의 거듭제곱급수 전개를 다룹니다.", "order": 15},
    {"id": "ch-16", "section_id": "part-d", "title": "16. 로랑급수, 유수 (Laurent Series, Residues)", "subtitle": "로랑급수와 유수정리를 학습합니다.", "order": 16},
    {"id": "ch-17", "section_id": "part-d", "title": "17. 등각사상 (Conformal Mapping)", "subtitle": "복소평면에서의 등각사상을 이해합니다.", "order": 17},
    {"id": "ch-18", "section_id": "part-d", "title": "18. 포텐셜 이론의 응용 (Applications to Potential Theory)", "subtitle": "복소해석의 포텐셜 이론 응용을 학습합니다.", "order": 18},
    # Part E: Numeric Analysis (Chapters 19-21)
    {"id": "ch-19", "section_id": "part-e", "title": "19. 수치해석 일반 (Numerics in General)", "subtitle": "수치해석의 기본 개념과 오차 분석을 학습합니다.", "order": 19},
    {"id": "ch-20", "section_id": "part-e", "title": "20. 수치 선형대수 (Numerical Linear Algebra)", "subtitle": "선형시스템의 수치적 해법을 다룹니다.", "order": 20},
    {"id": "ch-21", "section_id": "part-e", "title": "21. 상미분방정식과 편미분방정식의 수치해법 (Numerics for ODEs and PDEs)", "subtitle": "미분방정식의 수치적 해법을 학습합니다.", "order": 21},
    # Part F: Optimization, Graphs (Chapters 22-23)
    {"id": "ch-22", "section_id": "part-f", "title": "22. 비제약 최적화, 선형계획법 (Unconstrained Optimization, Linear Programming)", "subtitle": "최적화 문제와 선형계획법을 학습합니다.", "order": 22},
    {"id": "ch-23", "section_id": "part-f", "title": "23. 그래프와 조합 최적화 (Graphs and Combinatorial Optimization)", "subtitle": "그래프 이론과 조합 최적화를 다룹니다.", "order": 23},
    # Part G: Probability, Statistics (Chapters 24-25)
    {"id": "ch-24", "section_id": "part-g", "title": "24. 데이터 분석, 확률론 (Data Analysis, Probability Theory)", "subtitle": "데이터 분석과 확률론의 기초를 학습합니다.", "order": 24},
    {"id": "ch-25", "section_id": "part-g", "title": "25. 수리통계학 (Mathematical Statistics)", "subtitle": "수리통계학의 주요 개념을 다룹니다.", "order": 25},
    # General
    {"id": "uncategorized", "section_id": "general", "title": "기타 질문 (Uncategorized)", "subtitle": "특정 챕터에 속하지 않는 일반적인 질문입니다.", "order": 99},
]

# Initial questions data
INITIAL_QUESTIONS = [
    # Chapter 1
    {"id": "q1", "chapter_id": "ch-1", "question": "1계 미분방정식에서 변수분리법은 어떻게 사용하나요?", "order": 1},
    {"id": "q2", "chapter_id": "ch-1", "question": "완전미분방정식의 판별 조건은 무엇인가요?", "order": 2},
    # Chapter 2
    {"id": "q3", "chapter_id": "ch-2", "question": "2계 선형 상미분방정식의 일반해 구조를 설명해주세요.", "order": 1},
    {"id": "q4", "chapter_id": "ch-2", "question": "특성방정식을 이용한 2계 제차 미분방정식 풀이법은?", "order": 2},
    # Chapter 3
    {"id": "q5", "chapter_id": "ch-3", "question": "고계 미분방정식을 1계 연립방정식으로 변환하는 방법은?", "order": 1},
    # Chapter 4
    {"id": "q6", "chapter_id": "ch-4", "question": "위상평면에서 임계점의 안정성은 어떻게 분석하나요?", "order": 1},
    # Chapter 5
    {"id": "q7", "chapter_id": "ch-5", "question": "프로베니우스 방법(Frobenius method)을 설명해주세요.", "order": 1},
    {"id": "q8", "chapter_id": "ch-5", "question": "베셀 함수(Bessel functions)의 정의와 응용은?", "order": 2},
    # Chapter 6
    {"id": "q9", "chapter_id": "ch-6", "question": "라플라스 변환의 기본 성질과 공식은 무엇인가요?", "order": 1},
    {"id": "q10", "chapter_id": "ch-6", "question": "라플라스 변환을 이용해 미분방정식을 푸는 과정을 설명해주세요.", "order": 2},
    # Chapter 7
    {"id": "q11", "chapter_id": "ch-7", "question": "행렬의 역행렬이 존재할 조건은 무엇인가요?", "order": 1},
    {"id": "q12", "chapter_id": "ch-7", "question": "크래머 공식(Cramer's Rule)을 설명해주세요.", "order": 2},
    # Chapter 8
    {"id": "q13", "chapter_id": "ch-8", "question": "고유값과 고유벡터의 물리적 의미는 무엇인가요?", "order": 1},
    {"id": "q14", "chapter_id": "ch-8", "question": "대각화 가능한 행렬의 조건은 무엇인가요?", "order": 2},
    # Chapter 9
    {"id": "q15", "chapter_id": "ch-9", "question": "그래디언트(gradient)의 기하학적 의미를 설명해주세요.", "order": 1},
    {"id": "q16", "chapter_id": "ch-9", "question": "발산(divergence)과 회전(curl)의 차이점은?", "order": 2},
    # Chapter 10
    {"id": "q17", "chapter_id": "ch-10", "question": "그린 정리(Green's Theorem)를 설명해주세요.", "order": 1},
    {"id": "q18", "chapter_id": "ch-10", "question": "스토크스 정리(Stokes' Theorem)와 발산 정리의 관계는?", "order": 2},
    # Chapter 11
    {"id": "q19", "chapter_id": "ch-11", "question": "푸리에 급수의 수렴 조건은 무엇인가요?", "order": 1},
    {"id": "q20", "chapter_id": "ch-11", "question": "짝함수와 홀함수의 푸리에 급수는 어떻게 다른가요?", "order": 2},
    # Chapter 12
    {"id": "q21", "chapter_id": "ch-12", "question": "열방정식(Heat Equation)의 해법을 설명해주세요.", "order": 1},
    {"id": "q22", "chapter_id": "ch-12", "question": "파동방정식과 열방정식의 차이점은 무엇인가요?", "order": 2},
    # Chapter 13
    {"id": "q23", "chapter_id": "ch-13", "question": "복소수의 극형식(polar form)은 어떻게 표현하나요?", "order": 1},
    {"id": "q24", "chapter_id": "ch-13", "question": "해석함수(analytic function)의 정의와 조건은?", "order": 2},
    # Chapter 14
    {"id": "q25", "chapter_id": "ch-14", "question": "코시 적분 공식(Cauchy's Integral Formula)을 설명해주세요.", "order": 1},
    # Chapter 15
    {"id": "q26", "chapter_id": "ch-15", "question": "복소함수의 테일러 급수 전개는 어떻게 하나요?", "order": 1},
    # Chapter 16
    {"id": "q27", "chapter_id": "ch-16", "question": "유수 정리(Residue Theorem)의 응용 예시는?", "order": 1},
    {"id": "q28", "chapter_id": "ch-16", "question": "로랑 급수와 테일러 급수의 차이점은 무엇인가요?", "order": 2},
    # Chapter 17
    {"id": "q29", "chapter_id": "ch-17", "question": "등각사상(conformal mapping)이란 무엇인가요?", "order": 1},
    # Chapter 18
    {"id": "q30", "chapter_id": "ch-18", "question": "복소해석이 유체역학에 어떻게 응용되나요?", "order": 1},
    # Chapter 19
    {"id": "q31", "chapter_id": "ch-19", "question": "수치해석에서 오차의 종류와 분석 방법은?", "order": 1},
    {"id": "q32", "chapter_id": "ch-19", "question": "뉴턴-랩슨 방법(Newton-Raphson method)을 설명해주세요.", "order": 2},
    # Chapter 20
    {"id": "q33", "chapter_id": "ch-20", "question": "가우스 소거법(Gaussian elimination)의 원리는?", "order": 1},
    {"id": "q34", "chapter_id": "ch-20", "question": "LU 분해(LU decomposition)를 설명해주세요.", "order": 2},
    # Chapter 21
    {"id": "q35", "chapter_id": "ch-21", "question": "오일러 방법(Euler method)과 룽게-쿠타 방법의 차이점은?", "order": 1},
    {"id": "q36", "chapter_id": "ch-21", "question": "유한차분법(finite difference method)을 설명해주세요.", "order": 2},
    # Chapter 22
    {"id": "q37", "chapter_id": "ch-22", "question": "경사하강법(gradient descent)의 원리를 설명해주세요.", "order": 1},
    {"id": "q38", "chapter_id": "ch-22", "question": "심플렉스 방법(Simplex method)이란 무엇인가요?", "order": 2},
    # Chapter 23
    {"id": "q39", "chapter_id": "ch-23", "question": "그래프 이론에서 최단 경로 알고리즘은 어떤 것이 있나요?", "order": 1},
    {"id": "q40", "chapter_id": "ch-23", "question": "최소 신장 트리(minimum spanning tree)를 구하는 방법은?", "order": 2},
    # Chapter 24
    {"id": "q41", "chapter_id": "ch-24", "question": "베이즈 정리(Bayes' Theorem)를 설명해주세요.", "order": 1},
    {"id": "q42", "chapter_id": "ch-24", "question": "정규분포(normal distribution)의 특성은 무엇인가요?", "order": 2},
    # Chapter 25
    {"id": "q43", "chapter_id": "ch-25", "question": "최대우도추정(MLE)의 원리를 설명해주세요.", "order": 1},
    {"id": "q44", "chapter_id": "ch-25", "question": "가설검정(hypothesis testing)의 절차는 어떻게 되나요?", "order": 2},
]


def seed_textbook_data() -> bool:
    """
    데이터베이스에 초기 교재 데이터를 시딩합니다.
    이미 데이터가 존재하면 건너뜁니다.
    """
    with get_db() as db:
        # Check if data already exists
        existing_sections = db.query(TextbookSection).count()
        if existing_sections > 0:
            log.info("Textbook data already exists, skipping seed.")
            return False

        now = int(time.time())

        # Insert sections
        for section_data in INITIAL_SECTIONS:
            section = TextbookSection(
                id=section_data["id"],
                title=section_data["title"],
                order=section_data["order"],
                is_active=True,
                created_at=now,
                updated_at=now
            )
            db.add(section)

        db.commit()
        log.info(f"Seeded {len(INITIAL_SECTIONS)} textbook sections.")

        # Insert chapters
        for chapter_data in INITIAL_CHAPTERS:
            chapter = TextbookChapter(
                id=chapter_data["id"],
                section_id=chapter_data["section_id"],
                title=chapter_data["title"],
                subtitle=chapter_data.get("subtitle"),
                order=chapter_data["order"],
                is_active=True,
                created_at=now,
                updated_at=now
            )
            db.add(chapter)

        db.commit()
        log.info(f"Seeded {len(INITIAL_CHAPTERS)} textbook chapters.")

        # Insert questions
        for question_data in INITIAL_QUESTIONS:
            question = TextbookQuestion(
                id=question_data["id"],
                chapter_id=question_data["chapter_id"],
                question=question_data["question"],
                order=question_data["order"],
                is_active=True,
                created_at=now,
                updated_at=now
            )
            db.add(question)

        db.commit()
        log.info(f"Seeded {len(INITIAL_QUESTIONS)} textbook questions.")

        return True


def get_textbook_metadata() -> dict:
    """교재 메타데이터 반환"""
    return TEXTBOOK_METADATA
