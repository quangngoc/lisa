from datetime import datetime

import pytest

from lisa.scheduler import TimeSlotFetcher


@pytest.mark.anyio
async def test_get_available_time_slots():
    ## Arrange
    today = datetime.now()
    fetcher = TimeSlotFetcher()

    # Act
    slots = await fetcher.fetch(today)

    # Assert
    assert slots.date
    assert len(slots.slots) <= 5
