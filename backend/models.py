CREATE_EVENT_QUERY = """
INSERT INTO events (title, description, date, start_time, end_time, location, image_url)
VALUES (?, ?, ?, ?, ?, ?, ?)
"""

UPDATE_EVENT_QUERY = """
UPDATE events
SET title = ?,
    description = ?,
    date = ?,
    start_time = ?,
    end_time = ?,
    location = ?,
    image_url = ?,
    updated_at = CURRENT_TIMESTAMP
WHERE id = ?
"""

EVENT_FIELDS = """
id, title, description, date, start_time, end_time, location, image_url, created_at, updated_at
"""
