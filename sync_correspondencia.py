"""
Sincroniza el Excel de correspondencia CEN hacia Supabase.
Ejecutar desde la carpeta del proyecto:
  python sync_correspondencia.py

Opciones:
  --excel   Ruta al archivo Excel  (default: detecta automáticamente)
  --full    Fuerza actualización de todos los registros (no solo nuevos)
"""
import os, sys, argparse
from datetime import datetime
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
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--excel", default=None, help="Ruta al Excel")
    parser.add_argument("--full", action="store_true", help="Actualiza todos los registros")
    args = parser.parse_args()

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

    print(f"Registros en Excel: {len(df)}")

    db = SessionLocal()
    existentes = {r.correlativo for r in db.query(models.Correspondencia.correlativo).all()}
    print(f"Registros en DB: {len(existentes)}")

    nuevos = 0
    actualizados = 0

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

    print(f"\n✓ Nuevos: {nuevos} | Actualizados: {actualizados} | Sin cambios: {len(df) - nuevos - actualizados}")
    print("Sincronización completada.")


if __name__ == "__main__":
    main()
