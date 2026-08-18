from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .db import Store
from .integrations.cuntgoblin import opportunity_to_cuntgoblin, signal_to_market_observations
from .pipeline.scout import Scout
from .settings import AppSettings, SectorProfile


class SeedRequest(BaseModel):
    sector: str
    username: str


class ScanRequest(BaseModel):
    sector: str
    seeds: list[str] | None = None
    expand_per_seed: int = 2
    research: bool = True


def create_app(
    *,
    settings_path: str | None = None,
    db_path: str | None = None,
    config_root: str | Path = "configs",
) -> FastAPI:
    settings = AppSettings.load(settings_path)
    if db_path:
        settings.database_path = db_path
    store = Store(settings.database_path)
    config_root = Path(config_root)
    app = FastAPI(title="GitGoblin", version="0.1.0", description="Frontier technical-attention intelligence API")
    app.state.settings = settings
    app.state.store = store
    app.state.config_root = config_root

    def load_profile(sector: str) -> SectorProfile:
        path = config_root / "sectors" / f"{sector}.yaml"
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"Unknown sector profile: {sector}")
        return SectorProfile.load(path)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "version": "0.1.0", "database": str(store.path)}

    @app.post("/v1/seeds")
    def add_seed(req: SeedRequest) -> dict:
        load_profile(req.sector)
        store.add_seed(req.sector, req.username.lower())
        return {"sector": req.sector, "seeds": store.seeds(req.sector)}

    @app.get("/v1/seeds/{sector}")
    def get_seeds(sector: str) -> dict:
        profile = load_profile(sector)
        return {"sector": sector, "configured": profile.seed_builders, "persisted": store.seeds(sector)}

    @app.post("/v1/scans")
    def run_scan(req: ScanRequest) -> dict:
        profile = load_profile(req.sector)
        run = Scout(store, settings, profile).run(
            req.seeds,
            expand_per_seed=max(0, min(req.expand_per_seed, 10)),
            research=req.research,
        )
        return run.model_dump(mode="json")

    @app.get("/v1/signals")
    def signals(sector: str | None = None, limit: int = Query(default=100, ge=1, le=1000)) -> list[dict]:
        return [s.model_dump(mode="json") for s in store.signals(sector, limit)]

    @app.get("/v1/opportunities")
    def opportunities(sector: str | None = None, limit: int = Query(default=100, ge=1, le=1000)) -> list[dict]:
        return [o.model_dump(mode="json") for o in store.opportunities(sector, limit)]

    @app.get("/v1/entities/{entity_id:path}")
    def entity(entity_id: str) -> dict:
        item = store.get_entity(entity_id)
        if not item:
            raise HTTPException(status_code=404, detail="Entity not found")
        return item.model_dump(mode="json")

    @app.get("/v1/export/cuntgoblin")
    def export_cuntgoblin(sector: str | None = None) -> dict:
        signals_out = [obs for s in store.signals(sector, 1000) for obs in signal_to_market_observations(s)]
        opps_out = [opportunity_to_cuntgoblin(o) for o in store.opportunities(sector, 1000)]
        return {"market_observations": signals_out, "opportunities": opps_out}

    @app.get("/", response_class=HTMLResponse)
    def dashboard() -> str:
        page = Path(__file__).with_name("static") / "index.html"
        return page.read_text(encoding="utf-8")

    return app


app = create_app()
