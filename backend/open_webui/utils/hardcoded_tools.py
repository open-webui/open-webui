"""
Hardcoded Tools with Response Schema

Source code-defined tools that use Gemini's response_schema feature for:
- Fast JSON generation (1 API call instead of multiple)
- Type-safe structured output
- No validation needed (schema enforces structure)

These tools:
- Are NOT stored in DB
- Cannot be edited in UI
- Can be selected in prompt groups
- Use response_schema parameter in Gemini API calls
"""

import logging
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from enum import Enum

log = logging.getLogger(__name__)


# ============================================================================
# Graph Spec Tool - Pydantic Schemas
# ============================================================================

class GraphType(str, Enum):
    """Supported graph types"""
    FUNCTION_2D = "function_2d"
    PARAMETRIC_2D = "parametric_2d"
    SCATTER_2D = "scatter_2d"
    FUNCTION_3D = "function_3d"
    PARAMETRIC_3D = "parametric_3d"
    SCATTER_3D = "scatter_3d"


class AxisConfig(BaseModel):
    """Axis configuration"""
    label: str = Field(description="Axis label (x, y, z, t, etc.)")
    min: float = Field(description="Minimum value")
    max: float = Field(description="Maximum value")


class Function2DGraph(BaseModel):
    """2D function graph: y = f(x)"""
    type: str = Field(default="function_2d", description="Graph type")
    expression: str = Field(description="Function expression in terms of x (e.g., 'sin(x)', 'x**2')")
    x_axis: AxisConfig = Field(description="X-axis configuration")
    y_axis: Optional[AxisConfig] = Field(default=None, description="Y-axis configuration (optional)")
    caption: str = Field(description="Graph caption in Korean (200+ chars explaining mathematical meaning)")


class Parametric2DGraph(BaseModel):
    """2D parametric graph: x = f(t), y = g(t)"""
    type: str = Field(default="parametric_2d", description="Graph type")
    x_expression: str = Field(description="X expression in terms of t")
    y_expression: str = Field(description="Y expression in terms of t")
    t_axis: AxisConfig = Field(description="Parameter t configuration")
    x_axis: Optional[AxisConfig] = Field(default=None, description="X-axis configuration (optional)")
    y_axis: Optional[AxisConfig] = Field(default=None, description="Y-axis configuration (optional)")
    caption: str = Field(description="Graph caption in Korean (200+ chars explaining mathematical meaning)")


class Scatter2DGraph(BaseModel):
    """2D scatter plot"""
    type: str = Field(default="scatter_2d", description="Graph type")
    points: List[List[float]] = Field(description="List of [x, y] coordinate pairs")
    x_axis: Optional[AxisConfig] = Field(default=None, description="X-axis configuration (optional)")
    y_axis: Optional[AxisConfig] = Field(default=None, description="Y-axis configuration (optional)")
    caption: str = Field(description="Graph caption in Korean (200+ chars explaining mathematical meaning)")


class Function3DGraph(BaseModel):
    """3D function graph: z = f(x, y)"""
    type: str = Field(default="function_3d", description="Graph type")
    expression: str = Field(description="Function expression in terms of x and y (e.g., 'sin(x) * cos(y)')")
    x_axis: AxisConfig = Field(description="X-axis configuration")
    y_axis: AxisConfig = Field(description="Y-axis configuration")
    z_axis: Optional[AxisConfig] = Field(default=None, description="Z-axis configuration (optional)")
    caption: str = Field(description="Graph caption in Korean (200+ chars explaining mathematical meaning)")


class Parametric3DGraph(BaseModel):
    """3D parametric graph: x = f(t), y = g(t), z = h(t)"""
    type: str = Field(default="parametric_3d", description="Graph type")
    x_expression: str = Field(description="X expression in terms of t")
    y_expression: str = Field(description="Y expression in terms of t")
    z_expression: str = Field(description="Z expression in terms of t")
    t_axis: AxisConfig = Field(description="Parameter t configuration")
    x_axis: Optional[AxisConfig] = Field(default=None, description="X-axis configuration (optional)")
    y_axis: Optional[AxisConfig] = Field(default=None, description="Y-axis configuration (optional)")
    z_axis: Optional[AxisConfig] = Field(default=None, description="Z-axis configuration (optional)")
    caption: str = Field(description="Graph caption in Korean (200+ chars explaining mathematical meaning)")


class Scatter3DGraph(BaseModel):
    """3D scatter plot"""
    type: str = Field(default="scatter_3d", description="Graph type")
    points: List[List[float]] = Field(description="List of [x, y, z] coordinate tuples")
    x_axis: Optional[AxisConfig] = Field(default=None, description="X-axis configuration (optional)")
    y_axis: Optional[AxisConfig] = Field(default=None, description="Y-axis configuration (optional)")
    z_axis: Optional[AxisConfig] = Field(default=None, description="Z-axis configuration (optional)")
    caption: str = Field(description="Graph caption in Korean (200+ chars explaining mathematical meaning)")


