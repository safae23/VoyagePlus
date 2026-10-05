from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class TripRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    origin: str = Field(min_length=1, max_length=120)
    destination: str = Field(min_length=1, max_length=120)
    start_date: date
    end_date: date
    budget: float = Field(gt=0, le=1000000, allow_inf_nan=False)
    priority: Literal["best_location", "cheapest"] = "best_location"

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date <= self.start_date:
            raise ValueError("La date de retour doit suivre la date de départ.")
        return self

    @property
    def nights(self):
        return (self.end_date - self.start_date).days

    @property
    def lodging_per_night(self):
        # Explicit planning envelope: 50% lodging, 35% flights, 15% other costs.
        return round(self.budget * 0.5 / self.nights, 2)


class AiStatus(BaseModel):
    status: Literal["ok", "disabled", "error"]
    model: str
    message: str | None = None


class TripResponse(BaseModel):
    flights: dict
    stay: list[dict] | str
    activities: list[dict]
    weather: dict
    summary: str
    ai: AiStatus
    budget: dict
    errors: dict[str, str]
    sources: dict[str, str]
    architecture: dict
