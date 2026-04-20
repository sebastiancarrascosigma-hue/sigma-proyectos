"""Genera PDF de minutas usando weasyprint."""
try:
    from weasyprint import HTML as _WeasyHTML
    _WEASY_OK = True
except Exception:
    _WEASY_OK = False


def generar_pdf_minuta(minuta) -> bytes | None:
    """Devuelve los bytes del PDF o None si weasyprint no está disponible."""
    if not _WEASY_OK:
        return None
    try:
        html = _html_pdf(minuta)
        return _WeasyHTML(string=html).write_pdf()
    except Exception as e:
        print(f"[pdf] Error generando PDF: {e}")
        return None


def _html_pdf(minuta) -> str:
    # ── Filas de temas ────────────────────────────────────────────────────────
    filas = ""
    for t in minuta.temas:
        acuerdo = (f'<div style="border-left:3px solid #16a34a;padding-left:6px;white-space:pre-wrap">'
                   f'{t.acuerdos}</div>') if t.acuerdos else '<span style="color:#9ca3af">—</span>'
        resp    = f'<strong>{t.responsable.nombre}</strong>' if t.responsable else '<span style="color:#9ca3af">—</span>'
        fecha   = (f'<span style="background:#fef3c7;color:#92400e;padding:1px 6px;border-radius:10px;font-size:10px">'
                   f'{t.fecha_estimada_respuesta.strftime("%d/%m/%Y")}</span>'
                   if t.fecha_estimada_respuesta else '<span style="color:#9ca3af">—</span>')
        filas += f"""
        <tr style="border-bottom:1px solid #e5e7eb;vertical-align:top">
          <td style="padding:8px 10px;font-size:11px">
            <strong style="color:#1d4ed8">{t.proyecto.codigo}</strong><br>
            <span style="color:#6b7280;font-size:10px">{t.proyecto.nombre[:55]}</span>
          </td>
          <td style="padding:8px 10px;font-size:11px;white-space:pre-wrap">{t.lo_tratado}</td>
          <td style="padding:8px 10px;font-size:11px">{acuerdo}</td>
          <td style="padding:8px 10px;font-size:11px">{resp}</td>
          <td style="padding:8px 10px;font-size:11px;white-space:nowrap">{fecha}</td>
        </tr>"""

    # ── Participantes ─────────────────────────────────────────────────────────
    partic = "".join(
        f'<span style="display:inline-block;margin:2px 4px;padding:3px 10px;background:#f3f4f6;'
        f'border-radius:20px;font-size:11px">{p.nombre}'
        f'{" · " + p.empresa if p.empresa else ""}</span>'
        for p in minuta.participantes
    )

    resumen = (f'<div style="margin:16px 0;padding:10px 14px;background:#f9fafb;border:1px solid #e5e7eb;'
               f'border-radius:6px;font-size:11px;white-space:pre-wrap">{minuta.resumen}</div>'
               ) if minuta.resumen else ""

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
  @page {{ size: A4; margin: 1.8cm 1.5cm 1.8cm 1.5cm; }}
  body {{ font-family: Arial, Helvetica, sans-serif; margin:0; padding:0; color:#111827; font-size:12px; }}
  .header {{ background:#1d4ed8; color:#fff; padding:20px 24px; }}
  .header-sub {{ font-size:9px; font-weight:700; text-transform:uppercase; letter-spacing:.06em; opacity:.75; }}
  .header h1 {{ margin:4px 0 2px; font-size:18px; font-weight:700; color:#fff; }}
  .header .titulo {{ color:#dbeafe; font-size:12px; }}
  .meta {{ padding:14px 24px; border-bottom:1px solid #e5e7eb; }}
  .meta table {{ width:100%; font-size:11px; border-collapse:collapse; }}
  .meta td {{ padding:3px 0; vertical-align:top; }}
  .meta td:first-child {{ color:#6b7280; font-weight:600; width:110px; }}
  .section {{ padding:12px 24px; border-bottom:1px solid #f3f4f6; }}
  .section-title {{ font-size:9px; font-weight:700; text-transform:uppercase; letter-spacing:.07em; color:#9ca3af; margin-bottom:8px; }}
  .temas-table {{ width:100%; border-collapse:collapse; font-size:11px; }}
  .temas-table th {{ padding:6px 10px; text-align:left; font-size:9px; color:#6b7280; font-weight:700;
                     text-transform:uppercase; letter-spacing:.05em; background:#f8fafc;
                     border-bottom:2px solid #e2e8f0; }}
  .footer {{ padding:10px 24px; background:#f9fafb; border-top:1px solid #e5e7eb; font-size:9px;
             color:#9ca3af; text-align:center; }}
</style>
</head>
<body>

<div class="header">
  <div class="header-sub">Sigma Energía SpA · Minuta de Reunión</div>
  <h1>Minuta de Reunión</h1>
  <div class="titulo">{minuta.titulo}</div>
</div>

<div class="meta">
  <table>
    <tr>
      <td>Cliente</td>
      <td><strong>{minuta.cliente.nombre}</strong></td>
    </tr>
    <tr>
      <td>Fecha</td>
      <td>{minuta.fecha.strftime("%d de %B de %Y")}</td>
    </tr>
    <tr>
      <td>Elaboró</td>
      <td>{minuta.creador.nombre if minuta.creador else "—"}</td>
    </tr>
  </table>
</div>

{"<div class='section'><div class='section-title'>Participantes</div>" + partic + "</div>" if minuta.participantes else ""}

{"<div class='section'><div class='section-title'>Resumen General</div>" + resumen + "</div>" if minuta.resumen else ""}

<div class="section">
  <div class="section-title">Proyectos Tratados ({len(minuta.temas)})</div>
  <table class="temas-table">
    <thead>
      <tr>
        <th style="width:20%">Proyecto</th>
        <th style="width:28%">Lo Tratado</th>
        <th style="width:27%">Acuerdo / Compromiso</th>
        <th style="width:15%">Responsable</th>
        <th style="width:10%">Fecha Resp.</th>
      </tr>
    </thead>
    <tbody>{filas}</tbody>
  </table>
</div>

<div class="footer">
  Generado automáticamente por Sigma Proyectos · Sigma Energía SpA
</div>

</body></html>"""
