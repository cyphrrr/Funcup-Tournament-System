from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..db import get_db
from ..auth import get_current_user

router = APIRouter()


@router.post("/news", response_model=schemas.NewsRead)
def create_news(news: schemas.NewsCreate, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    """Neuen News-Artikel erstellen."""
    obj = models.News(
        title=news.title,
        content=news.content,
        author=news.author or "Admin",
        published=news.published if news.published is not None else 1,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/news", response_model=list[schemas.NewsRead])
def list_news(published_only: bool = True, db: Session = Depends(get_db)):
    """Alle News-Artikel abrufen. Default: nur veröffentlichte."""
    query = db.query(models.News)
    if published_only:
        query = query.filter(models.News.published == 1)
    return query.order_by(models.News.created_at.desc()).all()


@router.get("/news/{news_id}", response_model=schemas.NewsRead)
def get_news(news_id: int, db: Session = Depends(get_db)):
    """Einzelnen News-Artikel abrufen."""
    news = db.get(models.News, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="News not found")
    return news


@router.patch("/news/{news_id}", response_model=schemas.NewsRead)
def update_news(news_id: int, update: schemas.NewsUpdate, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    """News-Artikel aktualisieren."""
    news = db.get(models.News, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="News not found")

    if update.title is not None:
        news.title = update.title
    if update.content is not None:
        news.content = update.content
    if update.author is not None:
        news.author = update.author
    if update.published is not None:
        news.published = update.published

    db.commit()
    db.refresh(news)
    return news


@router.delete("/news/{news_id}")
def delete_news(news_id: int, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    """News-Artikel löschen."""
    news = db.get(models.News, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="News not found")

    db.delete(news)
    db.commit()
    return {"deleted": True, "id": news_id}
