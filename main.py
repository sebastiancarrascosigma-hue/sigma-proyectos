import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import database, models

from routers import auth_router, dashboard, clientes, proyectos, actividades, usuarios, correspondencia, minutas


def run_migrations():
    """Aplica columnas/tablas faltantes que create_all no agrega a tablas existentes."""
    from sqlalchemy import text
    stmts = [
        # minutas: columnas agregadas después de la creación inicial
        "ALTER TABLE minutas ADD COLUMN IF NOT EXISTS email_enviado BOOLEAN DEFAULT FALSE",
        "ALTER TABLE minutas ADD COLUMN IF NOT EXISTS notificacion_enviada BOOLEAN DEFAULT FALSE",
        "ALTER TABLE minutas ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP",
        # minuta_temas: fecha_estimada_respuesta agregada después
        "ALTER TABLE minuta_temas ADD COLUMN IF NOT EXISTS fecha_estimada_respuesta DATE",
        "ALTER TABLE comentarios ADD COLUMN IF NOT EXISTS minuta_id INTEGER REFERENCES minutas(id) ON DELETE SET NULL",
        # subactividades y documentos: create_all las crea si no existen
    ]
    with database.engine.connect() as conn:
        for stmt in stmts:
            try:
                conn.execute(text(stmt))
            except Exception as e:
                print(f"[migration] {stmt[:60]}… → {e}")
        conn.commit()


app = FastAPI(title="Sigma Proyectos")
app.add_middleware(SessionMiddleware, secret_key="sigma-session-key-2026")

run_migrations()
models.Base.metadata.create_all(bind=database.engine)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Directorio de archivos subidos (persistente en HF Spaces si UPLOAD_DIR=/data/uploads)
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/tmp/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
try:
    app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
except Exception as _e:
    print(f"[warn] No se pudo montar /uploads: {_e}")

app.include_router(auth_router.router)
app.include_router(dashboard.router)
app.include_router(clientes.router)
app.include_router(proyectos.router)
app.include_router(actividades.router)
app.include_router(usuarios.router)
app.include_router(correspondencia.router)
app.include_router(minutas.router)


@app.get("/")
async def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/dashboard", status_code=302)
