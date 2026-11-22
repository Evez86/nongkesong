from pathlib import Path
from typing import Literal

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, constr

from backend.api.app_fastapi import api_error_handler, app as team_api, handlers


DIST = Path(__file__).resolve().with_name('dist')
app = FastAPI(title='松果来信竞赛演示', docs_url=None, redoc_url=None, openapi_url=None)
app.add_exception_handler(handlers.ApiError, api_error_handler)

# Keep public read endpoints, with the same handlers as the team service.
PUBLIC_API_PATHS = {
    '/healthz',
    '/api/v1/opportunities',
    '/api/v1/opportunities/{oid}',
    '/api/v1/resources',
    '/api/v1/resources/{rid}',
}
app.router.routes.extend(route for route in team_api.routes if route.path in PUBLIC_API_PATHS)


class GuestPlanInput(BaseModel):
    mode: Literal['demo'] = 'demo'
    plan_id: None = None
    interests: list[constr(strip_whitespace=True, min_length=1, max_length=20)] = Field(
        default_factory=list, max_length=3,
    )


@app.post('/api/v1/growth-plans')
def create_guest_growth_plan(payload: GuestPlanInput):
    return handlers.create_growth_plan(None, payload.interests, payload.mode)[1]


app.mount('/', StaticFiles(directory=DIST, html=True), name='frontend')
