import aiohttp
import os
from datetime import datetime
from datatypes_timex_expression import TimexResolver


async def recognize_date_time(text: str, culture="fr-fr") -> datetime:
    url = f"{os.environ["RECOGNIZERS_BASE_URL"]}/api/recognizer/datetime"
    headers = {"Content-Type": "application/json"}
    payload = [text]
    async with aiohttp.ClientSession() as session:
        async with session.post(url, params={"culture": culture}, json=payload, headers=headers) as response:
            if response.status == 200:
                recognized_dates = await response.json()
                if recognized_dates[0]:
                    date_format = "%Y-%m-%dT%H:%M:%S"
                    return datetime.strptime(recognized_dates[0], date_format)
                else:
                    date = await recognize_date_range(text, culture)
                    return date
            else:
                error_text = await response.text()
                print(f"Request failed with status {response.status}: {error_text}")


async def recognize_date_range(text: str, culture="fr-fr") -> datetime:
    url = f"{os.environ["RECOGNIZERS_BASE_URL"]}/api/recognizer/daterange"
    headers = {"Content-Type": "application/json"}
    payload = [text]
    async with aiohttp.ClientSession() as session:
        async with session.post(url, params={"culture": culture}, json=payload, headers=headers) as response:
            if response.status == 200:
                recognized_timex = await response.json()
                if recognized_timex:
                    time_resolutions = TimexResolver.resolve(recognized_timex, datetime.today())
                    date_values = [v for v in time_resolutions.values if v.type == "date"]
                    date_range_values = [v for v in time_resolutions.values if v.type in ("daterange", "datetimerange")]
                    if date_values:
                        return datetime.fromisoformat(date_values[0].value)
                    elif date_range_values:
                        date_range_value = date_range_values[0]
                        return datetime.fromisoformat(date_range_value.start)
                return None
            else:
                error_text = await response.text()
                print(f"Request failed with status {response.status}: {error_text}")
