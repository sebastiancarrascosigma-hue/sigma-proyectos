"""Envío de minutas por email via SMTP (Microsoft 365 / Office 365)."""
import os, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.office365.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
EMAIL_SENDER  = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")


def enviar_minuta(minuta, destinatarios: list[str]) -> tuple[bool, str]:
    """
    Envía el resumen de la minuta a todos los destinatarios.
    Devuelve (ok: bool, mensaje: str).
    """
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        return False, "Credenciales de email no configuradas (EMAIL_SENDER / EMAIL_PASSWORD)."
    if not destinatarios:
        return False, "No hay participantes con email."

    asunto = f"Minuta {minuta.fecha.strftime('%d/%m/%Y')} · {minuta.cliente.nombre} · {minuta.titulo}"
    html   = _construir_html(minuta)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"]    = EMAIL_SENDER
    msg["To"]      = ", ".join(destinatarios)
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, destinatarios, msg.as_string())
        return True, f"Minuta enviada a {len(destinatarios)} participante(s)."
    except Exception as e:
        return False, f"Error al enviar email: {e}"


def _construir_html(minuta) -> str:
    temas_html = ""
    for t in minuta.temas:
        acuerdo_html = (
            f'<div style="margin-top:10px;padding:10px;background:#f0fdf4;border-left:3px solid #16a34a;border-radius:4px">'
            f'<strong style="color:#16a34a">Acuerdos / Compromisos</strong><br>'
            f'<span style="white-space:pre-wrap">{t.acuerdos}</span></div>'
        ) if t.acuerdos else ""

        resp_html = (
            f'<div style="margin-top:8px;font-size:12px;color:#6b7280">'
            f'👤 Responsable: <strong>{t.responsable.nombre}</strong></div>'
        ) if t.responsable else ""

        temas_html += f"""
        <div style="margin-bottom:20px;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden">
          <div style="background:#eff6ff;padding:12px 16px;border-bottom:1px solid #dbeafe">
            <strong style="color:#1d4ed8">{t.proyecto.codigo}</strong>
            <span style="color:#374151;margin-left:8px">{t.proyecto.nombre}</span>
          </div>
          <div style="padding:14px 16px">
            <div style="font-size:12px;color:#6b7280;margin-bottom:4px;font-weight:600;text-transform:uppercase">Lo tratado</div>
            <div style="white-space:pre-wrap;color:#111827">{t.lo_tratado}</div>
            {acuerdo_html}
            {resp_html}
          </div>
        </div>"""

    participantes_html = "".join(
        f'<span style="display:inline-block;margin:3px;padding:4px 10px;background:#f3f4f6;border-radius:20px;font-size:13px">'
        f'{"📧 " if p.email else ""}{p.nombre}'
        f'{"  ·  <span style=color:#6b7280>" + p.empresa + "</span>" if p.empresa else ""}'
        f'</span>'
        for p in minuta.participantes
    )

    resumen_html = (
        f'<div style="margin-bottom:20px;padding:12px 16px;background:#fafafa;border:1px solid #e5e7eb;border-radius:8px">'
        f'<strong>Resumen general</strong><br><span style="white-space:pre-wrap">{minuta.resumen}</span></div>'
    ) if minuta.resumen else ""

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:0;padding:0;background:#f9fafb">
<div style="max-width:680px;margin:30px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08)">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#1d4ed8,#3b82f6);padding:28px 32px">
    <div style="color:#bfdbfe;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.05em">Sigma Energía SpA</div>
    <h1 style="color:#fff;margin:6px 0 4px;font-size:22px;font-weight:700">Minuta de Reunión</h1>
    <div style="color:#dbeafe;font-size:14px">{minuta.titulo}</div>
  </div>

  <div style="padding:28px 32px">

    <!-- Metadata -->
    <table style="width:100%;margin-bottom:24px;font-size:14px;color:#374151">
      <tr>
        <td style="padding:4px 0;width:130px;color:#6b7280;font-weight:600">Cliente</td>
        <td style="padding:4px 0"><strong>{minuta.cliente.nombre}</strong></td>
      </tr>
      <tr>
        <td style="padding:4px 0;color:#6b7280;font-weight:600">Fecha</td>
        <td style="padding:4px 0">{minuta.fecha.strftime("%d de %B de %Y")}</td>
      </tr>
      <tr>
        <td style="padding:4px 0;color:#6b7280;font-weight:600">Elaboró</td>
        <td style="padding:4px 0">{minuta.creador.nombre if minuta.creador else "—"}</td>
      </tr>
    </table>

    <!-- Participantes -->
    {f'<div style="margin-bottom:24px"><div style="font-size:12px;font-weight:700;color:#6b7280;text-transform:uppercase;margin-bottom:8px">Participantes</div>{participantes_html}</div>' if minuta.participantes else ""}

    {resumen_html}

    <!-- Proyectos -->
    <div style="font-size:12px;font-weight:700;color:#6b7280;text-transform:uppercase;margin-bottom:12px">
      Proyectos Tratados ({len(minuta.temas)})
    </div>
    {temas_html}

  </div>

  <!-- Footer -->
  <div style="padding:16px 32px;background:#f9fafb;border-top:1px solid #e5e7eb;font-size:12px;color:#9ca3af;text-align:center">
    Este correo fue generado automáticamente por el sistema Sigma Proyectos · Sigma Energía SpA
  </div>
</div>
</body></html>"""
