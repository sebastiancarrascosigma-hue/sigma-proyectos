import os, json
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
from database import get_db
from templates_config import templates
import models, auth
from utils.email_sender import enviar_minuta

router = APIRouter(prefix="/minutas")


def _proyectos_como_json(proyectos):
    """Serializa proyectos para el JS del formulario."""
    data = {}
    for p in proyectos:
        resp = p.responsable
        data[p.id] = {
            "codigo": p.codigo,
            "nombre": p.nombre,
            "cliente_id": p.cliente_id,
            "responsable_nombre": resp.nombre if resp else "",
            "responsable_email": resp.email if resp else "",
        }
    return json.dumps(data, ensure_ascii=False)


def _clientes_como_json(clientes):
    data = {}
    for c in clientes:
        data[c.id] = {
            "nombre": c.nombre,
            "contacto_nombre": c.contacto_nombre or "",
            "contacto_email": c.contacto_email or "",
        }
    return json.dumps(data, ensure_ascii=False)


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
        "proyectos_json": _proyectos_como_json(proyectos),
        "clientes_json": _clientes_como_json(clientes),
        "hoy": datetime.utcnow().strftime("%Y-%m-%d"),
    })


@router.post("/nueva")
async def nueva_submit(
    request: Request,
    cliente_id: int = Form(...),
    titulo: str = Form(...),
    fecha: str = Form(...),
    resumen: str = Form(""),
    # Participantes
    part_nombres: List[str] = Form(default=[]),
    part_emails: List[str] = Form(default=[]),
    part_empresas: List[str] = Form(default=[]),
    # Temas
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
        resumen=resumen.strip() or None,
        created_by=user.id,
    )
    db.add(minuta)
    db.flush()

    # Participantes
    for i, nombre in enumerate(part_nombres):
        nombre = nombre.strip()
        if not nombre:
            continue
        db.add(models.MinutaParticipante(
            minuta_id=minuta.id,
            nombre=nombre,
            email=(part_emails[i].strip() if i < len(part_emails) else "") or None,
            empresa=(part_empresas[i].strip() if i < len(part_empresas) else "") or None,
        ))

    # Temas
    for i, pid in enumerate(proyecto_ids):
        tratado = lo_tratados[i].strip() if i < len(lo_tratados) else ""
        acuerdo = acuerdos_list[i].strip() if i < len(acuerdos_list) else ""
        resp_raw = responsable_ids[i] if i < len(responsable_ids) else ""
        resp_id = int(resp_raw) if resp_raw and resp_raw.isdigit() else None

        if not tratado:
            continue

        db.add(models.MinutaTema(
            minuta_id=minuta.id,
            proyecto_id=pid,
            lo_tratado=tratado,
            acuerdos=acuerdo or None,
            responsable_id=resp_id,
        ))

        # Bitácora del proyecto
        proyecto = db.query(models.Proyecto).filter(models.Proyecto.id == pid).first()
        if proyecto:
            texto = f"Minuta {minuta.fecha.strftime('%d/%m/%Y')} · {minuta.titulo}\n{tratado}"
            if acuerdo:
                texto += f"\nAcuerdo: {acuerdo}"
            db.add(models.Comentario(
                proyecto_id=pid,
                usuario_id=user.id,
                texto=texto,
                tipo_registro="comentario",
            ))
            proyecto.updated_at = datetime.utcnow()

    db.commit()
    request.session["flash"] = {"tipo": "success", "texto": f"Minuta '{titulo}' guardada."}
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
        "email_configurado": bool(os.getenv("EMAIL_SENDER")),
        "flash": request.session.pop("flash", None),
    })


@router.post("/{minuta_id}/enviar")
async def enviar(minuta_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    minuta = db.query(models.Minuta).filter(models.Minuta.id == minuta_id).first()
    if not minuta:
        return RedirectResponse("/minutas", status_code=302)

    destinatarios = [p.email for p in minuta.participantes if p.email and p.email.strip()]
    ok, mensaje = enviar_minuta(minuta, destinatarios)

    if ok:
        minuta.email_enviado = True
        db.commit()
        request.session["flash"] = {"tipo": "success", "texto": mensaje}
    else:
        request.session["flash"] = {"tipo": "danger", "texto": mensaje}

    return RedirectResponse(f"/minutas/{minuta_id}", status_code=302)


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
