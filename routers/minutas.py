from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from database import get_db
from templates_config import templates
import models, auth

router = APIRouter(prefix="/minutas")


@router.get("", response_class=HTMLResponse)
async def lista(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    minutas = db.query(models.Minuta).order_by(models.Minuta.fecha.desc()).all()
    return templates.TemplateResponse(request, "minutas/lista.html", {
        "current_user": user,
        "minutas": minutas,
        "flash": request.session.pop("flash", None),
    })


@router.get("/nueva", response_class=HTMLResponse)
async def nueva_form(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    clientes  = db.query(models.Cliente).filter(models.Cliente.activo == True).order_by(models.Cliente.nombre).all()
    proyectos = db.query(models.Proyecto).filter(models.Proyecto.estado == "Activo").order_by(models.Proyecto.nombre).all()
    usuarios  = db.query(models.Usuario).filter(models.Usuario.activo == True).order_by(models.Usuario.nombre).all()
    return templates.TemplateResponse(request, "minutas/form.html", {
        "current_user": user,
        "clientes": clientes,
        "proyectos": proyectos,
        "usuarios": usuarios,
        "minuta": None,
        "hoy": datetime.utcnow().strftime("%Y-%m-%d"),
    })


@router.post("/nueva")
async def nueva_submit(
    request: Request,
    cliente_id: int = Form(...),
    titulo: str = Form(...),
    fecha: str = Form(...),
    participantes: str = Form(""),
    resumen: str = Form(""),
    proyecto_ids: List[int] = Form(default=[]),
    lo_tratados: List[str] = Form(default=[]),
    acuerdos_list: List[str] = Form(default=[]),
    responsable_ids: List[str] = Form(default=[]),
    db: Session = Depends(get_db)
):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)

    minuta = models.Minuta(
        cliente_id=cliente_id,
        titulo=titulo.strip(),
        fecha=datetime.strptime(fecha, "%Y-%m-%d"),
        participantes=participantes.strip() or None,
        resumen=resumen.strip() or None,
        created_by=user.id,
    )
    db.add(minuta)
    db.flush()

    for i, pid in enumerate(proyecto_ids):
        tratado   = lo_tratados[i].strip()  if i < len(lo_tratados)       else ""
        acuerdo   = acuerdos_list[i].strip() if i < len(acuerdos_list)    else ""
        resp_raw  = responsable_ids[i]       if i < len(responsable_ids)  else ""
        resp_id   = int(resp_raw) if resp_raw and resp_raw.isdigit() else None

        if not tratado:
            continue

        tema = models.MinutaTema(
            minuta_id=minuta.id,
            proyecto_id=pid,
            lo_tratado=tratado,
            acuerdos=acuerdo or None,
            responsable_id=resp_id,
        )
        db.add(tema)

        # Registrar en bitácora del proyecto
        proyecto = db.query(models.Proyecto).filter(models.Proyecto.id == pid).first()
        if proyecto:
            texto_bitacora = f"📋 Minuta {minuta.fecha.strftime('%d/%m/%Y')} · {minuta.titulo}\n{tratado}"
            if acuerdo:
                texto_bitacora += f"\nAcuerdo: {acuerdo}"
            db.add(models.Comentario(
                proyecto_id=pid,
                usuario_id=user.id,
                texto=texto_bitacora,
                tipo_registro="comentario",
            ))
            proyecto.updated_at = datetime.utcnow()

    db.commit()
    request.session["flash"] = {"tipo": "success", "texto": f"Minuta '{titulo}' creada y registrada en los proyectos."}
    return RedirectResponse(f"/minutas/{minuta.id}", status_code=302)


@router.get("/{minuta_id}", response_class=HTMLResponse)
async def detalle(minuta_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    minuta = db.query(models.Minuta).filter(models.Minuta.id == minuta_id).first()
    if not minuta:
        return RedirectResponse("/minutas", status_code=302)
    return templates.TemplateResponse(request, "minutas/detalle.html", {
        "current_user": user,
        "minuta": minuta,
        "flash": request.session.pop("flash", None),
    })


@router.post("/{minuta_id}/eliminar")
async def eliminar(minuta_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user or user.rol != "admin":
        return RedirectResponse("/minutas", status_code=302)
    minuta = db.query(models.Minuta).filter(models.Minuta.id == minuta_id).first()
    if minuta:
        db.delete(minuta)
        db.commit()
        request.session["flash"] = {"tipo": "warning", "texto": "Minuta eliminada."}
    return RedirectResponse("/minutas", status_code=302)
