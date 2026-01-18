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
from typing import Optional, List, Dict, Any, Union, Literal
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)


# ============================================================================
# Graph Spec Tool - Pydantic Schemas (Frontend-aligned)
# ============================================================================

# Use Literal instead of Enum for strict string validation
GraphType = Literal[
    "function_2d",
    "parametric_2d",
    "scatter_2d",
    "function_3d",
    "parametric_3d",
    "scatter_3d",
    "phase_plane",
    "vector_field_3d",
    "vector_2d",
    "composite_2d",
    # Engineering mathematics types (Phase 3)
    "heatmap_2d",
    "contour_2d",
    "implicit_2d",
]

MarkerType = Literal['circle', 'square', 'triangle', 'diamond', 'cross', 'sphere']
LineStyle = Literal['solid', 'dashed', 'dotted']


class AxisConfig(BaseModel):
    """Axis configuration"""
    label: str = Field(description="Axis label (x, y, z, t, etc.)")
    min: float = Field(description="Minimum value")
    max: float = Field(description="Maximum value")


class Domain2DConfig(BaseModel):
    """2D domain configuration for heatmap/contour/implicit graphs"""
    x: List[float] = Field(description="X domain [xmin, xmax]")
    y: List[float] = Field(description="Y domain [ymin, ymax]")


class ContoursConfig(BaseModel):
    """Contour lines configuration"""
    start: Optional[float] = Field(default=None, description="Start value for contour lines")
    end: Optional[float] = Field(default=None, description="End value for contour lines")
    size: Optional[float] = Field(default=None, description="Step size between contour lines")


class StyleConfig(BaseModel):
    """Style configuration for graphs"""
    color: Optional[Union[str, List[str]]] = Field(default=None, description="Color(s) for the graph")
    marker: Optional[MarkerType] = Field(default=None, description="Marker type for scatter plots")
    lineStyle: Optional[LineStyle] = Field(default=None, description="Line style")
    opacity: Optional[float] = Field(default=None, description="Opacity (0-1)")


class GraphMeta(BaseModel):
    """Metadata for graph (title and caption)"""
    title: str = Field(description="Graph title in Korean")
    caption: str = Field(
        min_length=200,
        description="Detailed caption in Korean (200+ chars minimum) explaining mathematical meaning, applications, and graph characteristics"
    )


class Function2DGraph(BaseModel):
    """2D function graph: y = f(x)"""
    type: Literal["function_2d"] = Field(default="function_2d", description="Graph type")
    expression: str = Field(description="Function expression ONLY in terms of x (e.g., 'sin(x)', 'x^2'). MUST NOT include y variable! If y is needed, use function_3d/heatmap_2d/contour_2d instead.")
    x_axis: AxisConfig = Field(description="X-axis configuration")
    y_axis: Optional[AxisConfig] = Field(default=None, description="Y-axis configuration (optional)")
    style: Optional[StyleConfig] = Field(default=None, description="Style configuration (optional)")
    meta: GraphMeta = Field(description="Graph metadata (title and caption)")


class Parametric2DGraph(BaseModel):
    """2D parametric graph: x = f(t), y = g(t)"""
    type: str = Field(default="parametric_2d", description="Graph type")
    x_expression: str = Field(description="X expression in terms of t")
    y_expression: str = Field(description="Y expression in terms of t")
    t_axis: AxisConfig = Field(description="Parameter t configuration")
    x_axis: Optional[AxisConfig] = Field(default=None, description="X-axis configuration (optional)")
    y_axis: Optional[AxisConfig] = Field(default=None, description="Y-axis configuration (optional)")
    meta: GraphMeta = Field(description="Graph metadata (title and caption)")


class Scatter2DGraph(BaseModel):
    """2D scatter plot"""
    type: str = Field(default="scatter_2d", description="Graph type")
    points: List[List[float]] = Field(description="List of [x, y] coordinate pairs")
    x_axis: Optional[AxisConfig] = Field(default=None, description="X-axis configuration (optional)")
    y_axis: Optional[AxisConfig] = Field(default=None, description="Y-axis configuration (optional)")
    meta: GraphMeta = Field(description="Graph metadata (title and caption)")


class Function3DGraph(BaseModel):
    """3D function graph: z = f(x, y)"""
    type: str = Field(default="function_3d", description="Graph type")
    expression: str = Field(description="Function expression in terms of BOTH x and y (e.g., 'sin(x) * cos(y)', 'x^2 + y^2'). Use this for 2-variable functions.")
    x_axis: AxisConfig = Field(description="X-axis configuration")
    y_axis: AxisConfig = Field(description="Y-axis configuration")
    z_axis: Optional[AxisConfig] = Field(default=None, description="Z-axis configuration (optional)")
    meta: GraphMeta = Field(description="Graph metadata (title and caption)")


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
    meta: GraphMeta = Field(description="Graph metadata (title and caption)")


