"""
NotePlus Auto-Categorization Utility with Multi-language Support
"""

import re
from typing import Tuple, Optional, Dict

def detect_language(text: str) -> str:
    """
    Simple language detection based on character patterns.
    Returns 'ko' for Korean, 'en' for English (default)
    """
    # Check for Korean characters (Hangul)
    korean_pattern = re.compile('[가-힣]')
    korean_chars = len(korean_pattern.findall(text))
    
    # Check for Japanese characters (Hiragana, Katakana)
    japanese_pattern = re.compile('[ぁ-ゔァ-ヴー]')
    japanese_chars = len(japanese_pattern.findall(text))
    
    # Check for Chinese characters (common CJK)
    chinese_pattern = re.compile('[\u4e00-\u9fff]')
    chinese_chars = len(chinese_pattern.findall(text))
    
    total_chars = len(text.replace(' ', ''))
    
    if total_chars == 0:
        return 'en'
    
    # Calculate ratios
    korean_ratio = korean_chars / total_chars
    japanese_ratio = japanese_chars / total_chars
    chinese_ratio = chinese_chars / total_chars
    
    # If Korean is dominant (more than 20% of text)
    if korean_ratio > 0.2:
        return 'ko'
    # If Japanese is dominant
    elif japanese_ratio > 0.2:
        return 'ja'
    # If Chinese is dominant
    elif chinese_ratio > 0.2:
        return 'zh'
    else:
        return 'en'

