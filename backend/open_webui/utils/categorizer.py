"""
NotePlus Auto-Categorization Utility
"""

import re
from typing import Tuple, Optional

# Category keywords mapping
CATEGORY_KEYWORDS = {
    "Development": {
        "keywords": ["code", "programming", "api", "function", "class", "method", "bug", "fix", "feature", "development", "개발"],
        "middle": {
            "Frontend": ["react", "vue", "angular", "svelte", "html", "css", "javascript", "typescript", "ui", "ux"],
            "Backend": ["python", "java", "node", "django", "fastapi", "database", "sql", "api", "server"],
            "DevOps": ["docker", "kubernetes", "ci/cd", "deployment", "aws", "azure", "gcp", "jenkins"]
        }
    },
    "Documentation": {
        "keywords": ["document", "docs", "readme", "guide", "tutorial", "manual", "문서"],
        "middle": {
            "Technical": ["api", "specification", "architecture", "design", "technical"],
            "User": ["user guide", "manual", "help", "faq", "tutorial"],
            "Process": ["process", "workflow", "procedure", "policy"]
        }
    },
    "Meeting": {
        "keywords": ["meeting", "minutes", "agenda", "discussion", "회의"],
        "middle": {
            "Planning": ["planning", "roadmap", "strategy", "goal"],
            "Review": ["review", "retrospective", "feedback", "evaluation"],
            "Standup": ["standup", "daily", "weekly", "status"]
        }
    },
    "Research": {
        "keywords": ["research", "study", "analysis", "investigation", "연구"],
        "middle": {
            "Technical": ["technology", "framework", "library", "tool", "comparison"],
            "Market": ["market", "competitor", "trend", "industry"],
            "Academic": ["paper", "thesis", "journal", "publication"]
        }
    },
    "Personal": {
        "keywords": ["personal", "private", "diary", "thoughts", "개인"],
        "middle": {
            "Journal": ["journal", "diary", "daily", "reflection"],
            "Ideas": ["idea", "brainstorm", "concept", "thoughts"],
            "Tasks": ["todo", "task", "reminder", "checklist"]
        }
    }
}

def auto_categorize(title: str, content: Optional[str] = None) -> Tuple[str, str, str]:
    """
    Automatically categorize a note based on its title and content.
    
    Args:
        title: The title of the note
        content: The content of the note (optional)
        
    Returns:
        Tuple of (category_major, category_middle, category_minor)
    """
    
    # Combine title and content for analysis
    text = title.lower()
    if content:
        text += " " + content.lower()[:500]  # Use first 500 chars of content
    
    # Find best matching major category
    best_major = "General"
    best_middle = "Notes"
    best_minor = "Default"
    max_score = 0
    
    for major, major_data in CATEGORY_KEYWORDS.items():
        score = 0
        
        # Check major category keywords
        for keyword in major_data["keywords"]:
            if keyword.lower() in text:
                score += 2
        
        # Check middle category keywords
        for middle, middle_keywords in major_data.get("middle", {}).items():
            middle_score = 0
            for keyword in middle_keywords:
                if keyword.lower() in text:
                    middle_score += 1
            
            if middle_score > 0:
                score += middle_score
                if score > max_score:
                    best_major = major
                    best_middle = middle
                    best_minor = _get_minor_category(text, middle)
                    max_score = score
        
        # If only major category matches
        if score > max_score:
            best_major = major
            best_middle = list(major_data.get("middle", {}).keys())[0] if major_data.get("middle") else "General"
            best_minor = "Default"
            max_score = score
    
    # Date-based categorization for daily notes
    if re.match(r'^\d{4}-\d{2}-\d{2}', title):
        if best_major == "General":
            best_major = "Personal"
            best_middle = "Journal"
            best_minor = "Daily"
    
    return best_major, best_middle, best_minor

def _get_minor_category(text: str, middle_category: str) -> str:
    """
    Determine minor category based on text content and middle category.
    """
    
    # Simple heuristics for minor categories
    if middle_category == "Frontend":
        if "component" in text:
            return "Components"
        elif "style" in text or "css" in text:
            return "Styling"
        elif "state" in text or "redux" in text:
            return "State Management"
        else:
            return "General"
    
    elif middle_category == "Backend":
        if "api" in text or "endpoint" in text:
            return "API"
        elif "database" in text or "sql" in text:
            return "Database"
        elif "auth" in text or "security" in text:
            return "Security"
        else:
            return "General"
    
    elif middle_category == "Planning":
        if "sprint" in text:
            return "Sprint"
        elif "quarter" in text or "q1" in text or "q2" in text:
            return "Quarterly"
        elif "roadmap" in text:
            return "Roadmap"
        else:
            return "General"
    
    return "Default"

def suggest_categories(title: str, content: Optional[str] = None) -> dict:
    """
    Suggest multiple possible categories for a note.
    
    Returns:
        Dictionary with suggested categories and confidence scores
    """
    suggestions = []
    text = title.lower()
    if content:
        text += " " + content.lower()[:500]
    
    for major, major_data in CATEGORY_KEYWORDS.items():
        score = 0
        
        for keyword in major_data["keywords"]:
            if keyword.lower() in text:
                score += 1
        
        if score > 0:
            suggestions.append({
                "major": major,
                "confidence": min(score * 0.3, 1.0)
            })
    
    return sorted(suggestions, key=lambda x: x["confidence"], reverse=True)[:3]