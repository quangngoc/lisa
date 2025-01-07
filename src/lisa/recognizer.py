import aiohttp
import os
from datetime import datetime


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
                    return None
            else:
                error_text = await response.text()
                print(f"Request failed with status {response.status}: {error_text}")
