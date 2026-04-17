from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from database import get_db
from templates_config import templates
import models, auth

router = APIRouter(prefix="/usuarios")


@router.get("", response_class=HTMLResponse)
async def lista(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user or user.rol != "admin":
        return RedirectResponse("/dashboard", status_code=302)
    usuarios = db.query(models.Usuario).order_by(models.Usuario.nombre).all()
    return templates.TemplateResponse(request, "usuarios/lista.html", {
        "current_user": user,
        "usuarios": usuarios,
        "flash": request.session.pop("flash", None),
    })


@router.post("/nuevo")
async def nuevo_submit(
    request: Request,
    nombre: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    rol: str = Form("usuario"),
    db: Session = Depends(get_db)
):
    user = auth.get_current_user(request, db)
    if not user or user.rol != "admin":
        return RedirectResponse("/dashboard", status_code=302)
    existente = db.query(models.Usuario).filter(models.Usuario.email == email.lower().strip()).first()
    if existente:
        request.session["flash"] = {"tipo": "danger", "texto": "Ese email ya está registrado."}
        return RedirectResponse("/usuarios", status_code=302)
    nuevo = models.Usuario(
        nombre=nombre.strip(),
        email=email.lower().strip(),
        password_hash=auth.hash_password(password),
        rol=rol,
    )
    db.add(nuevo)
    db.commit()
    request.session["flash"] = {"tipo": "success", "texto": f"Usuario '{nombre}' creado exitosamente."}
    return RedirectResponse("/usuarios", status_code=302)


@router.post("/{usuario_id}/toggle")
async def toggle_activo(usuario_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user or user.rol != "admin":
        return RedirectResponse("/dashboard", status_code=302)
    u = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if u and u.id != user.id:
        u.activo = not u.activo
        db.commit()
    return RedirectResponse("/usuarios", status_code=302)


@router.post("/{usuario_id}/cambiar-rol")
async def cambiar_rol(
    usuario_id: int,
    request: Request,
    nuevo_rol: str = Form(...),
    db: Session = Depends(get_db)
):
    user = auth.get_current_user(request, db)
    if not user or user.rol != "admin":
        return RedirectResponse("/dashboard", status_code=302)
    u = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if u and u.id != user.id and nuevo_rol in ("admin", "usuario"):
        u.rol = nuevo_rol
        db.commit()
        request.session["flash"] = {"tipo": "success", "texto": f"Rol de '{u.nombre}' actualizado a {nuevo_rol}."}
    return RedirectResponse("/usuarios", status_code=302)


@router.post("/{usuario_id}/cambiar-password")
async def cambiar_password(
    usuario_id: int,
    request: Request,
    nueva_password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = auth.get_current_user(request, db)
    if not user or user.rol != "admin":
        return RedirectResponse("/dashboard", status_code=302)
    u = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if u:
        u.password_hash = auth.hash_password(nueva_password)
        db.commit()
        request.session["flash"] = {"tipo": "success", "texto": "Contraseña actualizada."}
    return RedirectResponse("/usuarios", status_code=302)
