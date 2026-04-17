from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from database import get_db
from templates_config import templates
import models, auth

router = APIRouter(prefix="/clientes")


@router.get("", response_class=HTMLResponse)
async def lista(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    clientes = db.query(models.Cliente).filter(models.Cliente.activo == True).order_by(models.Cliente.nombre).all()
    return templates.TemplateResponse(request, "clientes/lista.html", {
        "current_user": user,
        "clientes": clientes,
        "flash": request.session.pop("flash", None),
    })


@router.get("/nuevo", response_class=HTMLResponse)
async def nuevo_form(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user or user.rol != "admin":
        return RedirectResponse("/clientes", status_code=302)
    return templates.TemplateResponse(request, "clientes/form.html", {
        "current_user": user, "cliente": None
    })


@router.post("/nuevo")
async def nuevo_submit(
    request: Request,
    nombre: str = Form(...),
    rut: str = Form(""),
    contacto_nombre: str = Form(""),
    contacto_email: str = Form(""),
    contacto_telefono: str = Form(""),
    db: Session = Depends(get_db)
):
    user = auth.get_current_user(request, db)
    if not user or user.rol != "admin":
        return RedirectResponse("/clientes", status_code=302)
    cliente = models.Cliente(
        nombre=nombre.strip(),
        rut=rut.strip() or None,
        contacto_nombre=contacto_nombre.strip(),
        contacto_email=contacto_email.strip(),
        contacto_telefono=contacto_telefono.strip(),
    )
    db.add(cliente)
    db.commit()
    request.session["flash"] = {"tipo": "success", "texto": f"Cliente '{nombre}' creado exitosamente."}
    return RedirectResponse("/clientes", status_code=302)


@router.get("/{cliente_id}/editar", response_class=HTMLResponse)
async def editar_form(cliente_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user or user.rol != "admin":
        return RedirectResponse("/clientes", status_code=302)
    cliente = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if not cliente:
        return RedirectResponse("/clientes", status_code=302)
    return templates.TemplateResponse(request, "clientes/form.html", {
        "current_user": user, "cliente": cliente
    })


@router.post("/{cliente_id}/editar")
async def editar_submit(
    cliente_id: int,
    request: Request,
    nombre: str = Form(...),
    rut: str = Form(""),
    contacto_nombre: str = Form(""),
    contacto_email: str = Form(""),
    contacto_telefono: str = Form(""),
    db: Session = Depends(get_db)
):
    user = auth.get_current_user(request, db)
    if not user or user.rol != "admin":
        return RedirectResponse("/clientes", status_code=302)
    cliente = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if cliente:
        cliente.nombre = nombre.strip()
        cliente.rut = rut.strip() or None
        cliente.contacto_nombre = contacto_nombre.strip()
        cliente.contacto_email = contacto_email.strip()
        cliente.contacto_telefono = contacto_telefono.strip()
        db.commit()
        request.session["flash"] = {"tipo": "success", "texto": "Cliente actualizado."}
    return RedirectResponse("/clientes", status_code=302)


# ── Cuentas del cliente ────────────────────────────────────────────────────

@router.get("/{cliente_id}/cuentas", response_class=HTMLResponse)
async def cuentas(cliente_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    cliente = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if not cliente:
        return RedirectResponse("/clientes", status_code=302)
    return templates.TemplateResponse(request, "clientes/cuentas.html", {
        "current_user": user,
        "cliente": cliente,
        "flash": request.session.pop("flash", None),
    })


@router.post("/{cliente_id}/cuentas/nueva")
async def nueva_cuenta(
    cliente_id: int,
    request: Request,
    nombre_sistema: str = Form(...),
    url: str = Form(""),
    usuario: str = Form(...),
    password: str = Form(...),
    notas: str = Form(""),
    db: Session = Depends(get_db)
):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    cuenta = models.CuentaCliente(
        cliente_id=cliente_id,
        nombre_sistema=nombre_sistema.strip(),
        url=url.strip() or None,
        usuario=usuario.strip(),
        password=password,
        notas=notas.strip() or None,
        created_by=user.id,
    )
    db.add(cuenta)
    db.commit()
    request.session["flash"] = {"tipo": "success", "texto": f"Cuenta '{nombre_sistema}' agregada."}
    return RedirectResponse(f"/clientes/{cliente_id}/cuentas", status_code=302)


@router.post("/{cliente_id}/cuentas/{cuenta_id}/editar")
async def editar_cuenta(
    cliente_id: int,
    cuenta_id: int,
    request: Request,
    nombre_sistema: str = Form(...),
    url: str = Form(""),
    usuario: str = Form(...),
    password: str = Form(...),
    notas: str = Form(""),
    db: Session = Depends(get_db)
):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    cuenta = db.query(models.CuentaCliente).filter(
        models.CuentaCliente.id == cuenta_id,
        models.CuentaCliente.cliente_id == cliente_id
    ).first()
    if cuenta:
        cuenta.nombre_sistema = nombre_sistema.strip()
        cuenta.url = url.strip() or None
        cuenta.usuario = usuario.strip()
        if password.strip():
            cuenta.password = password
        cuenta.notas = notas.strip() or None
        from datetime import datetime
        cuenta.updated_at = datetime.utcnow()
        db.commit()
        request.session["flash"] = {"tipo": "success", "texto": "Cuenta actualizada."}
    return RedirectResponse(f"/clientes/{cliente_id}/cuentas", status_code=302)


@router.post("/{cliente_id}/cuentas/{cuenta_id}/eliminar")
async def eliminar_cuenta(
    cliente_id: int,
    cuenta_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    cuenta = db.query(models.CuentaCliente).filter(
        models.CuentaCliente.id == cuenta_id,
        models.CuentaCliente.cliente_id == cliente_id
    ).first()
    if cuenta:
        db.delete(cuenta)
        db.commit()
        request.session["flash"] = {"tipo": "warning", "texto": "Cuenta eliminada."}
    return RedirectResponse(f"/clientes/{cliente_id}/cuentas", status_code=302)
