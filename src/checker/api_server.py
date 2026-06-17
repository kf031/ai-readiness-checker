"""FastAPI server for AI Readiness Checker.

Start with: python -m checker serve --port 8000

Endpoints:
    GET  /health              — health check
    GET  /analyze?url=...     — analyze a URL, return JSON report
    POST /analyze             — analyze a URL (body: {"url": "..."})
    POST /fix                 — analyze + fix (body: {"url": "...", "backend": "ollama"})
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from src.checker.orchestrator import run_pipeline
from src.checker.contracts import CrawlError
from src.checker.agent import build_agent_report, run_llm_agent

app = FastAPI(
    title="AI Readiness Checker API",
    description="Analyze any website's AI search engine visibility",
    version="2.0.0",
)


class AnalyzeRequest(BaseModel):
    url: str
    timeout: float = 10.0


class AnalyzeResponse(BaseModel):
    url: str
    overall_score: float
    grade: str
    module_breakdown: dict
    recommendations: list[dict]
    errors: list[str]
    complete: bool
    stages_run: list[str]


class FixRequest(BaseModel):
    url: str
    timeout: float = 10.0
    backend: str | None = None  # "ollama", "openai", "anthropic"


class FixResponse(BaseModel):
    url: str
    skills_called: list[str]
    changes: list[str]
    explanation: str
    overall_score: float | None = None
    grade: str | None = None


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}


@app.get("/analyze")
async def analyze_get(url: str = Query(..., description="URL to analyze")):
    return _run_analysis(url)


@app.post("/analyze")
async def analyze_post(request: AnalyzeRequest):
    return _run_analysis(request.url, request.timeout)


@app.post("/fix")
async def fix_endpoint(request: FixRequest):
    """Analyze AND fix a URL — returns improvements from v2 agent."""
    pipeline_result = run_pipeline(request.url, timeout=request.timeout)

    fetch_result = pipeline_result.get("fetch_result")
    if fetch_result is None or isinstance(fetch_result, CrawlError):
        raise HTTPException(status_code=502, detail="Page fetch failed — cannot fix")

    html = getattr(fetch_result, "html", "")
    if not html:
        raise HTTPException(status_code=502, detail="No HTML content in fetch result")

    report = build_agent_report(pipeline_result)

    backend = None
    if request.backend:
        try:
            from src.checker.llm_backends import get_backend
            backend = get_backend(request.backend)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Backend unavailable: {e}")

    output = run_llm_agent(report, html, backend=backend)

    pipeline_report = pipeline_result.get("report")
    return {
        "url": request.url,
        "skills_called": output.skills_called,
        "changes": output.changes,
        "explanation": output.explanation,
        "overall_score": pipeline_report.overall_score if pipeline_report else None,
        "grade": pipeline_report.grade if pipeline_report else None,
    }


def _run_analysis(url: str, timeout: float = 10.0) -> dict:
    """Run the v1 pipeline and return a clean JSON response."""
    result = run_pipeline(url, timeout=timeout)
    report = result.get("report")
    if report is None:
        raise HTTPException(status_code=500, detail="Analysis failed")

    return {
        "url": getattr(report, "url", url),
        "overall_score": getattr(report, "overall_score", 0.0),
        "grade": getattr(report, "grade", "N/A"),
        "module_breakdown": _serialize(getattr(report, "module_breakdown", {})),
        "recommendations": _serialize_list(getattr(report, "recommendations", [])),
        "errors": result.get("errors", []),
        "complete": result.get("complete", False),
        "stages_run": result.get("stages_run", []),
    }


def _serialize(d) -> dict:
    """Recursively convert nested objects to plain dict."""
    if hasattr(d, "items") and callable(d.items):
        return {str(k): _serialize(v) for k, v in d.items()}
    if isinstance(d, list):
        return [_serialize(i) for i in d]
    return d


def _serialize_list(lst) -> list:
    return [_serialize(i) for i in (lst or [])]


def serve(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Start the uvicorn server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)