# Multi-language category definitions
CATEGORIES = {
    'en': {
        "Development": {
            "keywords": ["code", "programming", "api", "function", "class", "method", "bug", "fix", "feature", "development", "software", "app", "application"],
            "middle": {
                "Frontend": {
                    "keywords": ["react", "vue", "angular", "svelte", "html", "css", "javascript", "typescript", "ui", "ux", "frontend", "web"],
                    "minors": ["Components", "Styling", "State Management", "General"]
                },
                "Backend": {
                    "keywords": ["python", "java", "node", "django", "fastapi", "database", "sql", "api", "server", "backend"],
                    "minors": ["API", "Database", "Security", "General"]
                },
                "DevOps": {
                    "keywords": ["docker", "kubernetes", "ci/cd", "deployment", "aws", "azure", "gcp", "jenkins", "terraform"],
                    "minors": ["Infrastructure", "CI/CD", "Monitoring", "General"]
                }
            }
        },
        "Documentation": {
            "keywords": ["document", "docs", "readme", "guide", "tutorial", "manual", "documentation", "spec"],
            "middle": {
                "Technical": {
                    "keywords": ["api", "specification", "architecture", "design", "technical", "system"],
                    "minors": ["API Docs", "Architecture", "Design", "General"]
                },
                "User": {
                    "keywords": ["user guide", "manual", "help", "faq", "tutorial", "how-to"],
                    "minors": ["Guide", "Tutorial", "FAQ", "General"]
                },
                "Process": {
                    "keywords": ["process", "workflow", "procedure", "policy", "standard"],
                    "minors": ["Workflow", "Policy", "Standards", "General"]
                }
            }
        },
        "Meeting": {
            "keywords": ["meeting", "minutes", "agenda", "discussion", "conference", "call"],
            "middle": {
                "Planning": {
                    "keywords": ["planning", "roadmap", "strategy", "goal", "objective"],
                    "minors": ["Sprint", "Quarterly", "Roadmap", "General"]
                },
                "Review": {
                    "keywords": ["review", "retrospective", "feedback", "evaluation", "assessment"],
                    "minors": ["Performance", "Project", "Code Review", "General"]
                },
                "Standup": {
                    "keywords": ["standup", "daily", "weekly", "status", "update"],
                    "minors": ["Daily", "Weekly", "Status", "General"]
                }
            }
        },
        "Research": {
            "keywords": ["research", "study", "analysis", "investigation", "explore", "survey"],
            "middle": {
                "Technical": {
                    "keywords": ["technology", "framework", "library", "tool", "comparison", "benchmark"],
                    "minors": ["Framework", "Tools", "Comparison", "General"]
                },
                "Market": {
                    "keywords": ["market", "competitor", "trend", "industry", "business"],
                    "minors": ["Analysis", "Competitor", "Trends", "General"]
                },
                "Academic": {
                    "keywords": ["paper", "thesis", "journal", "publication", "academic"],
                    "minors": ["Paper", "Thesis", "Review", "General"]
                }
            }
        },
        "Personal": {
            "keywords": ["personal", "private", "diary", "thoughts", "note", "memo"],
            "middle": {
                "Journal": {
                    "keywords": ["journal", "diary", "daily", "reflection", "log"],
                    "minors": ["Daily", "Weekly", "Monthly", "General"]
                },
                "Ideas": {
                    "keywords": ["idea", "brainstorm", "concept", "thoughts", "inspiration"],
                    "minors": ["Concepts", "Brainstorm", "Innovation", "General"]
                },
                "Tasks": {
                    "keywords": ["todo", "task", "reminder", "checklist", "action"],
                    "minors": ["TODO", "Checklist", "Reminders", "General"]
                }
            }
        }
    },
    'ko': {
        "개발": {
            "keywords": ["코드", "프로그래밍", "개발", "함수", "클래스", "메소드", "버그", "수정", "기능", "소프트웨어", "앱", "애플리케이션"],
            "middle": {
                "프론트엔드": {
                    "keywords": ["리액트", "뷰", "앵귤러", "스벨트", "html", "css", "자바스크립트", "타입스크립트", "ui", "ux", "프론트엔드", "웹"],
                    "minors": ["컴포넌트", "스타일링", "상태관리", "일반"]
                },
                "백엔드": {
                    "keywords": ["파이썬", "자바", "노드", "장고", "fastapi", "데이터베이스", "sql", "api", "서버", "백엔드"],
                    "minors": ["API", "데이터베이스", "보안", "일반"]
                },
                "데브옵스": {
                    "keywords": ["도커", "쿠버네티스", "배포", "aws", "azure", "gcp", "젠킨스", "테라폼"],
                    "minors": ["인프라", "CI/CD", "모니터링", "일반"]
                }
            }
        },
        "문서": {
            "keywords": ["문서", "문서화", "가이드", "튜토리얼", "매뉴얼", "설명서", "스펙"],
            "middle": {
                "기술문서": {
                    "keywords": ["api", "명세", "아키텍처", "설계", "기술", "시스템"],
                    "minors": ["API 문서", "아키텍처", "설계", "일반"]
                },
                "사용자문서": {
                    "keywords": ["사용자 가이드", "매뉴얼", "도움말", "faq", "튜토리얼", "사용법"],
                    "minors": ["가이드", "튜토리얼", "FAQ", "일반"]
                },
                "프로세스": {
                    "keywords": ["프로세스", "워크플로우", "절차", "정책", "표준"],
                    "minors": ["워크플로우", "정책", "표준", "일반"]
                }
            }
        },
        "회의": {
            "keywords": ["회의", "회의록", "안건", "토론", "미팅", "논의"],
            "middle": {
                "기획": {
                    "keywords": ["기획", "계획", "로드맵", "전략", "목표"],
                    "minors": ["스프린트", "분기별", "로드맵", "일반"]
                },
                "리뷰": {
                    "keywords": ["리뷰", "회고", "피드백", "평가", "검토"],
                    "minors": ["성과", "프로젝트", "코드리뷰", "일반"]
                },
                "스탠드업": {
                    "keywords": ["스탠드업", "데일리", "주간", "상태", "업데이트"],
                    "minors": ["일일", "주간", "현황", "일반"]
                }
            }
        },
        "연구": {
            "keywords": ["연구", "조사", "분석", "탐구", "검토", "서베이"],
            "middle": {
                "기술연구": {
                    "keywords": ["기술", "프레임워크", "라이브러리", "도구", "비교", "벤치마크"],
                    "minors": ["프레임워크", "도구", "비교", "일반"]
                },
                "시장조사": {
                    "keywords": ["시장", "경쟁사", "트렌드", "산업", "비즈니스"],
                    "minors": ["분석", "경쟁사", "트렌드", "일반"]
                },
                "학술연구": {
                    "keywords": ["논문", "학위논문", "저널", "출판", "학술"],
                    "minors": ["논문", "학위논문", "리뷰", "일반"]
                }
            }
        },
        "개인": {
            "keywords": ["개인", "사적", "일기", "생각", "노트", "메모"],
            "middle": {
                "일기": {
                    "keywords": ["일기", "일지", "일일", "회고", "기록"],
                    "minors": ["일일", "주간", "월간", "일반"]
                },
                "아이디어": {
                    "keywords": ["아이디어", "브레인스토밍", "컨셉", "생각", "영감"],
                    "minors": ["컨셉", "브레인스토밍", "혁신", "일반"]
                },
                "할일": {
                    "keywords": ["할일", "작업", "리마인더", "체크리스트", "액션"],
                    "minors": ["TODO", "체크리스트", "리마인더", "일반"]
                }
            }
        }
    }
}

