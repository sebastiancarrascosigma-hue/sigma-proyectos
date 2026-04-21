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
        # participantes: campos agregados para cargo y selector de envío
        "ALTER TABLE minuta_participantes ADD COLUMN IF NOT EXISTS cargo VARCHAR(100)",
        "ALTER TABLE minuta_participantes ADD COLUMN IF NOT EXISTS enviar_minuta BOOLEAN DEFAULT TRUE",
        # proyectos: moneda del contrato
        "ALTER TABLE proyectos ADD COLUMN IF NOT EXISTS moneda_contrato VARCHAR(10) DEFAULT 'UF'",
    ]
    with database.engine.connect() as conn:
        for stmt in stmts:
            try:
                conn.execute(text(stmt))
            except Exception as e:
                print(f"[migration] {stmt[:60]}… → {e}")
        conn.commit()


def _migrate_contactos_iniciales():
    """Migra contactos existentes de Cliente.contacto_* a la tabla contactos_cliente."""
    from sqlalchemy import text
    with database.engine.connect() as conn:
        try:
            result = conn.execute(text(
                "SELECT id, contacto_nombre, contacto_email, contacto_telefono FROM clientes "
                "WHERE contacto_nombre IS NOT NULL AND contacto_nombre != '' "
                "AND id NOT IN (SELECT DISTINCT cliente_id FROM contactos_cliente WHERE tipo='principal')"
            ))
            rows = result.fetchall()
            for row in rows:
                conn.execute(text(
                    "INSERT INTO contactos_cliente "
                    "(cliente_id, nombre, email, telefono, tipo, activo, created_at) "
                    "VALUES (:cid, :nombre, :email, :telefono, 'principal', TRUE, CURRENT_TIMESTAMP)"
                ), {"cid": row[0], "nombre": row[1], "email": row[2] or "", "telefono": row[3] or ""})
            conn.commit()
            if rows:
                print(f"[migrate_contactos] {len(rows)} contacto(s) migrado(s).")
        except Exception as e:
            print(f"[migrate_contactos] {e}")


app = FastAPI(title="Sigma Proyectos")
_SESSION_SECRET = os.getenv("SESSION_SECRET", "sigma-session-key-2026")
app.add_middleware(SessionMiddleware, secret_key=_SESSION_SECRET)

run_migrations()
models.Base.metadata.create_all(bind=database.engine)
_migrate_contactos_iniciales()

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