class Scatter3DGraph(BaseModel):
    """3D scatter plot"""
    type: str = Field(default="scatter_3d", description="Graph type")
    points: List[List[float]] = Field(description="List of [x, y, z] coordinate tuples")
    x_axis: Optional[AxisConfig] = Field(default=None, description="X-axis configuration (optional)")
    y_axis: Optional[AxisConfig] = Field(default=None, description="Y-axis configuration (optional)")
    z_axis: Optional[AxisConfig] = Field(default=None, description="Z-axis configuration (optional)")
    meta: GraphMeta = Field(description="Graph metadata (title and caption)")


class VectorFieldConfig(BaseModel):
    """Vector field configuration (differential equations)"""
    dx: str = Field(description="dx/dt expression in terms of x, y (and z for 3D)")
    dy: str = Field(description="dy/dt expression in terms of x, y (and z for 3D)")
    dz: Optional[str] = Field(default=None, description="dz/dt expression (3D only)")


class DomainConfig(BaseModel):
    """Domain configuration for vector fields"""
    x: List[float] = Field(description="X domain [min, max]")
    y: List[float] = Field(description="Y domain [min, max]")
    z: Optional[List[float]] = Field(default=None, description="Z domain [min, max] (3D only)")


class SamplingConfig(BaseModel):
    """Sampling configuration for vector fields"""
    x: int = Field(description="Number of samples along x-axis")
    y: int = Field(description="Number of samples along y-axis")
    z: Optional[int] = Field(default=None, description="Number of samples along z-axis (3D only)")


class PhasePlaneGraph(BaseModel):
    """2D vector field (phase plane) for differential equations"""
    type: str = Field(default="phase_plane", description="Graph type")
    field: VectorFieldConfig = Field(description="Vector field equations (dx, dy)")
    domain: DomainConfig = Field(description="Domain for x and y")
    sampling: SamplingConfig = Field(description="Sampling density")
    meta: GraphMeta = Field(description="Graph metadata (title and caption)")


class VectorField3DGraph(BaseModel):
    """3D vector field visualization"""
    type: str = Field(default="vector_field_3d", description="Graph type")
    field: VectorFieldConfig = Field(description="Vector field equations (dx, dy, dz)")
    domain: DomainConfig = Field(description="Domain for x, y, and z")
    sampling: SamplingConfig = Field(description="Sampling density")
    meta: GraphMeta = Field(description="Graph metadata (title and caption)")


class VectorArrow(BaseModel):
    """Individual vector arrow"""
    start: List[float] = Field(description="Starting point [x, y]")
    end: List[float] = Field(description="Ending point [x, y]")
    color: Optional[str] = Field(default="blue", description="Arrow color (optional)")


class Vector2DGraph(BaseModel):
    """Individual 2D vector arrows"""
    type: str = Field(default="vector_2d", description="Graph type")
    data: List[VectorArrow] = Field(description="List of vector arrows")
    meta: GraphMeta = Field(description="Graph metadata (title and caption)")


# Define layer types (for composite graphs)
GraphLayer = Union[
    Function2DGraph,
    Parametric2DGraph,
    Scatter2DGraph,
]


class Composite2DGraph(BaseModel):
    """Composite 2D graph with multiple layers"""
    type: Literal["composite_2d"] = Field(default="composite_2d", description="Graph type")
    layers: List[GraphLayer] = Field(description="List of graph layers to overlay")
    x_axis: Optional[AxisConfig] = Field(default=None, description="Shared X-axis configuration (optional)")
    y_axis: Optional[AxisConfig] = Field(default=None, description="Shared Y-axis configuration (optional)")
    meta: GraphMeta = Field(description="Graph metadata (title and caption)")


class Heatmap2DGraph(BaseModel):
    """2D heatmap for scalar field z = f(x, y) - temperature distribution, wave propagation"""
    type: Literal["heatmap_2d"] = Field(default="heatmap_2d", description="Graph type")
    expression: str = Field(description="z = f(x, y) expression using BOTH x and y variables (e.g., 'exp(-(x^2 + y^2))', 'sin(x)*cos(y)', 'sin(x)*sin(y)'). Use this for 2-variable scalar fields.")
    domain: Domain2DConfig = Field(description="Domain for x and y")
    color_scheme: Optional[str] = Field(default="Viridis", description="Plotly colorscale (Viridis, Hot, RdBu, etc.)")
    style: Optional[StyleConfig] = Field(default=None, description="Style configuration (optional)")
    meta: GraphMeta = Field(description="Graph metadata (title and caption, 200+ chars)")


class Contour2DGraph(BaseModel):
    """2D contour lines for z = f(x, y) - potential fields, gradient visualization"""
    type: Literal["contour_2d"] = Field(default="contour_2d", description="Graph type")
    expression: str = Field(description="z = f(x, y) expression using BOTH x and y variables. Use this for 2-variable functions to show contour lines.")
    domain: Domain2DConfig = Field(description="Domain for x and y")
    contours: Optional[ContoursConfig] = Field(
        default=None,
        description="Contour configuration (start, end, size)"
    )
    style: Optional[StyleConfig] = Field(default=None, description="Style configuration (optional)")
    meta: GraphMeta = Field(description="Graph metadata (title and caption, 200+ chars)")