# Default fallback categories
DEFAULT_CATEGORIES = {
    'en': ("General", "Notes", "Default"),
    'ko': ("일반", "노트", "기본"),
    'ja': ("一般", "ノート", "デフォルト"),
    'zh': ("常规", "笔记", "默认")
}

def auto_categorize(title: str, content: Optional[str] = None) -> Tuple[str, str, str]:
    """
    Automatically categorize a note based on its title and content.
    Categories are generated in the detected language of the content.
    
    Args:
        title: The title of the note
        content: The content of the note (optional)
        
    Returns:
        Tuple of (category_major, category_middle, category_minor)
    """
    
    # Combine title and content for analysis
    text = title + " " + (content[:1000] if content else "")
    text_lower = text.lower()
    
    # Detect language
    lang = detect_language(text)
    
    # Get categories for the detected language, fallback to English
    categories = CATEGORIES.get(lang, CATEGORIES['en'])
    default = DEFAULT_CATEGORIES.get(lang, DEFAULT_CATEGORIES['en'])
    
    # Find best matching major category
    best_major = default[0]
    best_middle = default[1]
    best_minor = default[2]
    max_score = 0
    
    for major, major_data in categories.items():
        score = 0
        
        # Check major category keywords
        for keyword in major_data["keywords"]:
            if keyword.lower() in text_lower:
                score += 2
        
        # Check middle category keywords
        best_middle_for_major = None
        best_middle_score = 0
        
        for middle, middle_data in major_data.get("middle", {}).items():
            middle_score = 0
            for keyword in middle_data["keywords"]:
                if keyword.lower() in text_lower:
                    middle_score += 1
            
            if middle_score > best_middle_score:
                best_middle_score = middle_score
                best_middle_for_major = middle
        
        if best_middle_for_major:
            score += best_middle_score
            if score > max_score:
                best_major = major
                best_middle = best_middle_for_major
                best_minor = _get_minor_category(text_lower, best_middle, major_data["middle"][best_middle_for_major], lang)
                max_score = score
        elif score > max_score:
            best_major = major
            # Get first middle category as default
            middle_cats = list(major_data.get("middle", {}).keys())
            best_middle = middle_cats[0] if middle_cats else default[1]
            best_minor = default[2]
            max_score = score
    
    # Date-based categorization for daily notes
    if re.match(r'^\d{4}-\d{2}-\d{2}', title):
        if max_score == 0:  # Only if no other category was strongly matched
            if lang == 'ko':
                best_major = "개인"
                best_middle = "일기"
                best_minor = "일일"
            else:
                best_major = "Personal"
                best_middle = "Journal"
                best_minor = "Daily"
    
    return best_major, best_middle, best_minor

def _get_minor_category(text: str, middle_category: str, middle_data: Dict, lang: str) -> str:
    """
    Determine minor category based on text content and middle category.
    Returns category in the appropriate language.
    """
    
    # Get available minors for this middle category
    minors = middle_data.get("minors", [])
    if not minors:
        return DEFAULT_CATEGORIES[lang][2]
    
    # Simple keyword matching for minor categories
    # This could be enhanced with more sophisticated logic
    
    # For now, return the first minor as default
    # You can enhance this with specific keyword matching
    return minors[-1]  # Return "General" or "일반" which is typically last

def suggest_categories(title: str, content: Optional[str] = None) -> dict:
    """
    Suggest multiple possible categories for a note.
    Categories are suggested in the detected language.
    
    Returns:
        Dictionary with suggested categories and confidence scores
    """
    suggestions = []
    text = title + " " + (content[:1000] if content else "")
    text_lower = text.lower()
    
    # Detect language
    lang = detect_language(text)
    
    # Get categories for the detected language
    categories = CATEGORIES.get(lang, CATEGORIES['en'])
    
    for major, major_data in categories.items():
        score = 0
        
        for keyword in major_data["keywords"]:
            if keyword.lower() in text_lower:
                score += 1
        
        if score > 0:
            suggestions.append({
                "major": major,
                "confidence": min(score * 0.3, 1.0),
                "language": lang
            })
    
    return sorted(suggestions, key=lambda x: x["confidence"], reverse=True)[:3]