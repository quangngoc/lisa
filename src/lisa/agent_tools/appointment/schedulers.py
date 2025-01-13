import sys

from lisa.agent_tools.appointment.recognizers import recognize_date_time
from lisa.agent_tools.appointment.time_slot_fetcher import TimeSlotFetcher


async def get_available_time_slots(date_string: str) -> str:
    """Retrieve available date and time slots for appointment booking.

    Args:
        date_string (str): Date string for appointment booking. You can use:\n- Specific date (preferred)\n- Relative terms (e.g., 'tomorrow', 'next monday')

    Returns:
        str: _description_
    """
    date = await recognize_date_time(date_string)
    if not date:
        return f"Impossible de reconnaître la date '{date_string}'"
    fetcher = TimeSlotFetcher()
    slots = await fetcher.fetch(date)
    if sys.platform.startswith("win"):
        date_str = slots.date.strftime("%A %#d %B")
    else:
        date_str = slots.date.strftime("%A %-d %B")
    return f"Les créneaux disponibles du {date_str}: {str(slots.slots)}"
