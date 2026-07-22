from typing import Literal, Optional

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
    latitude: Optional[float] = None
    longitude: Optional[float] = None


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
    start_latitude: Optional[float] = None
    start_longitude: Optional[float] = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    # Only ever set on an assistant message that resulted from a successful
    # generate_itinerary tool call -- carried in history so a later "export
    # as PDF" request can find the last verified result without regenerating
    # anything.
    itinerary: Optional[ItineraryResponse] = None


class ChatRequest(BaseModel):
    history: list[ChatMessage] = []
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    reply: str
    itinerary: Optional[ItineraryResponse] = None
    pdf_base64: Optional[str] = None
    pdf_filename: Optional[str] = None


class SignupRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=8)
    display_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    display_name: Optional[str] = None


# Same shape as ItineraryRequest's own fields, but every field is optional --
# this is a partially-filled preference profile, not a ready-to-submit
# itinerary request (onboarding can be skipped/partially answered).
class ProfileData(BaseModel):
    budget: Optional[float] = None
    duration_nights: Optional[int] = None
    start_location: Optional[str] = None
    interests: Optional[list[str]] = None
    locale: Optional[str] = None


class MeResponse(BaseModel):
    user: Optional[UserOut] = None
    profile: Optional[ProfileData] = None
