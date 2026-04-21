from fastapi import APIRouter, Request, Depends, Form, File, UploadFile
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from database import get_db
from templates_config import templates
from utils.upload import guardar_archivo, eliminar_archivo
import models, auth

router = APIRouter(prefix="/proyectos")

TIPOS = ["Estudio", "Análisis Regulatorio", "Contrato Supervisión", "Auditoría", "Otro"]
ESTADOS = ["Activo", "En Espera", "Completado", "Cancelado"]


@router.get("", response_class=HTMLResponse)
async def lista(
    request: Request,
    estado: str = "",
    tipo: str = "",
    cliente_id: str = "",
    db: Session = Depends(get_db)
):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)

    q = db.query(models.Proyecto).join(models.Cliente)
    if estado:
        q = q.filter(models.Proyecto.estado == estado)
    if tipo:
        q = q.filter(models.Proyecto.tipo_proyecto == tipo)
    if cliente_id:
        q = q.filter(models.Proyecto.cliente_id == int(cliente_id))

    proyectos = q.order_by(models.Proyecto.updated_at.desc()).all()
    clientes = db.query(models.Cliente).filter(models.Cliente.activo == True).order_by(models.Cliente.nombre).all()
    hoy = datetime.utcnow()

    from datetime import timedelta
    proyectos_con_alarma = set()
    tareas_atrasadas_ids = set()
    for act in db.query(models.Actividad).filter(
        models.Actividad.estado.notin_(["Completado", "Cancelado"]),
        models.Actividad.fecha_limite != None
    ).all():
        if act.fecha_limite and act.fecha_limite < hoy:
            proyectos_con_alarma.add(act.proyecto_id)
            tareas_atrasadas_ids.add(act.proyecto_id)

    # Ingresos por año (solo admin)
    ingresos_por_anio = {}
    totales_ingresos = {"uf": 0.0, "clp": 0.0}
    if user.rol == "admin":
        from collections import defaultdict
        raw = defaultdict(lambda: {"uf": 0.0, "clp": 0.0, "proyectos": []})
        todos_con_valor = (
            db.query(models.Proyecto)
            .filter(models.Proyecto.valor_contrato != None, models.Proyecto.valor_contrato > 0)
            .order_by(models.Proyecto.fecha_estimada_cierre)
            .all()
        )
        for p in todos_con_valor:
            fecha_ref = p.fecha_estimada_cierre or p.fecha_inicio
            if not fecha_ref:
                continue
            anio = fecha_ref.year
            moneda = p.moneda_contrato or "UF"
            if moneda == "CLP":
                raw[anio]["clp"] += p.valor_contrato
                totales_ingresos["clp"] += p.valor_contrato
            else:
                raw[anio]["uf"] += p.valor_contrato
                totales_ingresos["uf"] += p.valor_contrato
            raw[anio]["proyectos"].append(p)
        ingresos_por_anio = dict(sorted(raw.items()))

    return templates.TemplateResponse(request, "proyectos/lista.html", {
        "current_user": user,
        "proyectos": proyectos,
        "clientes": clientes,
        "tipos": TIPOS,
        "estados": ESTADOS,
        "filtro_estado": estado,
        "filtro_tipo": tipo,
        "filtro_cliente": cliente_id,
        "proyectos_con_alarma": proyectos_con_alarma,
        "tareas_atrasadas_ids": tareas_atrasadas_ids,
        "ingresos_por_anio": ingresos_por_anio,
        "totales_ingresos": totales_ingresos,
        "flash": request.session.pop("flash", None),
        "hoy": hoy,
    })


