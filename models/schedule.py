from typing import Optional
from pydantic import BaseModel


class ScheduleCreate(BaseModel):
    slug:          str
    frequency:     str            # daily | weekly | biweekly | monthly | custom
    hour:          int  = 2       # 0-23 UTC
    minute:        int  = 0       # 0-59
    day_of_week:   Optional[int] = None  # 0=Lun, 6=Dim (weekly/biweekly)
    day_of_month:  Optional[int] = None  # 1-28 (monthly)
    interval_days: Optional[int] = None  # custom
    description:   Optional[str] = None
    active:        bool = True


class ScheduleUpdate(BaseModel):
    frequency:     Optional[str] = None
    hour:          Optional[int] = None
    minute:        Optional[int] = None
    day_of_week:   Optional[int] = None
    day_of_month:  Optional[int] = None
    interval_days: Optional[int] = None
    description:   Optional[str] = None
    active:        Optional[bool] = None
