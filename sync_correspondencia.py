"""
Sincroniza el Excel de correspondencia CEN hacia Supabase.
Ejecutar desde la carpeta del proyecto:
  python sync_correspondencia.py

Opciones:
  --excel   Ruta al archivo Excel  (default: detecta automáticamente)
  --full    Fuerza actualización de todos los registros (no solo nuevos)
"""
import os, sys, argparse
SUPABASE_URL = "https://burpgfobhpszpvagcvjg.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ1cnBnZm9iaHBzenB2YWdjdmpnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NjQzNzE2MCwiZXhwIjoyMDkyMDEzMTYwfQ.xu7tTlRUjtzxAiKVwaLj7c_-eC9BzaGklZUN2NJTNhE"
BUCKET = "correspondencia"
from datetime import datetime

try:
    import requests as _requests
    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False
    print("[aviso] 'requests' no instalado — se omite subida de PDFs. Instala con: pip install requests")
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://postgres.burpgfobhpszpvagcvjg:Sigma20026..%40@aws-1-sa-east-1.pooler.supabase.com:5432/postgres"
)

try:
    import pandas as pd
except ImportError:
    print("Instala pandas: pip install pandas openpyxl")
    sys.exit(1)

from database import SessionLocal, engine
import models

models.Base.metadata.create_all(bind=engine)

# ── Ruta por defecto al Excel ─────────────────────────────────────────────────
RUTAS_EXCEL = [
    r"C:\Users\sncar\OneDrive\Desktop\04 Script Revisión de Correspondencia\Revision_de_correspondencia.xlsx",
    r"C:\Users\sncar\OneDrive - Sigma Energia SpA\Estudios y Proyectos - Documentos\00 Correspondencia\Revision_de_correspondencia.xlsx",
    Path(__file__).parent.parent / "04 Script Revisión de Correspondencia" / "Revision_de_correspondencia.xlsx",
]

# ── Ruta base de PDFs (OneDrive) ──────────────────────────────────────────────
RUTAS_PDF_BASE = [
    r"C:\Users\sncar\OneDrive - Sigma Energia SpA\Estudios y Proyectos - Documentos\00 Correspondencia",
    r"C:\Users\sncar\OneDrive\Desktop\04 Script Revisión de Correspondencia\pdfs",
]


def encontrar_excel(override=None):
    if override:
        p = Path(override)
        if p.exists():
            return str(p)
        print(f"No se encontró: {override}")
        sys.exit(1)
    for ruta in RUTAS_EXCEL:
        p = Path(ruta)
        if p.exists():
            return str(p)
    print("No se encontró el Excel. Indica la ruta con --excel RUTA")
    sys.exit(1)


def parsear_fecha(valor):
    if pd.isna(valor) or str(valor).strip() in ("", "—", "-", "nan"):
        return None
    s = str(valor).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y",
                "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def buscar_pdf_local(correlativo, fecha):
    """Intenta encontrar el PDF en las carpetas locales de OneDrive."""
    if fecha is None:
        return None
    fecha_str = fecha.strftime("%Y.%m.%d")
    for base in RUTAS_PDF_BASE:
        p = Path(base) / fecha_str / f"{correlativo}.pdf"
        if p.exists():
            return str(p)
    return None


