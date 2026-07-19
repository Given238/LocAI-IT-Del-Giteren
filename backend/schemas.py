from typing import Optional

from pydantic import BaseModel, Field


class ItineraryRequest(BaseModel):
    budget: float = Field(..., gt=0, description="Total trip budget in IDR")
    duration_nights: int = Field(..., ge=0, description="Nights away; 0 = same-day trip, no lodging")
    start_location: str = Field(..., min_length=1)
    interests: Optional[list[str]] = Field(
        default=None, description='e.g. ["nature", "culture", "culinary", "spiritual", "recreation", "business"]'
    )
    locale: Optional[str] = Field(
        default=None,
        description="SEA locale for narrative tone only, e.g. \"indonesian\", \"malaysian\", \"singaporean\", "
        '"filipino", "thai", "vietnamese". Never affects candidate filtering/selection.',
    )


class PlaceOut(BaseModel):
    id: int
    name: str
    category: str
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    address: Optional[str] = None
    rating: Optional[float] = None
    detail: Optional[str] = None
    distance_km: Optional[float] = None


class DayPlan(BaseModel):
    day: int
    attractions: list[PlaceOut] = []
    meals: list[PlaceOut] = []
    lodging: Optional[PlaceOut] = None
    transport: list[PlaceOut] = []
    narrative: str
    estimated_cost_min: float
    estimated_cost_max: float


class ItineraryResponse(BaseModel):
    feasible: bool
    message: Optional[str] = None
    constraints: ItineraryRequest
    summary: Optional[str] = None
    days: list[DayPlan] = []
    estimated_total_cost_min: Optional[float] = None
    estimated_total_cost_max: Optional[float] = None
    candidates_considered: dict
    distance_reference: Optional[str] = None
