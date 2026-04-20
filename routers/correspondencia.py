from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, extract
from datetime import date, datetime
from database import get_db
from templates_config import templates
import models, auth

router = APIRouter(prefix="/correspondencia")


@router.get("", response_class=HTMLResponse)
async def lista(
    request: Request,
    q: str = "",
    desde: str = "",
    hasta: str = "",
    empresa: str = "",
    materia_macro: str = "",
    estado: str = "",
    respondida: str = "",
    page: int = 1,
    db: Session = Depends(get_db)
):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)

    PAGE_SIZE = 50
    query = db.query(models.Correspondencia)

    # ── Filtros ───────────────────────────────────────────────────────────────
    if desde:
        try:
            query = query.filter(models.Correspondencia.fecha >= datetime.strptime(desde, "%Y-%m-%d").date())
        except ValueError:
            pass
    if hasta:
        try:
            query = query.filter(models.Correspondencia.fecha <= datetime.strptime(hasta, "%Y-%m-%d").date())
        except ValueError:
            pass
    if empresa:
        query = query.filter(models.Correspondencia.empresas.ilike(f"%{empresa}%"))
    if materia_macro:
        query = query.filter(models.Correspondencia.materia_macro == materia_macro)
    if estado:
        query = query.filter(models.Correspondencia.estado == estado)
    if respondida:
        query = query.filter(models.Correspondencia.respondida == respondida)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            models.Correspondencia.correlativo.ilike(like),
            models.Correspondencia.referencia.ilike(like),
            models.Correspondencia.empresas.ilike(like),
            models.Correspondencia.materia_micro.ilike(like),
            models.Correspondencia.remitente.ilike(like),
        ))

    total = query.count()
    registros = query.order_by(
        models.Correspondencia.fecha.desc(),
        models.Correspondencia.correlativo.desc()
    ).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE).all()

    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    # Listas para selectores de filtro (valores únicos)
    materias = [r[0] for r in db.query(models.Correspondencia.materia_macro).distinct().order_by(models.Correspondencia.materia_macro).all() if r[0]]
    estados_unicos = [r[0] for r in db.query(models.Correspondencia.estado).distinct().order_by(models.Correspondencia.estado).all() if r[0]]

    # Estadísticas rápidas (sin filtros)
    total_db = db.query(models.Correspondencia).count()
    con_pdf  = db.query(models.Correspondencia).filter(models.Correspondencia.pdf_url.isnot(None)).count()

    return templates.TemplateResponse(request, "correspondencia/lista.html", {
        "current_user": user,
        "registros": registros,
        "total": total,
        "total_pages": total_pages,
        "page": page,
        "q": q,
        "desde": desde,
        "hasta": hasta,
        "filtro_empresa": empresa,
        "filtro_materia": materia_macro,
        "filtro_estado": estado,
        "filtro_respondida": respondida,
        "materias": materias,
        "estados_unicos": estados_unicos,
        "total_db": total_db,
        "con_pdf": con_pdf,
        "flash": request.session.pop("flash", None),
    })
