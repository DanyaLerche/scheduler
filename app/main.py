from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.models import ScheduleRequest, ScheduleResponse
from app.sample_data import sample_dataset
from app.scheduler import compare_algorithms, generate_schedule


app = FastAPI(
    title="Составитель расписаний",
    description="Генератор учебного расписания с жадным алгоритмом и проверкой конфликтов.",
    version="1.0.0",
)

templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/sample")
def get_sample() -> dict:
    return sample_dataset().model_dump(mode="json")


@app.post("/api/schedule", response_model=ScheduleResponse)
def create_schedule(payload: ScheduleRequest) -> ScheduleResponse:
    if payload.options.include_comparison:
        results = compare_algorithms(payload.dataset, seed=payload.options.seed)
        return ScheduleResponse(
            greedy=results[0],
            comparisons=[result.stats for result in results],
        )

    greedy = generate_schedule(payload.dataset, "greedy", seed=payload.options.seed)
    return ScheduleResponse(greedy=greedy, comparisons=[greedy.stats])
