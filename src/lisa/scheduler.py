import aiohttp
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List
import logging
import random
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
random.seed(42)


@dataclass
class TimeSlots:
    date: datetime
    slots: List[str]


class NoAvailableTimeSlotsError(Exception):
    pass


class TimeSlotFetcher:
    def __init__(self):
        pass  # No instance attributes

    async def fetch(self, date: datetime) -> TimeSlots:
        max_attempts = 5
        attempts = 0

        while attempts < max_attempts:
            attempts += 1
            end_date = date + timedelta(days=1)
            url = f"{os.environ["AGENDA_BASE_URL"]}/booking/available-slots"
            params = {
                "start": date.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d"),
            }
            logger.info(f"Attempt {attempts}: Fetching available slots for date {date.strftime('%Y-%m-%d')}")
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params) as response:
                        if response.status != 200:
                            text = await response.text()
                            error_message = f"Error while calling API: {text}"
                            logger.error(error_message)
                            raise EnvironmentError(error_message)

                        json_response = await response.json()
                        result = json_response.get("data", [])
                        if not result:
                            # No available slots, increment the date and try again
                            logger.info(f"No available slots found for date {date.strftime('%Y-%m-%d')}. Trying next day.")
                            date += timedelta(days=1)
                        else:
                            available_date = datetime.strptime(result[0]["date"], "%Y-%m-%d")
                            slots = result[0].get("availableSlots", [])
                            logger.info(f"Found available slots for date {available_date.strftime('%Y-%m-%d')}")
                            return TimeSlots(date=available_date, slots=slots)
            except aiohttp.ClientError as e:
                # Handle HTTP client exceptions (e.g., network errors)
                logger.error(f"HTTP request failed: {e}")
                raise e
            except Exception as e:
                # Handle any other exceptions that should not be retried
                logger.error(f"An unexpected error occurred: {e}")
                raise e

        # If we reach this point, no slots were found after max_attempts
        error_message = f"No available slots found in {max_attempts} attempts starting from date {date.strftime('%Y-%m-%d')}."

        logger.error(error_message)
        raise NoAvailableTimeSlotsError(error_message)
