"""
title: Konzertmeister Agent
description: |
  Vollständiger Agent für die Konzertmeister REST-API.
  Ermöglicht das Abfragen und Erstellen von Terminen, Anzeigen
  kommender Proben und Konzerte sowie die Verwaltung des Vereinskalenders.
  Unterstützt Filterung nach Typ, Status, Tags und Zeitraum.
author: OpenWebUI Tools
version: 1.0.0
required_open_webui_version: 0.3.9
"""

import json
import requests
from datetime import datetime, timedelta, timezone
from typing import Optional
from pydantic import BaseModel, Field


# Termin-Typ Mapping
APPOINTMENT_TYPES = {
    1: "Probe",
    2: "Auftritt",
    3: "Sonstiges",
    4: "Probenanfrage",
    5: "Auftrittanfrage",
    6: "Information",
}

APPOINTMENT_TYPE_IDS = {
    "probe": 1,
    "rehearsal": 1,
    "auftritt": 2,
    "konzert": 2,
    "performance": 2,
    "sonstiges": 3,
    "other": 3,
    "probenanfrage": 4,
    "rehearsalrequest": 4,
    "auftrittanfrage": 5,
    "performancerequest": 5,
    "information": 6,
    "info": 6,
}

BASE_URL = "https://rest.konzertmeister.app"





