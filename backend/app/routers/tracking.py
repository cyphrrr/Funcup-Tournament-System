import hashlib
from datetime import datetime, date, timedelta

from fastapi import APIRouter, Depends, Request, Response, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, and_

from .. import models
from ..db import get_db
from ..auth import get_current_user

router = APIRouter()

BOT_MARKERS = [
    "bot", "crawl", "spider", "slurp", "mediapartners",
    "feedfetcher", "lighthouse", "pagespeed", "headless",
]


@router.post("/track", status_code=204)
async def track_pageview(request: Request, db: Session = Depends(get_db)):
    """Trackt einen Seitenaufruf (DSGVO-konform: anonymer Hash, keine IP gespeichert)."""
    ua = request.headers.get("user-agent", "")
    ua_lower = ua.lower()
    if any(marker in ua_lower for marker in BOT_MARKERS):
        return Response(status_code=204)

    body = await request.json()
    path = body.get("path", "/")

    client_ip = request.client.host if request.client else "unknown"
    today_str = date.today().isoformat()
    raw = f"{client_ip}:{ua}:{today_str}"
    visitor_id = hashlib.sha256(raw.encode()).hexdigest()[:16]

    referrer = request.headers.get("referer")

    pv = models.PageView(
        path=path,
        visitor_id=visitor_id,
        referrer=referrer,
    )
    db.add(pv)
    db.commit()
    return Response(status_code=204)


@router.get("/admin/stats")
async def get_admin_stats(
    days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    """Gibt Besucherstatistiken zurück."""
    today = date.today()
    yesterday = today - timedelta(days=1)

    def counts_for_range(start_date, end_date):
        """Visitors + Views für einen Zeitraum."""
        q = db.query(
            func.count(distinct(models.PageView.visitor_id)),
            func.count(models.PageView.id),
        ).filter(
            func.date(models.PageView.timestamp) >= start_date,
            func.date(models.PageView.timestamp) <= end_date,
        ).one()
        return {"visitors": q[0], "views": q[1]}

    # Daily breakdown
    start = today - timedelta(days=days - 1)
    daily_rows = (
        db.query(
            func.date(models.PageView.timestamp).label("day"),
            func.count(distinct(models.PageView.visitor_id)).label("visitors"),
            func.count(models.PageView.id).label("views"),
        )
        .filter(func.date(models.PageView.timestamp) >= start)
        .group_by(func.date(models.PageView.timestamp))
        .all()
    )
    daily_map = {str(r.day): {"visitors": r.visitors, "views": r.views} for r in daily_rows}
    daily = []
    for i in range(days):
        d = start + timedelta(days=i)
        ds = d.isoformat()
        daily.append({"date": ds, **daily_map.get(ds, {"visitors": 0, "views": 0})})

    # Summary
    total = db.query(
        func.count(distinct(models.PageView.visitor_id)),
        func.count(models.PageView.id),
    ).one()

    summary = {
        "today": counts_for_range(today, today),
        "yesterday": counts_for_range(yesterday, yesterday),
        "last_7_days": counts_for_range(today - timedelta(days=6), today),
        "last_30_days": counts_for_range(today - timedelta(days=29), today),
        "total": {"visitors": total[0], "views": total[1]},
    }

    return {
        "period": f"{days}d",
        "daily": daily,
        "summary": summary,
    }
