from fastapi import APIRouter, Depends, HTTPException, Response, status

from ..auth import require_admin
from ..database import execute, fetch_all, fetch_one
from ..models import CREATE_EVENT_QUERY, EVENT_FIELDS, UPDATE_EVENT_QUERY
from ..schemas import EventCreate, EventOut, EventUpdate

router = APIRouter(prefix="/admin", tags=["admin"])


def row_to_event(row) -> EventOut:
    event = dict(row)
    event["date"] = str(event["date"])
    event["start_time"] = str(event["start_time"])[:5]
    event["end_time"] = str(event["end_time"])[:5]
    event["created_at"] = str(event["created_at"])
    event["updated_at"] = str(event["updated_at"])
    return EventOut(**event)


@router.get("/events", response_model=list[EventOut])
def list_admin_events(_: dict = Depends(require_admin)) -> list[EventOut]:
    rows = fetch_all(f"SELECT {EVENT_FIELDS} FROM events ORDER BY date ASC, start_time ASC")
    return [row_to_event(row) for row in rows]


@router.get("/events/{event_id}", response_model=EventOut)
def get_event(event_id: int, _: dict = Depends(require_admin)) -> EventOut:
    row = fetch_one(f"SELECT {EVENT_FIELDS} FROM events WHERE id = ?", (event_id,))
    if not row:
        raise HTTPException(404, "Evento não encontrado.")
    return row_to_event(row)


@router.post("/events", response_model=EventOut, status_code=status.HTTP_201_CREATED)
def create_event(payload: EventCreate, _: dict = Depends(require_admin)) -> EventOut:
    event_id = execute(
        CREATE_EVENT_QUERY,
        (
            payload.title,
            payload.description,
            payload.date,
            payload.start_time,
            payload.end_time,
            payload.location,
            payload.image_url,
        ),
    )
    row = fetch_one(f"SELECT {EVENT_FIELDS} FROM events WHERE id = ?", (event_id,))
    return row_to_event(row)


@router.put("/events/{event_id}", response_model=EventOut)
def update_event(event_id: int, payload: EventUpdate, _: dict = Depends(require_admin)) -> EventOut:
    exists = fetch_one("SELECT id FROM events WHERE id = ?", (event_id,))
    if not exists:
        raise HTTPException(404, "Evento não encontrado.")

    execute(
        UPDATE_EVENT_QUERY,
        (
            payload.title,
            payload.description,
            payload.date,
            payload.start_time,
            payload.end_time,
            payload.location,
            payload.image_url,
            event_id,
        ),
    )
    row = fetch_one(f"SELECT {EVENT_FIELDS} FROM events WHERE id = ?", (event_id,))
    return row_to_event(row)


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(event_id: int, _: dict = Depends(require_admin)) -> Response:
    execute("DELETE FROM events WHERE id = ?", (event_id,))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
