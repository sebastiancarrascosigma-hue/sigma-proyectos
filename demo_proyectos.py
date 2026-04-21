"""Crea proyectos y tareas de ejemplo por usuario. Ejecutar una sola vez."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://postgres.burpgfobhpszpvagcvjg:Sigma20026..%40@aws-1-sa-east-1.pooler.supabase.com:5432/postgres"
)

from database import SessionLocal, engine
import models
from datetime import datetime, timedelta

models.Base.metadata.create_all(bind=engine)
db = SessionLocal()

hoy = datetime.utcnow()

# usuario_id -> (nombre, cliente_id, tipo, descripcion)
proyectos_demo = [
    # Sebastián Carrasco
    (1, "SE-2026-001", "Auditoría Eléctrica AGUAS CAP",           13, "Auditoría",      "Revisión integral de instalaciones eléctricas de media tensión."),
    # Erwin Monsalve
    (2, "SE-2026-002", "Estudio de Factibilidad GNL",              5,  "Estudio",        "Evaluación técnica y económica de ampliación de capacidad."),
    # Gonzalo Lizama
    (3, "SE-2026-003", "Supervisión Obras ENAEX",                  22, "Supervisión",    "Supervisión técnica de obras de distribución eléctrica."),
    # Nicolás Ebner
    (4, "SE-2026-004", "Trámite Regulatorio ATLAS RENEWABLE",      19, "Regulatorio",    "Gestión de permisos y normativas ante la CNE y la SEC."),
    # Braulio Villa
    (5, "SE-2026-005", "Auditoría Sistema BT ANTUCOYA",            11, "Auditoría",      "Diagnóstico de sistema de baja tensión y propuesta de mejoras."),
    # Alex Hernández
    (6, "SE-2026-006", "Estudio Tarifario AGUAS CAP",              13, "Estudio",        "Análisis y optimización de contratos de suministro eléctrico."),
    # Pablo Arriagada
    (7, "SE-2026-007", "Supervisión Proyecto FPC TISSUE",          15, "Supervisión",    "Supervisión de montaje de subestación 110/13.2 kV."),
]

tareas_demo = {
    "SE-2026-001": [
        ("Revisión de single line diagram",         "Sigma",   hoy - timedelta(days=3),  "Alta",    "Pendiente"),
        ("Informe de hallazgos preliminar",         "Sigma",   hoy + timedelta(days=5),  "Alta",    "En Progreso"),
        ("Envío informe final al cliente",          "Sigma",   hoy + timedelta(days=20), "Media",   "Pendiente"),
    ],
    "SE-2026-002": [
        ("Levantamiento de datos de consumo",       "Sigma",   hoy - timedelta(days=1),  "Alta",    "Pendiente"),
        ("Confirmación de demanda máxima",          "Cliente", hoy + timedelta(days=4),  "Alta",    "Pendiente"),
        ("Modelamiento en DIgSILENT",               "Sigma",   hoy + timedelta(days=15), "Media",   "Pendiente"),
    ],
    "SE-2026-003": [
        ("Visita a terreno semana 1",               "Sigma",   hoy - timedelta(days=5),  "Alta",    "Completado"),
        ("Informe de avance semanal N°1",           "Sigma",   hoy + timedelta(days=2),  "Alta",    "En Progreso"),
        ("Aprobación planos constructivos",         "Cliente", hoy + timedelta(days=10), "Alta",    "Pendiente"),
    ],
    "SE-2026-004": [
        ("Preparar expediente técnico SEC",         "Sigma",   hoy - timedelta(days=2),  "Alta",    "Pendiente"),
        ("Respuesta a observaciones CNE",           "Sigma",   hoy + timedelta(days=6),  "Alta",    "Pendiente"),
        ("Firma de documentos por cliente",         "Cliente", hoy + timedelta(days=3),  "Media",   "Pendiente"),
    ],
    "SE-2026-005": [
        ("Medición de calidad de energía",          "Sigma",   hoy - timedelta(days=4),  "Alta",    "Pendiente"),
        ("Termografía de tableros principales",     "Sigma",   hoy + timedelta(days=7),  "Media",   "Pendiente"),
        ("Entrega de informe ejecutivo",            "Sigma",   hoy + timedelta(days=25), "Media",   "Pendiente"),
    ],
    "SE-2026-006": [
        ("Recopilación de facturas 12 meses",       "Cliente", hoy + timedelta(days=2),  "Alta",    "Pendiente"),
        ("Análisis de perfil de carga",             "Sigma",   hoy + timedelta(days=8),  "Alta",    "Pendiente"),
        ("Propuesta de optimización tarifaria",     "Sigma",   hoy + timedelta(days=18), "Media",   "Pendiente"),
    ],
    "SE-2026-007": [
        ("Revisión de ingeniería de detalle",       "Sigma",   hoy - timedelta(days=1),  "Alta",    "En Progreso"),
        ("Informe de avance mensual",               "Sigma",   hoy + timedelta(days=3),  "Alta",    "Pendiente"),
        ("Prueba de aislamiento transformadores",   "Cliente", hoy + timedelta(days=12), "Media",   "Pendiente"),
    ],
}

admin_id = 1  # Sebastián como creador

for responsable_id, codigo, nombre, cliente_id, tipo, desc in proyectos_demo:
    existe = db.query(models.Proyecto).filter(models.Proyecto.codigo == codigo).first()
    if existe:
        print(f"  Ya existe: {codigo}")
        continue
    p = models.Proyecto(
        codigo=codigo,
        nombre=nombre,
        cliente_id=cliente_id,
        tipo_proyecto=tipo,
        descripcion=desc,
        fecha_inicio=hoy - timedelta(days=10),
        fecha_estimada_cierre=hoy + timedelta(days=60),
        estado="Activo",
        responsable_id=responsable_id,
        created_by=admin_id,
    )
    db.add(p)
    db.flush()

    for titulo, resp_tipo, fecha_lim, prioridad, estado in tareas_demo[codigo]:
        t = models.Actividad(
            proyecto_id=p.id,
            titulo=titulo,
            tipo="Tarea",
            responsable_tipo=resp_tipo,
            responsable_usuario_id=responsable_id if resp_tipo == "Sigma" else None,
            estado=estado,
            prioridad=prioridad,
            fecha_limite=fecha_lim,
            created_by=admin_id,
        )
        db.add(t)

    print(f"  Creado: {codigo} — {nombre}")

db.commit()
db.close()
print("\nDatos de ejemplo cargados.")