def subir_pdf_supabase(ruta_local, correlativo, fecha):
    """Sube el PDF a Supabase Storage. Devuelve la URL pública o None."""
    if not _REQUESTS_OK or not SUPABASE_KEY:
        return None
    fecha_dir = fecha.strftime("%Y/%m") if fecha else "sin_fecha"
    storage_path = f"{fecha_dir}/{correlativo}.pdf"
    try:
        with open(ruta_local, "rb") as f:
            contenido = f.read()
        resp = _requests.post(
            f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{storage_path}",
            headers={
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/pdf",
                "x-upsert": "true",
            },
            data=contenido,
            timeout=60,
        )
        if resp.status_code in (200, 201):
            return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{storage_path}"
        print(f"  [pdf] Error {correlativo}: HTTP {resp.status_code} — {resp.text[:120]}")
        return None
    except Exception as e:
        print(f"  [pdf] Excepción {correlativo}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--excel", default=None, help="Ruta al Excel")
    parser.add_argument("--full", action="store_true", help="Actualiza todos los registros")
    parser.add_argument("--skip-pdfs", action="store_true", help="No subir PDFs a Supabase Storage")
    args = parser.parse_args()
    subir_pdfs = not args.skip_pdfs and _REQUESTS_OK and bool(SUPABASE_KEY)

    ruta = encontrar_excel(args.excel)
    print(f"Leyendo: {ruta}")

    df = pd.read_excel(ruta, engine="openpyxl")
    df.columns = [c.strip() for c in df.columns]

    # Mapeo de columnas (tolerante a variaciones de nombre)
    col_map = {
        "Correlativo": "correlativo",
        "Fecha": "fecha",
        "Empresa(s)": "empresas",
        "Remitente": "remitente",
        "Destinatario": "destinatario",
        "Materia Macro": "materia_macro",
        "Materia Micro": "materia_micro",
        "Referencia": "referencia",
        "Respondida": "respondida",
        "Estado": "estado",
    }
    df.rename(columns=col_map, inplace=True)

    # Asegurar que existan las columnas mínimas
    for col in ["correlativo", "fecha"]:
        if col not in df.columns:
            print(f"Columna obligatoria no encontrada: {col}")
            sys.exit(1)

    df = df[df["correlativo"].notna()].copy()
    df["correlativo"] = df["correlativo"].astype(str).str.strip()
    df = df.drop_duplicates(subset=["correlativo"], keep="last")

    print(f"Registros en Excel: {len(df)} (únicos)")

    db = SessionLocal()
    existentes = {r.correlativo for r in db.query(models.Correspondencia.correlativo).all()}
    print(f"Registros en DB: {len(existentes)}")

    nuevos = 0
    actualizados = 0
    pdfs_subidos = 0

    for _, row in df.iterrows():
        correlativo = row.get("correlativo", "").strip()
        if not correlativo:
            continue

        fecha = parsear_fecha(row.get("fecha"))

        def get(col):
            v = row.get(col)
            if pd.isna(v) if hasattr(v, '__class__') and v.__class__.__name__ == 'float' else False:
                return None
            s = str(v).strip() if v is not None else None
            return None if s in ("", "nan", "—", "-") else s

        if correlativo in existentes and not args.full:
            # Registro ya existe: solo intentar subir PDF si aún no tiene URL
            if subir_pdfs:
                reg = db.query(models.Correspondencia).filter(
                    models.Correspondencia.correlativo == correlativo
                ).first()
                if reg and not reg.pdf_url:
                    pdf_local = buscar_pdf_local(correlativo, fecha)
                    if pdf_local:
                        url = subir_pdf_supabase(pdf_local, correlativo, fecha)
                        if url:
                            reg.pdf_url = url
                            pdfs_subidos += 1
            continue

        data = dict(
            correlativo=correlativo,
            fecha=fecha,
            empresas=get("empresas"),
            remitente=get("remitente"),
            destinatario=get("destinatario"),
            materia_macro=get("materia_macro"),
            materia_micro=get("materia_micro"),
            referencia=get("referencia"),
            respondida=get("respondida"),
            estado=get("estado"),
            updated_at=datetime.utcnow(),
        )

        # Buscar y subir PDF
        if subir_pdfs:
            pdf_local = buscar_pdf_local(correlativo, fecha)
            if pdf_local:
                url = subir_pdf_supabase(pdf_local, correlativo, fecha)
                if url:
                    data["pdf_url"] = url
                    pdfs_subidos += 1
                    print(f"  [pdf] ↑ {correlativo}")

        if correlativo in existentes:
            db.query(models.Correspondencia).filter(
                models.Correspondencia.correlativo == correlativo
            ).update(data)
            actualizados += 1
        else:
            db.add(models.Correspondencia(**data))
            nuevos += 1

        if (nuevos + actualizados) % 200 == 0:
            db.commit()
            print(f"  …{nuevos + actualizados} procesados")

    db.commit()
    db.close()

    print(f"\n✓ Nuevos: {nuevos} | Actualizados: {actualizados} | PDFs subidos: {pdfs_subidos} | Sin cambios: {len(df) - nuevos - actualizados}")
    print("Sincronización completada.")


if __name__ == "__main__":
    main()
