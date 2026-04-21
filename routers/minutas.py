import os, json
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
from database import get_db
from templates_config import templates
import models, auth
from utils.email_sender import enviar_minuta, enviar_notificacion_interna

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
        contactos = [
            {
                "nombre": ct.nombre,
                "email": ct.email or "",
                "cargo": ct.cargo or "",
                "tipo": ct.tipo,
            }
            for ct in c.contactos if ct.activo
        ]
        data[c.id] = {
            "nombre": c.nombre,
            "contactos": contactos,
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


def _auto_agregar_contactos(db, cliente_id: int, part_nombres, part_emails, part_empresas, part_cargos, parte_enviar):
    """Agrega automáticamente participantes externos como contactos adicionales del cliente."""
    for i, nombre in enumerate(part_nombres):
        nombre = nombre.strip()
        if not nombre:
            continue
        empresa = (part_empresas[i].strip() if i < len(part_empresas) else "")
        email = (part_emails[i].strip() if i < len(part_emails) else "")
        cargo = (part_cargos[i].strip() if i < len(part_cargos) else "")
        if empresa == "Sigma Energía" or not email:
            continue
        existing = db.query(models.ContactoCliente).filter(
            models.ContactoCliente.cliente_id == cliente_id,
            models.ContactoCliente.email == email,
        ).first()
        if not existing:
            db.add(models.ContactoCliente(
                cliente_id=cliente_id,
                nombre=nombre,
                email=email,
                cargo=cargo or None,
                tipo="adicional",
            ))


@router.post("/nueva")
async def nueva_submit(
    request: Request,
    cliente_id: int = Form(...),
    titulo: str = Form(...),
    fecha: str = Form(...),
    resumen: str = Form(""),
    part_nombres: List[str] = Form(default=[]),
    part_emails: List[str] = Form(default=[]),
    part_empresas: List[str] = Form(default=[]),
    part_cargos: List[str] = Form(default=[]),
    part_enviar: List[str] = Form(default=[]),
    proyecto_ids: List[str] = Form(default=[]),
    lo_tratados: List[str] = Form(default=[]),
    acuerdos_list: List[str] = Form(default=[]),
    responsable_ids: List[str] = Form(default=[]),
    fechas_respuesta: List[str] = Form(default=[]),
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
            cargo=(part_cargos[i].strip() if i < len(part_cargos) else "") or None,
            enviar_minuta=(part_enviar[i] == "1" if i < len(part_enviar) else True),
        ))

    _auto_agregar_contactos(db, cliente_id, part_nombres, part_emails, part_empresas, part_cargos, part_enviar)

    # Temas (un registro por punto; proyecto_ids puede repetirse para multi-punto)
    for i, pid_raw in enumerate(proyecto_ids):
        pid_str = (pid_raw or "").strip()
        if not pid_str or not pid_str.isdigit():
            continue
        pid = int(pid_str)
        tratado = lo_tratados[i].strip() if i < len(lo_tratados) else ""
        acuerdo = acuerdos_list[i].strip() if i < len(acuerdos_list) else ""
        resp_raw = responsable_ids[i] if i < len(responsable_ids) else ""
        resp_id = int(resp_raw) if resp_raw and resp_raw.isdigit() else None
        fecha_raw = fechas_respuesta[i].strip() if i < len(fechas_respuesta) else ""
        fecha_resp = datetime.strptime(fecha_raw, "%Y-%m-%d").date() if fecha_raw else None

        if not tratado:
            continue

        db.add(models.MinutaTema(
            minuta_id=minuta.id,
            proyecto_id=pid,
            lo_tratado=tratado,
            acuerdos=acuerdo or None,
            responsable_id=resp_id,
            fecha_estimada_respuesta=fecha_resp,
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
                minuta_id=minuta.id,
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
    comentarios_minuta = db.query(models.Comentario).filter(
        models.Comentario.minuta_id == minuta_id
    ).count()
    return templates.TemplateResponse(request, "minutas/detalle.html", {
        "current_user": user,
        "minuta": minuta,
        "email_configurado": bool(os.getenv("EMAIL_SENDER")),
        "comentarios_minuta": comentarios_minuta,
        "flash": request.session.pop("flash", None),
    })


@router.get("/{minuta_id}/editar", response_class=HTMLResponse)
async def editar_form(minuta_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    minuta = db.query(models.Minuta).filter(models.Minuta.id == minuta_id).first()
    if not minuta:
        return RedirectResponse("/minutas", status_code=302)
    if user.rol != "admin" and minuta.created_by != user.id:
        request.session["flash"] = {"tipo": "danger", "texto": "No tienes permiso para editar esta minuta."}
        return RedirectResponse(f"/minutas/{minuta_id}", status_code=302)

    clientes  = db.query(models.Cliente).filter(models.Cliente.activo == True).order_by(models.Cliente.nombre).all()
    proyectos = db.query(models.Proyecto).order_by(models.Proyecto.nombre).all()
    usuarios  = db.query(models.Usuario).filter(models.Usuario.activo == True).order_by(models.Usuario.nombre).all()

    participantes_json = json.dumps([
        {
            "nombre": p.nombre,
            "email": p.email or "",
            "empresa": p.empresa or "",
            "cargo": p.cargo or "",
            "enviarMinuta": p.enviar_minuta if p.enviar_minuta is not None else True,
        }
        for p in minuta.participantes
    ], ensure_ascii=False)

    temas_json = json.dumps([
        {
            "proyecto_id": str(t.proyecto_id),
            "lo_tratado": t.lo_tratado,
            "acuerdos": t.acuerdos or "",
            "responsable_id": str(t.responsable_id) if t.responsable_id else "",
            "fecha_estimada_respuesta": t.fecha_estimada_respuesta.strftime("%Y-%m-%d") if t.fecha_estimada_respuesta else "",
        }
        for t in minuta.temas
    ], ensure_ascii=False)

    return templates.TemplateResponse(request, "minutas/editar.html", {
        "current_user": user,
        "minuta": minuta,
        "clientes": clientes,
        "proyectos": proyectos,
        "usuarios": usuarios,
        "proyectos_json": _proyectos_como_json(proyectos),
        "clientes_json": _clientes_como_json(clientes),
        "participantes_json": participantes_json,
        "temas_json": temas_json,
    })


@router.post("/{minuta_id}/editar")
async def editar_submit(
    minuta_id: int,
    request: Request,
    cliente_id: int = Form(...),
    titulo: str = Form(...),
    fecha: str = Form(...),
    resumen: str = Form(""),
    part_nombres: List[str] = Form(default=[]),
    part_emails: List[str] = Form(default=[]),
    part_empresas: List[str] = Form(default=[]),
    part_cargos: List[str] = Form(default=[]),
    part_enviar: List[str] = Form(default=[]),
    proyecto_ids: List[str] = Form(default=[]),
    lo_tratados: List[str] = Form(default=[]),
    acuerdos_list: List[str] = Form(default=[]),
    responsable_ids: List[str] = Form(default=[]),
    fechas_respuesta: List[str] = Form(default=[]),
    db: Session = Depends(get_db)
):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    minuta = db.query(models.Minuta).filter(models.Minuta.id == minuta_id).first()
    if not minuta:
        return RedirectResponse("/minutas", status_code=302)
    if user.rol != "admin" and minuta.created_by != user.id:
        request.session["flash"] = {"tipo": "danger", "texto": "No tienes permiso para editar esta minuta."}
        return RedirectResponse(f"/minutas/{minuta_id}", status_code=302)

    minuta.cliente_id = cliente_id
    minuta.titulo = titulo.strip()
    minuta.fecha = datetime.strptime(fecha, "%Y-%m-%d")
    minuta.resumen = resumen.strip() or None
    minuta.email_enviado = False

    db.query(models.MinutaParticipante).filter(models.MinutaParticipante.minuta_id == minuta_id).delete()
    db.query(models.MinutaTema).filter(models.MinutaTema.minuta_id == minuta_id).delete()
    db.flush()

    for i, nombre in enumerate(part_nombres):
        nombre = nombre.strip()
        if not nombre:
            continue
        db.add(models.MinutaParticipante(
            minuta_id=minuta.id,
            nombre=nombre,
            email=(part_emails[i].strip() if i < len(part_emails) else "") or None,
            empresa=(part_empresas[i].strip() if i < len(part_empresas) else "") or None,
            cargo=(part_cargos[i].strip() if i < len(part_cargos) else "") or None,
            enviar_minuta=(part_enviar[i] == "1" if i < len(part_enviar) else True),
        ))

    _auto_agregar_contactos(db, cliente_id, part_nombres, part_emails, part_empresas, part_cargos, part_enviar)

    for i, pid_raw in enumerate(proyecto_ids):
        pid_str = (pid_raw or "").strip()
        if not pid_str or not pid_str.isdigit():
            continue
        pid = int(pid_str)
        tratado = lo_tratados[i].strip() if i < len(lo_tratados) else ""
        acuerdo = acuerdos_list[i].strip() if i < len(acuerdos_list) else ""
        resp_raw = responsable_ids[i] if i < len(responsable_ids) else ""
        resp_id = int(resp_raw) if resp_raw and resp_raw.isdigit() else None
        fecha_raw = fechas_respuesta[i].strip() if i < len(fechas_respuesta) else ""
        fecha_resp = datetime.strptime(fecha_raw, "%Y-%m-%d").date() if fecha_raw else None
        if not tratado:
            continue
        db.add(models.MinutaTema(
            minuta_id=minuta.id,
            proyecto_id=pid,
            lo_tratado=tratado,
            acuerdos=acuerdo or None,
            responsable_id=resp_id,
            fecha_estimada_respuesta=fecha_resp,
        ))

    db.commit()
    request.session["flash"] = {"tipo": "success", "texto": "Minuta actualizada."}
    return RedirectResponse(f"/minutas/{minuta_id}", status_code=302)


@router.post("/{minuta_id}/notificar")
async def notificar_equipo(minuta_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    minuta = db.query(models.Minuta).filter(models.Minuta.id == minuta_id).first()
    if not minuta:
        return RedirectResponse("/minutas", status_code=302)

    emails = [p.email for p in minuta.participantes if p.email and p.email.strip()]
    ok, mensaje = enviar_notificacion_interna(minuta, emails)

    db.add(models.MinutaEnvio(
        minuta_id=minuta_id,
        tipo="equipo",
        destinatarios=", ".join(emails),
        num_destinatarios=len(emails),
        enviado_por=user.id,
        exitoso=ok,
        mensaje=mensaje,
    ))
    if ok:
        minuta.notificacion_enviada = True
    db.commit()
    request.session["flash"] = {"tipo": "success" if ok else "danger", "texto": mensaje}
    return RedirectResponse(f"/minutas/{minuta_id}", status_code=302)


@router.post("/{minuta_id}/enviar")
async def enviar(minuta_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    minuta = db.query(models.Minuta).filter(models.Minuta.id == minuta_id).first()
    if not minuta:
        return RedirectResponse("/minutas", status_code=302)

    destinatarios = [
        p.email for p in minuta.participantes
        if p.email and p.email.strip() and (p.enviar_minuta if p.enviar_minuta is not None else True)
    ]
    ok, mensaje = enviar_minuta(minuta, destinatarios)

    db.add(models.MinutaEnvio(
        minuta_id=minuta_id,
        tipo="cliente",
        destinatarios=", ".join(destinatarios),
        num_destinatarios=len(destinatarios),
        enviado_por=user.id,
        exitoso=ok,
        mensaje=mensaje,
    ))
    if ok:
        minuta.email_enviado = True
    db.commit()
    request.session["flash"] = {"tipo": "success" if ok else "danger", "texto": mensaje}
    return RedirectResponse(f"/minutas/{minuta_id}", status_code=302)


@router.post("/{minuta_id}/eliminar")
async def eliminar(
    minuta_id: int,
    request: Request,
    eliminar_comentarios: str = Form("no"),
    db: Session = Depends(get_db)
):
    user = auth.get_current_user(request, db)
    if not user or user.rol != "admin":
        return RedirectResponse("/minutas", status_code=302)
    minuta = db.query(models.Minuta).filter(models.Minuta.id == minuta_id).first()
    if minuta:
        comentarios_eliminados = 0
        if eliminar_comentarios == "si":
            comentarios_eliminados = db.query(models.Comentario).filter(
                models.Comentario.minuta_id == minuta_id
            ).delete()
        db.delete(minuta)
        db.commit()
        msg = "Minuta eliminada."
        if comentarios_eliminados:
            msg += f" Se eliminaron {comentarios_eliminados} comentario(s) de bitácoras."
        request.session["flash"] = {"tipo": "warning", "texto": msg}
    return RedirectResponse("/minutas", status_code=302)