@router.get("/nuevo", response_class=HTMLResponse)
async def nuevo_form(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    clientes = db.query(models.Cliente).filter(models.Cliente.activo == True).order_by(models.Cliente.nombre).all()
    usuarios = db.query(models.Usuario).filter(models.Usuario.activo == True).order_by(models.Usuario.nombre).all()
    return templates.TemplateResponse(request, "proyectos/form.html", {
        "current_user": user,
        "proyecto": None, "clientes": clientes,
        "usuarios": usuarios, "tipos": TIPOS,
    })


@router.post("/nuevo")
async def nuevo_submit(
    request: Request,
    nombre: str = Form(...),
    cliente_id: int = Form(...),
    tipo_proyecto: str = Form(...),
    orden_compra: str = Form(""),
    descripcion: str = Form(""),
    valor_contrato: str = Form(""),
    moneda_contrato: str = Form("UF"),
    fecha_inicio: str = Form(...),
    fecha_estimada_cierre: str = Form(""),
    responsable_id: int = Form(...),
    archivos: List[UploadFile] = File(default=[]),
    tipos_doc: List[str] = Form(default=[]),
    db: Session = Depends(get_db)
):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)

    ultimo = db.query(models.Proyecto).count()
    anio = datetime.utcnow().year
    codigo = f"SE-{anio}-{str(ultimo + 1).zfill(3)}"

    proyecto = models.Proyecto(
        codigo=codigo,
        nombre=nombre.strip(),
        cliente_id=cliente_id,
        tipo_proyecto=tipo_proyecto,
        descripcion=descripcion.strip(),
        orden_compra=orden_compra.strip(),
        valor_contrato=float(valor_contrato) if valor_contrato.strip() else None,
        moneda_contrato=moneda_contrato if moneda_contrato in ("UF", "CLP") else "UF",
        fecha_inicio=datetime.strptime(fecha_inicio, "%Y-%m-%d"),
        fecha_estimada_cierre=datetime.strptime(fecha_estimada_cierre, "%Y-%m-%d") if fecha_estimada_cierre else None,
        responsable_id=responsable_id,
        created_by=user.id,
        estado="Activo",
    )
    db.add(proyecto)
    db.commit()
    db.refresh(proyecto)

    # Registrar en bitácora
    comentario = models.Comentario(
        proyecto_id=proyecto.id,
        usuario_id=user.id,
        texto=f"Proyecto creado por {user.nombre}.",
        tipo_registro="sistema",
    )
    db.add(comentario)
    db.flush()

    # Guardar documentos iniciales
    for i, archivo in enumerate(archivos):
        if archivo and archivo.filename:
            tipo = tipos_doc[i] if i < len(tipos_doc) else "otro"
            nombre_guardado = await guardar_archivo(archivo)
            db.add(models.Documento(
                proyecto_id=proyecto.id,
                comentario_id=None,
                nombre_original=archivo.filename,
                nombre_archivo=nombre_guardado,
                tipo=tipo,
                uploaded_by=user.id,
            ))

    db.commit()

    request.session["flash"] = {"tipo": "success", "texto": f"Proyecto '{codigo}' creado exitosamente."}
    return RedirectResponse(f"/proyectos/{proyecto.id}", status_code=302)


@router.get("/{proyecto_id}", response_class=HTMLResponse)
async def ficha(proyecto_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)

    proyecto = db.query(models.Proyecto).filter(models.Proyecto.id == proyecto_id).first()
    if not proyecto:
        return RedirectResponse("/proyectos", status_code=302)

    usuarios = db.query(models.Usuario).filter(models.Usuario.activo == True).order_by(models.Usuario.nombre).all()
    clientes = db.query(models.Cliente).filter(models.Cliente.activo == True).order_by(models.Cliente.nombre).all()
    hoy = datetime.utcnow()

    total_act = len(proyecto.actividades)
    completadas = sum(1 for a in proyecto.actividades if a.estado == "Completado")
    progreso = int((completadas / total_act * 100)) if total_act > 0 else 0

    return templates.TemplateResponse(request, "proyectos/ficha.html", {
        "current_user": user,
        "proyecto": proyecto,
        "usuarios": usuarios,
        "tipos_actividad": ["Tarea", "Hito", "Entregable", "Reunión", "Revisión"],
        "prioridades": ["Baja", "Media", "Alta", "Crítica"],
        "estados_proyecto": ESTADOS,
        "total_act": total_act,
        "completadas": completadas,
        "progreso": progreso,
        "clientes": clientes,
        "flash": request.session.pop("flash", None),
        "hoy": hoy,
    })


@router.post("/{proyecto_id}/editar")
async def editar_submit(
    proyecto_id: int,
    request: Request,
    nombre: str = Form(...),
    cliente_id: int = Form(...),
    tipo_proyecto: str = Form(...),
    orden_compra: str = Form(""),
    descripcion: str = Form(""),
    valor_contrato: str = Form(""),
    moneda_contrato: str = Form("UF"),
    fecha_inicio: str = Form(...),
    fecha_estimada_cierre: str = Form(""),
    responsable_id: int = Form(...),
    estado: str = Form(...),
    db: Session = Depends(get_db)
):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)

    proyecto = db.query(models.Proyecto).filter(models.Proyecto.id == proyecto_id).first()
    if not proyecto:
        return RedirectResponse("/proyectos", status_code=302)

    estado_anterior = proyecto.estado
    proyecto.nombre = nombre.strip()
    proyecto.cliente_id = cliente_id
    proyecto.tipo_proyecto = tipo_proyecto
    proyecto.orden_compra = orden_compra.strip()
    proyecto.descripcion = descripcion.strip()
    proyecto.valor_contrato = float(valor_contrato) if valor_contrato.strip() else None
    proyecto.moneda_contrato = moneda_contrato if moneda_contrato in ("UF", "CLP") else "UF"
    proyecto.fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d")
    proyecto.fecha_estimada_cierre = datetime.strptime(fecha_estimada_cierre, "%Y-%m-%d") if fecha_estimada_cierre else None
    proyecto.responsable_id = responsable_id
    proyecto.estado = estado
    proyecto.updated_at = datetime.utcnow()
    db.commit()

    if estado_anterior != estado:
        db.add(models.Comentario(
            proyecto_id=proyecto_id,
            usuario_id=user.id,
            texto=f"Estado cambiado de '{estado_anterior}' a '{estado}'.",
            tipo_registro="cambio_estado",
        ))
        db.commit()

    request.session["flash"] = {"tipo": "success", "texto": "Proyecto actualizado."}
    return RedirectResponse(f"/proyectos/{proyecto_id}", status_code=302)


