from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from database import get_db
from templates_config import templates
import models, auth

router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)

    hoy = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    en_7_dias = hoy + timedelta(days=7)

    # Estadísticas generales
    total = db.query(models.Proyecto).count()
    activos = db.query(models.Proyecto).filter(models.Proyecto.estado == "Activo").count()
    completados = db.query(models.Proyecto).filter(models.Proyecto.estado == "Completado").count()
    en_espera = db.query(models.Proyecto).filter(models.Proyecto.estado == "En Espera").count()

    # Alarmas
    tareas_atrasadas = db.query(models.Actividad).join(models.Proyecto).filter(
        models.Actividad.fecha_limite < hoy,
        models.Actividad.estado.notin_(["Completado", "Cancelado"]),
        models.Proyecto.estado != "Cancelado"
    ).all()

    tareas_por_vencer = db.query(models.Actividad).join(models.Proyecto).filter(
        models.Actividad.fecha_limite >= hoy,
        models.Actividad.fecha_limite <= en_7_dias,
        models.Actividad.estado.notin_(["Completado", "Cancelado"]),
        models.Proyecto.estado != "Cancelado"
    ).all()

    pendientes_cliente = db.query(models.Actividad).join(models.Proyecto).filter(
        models.Actividad.responsable_tipo == "Cliente",
        models.Actividad.estado.notin_(["Completado", "Cancelado"]),
        models.Proyecto.estado == "Activo"
    ).all()

    quince_dias_atras = datetime.utcnow() - timedelta(days=15)
    proyectos_sin_movimiento = db.query(models.Proyecto).filter(
        models.Proyecto.estado == "Activo",
        models.Proyecto.updated_at < quince_dias_atras
    ).all()

    # Mis tareas pendientes
    mis_tareas = db.query(models.Actividad).join(models.Proyecto).filter(
        models.Actividad.responsable_usuario_id == user.id,
        models.Actividad.estado.notin_(["Completado", "Cancelado"]),
        models.Proyecto.estado != "Cancelado"
    ).order_by(models.Actividad.fecha_limite).limit(10).all()

    # Actividad reciente (últimos comentarios)
    actividad_reciente = db.query(models.Comentario).order_by(
        models.Comentario.created_at.desc()
    ).limit(8).all()

    return templates.TemplateResponse(request, "dashboard.html", {
        "current_user": user,
        "flash": request.session.pop("flash", None),
        "stats": {
            "total": total,
            "activos": activos,
            "completados": completados,
            "en_espera": en_espera,
        },
        "tareas_atrasadas": tareas_atrasadas,
        "tareas_por_vencer": tareas_por_vencer,
        "pendientes_cliente": pendientes_cliente,
        "proyectos_sin_movimiento": proyectos_sin_movimiento,
        "mis_tareas": mis_tareas,
        "actividad_reciente": actividad_reciente,
        "hoy": hoy,
    })


@router.get("/mis-tareas", response_class=HTMLResponse)
async def mis_tareas(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)

    tareas = db.query(models.Actividad).join(models.Proyecto).filter(
        models.Actividad.responsable_usuario_id == user.id,
        models.Actividad.estado.notin_(["Completado", "Cancelado"])
    ).order_by(models.Actividad.fecha_limite).all()

    return templates.TemplateResponse(request, "mis_tareas.html", {
        "current_user": user,
        "tareas": tareas,
        "hoy": datetime.utcnow(),
    })
