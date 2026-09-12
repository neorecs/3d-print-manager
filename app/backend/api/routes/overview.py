from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from services.overview_service import catalog_overview, dashboard_overview, orders_overview, search_overview


router = APIRouter(tags=["overviews"])


@router.get("/dashboard/overview")
def dashboard(db: Session = Depends(get_db)):
    return dashboard_overview(db)


@router.get("/products/overview")
def products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    view: str = Query("actief", pattern="^(actief|archief|alle)$"),
    db: Session = Depends(get_db),
):
    return catalog_overview(db, page, page_size, view)


@router.get("/orders/overview")
def orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    status: str = Query("alle", max_length=40),
    db: Session = Depends(get_db),
):
    return orders_overview(db, page, page_size, status)


@router.get("/search")
def search(
    q: str = Query(..., min_length=2, max_length=120),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return search_overview(db, q, limit)