@router.post("/{proyecto_id}/finalizar")
async def finalizar(proyecto_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user or user.rol != "admin":
        return RedirectResponse("/proyectos", status_code=302)
    proyecto = db.query(models.Proyecto).filter(models.Proyecto.id == proyecto_id).first()
    if proyecto and proyecto.estado not in ("Completado", "Cancelado"):
        proyecto.estado = "Completado"
        proyecto.fecha_cierre_real = datetime.utcnow()
        proyecto.updated_at = datetime.utcnow()
        db.add(models.Comentario(
            proyecto_id=proyecto_id,
            usuario_id=user.id,
            texto=f"Proyecto marcado como Completado por {user.nombre}.",
            tipo_registro="cambio_estado",
        ))
        db.commit()
        request.session["flash"] = {"tipo": "success", "texto": "Proyecto finalizado exitosamente."}
    return RedirectResponse(f"/proyectos/{proyecto_id}", status_code=302)


@router.post("/{proyecto_id}/reactivar")
async def reactivar(proyecto_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user or user.rol != "admin":
        return RedirectResponse("/proyectos", status_code=302)
    proyecto = db.query(models.Proyecto).filter(models.Proyecto.id == proyecto_id).first()
    if proyecto and proyecto.estado == "Completado":
        proyecto.estado = "Activo"
        proyecto.fecha_cierre_real = None
        proyecto.updated_at = datetime.utcnow()
        db.add(models.Comentario(
            proyecto_id=proyecto_id,
            usuario_id=user.id,
            texto=f"Proyecto reactivado (vuelto a Activo) por {user.nombre}.",
            tipo_registro="cambio_estado",
        ))
        db.commit()
        request.session["flash"] = {"tipo": "info", "texto": "Proyecto reactivado y vuelto a estado Activo."}
    return RedirectResponse(f"/proyectos/{proyecto_id}", status_code=302)


@router.post("/{proyecto_id}/eliminar")
async def eliminar(proyecto_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user or user.rol != "admin":
        return RedirectResponse("/proyectos", status_code=302)
    proyecto = db.query(models.Proyecto).filter(models.Proyecto.id == proyecto_id).first()
    if proyecto:
        for doc in proyecto.documentos:
            eliminar_archivo(doc.nombre_archivo)
        codigo = proyecto.codigo
        db.delete(proyecto)
        db.commit()
        request.session["flash"] = {"tipo": "warning", "texto": f"Proyecto '{codigo}' eliminado."}
    return RedirectResponse("/proyectos", status_code=302)


@router.post("/{proyecto_id}/comentar")
async def agregar_comentario(
    proyecto_id: int,
    request: Request,
    texto: str = Form(...),
    tipo_doc: str = Form("otro"),
    archivos: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db)
):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)

    proyecto = db.query(models.Proyecto).filter(models.Proyecto.id == proyecto_id).first()
    if proyecto and texto.strip():
        comentario = models.Comentario(
            proyecto_id=proyecto_id,
            usuario_id=user.id,
            texto=texto.strip(),
            tipo_registro="comentario",
        )
        db.add(comentario)
        db.flush()

        for archivo in archivos:
            if archivo and archivo.filename:
                nombre_guardado = await guardar_archivo(archivo)
                db.add(models.Documento(
                    proyecto_id=proyecto_id,
                    comentario_id=comentario.id,
                    nombre_original=archivo.filename,
                    nombre_archivo=nombre_guardado,
                    tipo=tipo_doc,
                    uploaded_by=user.id,
                ))

        proyecto.updated_at = datetime.utcnow()
        db.commit()

    return RedirectResponse(f"/proyectos/{proyecto_id}#bitacora", status_code=302)
