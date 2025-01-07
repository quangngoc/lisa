import random
from fastapi import FastAPI, Query
from typing import List, Optional
from datetime import datetime, date, timedelta, time

app = FastAPI(title="Fake agenda API")


@app.get("/booking/available-slots")
def available_slots(start: Optional[str] = Query(None), end: Optional[str] = Query(None)):
    # Define date format
    date_format = "%Y-%m-%d"

    # Get today's date
    today = date.today()

    # Parse 'start' parameter
    if start:
        try:
            start_date = datetime.strptime(start, date_format).date()
        except ValueError:
            return {"error": "Invalid start date format. Use YYYY-MM-DD."}
    else:
        start_date = today

    # Parse 'end' parameter
    if end:
        try:
            end_date = datetime.strptime(end, date_format).date()
        except ValueError:
            return {"error": "Invalid end date format. Use YYYY-MM-DD."}
    else:
        # If 'end' is not set, set it based on 'start'
        end_date = start_date + timedelta(days=7)

    # Ensure start_date is before or equal to end_date
    if start_date > end_date:
        return {"error": "'start' date must be before 'end' date."}

    # Generate list of dates from start_date to end_date inclusive
    delta = end_date - start_date

    available_slots_list = []

    for i in range(delta.days):
        day = start_date + timedelta(days=i)
        if day.weekday() >= 5:
            # Skip weekends (Saturday=5, Sunday=6)
            continue
        date_str = day.strftime("%Y-%m-%d")
        # Generate time slots from 09:00 to 17:45 every 15 minutes
        slots = []
        start_time = time(9, 0)
        end_time = time(18, 0)
        slot_duration = timedelta(minutes=15)
        current_time = datetime.combine(day, start_time)
        end_datetime = datetime.combine(day, end_time)

        while current_time < end_datetime:
            slots.append(current_time.strftime("%H:%M"))
            current_time += slot_duration

        # Random 5 slots
        selected_indices = sorted(random.sample(range(len(slots)), min(5, len(slots))))
        selected_slots = [slots[i] for i in selected_indices]
        available_slots_list.append({"date": date_str, "availableSlots": selected_slots})

    return {"data": available_slots_list}
