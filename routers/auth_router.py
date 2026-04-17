from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from database import get_db
from templates_config import templates
import models, auth

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if user:
        return RedirectResponse("/dashboard", status_code=302)
    error = request.session.pop("login_error", None)
    return templates.TemplateResponse(request, "login.html", {"error": error})


@router.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(models.Usuario).filter(
        models.Usuario.email == email.lower().strip(),
        models.Usuario.activo == True
    ).first()

    if not user or not auth.verify_password(password, user.password_hash):
        request.session["login_error"] = "Email o contraseña incorrectos"
        return RedirectResponse("/login", status_code=302)

    token = auth.create_token(user.id)
    response = RedirectResponse("/dashboard", status_code=302)
    response.set_cookie("access_token", token, httponly=True, secure=True, samesite="lax", max_age=60 * 60 * 24 * 7)
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie("access_token")
    return response
