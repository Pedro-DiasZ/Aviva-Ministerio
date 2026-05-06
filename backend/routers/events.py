from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ..database import fetch_all, fetch_one
from ..models import EVENT_FIELDS
from ..schemas import EventOut

router = APIRouter(prefix="/events", tags=["events"])
SAO_PAULO_TZ = timezone(timedelta(hours=-3))


def row_to_event(row) -> EventOut:
    event = dict(row)
    event["date"] = str(event["date"])
    event["start_time"] = str(event["start_time"])[:5]
    event["end_time"] = str(event["end_time"])[:5]
    event["created_at"] = str(event["created_at"])
    event["updated_at"] = str(event["updated_at"])
    return EventOut(**event)


@router.get("", response_model=list[EventOut])
def list_events() -> list[EventOut]:
    rows = fetch_all(f"SELECT {EVENT_FIELDS} FROM events ORDER BY date ASC, start_time ASC")
    return [row_to_event(row) for row in rows]


def ics_datetime(date_value: str, time_value: str) -> str:
    local_dt = datetime.fromisoformat(f"{date_value}T{time_value}:00").replace(tzinfo=SAO_PAULO_TZ)
    return local_dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def escape_ics(text: str) -> str:
    return text.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")


@router.get("/{event_id}/ics")
def event_calendar(event_id: int) -> Response:
    row = fetch_one(f"SELECT {EVENT_FIELDS} FROM events WHERE id = ?", (event_id,))
    if not row:
        raise HTTPException(404, "Evento não encontrado.")

    event = dict(row)
    uid = f"aviva-event-{event['id']}@aviva.local"
    now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    ics = "\r\n".join(
        [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Ministerio Aviva//Eventos//PT-BR",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now}",
            f"DTSTART:{ics_datetime(event['date'], event['start_time'])}",
            f"DTEND:{ics_datetime(event['date'], event['end_time'])}",
            f"SUMMARY:{escape_ics(event['title'])}",
            f"DESCRIPTION:{escape_ics(event['description'])}",
            f"LOCATION:{escape_ics(event['location'])}",
            "END:VEVENT",
            "END:VCALENDAR",
            "",
        ]
    )
    filename = f"aviva-evento-{event_id}.ics"
    return Response(
        content=ics,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
