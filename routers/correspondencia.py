import os
from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import date, datetime
from database import get_db
from templates_config import templates
import models, auth

router = APIRouter(prefix="/correspondencia")


@router.post("/sync")
async def sync_correspondencia(request: Request, db: Session = Depends(get_db)):
    """Endpoint llamado por el scraper local para sincronizar registros del Excel a la BD."""
    api_key = request.headers.get("X-Sync-Key", "")
    expected = os.getenv("SYNC_API_KEY", "")
    if not expected or api_key != expected:
        return JSONResponse({"error": "no autorizado"}, status_code=401)

    body = await request.json()
    registros = body.get("registros", [])

    nuevos = 0
    actualizados = 0
    for rec in registros:
        correlativo = (rec.get("Correlativo") or "").strip()
        if not correlativo:
            continue
        fecha_str = (rec.get("Fecha") or "").strip()
        try:
            fecha = datetime.strptime(fecha_str, "%d/%m/%Y").date() if fecha_str else None
        except ValueError:
            fecha = None

        existing = db.query(models.Correspondencia).filter_by(correlativo=correlativo).first()
        if existing:
            existing.fecha          = fecha
            existing.empresas       = rec.get("Empresa(s)", "") or ""
            existing.remitente      = rec.get("Remitente", "") or ""
            existing.destinatario   = rec.get("Destinatario", "") or ""
            existing.materia_macro  = rec.get("Materia Macro", "") or ""
            existing.materia_micro  = rec.get("Materia Micro", "") or ""
            existing.referencia     = rec.get("Referencia", "") or ""
            existing.respondida     = rec.get("Respondida", "") or ""
            existing.estado         = rec.get("Estado", "") or ""
            existing.updated_at     = datetime.utcnow()
            actualizados += 1
        else:
            db.add(models.Correspondencia(
                correlativo   = correlativo,
                fecha         = fecha,
                empresas      = rec.get("Empresa(s)", "") or "",
                remitente     = rec.get("Remitente", "") or "",
                destinatario  = rec.get("Destinatario", "") or "",
                materia_macro = rec.get("Materia Macro", "") or "",
                materia_micro = rec.get("Materia Micro", "") or "",
                referencia    = rec.get("Referencia", "") or "",
                respondida    = rec.get("Respondida", "") or "",
                estado        = rec.get("Estado", "") or "",
            ))
            nuevos += 1

    db.commit()
    return JSONResponse({"ok": True, "nuevos": nuevos, "actualizados": actualizados, "total": len(registros)})


@router.get("/api/count")
async def api_count(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "no autorizado"}, status_code=401)
    total = db.query(models.Correspondencia).count()
    ultimo = db.query(models.Correspondencia.id).order_by(models.Correspondencia.id.desc()).scalar()
    return JSONResponse({"total": total, "ultimo_id": ultimo or 0})


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
