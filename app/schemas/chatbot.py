from pydantic import BaseModel


class ChatbotQuestion(BaseModel):
    question: str
    stream: bool = False


class ChatbotResponse(BaseModel):
    answer: str