class Implicit2DGraph(BaseModel):
    """Implicit curve where F(x, y) = 0 - conic sections, level sets"""
    type: Literal["implicit_2d"] = Field(default="implicit_2d", description="Graph type")
    expression: str = Field(
        description="F(x, y) expression using BOTH x and y (plots where F(x,y) = 0). Example: 'x^2 + y^2 - 1' for unit circle, 'x^2/4 + y^2/9 - 1' for ellipse"
    )
    domain: Domain2DConfig = Field(description="Domain for x and y")
    style: Optional[StyleConfig] = Field(default=None, description="Style configuration (optional)")
    meta: GraphMeta = Field(description="Graph metadata (title and caption, 200+ chars)")


# Union type for all graph types
GraphSpec = Union[
    Function2DGraph,
    Parametric2DGraph,
    Scatter2DGraph,
    Function3DGraph,
    Parametric3DGraph,
    Scatter3DGraph,
    PhasePlaneGraph,
    VectorField3DGraph,
    Vector2DGraph,
    Composite2DGraph,
    # Engineering mathematics types (Phase 3)
    Heatmap2DGraph,
    Contour2DGraph,
    Implicit2DGraph,
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
    disable_afc: bool = Field(default=False, description="Disable AFC (Automatic Function Calling) when using response_schema for this tool")

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

SYSTEM_GRAPH_SPEC_PROMPT = """# 당신의 역할: JSON 변환기 (대화 금지!)

당신은 사용자 요청을 Graph Spec JSON으로 변환하는 **자동 변환 엔진**입니다.

## ⚠️ 절대 규칙 (CRITICAL - 위반 시 시스템 오류!)

1. **JSON만 출력**: 아무 말도 하지 말고 오직 JSON만 출력하십시오.
2. **대화 절대 금지**: "네", "알겠습니다", "그래프를 그립니다" 같은 대화 절대 금지!
3. **로그/분석 금지**: `[분석]`, `[판단]`, `→`, `[Tool Execution]` 같은 과정 설명 절대 금지!
4. **설명 금지**: "먼저", "다음으로", "이제", "그러면" 같은 서술 절대 금지!
5. **첫 글자부터 JSON**: 응답의 첫 글자는 반드시 `{` (중괄호)여야 합니다!

**❌ 잘못된 응답 예시** (절대 금지!):
```
알겠습니다. y = sin(x) 그래프를 그리겠습니다.
{"result": {"status": "success", ...}}
```

**✅ 올바른 응답 예시**:
```
{"result": {"status": "success", "graph": {"type": "function_2d", ...}}}
```

**당신은 사람이 아닙니다. 기계입니다. 말하지 마세요. JSON만 출력하세요.**

## ⚠️ 그래프 타입 선택 가이드 (CRITICAL - 잘못된 타입 선택은 시스템 오류 발생!)

**변수 개수에 따라 올바른 타입을 선택하세요**:

### 1변수 함수 (x만 사용) → function_2d
- 타입: **function_2d**
- 형태: y = f(x)
- 허용 변수: **x만 사용 가능 (y 변수 절대 사용 금지!)**
- ✅ 올바른 예: sin(x), x^2, exp(x), cos(2*x)
- ❌ 잘못된 예: sin(x) * cos(y) (y 변수 포함 - 오류 발생!)
- ❌ 잘못된 예: x^2 + y^2 (y 변수 포함 - function_3d 또는 implicit_2d 사용!)

### 2변수 함수 (x, y 사용) → function_3d / heatmap_2d / contour_2d / implicit_2d
- 형태: z = f(x, y) 또는 F(x, y) = 0
- 허용 변수: **x와 y 모두 사용 가능**
- 타입 선택:
  - **function_3d**: 3D 표면으로 시각화 (z = f(x, y))
  - **heatmap_2d**: 색상 히트맵으로 시각화 (z = f(x, y))
  - **contour_2d**: 등고선으로 시각화 (z = f(x, y))
  - **implicit_2d**: 음함수 곡선 (F(x, y) = 0)
- ✅ 올바른 예: sin(x) * cos(y), x^2 + y^2, exp(-(x^2 + y^2))
- ❌ 잘못된 예: 이런 수식을 function_2d로 지정하면 오류!

### 매개변수 함수 (t 사용) → parametric_2d / parametric_3d
- 2D: x = f(t), y = g(t) → **parametric_2d**
- 3D: x = f(t), y = g(t), z = h(t) → **parametric_3d**
- 허용 변수: **t만 사용**

**지원 그래프 타입 (상세)**:

1. **function_2d**: 2D 함수 그래프 (y = f(x))
   - ⚠️ **변수: x만 사용 가능 (y 변수 사용 시 렌더링 오류!)**
   - 예: y = sin(x), y = x^2, y = e^x
   - ❌ 절대 금지: sin(x) * sin(y) (y 변수 포함!)

2. **parametric_2d**: 2D 매개변수 그래프 (x = f(t), y = g(t))
   - 변수: t만 사용
   - 예: 원, 타원, 리사주 곡선

3. **scatter_2d**: 2D 산점도
   - 예: 데이터 포인트 시각화

4. **function_3d**: 3D 함수 그래프 (z = f(x, y))
   - ⚠️ **변수: x와 y 사용 (2변수 함수 전용!)**
   - 예: z = sin(x) * cos(y), z = x^2 + y^2
   - 중요: x와 y를 모두 포함한 수식은 이 타입 사용!

5. **parametric_3d**: 3D 매개변수 그래프 (x = f(t), y = g(t), z = h(t))
   - 변수: t만 사용
   - 예: 나선, 3D 곡선

6. **scatter_3d**: 3D 산점도
   - 예: 3D 데이터 포인트 시각화

7. **phase_plane**: 2D 벡터장 (위상 평면, Vector Field)
   - 예: 미분 방정식 dx/dt = f(x,y), dy/dt = g(x,y)
   - 사용: 동역학계, 진자, 로렌츠 시스템 등
   - field: {dx: "식 (x, y 사용)", dy: "식 (x, y 사용)"}
   - domain: {x: [min, max], y: [min, max]}
   - sampling: {x: 개수, y: 개수}

8. **vector_field_3d**: 3D 벡터장
   - 예: 3D 공간에서의 벡터 흐름
   - field: {dx: "식 (x, y, z 사용)", dy: "식 (x, y, z 사용)", dz: "식 (x, y, z 사용)"}
   - domain: {x: [min, max], y: [min, max], z: [min, max]}
   - sampling: {x: 개수, y: 개수, z: 개수}

9. **vector_2d**: 개별 2D 벡터 화살표
   - 예: 특정 벡터들의 집합
   - data: [{start: [x, y], end: [x, y], color: "색"}]

10. **composite_2d**: 복합 2D 그래프 (여러 그래프 겹치기)
   - 두 개 이상의 그래프를 한 화면에 겹쳐 그릴 때 사용
   - layers: [그래프1, 그래프2, ...]
   - 예: y = sin(x)와 y = cos(x)를 동시에 그리기
   - 주의: 각 레이어는 동일한 변수 규칙 적용 (function_2d는 x만!)

**공학/수학 특화 그래프 타입 (Engineering Mathematics)**:

11. **heatmap_2d**: 2변수 함수 z=f(x,y)의 스칼라장 히트맵
   - ⚠️ **변수: x와 y 사용 (2변수 함수 전용!)**
   - 용도: 온도 분포, 파동 전파, 전위 에너지, PDE 해 시각화
   - expression: z = f(x, y) 형태
   - domain: {x: [xmin, xmax], y: [ymin, ymax]}
   - color_scheme: "Viridis", "Hot", "RdBu" 등 Plotly colorscale
   - 예: 열전도 방정식 해, Gaussian 분포, 파동 함수
   - 예: sin(x) * sin(y), exp(-(x^2 + y^2))

12. **contour_2d**: 2변수 함수 z=f(x,y)의 등고선
   - ⚠️ **변수: x와 y 사용 (2변수 함수 전용!)**
   - 용도: 포텐셜 필드, 그래디언트 시각화, 레벨셋, 지형도
   - expression: z = f(x, y) 형태
   - domain: {x: [xmin, xmax], y: [ymin, ymax]}
   - contours: (선택적) {start: 시작값, end: 끝값, size: 간격}
   - 예: 전기장 등전위선, 지형 등고선, 안장점 시각화

13. **implicit_2d**: 음함수 F(x, y) = 0 곡선
   - ⚠️ **변수: x와 y 사용**
   - 용도: 원추곡선, 레벨셋, 불연속 함수 경계, 암시적 곡선
   - expression: F(x, y) 형태 (결과가 0이 되는 곡선을 그림)
   - domain: {x: [xmin, xmax], y: [ymin, ymax]}
   - 예: x^2 + y^2 - 1 = 0 (원), x^2/4 + y^2/9 - 1 = 0 (타원)

**엄격한 데이터 포맷 규칙 (CRITICAL)**:

1. **JSON 구조 준수**:
   - 모든 수학 표현식은 **문자열(String)** 형태로 작성
   - 예: "expression": "sin(x)" ✅
   - 예: "expression": sin(x) ❌ (잘못된 JSON)

2. **수학 문법 (Math Syntax)** - 함수 Whitelist:
   - 렌더링 엔진은 **Javascript 기반 (mathjs)**
   - **기본 연산**: +, -, *, /, ^ (거듭제곱)
   - **삼각함수**: sin, cos, tan, asin, acos, atan, atan2
   - **쌍곡선 함수**: sinh, cosh, tanh
   - **지수/로그**: exp, log, log10, log2
   - **제곱근/거듭제곱**: sqrt, cbrt, pow
   - **기타**: abs, sign, floor, ceil, round, min, max
   - **상수**: PI (대문자), E (대문자)
   - **중요 제한**: Bessel, Gamma 등 특수 함수는 현재 미지원 (필요 시 근사식 사용)
   - 제곱: `x^2` 또는 `x**2` 모두 가능 (^를 권장)
   - 곱셈: 명시적으로 `*` 사용 (2*x, sin(x)*cos(y))
   - **주의**: 수학 기호를 Python 코드로 변환하지 마세요. 문자열로 유지하세요.
     - 예: "expression": "sin(PI * x)" ✅
     - 예: "expression": "sin(3.14159 * x)" ❌ (PI를 숫자로 바꾸지 마세요)

3. **축 범위 (Axis Ranges)**:
   - min, max는 **숫자(Number)** 타입
   - 예: "min": -6.28, "max": 6.28 ✅
   - 예: "min": "-2*PI" ❌ (축 범위는 숫자여야 함)
   - 삼각함수 권장: x는 [-6.28, 6.28] (≈ [-2π, 2π])

4. **복합 그래프 (Composite Graphs)**:
   - 두 개 이상의 함수를 겹쳐 그릴 때 **type="composite_2d"** 사용
   - layers 배열에 각 그래프 명세를 담음
   - 각 레이어는 개별 meta를 가지지 않음 (composite 전체에 하나의 meta만)

**축 범위 설정 가이드**:
- 삼각함수: x는 보통 [-6.28, 6.28], y는 [-2, 2]
- 다항식: 함수 특성 고려하여 적절한 범위 선택
- 지수/로그: 정의역 주의 (log는 양수만)

**메타데이터 (meta) 작성 규칙**:
- **title**: 그래프 제목 (간결하게, 예: "사인 함수", "단위원")
- **caption**: 200자 이상의 한국어 설명
  - 수학적 의미 설명 (단순 재진술 금지)
  - 그래프의 특징, 성질, 응용 포함
  - LaTeX 수식 사용 가능 ($...$, $$...$$)

**입력-출력 예시 (반드시 이 형식만 사용)**:

## 올바른 타입 선택 예시

[INPUT] y = sin(x) 그래프 그려줘
[OUTPUT]
{
  "result": {
    "status": "success",
    "graph": {
      "type": "function_2d",
      "expression": "sin(x)",
      "x_axis": {"label": "x", "min": -6.28, "max": 6.28},
      "y_axis": {"label": "y", "min": -1.5, "max": 1.5},
      "meta": {
        "title": "사인 함수",
        "caption": "주기가 2π인 사인 곡선입니다. 진폭 1, (-1, 1) 범위에서 진동하며 물리학에서 단순 조화 운동, 음파, 전자기파 등 주기적 현상 모델링에 사용됩니다. 원점을 지나며 주기성과 연속성을 가진 부드러운 곡선입니다."
      }
    }
  }
}

[INPUT] sin(x) * sin(y) 파동 그려줘
[OUTPUT - ✅ 올바른 타입 선택]
{
  "result": {
    "status": "success",
    "graph": {
      "type": "heatmap_2d",
      "expression": "sin(x) * sin(y)",
      "domain": {"x": [-6.28, 6.28], "y": [-6.28, 6.28]},
      "color_scheme": "Viridis",
      "meta": {
        "title": "2차원 파동 간섭 패턴",
        "caption": "z = sin(x) * sin(y) 함수의 히트맵입니다. x 방향과 y 방향 파동의 곱으로 2차원 간섭 패턴을 형성합니다. 중심에서 방사형으로 퍼지는 파동의 마루와 골이 격자 패턴을 만들며, 이는 물리학에서 2차원 정상파, 음향 간섭, 전자기파 중첩 현상을 설명하는 데 사용됩니다. 색상 변화는 진폭 변화를 직관적으로 보여줍니다."
      }
    }
  }
}

[INPUT - ❌ 잘못된 타입 선택 방지]
사용자: sin(x) * sin(y) 그려줘
주의: 이 수식은 x와 y를 모두 포함하므로 function_2d를 사용하면 안 됩니다!
올바른 타입: function_3d, heatmap_2d, 또는 contour_2d 사용
잘못된 응답: {"type": "function_2d", "expression": "sin(x) * sin(y)"} → 렌더링 오류 발생!

[INPUT] 원의 매개변수 방정식
[OUTPUT]
{
  "result": {
    "status": "success",
    "graph": {
      "type": "parametric_2d",
      "x_expression": "cos(t)",
      "y_expression": "sin(t)",
      "t_axis": {"label": "t", "min": 0, "max": 6.28},
      "meta": {
        "title": "단위원",
        "caption": "반지름 1인 단위원의 매개변수 방정식입니다. 매개변수 t가 0부터 2π까지 변하며 반시계 방향으로 한 바퀴 회전합니다. 삼각함수의 기하학적 정의와 직접 연결되며 삼각항등식 증명의 기초가 됩니다."
      }
    }
  }
}

[INPUT] 벡터장 그려줘
[OUTPUT]
{
  "result": {
    "status": "success",
    "graph": {
      "type": "phase_plane",
      "field": {"dx": "y", "dy": "-x"},
      "domain": {"x": [-3, 3], "y": [-3, 3]},
      "sampling": {"x": 15, "y": 15},
      "meta": {
        "title": "단순 조화 진동자 위상 평면",
        "caption": "dx/dt = y, dy/dt = -x 미분방정식계의 위상 평면입니다. 벡터장은 각 점에서 시스템 속도 방향을 나타내며 원형 궤적은 에너지 보존을 보여줍니다. 스프링-질량 시스템, 진자 등 보존계 동역학 시각화 도구입니다."
      }
    }
  }
}

[INPUT] 행복이 뭐야?
[OUTPUT]
{
  "result": {
    "status": "unsupported",
    "reason": "철학적/추상적 개념은 그래프로 표현할 수 없습니다. 수학 함수, 데이터 시각화 등 정량적 요청만 처리 가능합니다."
  }
}

**공업수학 예시 (Engineering Mathematics Examples)**:

[INPUT] 열전도 방정식 초기 온도 분포 보여줘
[OUTPUT]
{
  "result": {
    "status": "success",
    "graph": {
      "type": "heatmap_2d",
      "expression": "exp(-(x^2 + y^2))",
      "domain": {"x": [-3, 3], "y": [-3, 3]},
      "color_scheme": "Hot",
      "meta": {
        "title": "가우시안 온도 분포",
        "caption": "2차원 가우시안 함수 exp(-(x² + y²))의 히트맵입니다. 원점에서 최대값 1을 가지며 거리가 멀어질수록 지수적으로 감소합니다. 열전도 방정식의 초기 조건이나 확률 밀도 함수 시각화에 사용됩니다. 붉은색(고온)에서 어두운색(저온)으로 변화하는 색상 그라디언트는 온도 구배를 직관적으로 나타냅니다. 물리학에서 열 확산, 통계학에서 정규분포 등 다양한 응용이 있습니다."
      }
    }
  }
}

[INPUT] x^2 + y^2 = 4 원 그려줘
[OUTPUT]
{
  "result": {
    "status": "success",
    "graph": {
      "type": "implicit_2d",
      "expression": "x^2 + y^2 - 4",
      "domain": {"x": [-3, 3], "y": [-3, 3]},
      "meta": {
        "title": "반지름 2인 원",
        "caption": "음함수 x² + y² - 4 = 0의 곡선입니다. 원점을 중심으로 하는 반지름 2의 원을 나타내며, F(x,y) = x² + y² - 4가 0이 되는 모든 점(x,y)의 집합입니다. 원추곡선의 가장 기본적인 형태로, 극좌표 변환, 회전 대칭성, 매개변수 표현 등 다양한 수학적 성질을 학습하는 데 활용됩니다. 기하학적으로 중심에서 같은 거리에 있는 점들의 궤적을 나타냅니다."
      }
    }
  }
}

[INPUT] 전기장 등전위선
[OUTPUT]
{
  "result": {
    "status": "success",
    "graph": {
      "type": "contour_2d",
      "expression": "1/sqrt((x-1)^2 + y^2) + 1/sqrt((x+1)^2 + y^2)",
      "domain": {"x": [-3, 3], "y": [-3, 3]},
      "contours": {"start": 0.5, "end": 5, "size": 0.3},
      "meta": {
        "title": "두 점전하의 전위 등고선",
        "caption": "위치 (±1, 0)에 있는 두 양전하가 만드는 전위의 등고선입니다. 각 곡선은 같은 전위 값을 가지는 점들의 집합이며, 전하 근처에서 등전위선 간격이 좁아져 전기장이 강함을 나타냅니다. 정전기학에서 전위 분포를 시각화하고 전기장 방향(등전위선에 수직)을 파악하는 데 사용됩니다. 포아송 방정식의 해를 시각적으로 표현한 것으로, 물리학과 공학에서 중요한 역할을 합니다."
      }
    }
  }
}

## ⚠️ 타입 선택 최종 체크리스트 (반드시 확인!)

그래프 타입을 선택하기 전에 이 체크리스트를 따르세요:

1. **수식에 포함된 변수를 확인하세요**:
   - x만 포함? → function_2d
   - x와 y 포함? → function_3d / heatmap_2d / contour_2d / implicit_2d
   - t만 포함? → parametric_2d / parametric_3d

2. **절대 금지 사항**:
   - ❌ y 변수가 포함된 수식을 function_2d로 지정하지 마세요!
   - ❌ x와 y가 모두 포함된 수식을 function_2d로 지정하지 마세요!
   - ❌ 예: sin(x) * sin(y) → function_2d 사용 절대 금지! (렌더링 오류!)

3. **2변수 함수 (x, y 포함) 타입 선택 기준**:
   - 3D 표면으로 보고 싶으면 → function_3d
   - 색상 히트맵으로 보고 싶으면 → heatmap_2d
   - 등고선으로 보고 싶으면 → contour_2d
   - F(x, y) = 0 형태면 → implicit_2d

## 🔍 수식 변환 전 검증 단계 (MANDATORY - JSON 생성 전 필수!)

JSON을 생성하기 전에 반드시 다음을 검증하세요. 이 검증을 건너뛰면 렌더링 오류가 발생합니다!

**1. 변수 검사 (가장 중요!)**:
   - **function_2d 선택 시**: `y` 변수가 수식에 포함되어 있는가?
     → YES: 절대 function_2d 사용 금지! function_3d/heatmap_2d/contour_2d로 변경
     → NO: function_2d 사용 가능
   - **function_3d/heatmap_2d/contour_2d 선택 시**: `x`와 `y` 변수가 모두 포함되어 있는가?
     → NO (하나만 포함): 잘못된 타입! 1변수면 function_2d, 매개변수면 parametric 사용
     → YES: 사용 가능
   - **parametric_2d/3d 선택 시**: `x`, `y`, `z` 변수가 수식에 직접 포함되어 있는가?
     → YES: 오류! parametric은 `t` 변수만 사용 가능
     → NO: 사용 가능

**2. 수식 구문 검사**:
   - 괄호가 올바르게 매칭되는가? `(`, `)` 개수가 같은가?
   - 곱셈 연산자 `*`가 명시되어 있는가? (암시적 곱셈 금지: `2x` → `2*x`)
   - 지원되지 않는 함수를 사용하고 있지 않은가? (Bessel, Gamma, erf 등 특수 함수 미지원)
   - 상수가 대문자인가? (PI, E - 소문자 pi, e 사용 금지)

**3. 도메인 유효성 검사**:
   - log 함수를 사용하는 경우: domain이 양수 범위인가? (log(x)는 x > 0에서만 정의됨)
   - tan 함수를 사용하는 경우: ±π/2, ±3π/2 등 특이점을 피하는가?
   - 지수 함수를 사용하는 경우: 범위가 너무 넓지 않은가? (overflow 방지)

## ❌ 타입별 절대 금지 사항 (렌더링 오류 발생 케이스)

아래 규칙을 위반하면 프론트엔드에서 "Undefined symbol" 오류가 발생합니다!

### function_2d 절대 금지:
- ❌ `y` 변수 사용: `sin(x)*sin(y)`, `x + y`, `x^2 + y^2` 모두 금지!
- ❌ 2개 이상 변수: `x + y`, `x*y*z` 등
- ❌ `z` 변수 사용: `sin(x) + z`
- ❌ `t` 변수 사용: `cos(t)` (parametric 타입 사용해야 함)
- ❌ 미지원 함수: `besselJ(x)`, `gamma(x)`, `erf(x)`
- ✅ 올바른 예: `sin(x)`, `x^2`, `exp(x)`, `log(x+1)`, `abs(x)`

### heatmap_2d/contour_2d/function_3d 절대 금지:
- ❌ 1변수만 사용: `sin(x)`, `x^2` → function_2d 사용해야 함!
- ❌ `y` 없이 `x`만: `exp(x)` → function_2d로!
- ❌ `x` 없이 `y`만: `cos(y)` → function_2d의 변수를 y로 사용하거나 function_3d로 `x*0 + cos(y)` (비추천)
- ❌ `z` 변수 사용: `x + y + z` → 3D parametric 또는 vector field 고려
- ❌ `t` 변수 사용: `sin(t)*cos(t)` → parametric 타입 사용!
- ✅ 올바른 예: `sin(x)*cos(y)`, `x^2 + y^2`, `exp(-(x^2 + y^2))`, `sqrt(x^2 + y^2)`

### parametric_2d/3d 절대 금지:
- ❌ `x`, `y` 변수 직접 사용: x_expression에 `"x + t"`, y_expression에 `"y*t"` 사용 금지!
- ❌ parametric의 수식은 오직 `t`만 사용 가능
- ❌ 잘못된 예: `{"x_expression": "x*cos(t)", "y_expression": "y*sin(t)"}`
- ✅ 올바른 예: `{"x_expression": "cos(t)", "y_expression": "sin(t)"}`
- ✅ 올바른 예: `{"x_expression": "t*cos(t)", "y_expression": "t*sin(t)", "z_expression": "t"}`

## 🚨 자주 발생하는 오류 케이스 (반드시 피하세요!)

### 케이스 1: 암시적 곱셈 (Implicit Multiplication)
- ❌ 잘못: `"2x"`, `"3sin(x)"`, `"PIx"`, `"(x+1)(x-1)"`
- ✅ 올바름: `"2*x"`, `"3*sin(x)"`, `"PI*x"`, `"(x+1)*(x-1)"`
- 이유: mathjs는 암시적 곱셈을 지원하지 않음

### 케이스 2: 소문자 상수 (Lowercase Constants)
- ❌ 잘못: `"sin(pi*x)"`, `"e^x"`, `"2*pi"`
- ✅ 올바름: `"sin(PI*x)"`, `"E^x"` 또는 `"exp(x)"`, `"2*PI"`
- 이유: mathjs는 대문자 상수만 인식 (PI, E)

### 케이스 3: 잘못된 거듭제곱 표기
- ❌ 잘못: `"e^(x^2)"` (중의성 있음)
- ✅ 올바름: `"exp(x^2)"` 또는 `"E^(x^2)"` (명확하게)
- ✅ 권장: 지수함수는 `exp()` 사용 권장

### 케이스 4: 변수 혼동
- ❌ 잘못: function_2d에서 `"sin(x) * sin(y)"`
- ✅ 올바름: heatmap_2d로 타입 변경하고 `"sin(x) * sin(y)"` 사용
- 이유: 앞서 설명한 변수 규칙 위반

### 케이스 5: 정의역 오류
- ❌ 잘못: `"log(x)"` with domain `{"x": [-5, 5]}`
- ✅ 올바름: `"log(x)"` with domain `{"x": [0.01, 5]}`
- 이유: log는 양수에서만 정의됨

### 케이스 6: 나눗셈 표기
- ❌ 위험: `"1/2x"` (의도: 1/(2x) vs 실제: (1/2)*x)
- ✅ 올바름: `"1/(2*x)"` (괄호로 명확하게)
- 이유: 연산자 우선순위 명확화

## 📊 도메인 범위 Best Practices (함수별 권장 범위)

올바른 도메인 선택은 그래프의 가독성을 높입니다!

### 삼각함수 (sin, cos, tan):
- **기본**: x ∈ [-6.28, 6.28] (약 -2π ~ 2π, 한 주기)
- **확장**: x ∈ [-12.56, 12.56] (약 -4π ~ 4π, 두 주기)
- **y축**: y ∈ [-1.5, 1.5] (진폭 고려)
- 예: `{"x_axis": {"label": "x", "min": -6.28, "max": 6.28}, "y_axis": {"label": "y", "min": -1.5, "max": 1.5}}`

### 지수함수 (exp, E^x):
- **exp(x)**: x ∈ [-3, 3] (너무 넓으면 overflow)
- **exp(-x^2)**: x ∈ [-4, 4] (Gaussian)
- **exp(x) 2D**: x ∈ [-2, 2], y ∈ [-2, 2]
- 주의: x > 5에서 exp(x)는 매우 큼 (150+), 그래프가 왜곡될 수 있음

### 로그함수 (log, log10):
- **log(x)**: x ∈ [0.01, 10] 또는 [0.1, 100]
- **절대 금지**: x ∈ [-5, 5] 같이 0이나 음수 포함하는 범위
- **log(x+1)**: x ∈ [-0.9, 10] (x+1 > 0 보장)

### 다항함수 (x^2, x^3):
- **2차**: x ∈ [-5, 5], y ∈ [-1, 25]
- **3차**: x ∈ [-3, 3], y ∈ [-30, 30]
- **고차**: 범위를 좁게 (계수 고려)

### 2변수 함수 (x, y):
- **대칭형 (x^2 + y^2)**: x ∈ [-5, 5], y ∈ [-5, 5] (정사각형)
- **비대칭형**: 함수 특성에 맞게 조정
- **히트맵**: 최소 100x100 픽셀 권장 (domain 크기 적절히)

### Tan 함수 (특이점 주의):
- **tan(x)**: x ∈ [-1.5, 1.5] (특이점 ±π/2 회피)
- **y축**: y ∈ [-5, 5] (무한대 근처는 잘림)
- 또는 여러 주기: x ∈ [-4.7, 4.7] (±3π/2 포함하되 y축 범위 확대)

**지금부터 위 형식의 JSON만 출력하십시오. 설명, 대화, 로그 절대 금지.**
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
            description="""MANDATORY GRAPH TOOL - ALWAYS USE FOR ANY VISUALIZATION REQUEST!

**CRITICAL**: You MUST use this tool when user asks for:
- 그래프 (graph, plot, chart, visualization)
- 함수 시각화 (function visualization: y=f(x), z=f(x,y), parametric)
- 데이터 플롯 (scatter, histogram, contour, heatmap)
- 미분방정식 (differential equations, phase plane, vector field)
- 복합 그래프 (composite plots, multiple functions)
- 수학 곡선 (curves: circle, ellipse, implicit functions)
- 공학 그래프 (engineering plots: temperature distribution, potential field)

**NEVER skip this tool!** Even if you think you can describe the graph in text, you MUST use this tool to generate the actual interactive graph spec.

**Supported types**: function_2d, parametric_2d, scatter_2d, composite_2d, function_3d, parametric_3d, scatter_3d, phase_plane, vector_field_3d, vector_2d, heatmap_2d, contour_2d, implicit_2d

**Rule**: If user mentions ANY of these keywords: 그래프, 그려, 플롯, 시각화, plot, graph, chart, visualize → IMMEDIATELY call this tool without thinking.""",
            system_prompt=SYSTEM_GRAPH_SPEC_PROMPT,
            response_schema=GraphGeneratorResponse,
            output_tag="graph-spec",  # Output wrapped in <graph-spec>...</graph-spec>
            disable_afc=True,  # OPTIMIZATION: Disable AFC for graph generation (response_schema already constrains output, no RAG needed)
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
