"""
title: Konzertmeister Agent
description: Verwaltet Konzertmeister-Termine, Mitglieder, Rückmeldungen und Anwesenheiten
             über die Konzertmeister M2M API v4. Unterstützt Terminerstellung aus Vorlagen
             (Musikprobe, Marschprobe, Cäcilienkonzert), Mitgliederverwaltung und Auswertungen.
             Bei jeder schreibenden Aktion wird eine Bestätigung vom User angefordert.
author: open-webui
version: 1.0.0
required_open_webui_version: 0.3.9
"""

import json
from collections import Counter
from datetime import datetime
from typing import Awaitable, Callable, Optional

import requests
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Event Emitter Helper
# ─────────────────────────────────────────────────────────────────────────────
class EventEmitter:
    def __init__(self, event_emitter: Callable[[dict], Awaitable[None]]):
        self.event_emitter = event_emitter

    async def emit_status(self, description: str, done: bool, error: bool = False):
        icon = ("❌" if error else "✅") if done else "🔎"
        await self.event_emitter(
            {
                "type": "status",
                "data": {
                    "description": f"{icon} {description}",
                    "status": "complete" if done else "in_progress",
                    "done": done,
                },
            }
        )

    async def emit_message(self, content: str):
        await self.event_emitter({"type": "message", "data": {"content": content}})


