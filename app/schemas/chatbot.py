from pydantic import BaseModel, Field


class ChatbotQuestion(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    stream: bool = False


class ChatbotResponse(BaseModel):
    answer: str
