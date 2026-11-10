from pydantic import BaseModel, Field
class Location(BaseModel): lat: float; lon: float; accuracy: float | None = None
class ConversationInput(BaseModel): text: str = Field(min_length=1, max_length=600); location: Location | None = None; transport: str = "walk"; history: list[dict] = []