# Union type for all graph types
GraphSpec = Union[
    Function2DGraph,
    Parametric2DGraph,
    Scatter2DGraph,
    Function3DGraph,
    Parametric3DGraph,
    Scatter3DGraph,
]


class SuccessResponse(BaseModel):
    """Successful graph generation (Mode A)"""
    status: str = Field(default="success", description="Status of graph generation")
    graph: GraphSpec = Field(description="Graph specification")


class UnsupportedResponse(BaseModel):
    """Unsupported graph request (Mode B)"""
    status: str = Field(default="unsupported", description="Status indicating unsupported request")
    reason: str = Field(description="Reason why graph cannot be generated in Korean")


class GraphGeneratorResponse(BaseModel):
    """
    Graph generator response with two modes:
    - Mode A (success): Return graph specification
    - Mode B (unsupported): Explain why graph cannot be generated
    """
    result: Union[SuccessResponse, UnsupportedResponse] = Field(
        description="Either successful graph spec or unsupported reason"
    )


# ============================================================================
# Hardcoded Tool Metadata
# ============================================================================

class HardcodedToolMetadata(BaseModel):
    """
    Metadata for a hardcoded tool.

    Compatible with PromptModel - includes all fields needed for tool_prompts list.
    """
    # Core tool fields
    id: str = Field(description="Unique tool ID (e.g., 'hardcoded-system-graph-spec')")
    command: str = Field(description="Tool command/tag name (e.g., 'system-graph-spec')")
    name: str = Field(description="Display name")
    title: str = Field(description="Tool title")
    description: str = Field(description="Tool description")
    system_prompt: str = Field(description="System prompt for this tool (focused on logic, not format)")
    response_schema: type[BaseModel] = Field(description="Pydantic model for response_schema")
    output_tag: str = Field(description="Tag name for wrapping output (e.g., 'graph-spec')")

    # Hardcoded tool specific fields
    is_hardcoded: bool = True
    editable: bool = False

    # PromptModel compatibility fields
    content: str = Field(default="", description="Prompt content (auto-populated from system_prompt)")
    user_id: str = Field(default="system", description="User ID (always 'system' for hardcoded tools)")
    timestamp: int = Field(default=0, description="Timestamp (always 0 for hardcoded tools)")
    access_control: Optional[dict] = Field(default=None, description="Access control (always None/public)")
    prompt_type: str = Field(default="hardcoded_tool", description="Prompt type")
    persona_value: Optional[str] = Field(default=None, description="Persona value (not used)")
    tool_priority: int = Field(default=50, description="Tool priority for sorting (default: 50)")
    tool_description: Optional[str] = Field(default=None, description="Tool description for catalog")
    validation_rules: Optional[dict] = Field(default=None, description="Validation rules (not used)")

    def model_post_init(self, __context) -> None:
        """Auto-populate fields for PromptModel compatibility"""
        # Auto-populate tool_description from description if not provided
        if self.tool_description is None:
            self.tool_description = self.description

        # Auto-populate content from system_prompt for compatibility
        # content field is used by some parts of the codebase
        object.__setattr__(self, 'content', self.system_prompt)


# ============================================================================
# Tool Definitions
# ============================================================================

