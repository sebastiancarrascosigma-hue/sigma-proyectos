from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
import models, auth

router = APIRouter(prefix="/actividades")


@router.post("/nueva/{proyecto_id}")
async def nueva(
    proyecto_id: int,
    request: Request,
    titulo: str = Form(...),
    descripcion: str = Form(""),
    tipo: str = Form("Tarea"),
    responsable_tipo: str = Form("Sigma"),
    responsable_usuario_id: str = Form(""),
    responsable_cliente_nombre: str = Form(""),
    prioridad: str = Form("Media"),
    fecha_limite: str = Form(""),
    db: Session = Depends(get_db)
):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)

    proyecto = db.query(models.Proyecto).filter(models.Proyecto.id == proyecto_id).first()
    if not proyecto:
        return RedirectResponse("/proyectos", status_code=302)

    actividad = models.Actividad(
        proyecto_id=proyecto_id,
        titulo=titulo.strip(),
        descripcion=descripcion.strip(),
        tipo=tipo,
        responsable_tipo=responsable_tipo,
        responsable_usuario_id=int(responsable_usuario_id) if responsable_usuario_id.strip() else None,
        responsable_cliente_nombre=responsable_cliente_nombre.strip() or None,
        prioridad=prioridad,
        fecha_limite=datetime.strptime(fecha_limite, "%Y-%m-%d") if fecha_limite.strip() else None,
        estado="Pendiente",
        created_by=user.id,
    )
    db.add(actividad)
    proyecto.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(actividad)

    db.add(models.Comentario(
        proyecto_id=proyecto_id,
        actividad_id=actividad.id,
        usuario_id=user.id,
        texto=f"Actividad '{titulo}' creada ({responsable_tipo}).",
        tipo_registro="sistema",
    ))
    db.commit()

    request.session["flash"] = {"tipo": "success", "texto": f"Actividad '{titulo}' agregada."}
    return RedirectResponse(f"/proyectos/{proyecto_id}", status_code=302)


@router.post("/{actividad_id}/estado")
async def cambiar_estado(
    actividad_id: int,
    request: Request,
    nuevo_estado: str = Form(...),
    db: Session = Depends(get_db)
):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)

    actividad = db.query(models.Actividad).filter(models.Actividad.id == actividad_id).first()
    if actividad:
        estado_anterior = actividad.estado
        actividad.estado = nuevo_estado
        if nuevo_estado == "Completado":
            actividad.fecha_completado = datetime.utcnow()
        actividad.updated_at = datetime.utcnow()

        proyecto = db.query(models.Proyecto).filter(models.Proyecto.id == actividad.proyecto_id).first()
        if proyecto:
            proyecto.updated_at = datetime.utcnow()

        db.add(models.Comentario(
            proyecto_id=actividad.proyecto_id,
            actividad_id=actividad.id,
            usuario_id=user.id,
            texto=f"Estado de '{actividad.titulo}' cambiado de '{estado_anterior}' a '{nuevo_estado}'.",
            tipo_registro="cambio_estado",
        ))
        db.commit()
        request.session["flash"] = {"tipo": "success", "texto": f"Estado actualizado a '{nuevo_estado}'."}
        return RedirectResponse(f"/proyectos/{actividad.proyecto_id}", status_code=302)

    return RedirectResponse("/proyectos", status_code=302)


@router.post("/{actividad_id}/eliminar")
async def eliminar(actividad_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)

    actividad = db.query(models.Actividad).filter(models.Actividad.id == actividad_id).first()
    if actividad:
        proyecto_id = actividad.proyecto_id
        db.delete(actividad)
        db.commit()
        request.session["flash"] = {"tipo": "warning", "texto": "Actividad eliminada."}
        return RedirectResponse(f"/proyectos/{proyecto_id}", status_code=302)

    return RedirectResponse("/proyectos", status_code=302)