def _headers(api_key: str) -> dict:
    return {
        "X-KM-ORG-API-KEY": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _now_iso(tz_offset: str = "+01:00") -> str:
    now = datetime.now()
    return now.strftime(f"%Y-%m-%dT%H:%M:%S{tz_offset}")


def _date_iso(dt: datetime, tz_offset: str = "+01:00") -> str:
    return dt.strftime(f"%Y-%m-%dT%H:%M:%S{tz_offset}")


def _parse_appointment(appt: dict, timezone_hint: str = "Europe/Vienna") -> dict:
    """Formatiert einen Termin-Dict für die LLM-Ausgabe."""

    def fmt_date(iso_str: str) -> str:
        if not iso_str:
            return "–"
        try:
            dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
            # In lokale Zeit umrechnen (vereinfacht: +1h für MEZ)
            dt = dt + timedelta(hours=1)
            return dt.strftime("%d.%m.%Y %H:%M")
        except Exception:
            return iso_str

    typ = APPOINTMENT_TYPES.get(appt.get("typId"), "Unbekannt")
    status = "✅ Aktiv" if appt.get("active") else "❌ Abgesagt"
    published = "📢 Veröffentlicht" if appt.get("published") else "📝 Entwurf"

    location = ""
    if appt.get("location"):
        location = appt["location"].get("formattedAddress") or appt["location"].get("name", "")
    elif appt.get("room"):
        location = appt["room"].get("name", "")

    tags = ", ".join([t.get("tag", "") for t in appt.get("tags", [])]) or "–"

    return {
        "id": appt.get("id"),
        "name": appt.get("name", ""),
        "typ": typ,
        "status": status,
        "published": published,
        "start": fmt_date(appt.get("start")),
        "end": fmt_date(appt.get("end")),
        "beschreibung": appt.get("description", "–"),
        "ort": location or "–",
        "tags": tags,
        "reminder_deadline": fmt_date(appt.get("remindDeadline")),
        "status_deadline": fmt_date(appt.get("statusDeadline")),
        "link": appt.get("privateLinkURL", ""),
    }


def _format_appointment_list(appointments: list, show_details: bool = False) -> str:
    if not appointments:
        return "Keine Termine gefunden."

    lines = []
    for a in appointments:
        p = _parse_appointment(a)
        line = f"📅 **{p['name']}** ({p['typ']})\n"
        line += f"   🕐 {p['start']} – {p['end']}\n"
        line += f"   {p['status']} | {p['published']}\n"
        if p["ort"] != "–":
            line += f"   📍 {p['ort']}\n"
        if show_details:
            if p["beschreibung"] and p["beschreibung"] != "–":
                line += f"   📝 {p['beschreibung']}\n"
            if p["tags"] != "–":
                line += f"   🏷️ Tags: {p['tags']}\n"
            if p["reminder_deadline"] != "–":
                line += f"   🔔 Erinnerung bis: {p['reminder_deadline']}\n"
            if p["status_deadline"] != "–":
                line += f"   ⏰ Zu-/Absage bis: {p['status_deadline']}\n"
        if p["link"]:
            line += f"   🔗 [In Konzertmeister öffnen]({p['link']})\n"
        lines.append(line)

    return "\n".join(lines)


class Tools:
    class Valves(BaseModel):
        api_key: str = Field(
            default="",
            description="Konzertmeister API-Schlüssel (X-KM-ORG-API-KEY). "
            "Zu finden in der Web App unter Vereinsdetails → Bearbeiten → Öffentliche API.",
        )
        creator_email: str = Field(
            default="",
            description="E-Mail-Adresse des Standard-Erstellers für neue Termine. "
            "Muss Berechtigung zum Erstellen von Terminen im Verein haben.",
        )
        default_template_id: str = Field(
            default="",
            description="Externe Template-ID für neue Termine (APP_TEMP_...). "
            "Zu finden in der Web App unter Terminvorlagen → Details.",
        )
        timezone: str = Field(
            default="Europe/Vienna",
            description="Zeitzone für Terminanzeige und -erstellung (z.B. Europe/Vienna, Europe/Berlin).",
        )

    class UserValves(BaseModel):
        reminder_days_before: int = Field(
            default=7,
            description="Anzahl Tage VOR dem Termin, an dem die Erinnerung gesendet wird. "
            "Wird bei der Terminerstellung für den LLM-Hinweis verwendet (Standard: 7).",
            ge=1,
            le=60,
        )
        status_deadline_days_before: int = Field(
            default=6,
            description="Anzahl Tage VOR dem Termin, bis zu dem Zu-/Absagen möglich sind. "
            "Wird bei der Terminerstellung für den LLM-Hinweis verwendet (Standard: 6).",
            ge=1,
            le=60,
        )
        default_page_size_weeks: int = Field(
            default=8,
            description="Standard-Zeitraum in Wochen für Terminabfragen ohne explizites Datum (Standard: 8).",
            ge=1,
            le=52,
        )

    def __init__(self):
        self.valves = self.Valves()
        self.user_valves = self.UserValves()

    def get_upcoming_appointments(
        self,
        weeks_ahead: Optional[int] = None,
        types: Optional[str] = None,
        include_cancelled: bool = False,
        show_details: bool = False,
    ) -> str:
        """
        Ruft kommende Termine aus Konzertmeister ab.

        :param weeks_ahead: Wie viele Wochen in die Zukunft (Standard: aus UserValves).
        :param types: Kommagetrennte Termintypen, z.B. "Probe,Auftritt" oder "1,2". Leer = alle.
        :param include_cancelled: Abgesagte Termine ebenfalls anzeigen (Standard: Nein).
        :param show_details: Detailierte Informationen anzeigen inkl. Beschreibung, Tags, Deadlines.
        :return: Formatierte Terminliste.
        """
        if not self.valves.api_key:
            return "❌ Kein API-Schlüssel konfiguriert. Bitte in den Valves den Konzertmeister API-Schlüssel hinterlegen."

        weeks = weeks_ahead or self.user_valves.default_page_size_weeks
        now = datetime.now()
        end = now + timedelta(weeks=weeks)

        # Termin-Typen parsen
        type_ids = []
        if types:
            for t in types.replace(" ", "").split(","):
                t_lower = t.lower()
                if t_lower.isdigit():
                    type_ids.append(int(t_lower))
                elif t_lower in APPOINTMENT_TYPE_IDS:
                    type_ids.append(APPOINTMENT_TYPE_IDS[t_lower])
        if not type_ids:
            type_ids = [1, 2, 3, 4, 5, 6]

        status_filter = ["ACTIVE", "CANCELLED"] if include_cancelled else ["ACTIVE"]

        body = {
            "filterStart": _date_iso(now),
            "filterEnd": _date_iso(end),
            "typeIds": type_ids,
            "activationStatusList": status_filter,
            "publishedStatus": "ALL",
            "tags": [],
            "sortMode": "STARTDATE",
            "dateMode": "UPCOMING",
            "page": 0,
        }

        all_appointments = []
        page = 0
        while True:
            body["page"] = page
            try:
                resp = requests.post(
                    f"{BASE_URL}/api/v4/org/m2m/appointments",
                    headers=_headers(self.valves.api_key),
                    json=body,
                    timeout=15,
                )
                if resp.status_code == 401:
                    return "❌ Authentifizierung fehlgeschlagen. Bitte API-Schlüssel prüfen."
                if resp.status_code != 200:
                    return f"❌ API-Fehler {resp.status_code}: {resp.text[:200]}"

                data = resp.json()
                if not data:
                    break

                all_appointments.extend(data)
                if len(data) < 10:
                    break
                page += 1

            except requests.exceptions.ConnectionError:
                return "❌ Verbindung zu Konzertmeister fehlgeschlagen. Bitte Internetverbindung prüfen."
            except Exception as e:
                return f"❌ Fehler: {str(e)}"

        header = f"## 📅 Konzertmeister – Kommende Termine\n"
        header += f"*Zeitraum: {now.strftime('%d.%m.%Y')} bis {end.strftime('%d.%m.%Y')} ({weeks} Wochen)*\n"
        header += f"*{len(all_appointments)} Termin(e) gefunden*\n\n"

        return header + _format_appointment_list(all_appointments, show_details=show_details)

    def get_appointments_by_date(
        self,
        start_date: str,
        end_date: str,
        types: Optional[str] = None,
        include_cancelled: bool = False,
        page: int = 0,
        show_details: bool = False,
    ) -> str:
        """
        Ruft Termine in einem bestimmten Zeitraum ab.

        :param start_date: Startdatum im Format YYYY-MM-DD oder DD.MM.YYYY.
        :param end_date: Enddatum im Format YYYY-MM-DD oder DD.MM.YYYY.
        :param types: Kommagetrennte Termintypen, z.B. "Probe,Auftritt".
        :param include_cancelled: Abgesagte Termine ebenfalls anzeigen.
        :param page: Seite (0-basiert, 10 Termine pro Seite).
        :param show_details: Detailierte Informationen anzeigen.
        :return: Formatierte Terminliste.
        """
        if not self.valves.api_key:
            return "❌ Kein API-Schlüssel konfiguriert."

        # Datum parsen
        def parse_date(d: str) -> datetime:
            for fmt in ["%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y"]:
                try:
                    return datetime.strptime(d.strip(), fmt)
                except ValueError:
                    continue
            raise ValueError(f"Ungültiges Datumsformat: {d}")

        try:
            dt_start = parse_date(start_date)
            dt_end = parse_date(end_date).replace(hour=23, minute=59, second=59)
        except ValueError as e:
            return f"❌ {e}. Bitte Datum im Format YYYY-MM-DD oder DD.MM.YYYY angeben."

        type_ids = []
        if types:
            for t in types.replace(" ", "").split(","):
                t_lower = t.lower()
                if t_lower.isdigit():
                    type_ids.append(int(t_lower))
                elif t_lower in APPOINTMENT_TYPE_IDS:
                    type_ids.append(APPOINTMENT_TYPE_IDS[t_lower])
        if not type_ids:
            type_ids = [1, 2, 3, 4, 5, 6]

        body = {
            "filterStart": _date_iso(dt_start),
            "filterEnd": _date_iso(dt_end),
            "typeIds": type_ids,
            "activationStatusList": ["ACTIVE", "CANCELLED"] if include_cancelled else ["ACTIVE"],
            "publishedStatus": "ALL",
            "tags": [],
            "sortMode": "STARTDATE",
            "dateMode": "FROM_DATE",
            "page": page,
        }

        try:
            resp = requests.post(
                f"{BASE_URL}/api/v4/org/m2m/appointments",
                headers=_headers(self.valves.api_key),
                json=body,
                timeout=15,
            )
            if resp.status_code == 401:
                return "❌ Authentifizierung fehlgeschlagen."
            if resp.status_code != 200:
                return f"❌ API-Fehler {resp.status_code}: {resp.text[:200]}"

            data = resp.json()
            header = f"## 📅 Termine {dt_start.strftime('%d.%m.%Y')} – {dt_end.strftime('%d.%m.%Y')}\n"
            header += f"*{len(data)} Termin(e) auf Seite {page + 1}*\n\n"

            pagination = ""
            if len(data) == 10:
                pagination = f"\n\n*📄 Es gibt möglicherweise weitere Termine. Mit `page={page + 1}` die nächste Seite abfragen.*"

            return header + _format_appointment_list(data, show_details) + pagination

        except Exception as e:
            return f"❌ Fehler: {str(e)}"

    def create_appointment(
        self,
        name: str,
        start_datetime: str,
        description: Optional[str] = None,
        template_id: Optional[str] = None,
        creator_email: Optional[str] = None,
    ) -> str:
        """
        Erstellt einen neuen Termin in Konzertmeister auf Basis einer Vorlage.

        :param name: Name/Titel des Termins.
        :param start_datetime: Startdatum und -uhrzeit, z.B. "2025-12-15 19:30" oder "15.12.2025 19:30".
        :param description: Beschreibung des Termins (optional).
        :param template_id: Externe Template-ID (APP_TEMP_...). Falls leer, wird der Default-Wert aus Valves verwendet.
        :param creator_email: E-Mail des Erstellers. Falls leer, wird der Default-Wert aus Valves verwendet.
        :return: Bestätigung mit Details des erstellten Termins.
        """
        if not self.valves.api_key:
            return "❌ Kein API-Schlüssel konfiguriert."

        template = template_id or self.valves.default_template_id
        if not template:
            return (
                "❌ Keine Template-ID angegeben. Bitte die externe Template-ID (APP_TEMP_...) angeben "
                "oder in den Valves als Default hinterlegen.\n\n"
                "Die Template-ID findest du in der Konzertmeister Web App unter: "
                "**Terminvorlagen → Vorlage auswählen → Details**"
            )

        email = creator_email or self.valves.creator_email
        if not email:
            return (
                "❌ Keine Ersteller-E-Mail angegeben. Bitte E-Mail-Adresse eines Vereins-Leiters angeben "
                "oder in den Valves als Default hinterlegen."
            )

        # Datum/Zeit parsen
        def parse_datetime(s: str) -> datetime:
            for fmt in [
                "%Y-%m-%d %H:%M",
                "%d.%m.%Y %H:%M",
                "%Y-%m-%dT%H:%M",
                "%Y-%m-%d",
                "%d.%m.%Y",
            ]:
                try:
                    return datetime.strptime(s.strip(), fmt)
                except ValueError:
                    continue
            raise ValueError(f"Ungültiges Datums-/Zeitformat: {s}")

        try:
            dt = parse_datetime(start_datetime)
        except ValueError as e:
            return f"❌ {e}. Bitte Format YYYY-MM-DD HH:MM oder DD.MM.YYYY HH:MM verwenden."

        # Reminder und Deadline basierend auf UserValves berechnen
        reminder_date = dt - timedelta(days=self.user_valves.reminder_days_before)
        deadline_date = dt - timedelta(days=self.user_valves.status_deadline_days_before)

        # ISO 8601 mit Zeitzone
        tz_suffix = "+01:00"
        start_zoned = dt.strftime(f"%Y-%m-%dT%H:%M:%S{tz_suffix}")

        body = {
            "name": name,
            "description": description or "",
            "startZoned": start_zoned,
            "appointmentTemplateExtId": template,
            "creatorMail": email,
        }

        try:
            resp = requests.post(
                f"{BASE_URL}/api/v4/app/m2m/create",
                headers=_headers(self.valves.api_key),
                json=body,
                timeout=15,
            )

            if resp.status_code == 401:
                return "❌ Authentifizierung fehlgeschlagen. Bitte API-Schlüssel prüfen."
            if resp.status_code == 404:
                return (
                    f"❌ Template nicht gefunden: `{template}`\n"
                    "Bitte die korrekte Template-ID in Konzertmeister prüfen."
                )
            if resp.status_code not in [200, 201]:
                return f"❌ API-Fehler {resp.status_code}: {resp.text[:300]}"

            created = resp.json()
            p = _parse_appointment(created)

            result = f"## ✅ Termin erfolgreich erstellt!\n\n"
            result += f"**{p['name']}** (ID: {p['id']})\n\n"
            result += f"| Feld | Wert |\n|------|------|\n"
            result += f"| 🕐 Start | {p['start']} |\n"
            result += f"| 📅 Ende | {p['end']} |\n"
            result += f"| 📋 Typ | {p['typ']} |\n"
            result += f"| {p['status']} | | \n"
            result += f"| {p['published']} | |\n"
            if p["ort"] != "–":
                result += f"| 📍 Ort | {p['ort']} |\n"
            result += f"\n**Fristen (basierend auf deinen Einstellungen):**\n"
            result += f"- 🔔 Erinnerung wird gesendet: **{reminder_date.strftime('%d.%m.%Y')}** "
            result += f"({self.user_valves.reminder_days_before} Tage vorher)\n"
            result += f"- ⏰ Zu-/Absage bis: **{deadline_date.strftime('%d.%m.%Y')}** "
            result += f"({self.user_valves.status_deadline_days_before} Tage vorher)\n"
            if p["link"]:
                result += f"\n🔗 [Termin in Konzertmeister öffnen]({p['link']})\n"

            return result

        except Exception as e:
            return f"❌ Fehler beim Erstellen: {str(e)}"

    def get_appointment_types(self) -> str:
        """
        Zeigt alle verfügbaren Termintypen in Konzertmeister.
        Hilfreich um die richtigen Typ-IDs für Filterabfragen zu kennen.

        :return: Liste aller Termintypen mit IDs.
        """
        result = "## 📋 Konzertmeister Termintypen\n\n"
        result += "| ID | Typ | Verwendung |\n|----|----|----|\n"
        descriptions = {
            1: "Reguläre Probe",
            2: "Konzert, Auftritt, Veranstaltung",
            3: "Meetings, Ausflüge, etc.",
            4: "Anfrage für eine Probe",
            5: "Anfrage für einen Auftritt",
            6: "Nur zur Information, keine Zu-/Absage",
        }
        for id_, name in APPOINTMENT_TYPES.items():
            result += f"| {id_} | {name} | {descriptions.get(id_, '–')} |\n"

        result += "\n**Verwendung beim Abfragen:**\n"
        result += 'Gib die Typen als Text an, z.B.: `types="Probe,Auftritt"` oder `types="1,2"`\n'
        return result

    def get_next_appointment(
        self,
        type_filter: Optional[str] = None,
    ) -> str:
        """
        Zeigt den nächsten anstehenden Termin (oder den nächsten Termin eines bestimmten Typs).

        :param type_filter: Filter auf Termintyp, z.B. "Probe", "Auftritt" (optional).
        :return: Details zum nächsten Termin.
        """
        if not self.valves.api_key:
            return "❌ Kein API-Schlüssel konfiguriert."

        now = datetime.now()
        end = now + timedelta(weeks=26)  # 6 Monate voraus

        type_ids = []
        if type_filter:
            t_lower = type_filter.lower().strip()
            if t_lower in APPOINTMENT_TYPE_IDS:
                type_ids = [APPOINTMENT_TYPE_IDS[t_lower]]

        if not type_ids:
            type_ids = [1, 2, 3, 4, 5, 6]

        body = {
            "filterStart": _date_iso(now),
            "filterEnd": _date_iso(end),
            "typeIds": type_ids,
            "activationStatusList": ["ACTIVE"],
            "publishedStatus": "PUBLISHED",
            "tags": [],
            "sortMode": "STARTDATE",
            "dateMode": "UPCOMING",
            "page": 0,
        }

        try:
            resp = requests.post(
                f"{BASE_URL}/api/v4/org/m2m/appointments",
                headers=_headers(self.valves.api_key),
                json=body,
                timeout=15,
            )
            if resp.status_code != 200:
                return f"❌ API-Fehler {resp.status_code}"

            data = resp.json()
            if not data:
                filter_text = f" ({APPOINTMENT_TYPES.get(type_ids[0], type_filter)})" if type_filter else ""
                return f"📅 Keine kommenden Termine{filter_text} gefunden."

            next_appt = data[0]
            p = _parse_appointment(next_appt)

            type_text = f" ({type_filter})" if type_filter else ""
            result = f"## 📅 Nächster Termin{type_text}\n\n"
            result += f"**{p['name']}**\n\n"
            result += f"| | |\n|--|--|\n"
            result += f"| 🕐 Start | {p['start']} |\n"
            result += f"| 📅 Ende | {p['end']} |\n"
            result += f"| 📋 Typ | {p['typ']} |\n"
            result += f"| Status | {p['status']} |\n"
            if p["ort"] != "–":
                result += f"| 📍 Ort | {p['ort']} |\n"
            if p["beschreibung"] != "–":
                result += f"\n**📝 Beschreibung:**\n{p['beschreibung']}\n"
            if p["reminder_deadline"] != "–":
                result += f"\n🔔 **Erinnerung bis:** {p['reminder_deadline']}\n"
            if p["status_deadline"] != "–":
                result += f"⏰ **Zu-/Absage bis:** {p['status_deadline']}\n"
            if p["link"]:
                result += f"\n🔗 [In Konzertmeister öffnen]({p['link']})\n"

            return result

        except Exception as e:
            return f"❌ Fehler: {str(e)}"