# ─────────────────────────────────────────────────────────────────────────────
# Konzertmeister API Client
# ─────────────────────────────────────────────────────────────────────────────
class KonzertmeisterClient:

    APPOINTMENT_TYPE_LABELS = {
        1: "Probe",
        2: "Auftritt",
        3: "Sonstiges",
        4: "Probenanfrage",
        5: "Auftrittsanfrage",
        6: "Information",
    }

    def __init__(self, api_key: str, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "X-KM-ORG-API-KEY": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # ── HTTP Helpers ──────────────────────────────────────────────────────────
    def _get(self, path: str, params: dict = None):
        resp = requests.get(
            f"{self.base_url}{path}",
            params=params or {},
            headers=self.headers,
        )
        if not resp.ok:
            raise Exception(f"GET {path} → {resp.status_code}: {resp.text[:400]}")
        return resp.json()

    def _post(self, path: str, payload: dict):
        resp = requests.post(
            f"{self.base_url}{path}",
            headers=self.headers,
            json=payload,
        )
        if not resp.ok:
            raise Exception(f"POST {path} → {resp.status_code}: {resp.text[:400]}")
        if not resp.content or resp.status_code == 204:
            return {}
        return resp.json()

    # ── Members ───────────────────────────────────────────────────────────────
    def get_members(self) -> list:
        """GET /api/v4/org/m2m/members"""
        return self._get("/api/v4/org/m2m/members")

    def add_member(
        self,
        mail: str,
        firstname: str = "",
        lastname: str = "",
        mobile_phone: str = "",
        properties: list = None,
    ) -> dict:
        """POST /api/v4/org/m2m/addmember"""
        payload = {"mail": mail}
        if firstname:
            payload["firstname"] = firstname
        if lastname:
            payload["lastname"] = lastname
        if mobile_phone:
            payload["mobilePhone"] = mobile_phone
        if properties:
            payload["properties"] = properties
        return self._post("/api/v4/org/m2m/addmember", payload)

    def update_member(
        self,
        mail: str,
        firstname: str = "",
        lastname: str = "",
        mobile_phone: str = "",
        properties: list = None,
    ) -> dict:
        """POST /api/v4/org/m2m/updatemember"""
        payload = {"mail": mail}
        if firstname:
            payload["firstname"] = firstname
        if lastname:
            payload["lastname"] = lastname
        if mobile_phone:
            payload["mobilePhone"] = mobile_phone
        if properties:
            payload["properties"] = properties
        return self._post("/api/v4/org/m2m/updatemember", payload)

    # ── Appointments ──────────────────────────────────────────────────────────
    def get_appointments(
        self,
        type_ids: list = None,
        filter_start: str = "",
        filter_end: str = "",
        activation_status: list = None,
        published_status: str = "ALL",
        tags: list = None,
        sort_mode: str = "STARTDATE",
        date_mode: str = "UPCOMING",
        page: int = 0,
    ) -> list:
        """POST /api/v4/org/m2m/appointments"""
        payload = {
            "typeIds": type_ids or [1, 2, 3, 4, 5, 6],
            "sortMode": sort_mode,
            "dateMode": date_mode,
            "publishedStatus": published_status,
            "page": page,
        }
        if filter_start:
            payload["filterStart"] = filter_start
        if filter_end:
            payload["filterEnd"] = filter_end
        if activation_status:
            payload["activationStatusList"] = activation_status
        if tags:
            payload["tags"] = tags
        return self._post("/api/v4/org/m2m/appointments", payload)

    def create_appointment_from_template(
        self,
        template_ext_id: str,
        creator_mail: str,
        start_zoned: str,
        name: str = "",
        description: str = "",
    ) -> dict:
        """POST /api/v4/app/m2m/create"""
        payload = {
            "appointmentTemplateExtId": template_ext_id,
            "creatorMail": creator_mail,
            "startZoned": start_zoned,
        }
        if name:
            payload["name"] = name
        if description:
            payload["description"] = description
        return self._post("/api/v4/app/m2m/create", payload)

    # ── Replies & Attendances ─────────────────────────────────────────────────
    def get_replies(self, app_id: int) -> list:
        """GET /api/v4/att/m2m/{appId}"""
        return self._get(f"/api/v4/att/m2m/{app_id}")

    def get_attendances(self, app_id: int) -> list:
        """GET /api/v2/attreal/m2m/{appId}"""
        return self._get(f"/api/v2/attreal/m2m/{app_id}")


# ─────────────────────────────────────────────────────────────────────────────
# Open WebUI Tools Class — jede public Methode = eigenes Tool
# ─────────────────────────────────────────────────────────────────────────────
class Tools:
    class Valves(BaseModel):
        base_url: str = Field(
            "https://rest.konzertmeister.app",
            description="Base URL der Konzertmeister API",
        )
        api_key: str = Field(
            "",
            description="Konzertmeister M2M API Key – wird als Query-Parameter ?apiKey=... übergeben. Zu finden im Konzertmeister Webclient unter Einstellungen > Integrationen.",
        )
        creator_mail: str = Field(
            "",
            description="E-Mail-Adresse des Standard-Erstellers für neue Termine. Der Account muss Berechtigung zur Terminerstellung besitzen.",
        )
        template_id_musikprobe: str = Field(
            "",
            description="External Template ID für Musikprobe. Zu finden in den Vorlagen-Details im Konzertmeister Webclient.",
        )
        template_id_marschprobe: str = Field(
            "",
            description="External Template ID für Marschprobe. Zu finden in den Vorlagen-Details im Konzertmeister Webclient.",
        )
        template_id_caecilienkonzert: str = Field(
            "",
            description="External Template ID für Cäcilienkonzert. Zu finden in den Vorlagen-Details im Konzertmeister Webclient.",
        )

    def __init__(self):
        self.valves = self.Valves()

    def _get_client(self) -> KonzertmeisterClient:
        if not self.valves.api_key:
            raise Exception(
                "API Key ist nicht konfiguriert. Bitte in den globalen Valves eintragen."
            )
        return KonzertmeisterClient(self.valves.api_key, self.valves.base_url)

    @staticmethod
    def _fmt_dt(dt_str: str) -> str:
        """Formatiert ISO-Datetime zu lesbarem DE-Format."""
        if not dt_str:
            return "–"
        try:
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            return dt.strftime("%d.%m.%Y %H:%M")
        except Exception:
            return dt_str

    async def _confirm_action(
        self,
        emitter,  # EventEmitter – kein Type Hint, sonst Pydantic-Schema-Fehler
        event_call,
        title: str,
        preview_lines: list,
    ) -> bool:
        """
        Zeigt eine Vorschau und wartet auf Bestätigung. Gibt True zurück wenn bestätigt.
        Falls __event_call__ nicht verfügbar: Vorschau emittieren und direkt fortfahren.
        """
        if not event_call:
            await emitter.emit_message(
                f"**Vorschau: {title}**\n" + "\n".join(preview_lines)
            )
            return True

        result = await event_call({
            "type": "confirmation",
            "data": {
                "title": f"Bitte bestätigen: {title}",
                "message": "\n".join(preview_lines),
            },
        })

        if result:
            return True

        await emitter.emit_status("Aktion abgebrochen", done=True, error=False)
        await emitter.emit_message(f"Aktion **{title}** wurde abgebrochen.")
        return False

    # ── Tool 1: get_members ───────────────────────────────────────────────────
    async def get_members(
        self,
        __event_emitter__: Callable[[dict], Awaitable[None]] = None,
    ) -> str:
        """
        Lädt alle Mitglieder der Vereinigung mit ihren Stammdaten und Datenfeldern.
        Liefert Name, E-Mail, Telefon, Adresse und alle konfigurierten Eigenschaften.
        """
        emitter = EventEmitter(__event_emitter__)
        await emitter.emit_status("Lade Mitglieder ...", done=False)
        try:
            client = self._get_client()
            members = client.get_members()
            await emitter.emit_status(f"{len(members)} Mitglieder geladen", done=True)
            lines = [
                f"- **{m.get('firstname', '')} {m.get('lastname', '')}** "
                f"({m.get('mail', '')}) "
                f"| Tel: {m.get('mobilePhone', '') or '–'}"
                for m in members
            ]
            await emitter.emit_message(
                f"**{len(members)} Mitglieder:**\n" + "\n".join(lines)
            )
            return json.dumps(members, ensure_ascii=False, indent=2)
        except Exception as e:
            await emitter.emit_status(f"Fehler: {e}", done=True, error=True)
            return f"Fehler beim Laden der Mitglieder: {e}"

    # ── Tool 2: add_member ────────────────────────────────────────────────────
    async def add_member(
        self,
        mail: str,
        firstname: str = "",
        lastname: str = "",
        mobile_phone: str = "",
        __event_emitter__: Callable[[dict], Awaitable[None]] = None,
        __event_call__: Callable[[dict], Awaitable[dict]] = None,
    ) -> str:
        """
        Fügt eine Person zur Vereinigung hinzu. Falls kein Konto mit dieser E-Mail existiert,
        wird eine Einladung verschickt.
        Vor dem Hinzufügen wird eine Vorschau angezeigt und eine Bestätigung angefordert.

        :param mail: E-Mail-Adresse der Person (Pflichtfeld).
        :param firstname: Vorname.
        :param lastname: Nachname.
        :param mobile_phone: Mobiltelefonnummer.
        """
        emitter = EventEmitter(__event_emitter__)
        if not mail:
            return "Fehler: E-Mail-Adresse ist ein Pflichtfeld."

        preview = [
            f"| Feld         | Wert |",
            f"|--------------|------|",
            f"| **E-Mail**   | {mail} |",
            f"| **Vorname**  | {firstname or '–'} |",
            f"| **Nachname** | {lastname or '–'} |",
            f"| **Telefon**  | {mobile_phone or '–'} |",
        ]
        confirmed = await self._confirm_action(
            emitter, __event_call__, "Mitglied hinzufügen", preview
        )
        if not confirmed:
            return json.dumps({"aborted": True, "reason": "User hat abgebrochen"})

        await emitter.emit_status(f"Füge Mitglied {mail} hinzu ...", done=False)
        try:
            client = self._get_client()
            client.add_member(mail, firstname, lastname, mobile_phone)
            await emitter.emit_status(f"Mitglied {mail} hinzugefügt", done=True)
            await emitter.emit_message(
                f"Mitglied **{firstname} {lastname}** ({mail}) wurde hinzugefügt."
            )
            return json.dumps({"success": True, "mail": mail})
        except Exception as e:
            await emitter.emit_status(f"Fehler: {e}", done=True, error=True)
            return f"Fehler beim Hinzufügen des Mitglieds: {e}"

    # ── Tool 3: update_member ─────────────────────────────────────────────────
    async def update_member(
        self,
        mail: str,
        firstname: str = "",
        lastname: str = "",
        mobile_phone: str = "",
        __event_emitter__: Callable[[dict], Awaitable[None]] = None,
        __event_call__: Callable[[dict], Awaitable[dict]] = None,
    ) -> str:
        """
        Aktualisiert die Daten eines bestehenden Mitglieds anhand der E-Mail-Adresse.
        Bei nicht registrierten Konten können auch Vor- und Nachname geändert werden.
        Vor der Änderung wird eine Vorschau angezeigt und eine Bestätigung angefordert.

        :param mail: E-Mail-Adresse des Mitglieds (Pflichtfeld zur Identifikation).
        :param firstname: Neuer Vorname (nur bei nicht registrierten Konten wirksam).
        :param lastname: Neuer Nachname (nur bei nicht registrierten Konten wirksam).
        :param mobile_phone: Neue Mobiltelefonnummer.
        """
        emitter = EventEmitter(__event_emitter__)
        if not mail:
            return "Fehler: E-Mail-Adresse ist ein Pflichtfeld."

        updates = []
        if firstname:
            updates.append(f"Vorname → {firstname}")
        if lastname:
            updates.append(f"Nachname → {lastname}")
        if mobile_phone:
            updates.append(f"Telefon → {mobile_phone}")
        if not updates:
            return "Fehler: Mindestens eine Änderung (firstname, lastname oder mobile_phone) muss angegeben werden."

        preview = [
            f"**Mitglied:** {mail}",
            f"**Änderungen:**",
        ] + [f"- {u}" for u in updates]
        confirmed = await self._confirm_action(
            emitter, __event_call__, f"Mitglied aktualisieren: {mail}", preview
        )
        if not confirmed:
            return json.dumps({"aborted": True, "reason": "User hat abgebrochen"})

        await emitter.emit_status(f"Aktualisiere Mitglied {mail} ...", done=False)
        try:
            client = self._get_client()
            client.update_member(mail, firstname, lastname, mobile_phone)
            await emitter.emit_status(f"Mitglied {mail} aktualisiert", done=True)
            await emitter.emit_message(
                f"Mitglied **{mail}** aktualisiert: {', '.join(updates)}"
            )
            return json.dumps({"success": True, "mail": mail, "updates": updates})
        except Exception as e:
            await emitter.emit_status(f"Fehler: {e}", done=True, error=True)
            return f"Fehler beim Aktualisieren des Mitglieds: {e}"

    # ── Tool 4: get_appointments ──────────────────────────────────────────────
    async def get_appointments(
        self,
        filter_start: str = "",
        filter_end: str = "",
        type_ids: str = "",
        published_status: str = "ALL",
        date_mode: str = "UPCOMING",
        page: int = 0,
        __event_emitter__: Callable[[dict], Awaitable[None]] = None,
    ) -> str:
        """
        Lädt Termine der Vereinigung mit optionalen Filtern.

        :param filter_start: Startdatum ISO-Format z.B. '2025-01-01T00:00:00+01:00'. Leer = kein Filter.
        :param filter_end: Enddatum ISO-Format z.B. '2025-12-31T23:59:59+01:00'. Leer = kein Filter.
        :param type_ids: Kommagetrennte Typ-IDs: 1=Probe, 2=Auftritt, 3=Sonstiges,
                         4=Probenanfrage, 5=Auftrittsanfrage, 6=Information. Leer = alle.
        :param published_status: ALL, PUBLISHED oder UNPUBLISHED. Standard: ALL.
        :param date_mode: UPCOMING (ab jetzt) oder FROM_DATE (ab filterStart). Standard: UPCOMING.
        :param page: Seitenzahl für Pagination (0-basiert). Standard: 0.
        """
        emitter = EventEmitter(__event_emitter__)
        await emitter.emit_status("Lade Termine ...", done=False)
        try:
            client = self._get_client()
            parsed_type_ids = (
                [int(x.strip()) for x in type_ids.split(",") if x.strip().isdigit()]
                if type_ids
                else [1, 2, 3, 4, 5, 6]
            )
            appointments = client.get_appointments(
                type_ids=parsed_type_ids,
                filter_start=filter_start,
                filter_end=filter_end,
                published_status=published_status,
                date_mode=date_mode,
                page=page,
            )
            await emitter.emit_status(f"{len(appointments)} Termine geladen", done=True)

            type_labels = KonzertmeisterClient.APPOINTMENT_TYPE_LABELS
            lines = [
                f"- **[ID {a.get('id')}]** {self._fmt_dt(a.get('start', ''))} – "
                f"**{a.get('name', '(kein Name)')}** "
                f"[{type_labels.get(a.get('typId', 0), '?')}] "
                f"| {'aktiv' if a.get('active') else 'inaktiv'} "
                f"| {'veroeffentlicht' if a.get('published') else 'unveröffentlicht'}"
                + (f" | {a['location']['name']}" if a.get("location") else "")
                for a in appointments
            ]
            await emitter.emit_message(
                f"**{len(appointments)} Termine:**\n" + "\n".join(lines)
            )
            return json.dumps(appointments, ensure_ascii=False, indent=2)
        except Exception as e:
            await emitter.emit_status(f"Fehler: {e}", done=True, error=True)
            return f"Fehler beim Laden der Termine: {e}"

    # ── Tool 5: create_appointment ────────────────────────────────────────────
    async def create_appointment(
        self,
        template_ext_id: str,
        start_zoned: str,
        creator_mail: str = "",
        name: str = "",
        description: str = "",
        __event_emitter__: Callable[[dict], Awaitable[None]] = None,
        __event_call__: Callable[[dict], Awaitable[dict]] = None,
    ) -> str:
        """
        Erstellt einen neuen Termin basierend auf einer beliebigen Konzertmeister-Vorlage.
        Für die vordefinierten Typen (Musikprobe, Marschprobe, Cäcilienkonzert) die
        spezialisierten Tools verwenden.
        Vor der Erstellung wird eine Vorschau angezeigt und eine Bestätigung angefordert.

        :param template_ext_id: External ID der Vorlage (aus Konzertmeister Webclient > Vorlagen > Details).
        :param start_zoned: Startdatum mit Zeitzone, z.B. '2025-06-15T19:00:00+02:00'.
        :param creator_mail: E-Mail des Erstellers. Leer = globale Valve-Einstellung.
        :param name: Optionaler Name (überschreibt den Vorlagen-Namen).
        :param description: Optionale Beschreibung des Termins.
        """
        emitter = EventEmitter(__event_emitter__)
        effective_creator = creator_mail or self.valves.creator_mail
        if not effective_creator:
            return "Fehler: creator_mail nicht angegeben und kein Standard in den Valves konfiguriert."
        if not template_ext_id:
            return "Fehler: template_ext_id ist ein Pflichtfeld."
        if not start_zoned:
            return "Fehler: start_zoned ist ein Pflichtfeld."

        desc_preview = (description[:150] + "...") if len(description) > 150 else description
        preview = [
            f"| Feld             | Wert |",
            f"|------------------|------|",
            f"| **Vorlage ID**   | {template_ext_id} |",
            f"| **Start**        | {start_zoned} |",
            f"| **Ersteller**    | {effective_creator} |",
            f"| **Name**         | {name or '(aus Vorlage)'} |",
            f"| **Beschreibung** | {desc_preview or '–'} |",
        ]
        confirmed = await self._confirm_action(
            emitter, __event_call__, "Termin erstellen", preview
        )
        if not confirmed:
            return json.dumps({"aborted": True, "reason": "User hat abgebrochen"})

        await emitter.emit_status("Erstelle Termin ...", done=False)
        try:
            client = self._get_client()
            result = client.create_appointment_from_template(
                template_ext_id=template_ext_id,
                creator_mail=effective_creator,
                start_zoned=start_zoned,
                name=name,
                description=description,
            )
            apt_name = result.get("name", "")
            apt_start = self._fmt_dt(result.get("start", ""))
            apt_id = result.get("id", "?")
            await emitter.emit_status(f"Termin '{apt_name}' erstellt (ID {apt_id})", done=True)
            await emitter.emit_message(
                f"Termin **{apt_name}** am {apt_start} erstellt (ID: {apt_id})"
            )
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            await emitter.emit_status(f"Fehler: {e}", done=True, error=True)
            return f"Fehler beim Erstellen des Termins: {e}"

    # ── Tool 6: create_musikprobe ─────────────────────────────────────────────
    async def create_musikprobe(
        self,
        start_zoned: str,
        name: str = "",
        description: str = "",
        creator_mail: str = "",
        __event_emitter__: Callable[[dict], Awaitable[None]] = None,
        __event_call__: Callable[[dict], Awaitable[dict]] = None,
    ) -> str:
        """
        Erstellt eine neue Musikprobe basierend auf der konfigurierten Vorlage (template_id_musikprobe).
        Vor der Erstellung wird eine Vorschau angezeigt und eine Bestätigung angefordert.

        :param start_zoned: Startdatum mit Zeitzone, z.B. '2025-06-15T19:00:00+02:00'.
        :param name: Optionaler Name der Probe (überschreibt Vorlagen-Namen).
        :param description: Optionale Beschreibung / Programm der Probe.
        :param creator_mail: E-Mail des Erstellers. Leer = globale Valve-Einstellung.
        """
        if not self.valves.template_id_musikprobe:
            return "Fehler: template_id_musikprobe ist nicht in den globalen Valves konfiguriert."
        return await self.create_appointment(
            template_ext_id=self.valves.template_id_musikprobe,
            start_zoned=start_zoned,
            creator_mail=creator_mail,
            name=name,
            description=description,
            __event_emitter__=__event_emitter__,
            __event_call__=__event_call__,
        )

    # ── Tool 7: create_marschprobe ────────────────────────────────────────────
    async def create_marschprobe(
        self,
        start_zoned: str,
        name: str = "",
        description: str = "",
        creator_mail: str = "",
        __event_emitter__: Callable[[dict], Awaitable[None]] = None,
        __event_call__: Callable[[dict], Awaitable[dict]] = None,
    ) -> str:
        """
        Erstellt eine neue Marschprobe basierend auf der konfigurierten Vorlage (template_id_marschprobe).
        Vor der Erstellung wird eine Vorschau angezeigt und eine Bestätigung angefordert.

        :param start_zoned: Startdatum mit Zeitzone, z.B. '2025-06-15T14:00:00+02:00'.
        :param name: Optionaler Name der Probe (überschreibt Vorlagen-Namen).
        :param description: Optionale Beschreibung / Programm der Probe.
        :param creator_mail: E-Mail des Erstellers. Leer = globale Valve-Einstellung.
        """
        if not self.valves.template_id_marschprobe:
            return "Fehler: template_id_marschprobe ist nicht in den globalen Valves konfiguriert."
        return await self.create_appointment(
            template_ext_id=self.valves.template_id_marschprobe,
            start_zoned=start_zoned,
            creator_mail=creator_mail,
            name=name,
            description=description,
            __event_emitter__=__event_emitter__,
            __event_call__=__event_call__,
        )

    # ── Tool 8: create_caecilienkonzert ───────────────────────────────────────
    async def create_caecilienkonzert(
        self,
        start_zoned: str,
        name: str = "",
        description: str = "",
        creator_mail: str = "",
        __event_emitter__: Callable[[dict], Awaitable[None]] = None,
        __event_call__: Callable[[dict], Awaitable[dict]] = None,
    ) -> str:
        """
        Erstellt ein neues Cäcilienkonzert basierend auf der konfigurierten Vorlage (template_id_caecilienkonzert).
        Vor der Erstellung wird eine Vorschau angezeigt und eine Bestätigung angefordert.

        :param start_zoned: Startdatum mit Zeitzone, z.B. '2025-11-22T19:30:00+01:00'.
        :param name: Optionaler Name des Konzerts (überschreibt Vorlagen-Namen).
        :param description: Optionale Beschreibung / Programm des Konzerts.
        :param creator_mail: E-Mail des Erstellers. Leer = globale Valve-Einstellung.
        """
        if not self.valves.template_id_caecilienkonzert:
            return "Fehler: template_id_caecilienkonzert ist nicht in den globalen Valves konfiguriert."
        return await self.create_appointment(
            template_ext_id=self.valves.template_id_caecilienkonzert,
            start_zoned=start_zoned,
            creator_mail=creator_mail,
            name=name,
            description=description,
            __event_emitter__=__event_emitter__,
            __event_call__=__event_call__,
        )

    # ── Tool 9: get_replies ───────────────────────────────────────────────────
    async def get_replies(
        self,
        appointment_id: int,
        __event_emitter__: Callable[[dict], Awaitable[None]] = None,
    ) -> str:
        """
        Lädt alle Rückmeldungen (Zu-/Absagen) zu einem Termin.
        Zeigt Name, E-Mail, Antwort (POSITIVE / NEGATIVE / MAYBE / UNANSWERED) und Kommentar.
        Liefert auch eine Zusammenfassung der Verteilung.

        :param appointment_id: Numerische ID des Termins (aus get_appointments).
        """
        emitter = EventEmitter(__event_emitter__)
        await emitter.emit_status(
            f"Lade Rückmeldungen für Termin {appointment_id} ...", done=False
        )
        try:
            client = self._get_client()
            replies = client.get_replies(appointment_id)
            await emitter.emit_status(f"{len(replies)} Rückmeldungen geladen", done=True)

            icons = {"POSITIVE": "Ja", "NEGATIVE": "Nein", "MAYBE": "Vielleicht", "UNANSWERED": "Ausstehend"}
            counts = Counter(r.get("reply", "UNANSWERED") for r in replies)
            summary = " | ".join(
                f"{icons.get(k, k)}: {v}" for k, v in counts.most_common()
            )
            lines = [
                f"- [{icons.get(r.get('reply', 'UNANSWERED'), '?')}] "
                f"**{r.get('kmUserFirstName', '')} {r.get('kmUserLastName', '')}** "
                f"({r.get('kmUserEmail', '')})"
                + (f" – {r['replyComment']}" if r.get("replyComment") else "")
                for r in replies
            ]
            await emitter.emit_message(
                f"**Rückmeldungen Termin {appointment_id}** ({summary}):\n\n"
                + "\n".join(lines)
            )
            return json.dumps(replies, ensure_ascii=False, indent=2)
        except Exception as e:
            await emitter.emit_status(f"Fehler: {e}", done=True, error=True)
            return f"Fehler beim Laden der Rückmeldungen: {e}"

    # ── Tool 10: get_attendances ──────────────────────────────────────────────
    async def get_attendances(
        self,
        appointment_id: int,
        __event_emitter__: Callable[[dict], Awaitable[None]] = None,
    ) -> str:
        """
        Lädt die dokumentierten tatsächlichen Anwesenheiten eines Termins
        (nach der Veranstaltung erfasst, nicht die Rückmeldungen im Vorfeld).
        Zeigt Anwesende und Abwesende mit optionalen Kommentaren.

        :param appointment_id: Numerische ID des Termins (aus get_appointments).
        """
        emitter = EventEmitter(__event_emitter__)
        await emitter.emit_status(
            f"Lade Anwesenheiten für Termin {appointment_id} ...", done=False
        )
        try:
            client = self._get_client()
            attendances = client.get_attendances(appointment_id)
            await emitter.emit_status(f"{len(attendances)} Einträge geladen", done=True)

            present = [a for a in attendances if a.get("attending")]
            absent = [a for a in attendances if not a.get("attending")]

            def fmt_person(a: dict) -> str:
                name = f"**{a.get('kmUserFirstName', '')} {a.get('kmUserLastName', '')}** ({a.get('kmUserEmail', '')})"
                return name + (f" – {a['comment']}" if a.get("comment") else "")

            lines_present = [f"  - {fmt_person(a)}" for a in present] or ["  – keine"]
            lines_absent = [f"  - {fmt_person(a)}" for a in absent] or ["  – keine"]

            await emitter.emit_message(
                f"**Anwesenheiten Termin {appointment_id}:**\n\n"
                f"**Anwesend ({len(present)}):**\n" + "\n".join(lines_present) +
                f"\n\n**Abwesend ({len(absent)}):**\n" + "\n".join(lines_absent)
            )
            return json.dumps(attendances, ensure_ascii=False, indent=2)
        except Exception as e:
            await emitter.emit_status(f"Fehler: {e}", done=True, error=True)
            return f"Fehler beim Laden der Anwesenheiten: {e}"