SYSTEM_GRAPH_SPEC_PROMPT = """당신은 수학 그래프 생성 전문가입니다.

**역할**: 사용자의 요청을 분석하여 적절한 그래프 사양을 생성합니다.

**지원 그래프 타입**:
1. **function_2d**: 2D 함수 그래프 (y = f(x))
   - 예: y = sin(x), y = x^2, y = e^x

2. **parametric_2d**: 2D 매개변수 그래프 (x = f(t), y = g(t))
   - 예: 원, 타원, 리사주 곡선

3. **scatter_2d**: 2D 산점도
   - 예: 데이터 포인트 시각화

4. **function_3d**: 3D 함수 그래프 (z = f(x, y))
   - 예: z = sin(x) * cos(y), z = x^2 + y^2

5. **parametric_3d**: 3D 매개변수 그래프 (x = f(t), y = g(t), z = h(t))
   - 예: 나선, 3D 곡선

6. **scatter_3d**: 3D 산점도
   - 예: 3D 데이터 포인트 시각화

**표현식 작성 규칙**:
- Python 수식 사용 (sin, cos, tan, exp, log, sqrt, pi 등)
- 제곱: x**2 (x^2 아님)
- 곱셈: 명시적으로 * 사용 (2*x, sin(x)*cos(y))

**축 범위 설정 가이드**:
- 삼각함수: x는 보통 [-2*pi, 2*pi], y는 [-2, 2]
- 다항식: 적절한 범위 선택 (함수 특성 고려)
- 지수/로그: 정의역 주의 (log는 양수만)

**캡션 작성 규칙**:
- **필수**: 200자 이상의 한국어 설명
- 수학적 의미 설명 (단순 재진술 금지)
- 그래프의 특징, 성질, 응용 포함
- LaTeX 수식 사용 가능 ($...$, $$...$$)

**판단 기준**:
1. 요청이 그래프로 표현 가능한가?
   - Yes → status: "success", graph 생성
   - No → status: "unsupported", 이유 설명

2. Unsupported 케이스:
   - 추상적/철학적 질문
   - 그래프와 무관한 요청
   - 데이터가 없는 통계 분석
   - 정의되지 않은 수식

**예시**:

요청: "y = sin(x) 그래프 그려줘"
→ status: "success"
→ type: "function_2d"
→ expression: "sin(x)"
→ x_axis: {label: "x", min: -6.28, max: 6.28}
→ caption: "사인 함수 y = sin(x)는 주기가 $2\\pi$인 삼각함수로, 진폭이 1이고 원점을 지나는 부드러운 파동을 나타냅니다. 이 함수는 물리학에서 단순 조화 운동, 음파, 전자기파 등 주기적 현상을 모델링하는 데 사용되며, (-1, 1) 범위에서 진동합니다..."

요청: "원의 매개변수 방정식"
→ status: "success"
→ type: "parametric_2d"
→ x_expression: "cos(t)"
→ y_expression: "sin(t)"
→ t_axis: {label: "t", min: 0, max: 6.28}
→ caption: "원의 매개변수 방정식 $x = \\cos(t), y = \\sin(t)$는 반지름 1인 단위원을 나타냅니다. 매개변수 $t$는 0부터 $2\\pi$까지 변하며, 이는 원 위의 점이 반시계 방향으로 한 바퀴 회전하는 것을 의미합니다. 이 표현은 삼각함수의 기하학적 정의와 직접 연결되며..."

요청: "행복이 뭐야?"
→ status: "unsupported"
→ reason: "이 질문은 철학적/추상적 개념에 대한 질문으로, 수학적 그래프로 표현할 수 없습니다. 그래프 생성 도구는 수학 함수, 데이터 시각화 등 정량적 표현이 가능한 요청만 처리할 수 있습니다."

**중요**: 응답은 JSON 스키마에 맞춰 자동으로 생성됩니다. 형식을 신경 쓰지 말고 수학적 정확성과 의미 있는 캡션 작성에 집중하세요.
"""


# ============================================================================
# Public API
# ============================================================================

def get_hardcoded_tools() -> List[HardcodedToolMetadata]:
    """
    Get all hardcoded tools.

    Returns:
        List of hardcoded tool metadata
    """
    return [
        HardcodedToolMetadata(
            id="hardcoded-system-graph-spec",
            command="system-graph-spec",
            title="시스템 그래프 생성기",
            name="시스템 그래프 생성기",
            description="수학 그래프를 빠르고 정확하게 생성합니다 (response_schema 사용) Use graph_spec for any requested visualization (charts/plots). Decide 2D vs 3D from the math object. Follow the graph_spec prompt as the source of truth for allowed types/fields; never invent keys. If an exact chart type is not supported, still use graph_spec and encode it via the closest supported form (e.g., binned/categorical data in 2D, or composite layers) rather than skipping the tool. meta only for title/caption.",
            system_prompt=SYSTEM_GRAPH_SPEC_PROMPT,
            response_schema=GraphGeneratorResponse,
            output_tag="graph-spec",  # Output wrapped in <graph-spec>...</graph-spec>
        )
    ]


def get_hardcoded_tool_by_command(command: str) -> Optional[HardcodedToolMetadata]:
    """
    Get hardcoded tool by command name.

    Args:
        command: Tool command (e.g., 'system-graph-spec' or '/system-graph-spec')

    Returns:
        Tool metadata if found, None otherwise
    """
    # Normalize command - remove leading slash if present
    normalized_command = command.lstrip('/')

    tools = get_hardcoded_tools()
    for tool in tools:
        if tool.command == normalized_command:
            return tool
    return None


def is_hardcoded_tool(command: str) -> bool:
    """
    Check if a tool is hardcoded.

    Args:
        command: Tool command name (with or without leading slash)

    Returns:
        True if tool is hardcoded, False otherwise
    """
    return get_hardcoded_tool_by_command(command) is not None
