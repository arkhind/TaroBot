# src/vox_wrapper/models.py

from __future__ import annotations
from typing import List, Optional, Union
from enum import Enum
from datetime import datetime, date
from pydantic import BaseModel, Field


# --- Enums ---

class Subject(str, Enum):
    USER = "USER"
    GROUP = "GROUP"


class Source(str, Enum):
    TELEGRAM = "TELEGRAM"
    SLACK = "SLACK"
    HN = "HN"
    NONE = "NONE"


class Type(str, Enum):
    CHAT = "CHAT"
    CHANNEL = "CHANNEL"
    PRIVATE = "PRIVATE"


class ContentType(str, Enum):
    TEXT = "TEXT"
    MEDIA = "MEDIA"
    POLL = "POLL"
    STICKER = "STICKER"
    VOICE = "VOICE"
    FILE = "FILE"
    CONTACT = "CONTACT"
    GEO = "GEO"
    VIDEO = "VIDEO"


class ActionType(str, Enum):
    MESSAGE = "message"
    REACTION = "reaction"


class Sex(str, Enum):
    male = "male"
    female = "female"


# --- Core analytics models ---

class AIAnalytics(BaseModel):
    type: Subject
    id: int
    message_count: int = 0
    report: str = ""
    embedding: List[float] = Field(default_factory=list)
    date: datetime
    version: int = 1


class EmptyResponse(BaseModel):
    """Пустой ответ без полей."""


class CosineSimilarityResponse(BaseModel):
    cosine_similarity: float = 0.0


# --- Fast report models ---

class FastGroupTag(BaseModel):
    group_name: str
    tags: List[str]


class FastReport(BaseModel):
    id: int
    interests: List[FastGroupTag]
    countries: List[str]
    cities: List[str]


# --- Structured Report models ---

class UserBelief(BaseModel):
    """
    Политические или идеологические убеждения пользователя.
    """
    belief: str
    sub_beliefs: List[str]
    probability: float


class UserInterest(BaseModel):
    """
    Интересы пользователя.
    """
    interest: str
    sub_interests: List[str]
    probability: float


class UserStructuredReport(BaseModel):
    """
    Структурированный отчёт по пользователю.
    """
    language: str
    sex: Sex
    age_range: List[int]
    income_range: List[int]
    occupation: str
    locations: List[str]
    is_bot: bool = False
    beliefs: List[UserBelief] = Field(default_factory=list)
    interests: List[UserInterest]
    left_right: int = 0
    authoritarian_libertarian: int = 0

# --- Search models ---

class CloseUser(BaseModel):
    id: int
    alias: str
    name: str
    report: str
    message_url: str
    channel_url: str


class CloseUsers(BaseModel):
    close_users: List[CloseUser]


# --- Activity models ---

class UserActivity(BaseModel):
    id: int
    alias: str
    name: str
    frequency: float


class ActivityHourly(BaseModel):
    hour: int
    count: int


class ActivitiesHourly(BaseModel):
    activities: List[ActivityHourly]


class ActivityWeekly(BaseModel):
    day: int
    count: int


class ActivitiesWeekly(BaseModel):
    activities: List[ActivityWeekly]


class Activity(BaseModel):
    user_id: int
    group_id: int
    group_name: str
    related_group_name: str
    related_group_id: int
    messages_count: int


class ActivitiesTotal(BaseModel):
    activities: List[Activity] = Field(default_factory=list)


# --- User profile & misc models ---

class UserLanguageResponse(BaseModel):
    language: str


class GenderResponse(BaseModel):
    gender: str
    probability: float


class CompactResponse(BaseModel):
    language_response: UserLanguageResponse
    gender_response: GenderResponse


class UserNameAlias(BaseModel):
    name: str
    alias: str


class UserID(BaseModel):
    id: int


class UserRegistrationDate(BaseModel):
    bucket: int
    date: date


class UserProfileReaction(BaseModel):
    emoji: str
    count: int


class UserProfileMessageContent(BaseModel):
    id: int
    text: str = ""
    content_type: ContentType = ContentType.TEXT
    reactions: List[UserProfileReaction] = Field(default_factory=list)


class UserProfileActionMessage(BaseModel):
    group_id: int
    date: datetime
    type: ActionType = ActionType.MESSAGE
    content: UserProfileMessageContent


class UserProfileGroup(BaseModel):
    id: int
    name: str
    about: str = ""
    members_count: int = 0
    alias: str = ""


class UserProfile(BaseModel):
    id: int
    full_name: str
    alias: str
    about: str = ""
    account_age: float = 0
    pic: str = ""
    groups: List[UserProfileGroup] = Field(default_factory=list)
    actions: List[Union[UserProfileActionMessage, UserProfileReaction]] = Field(default_factory=list)


# --- Group models ---

class Group(BaseModel):
    source: Source
    id: int
    alias: str = ""
    related_group: int = 0
    server_id: str = ""
    access_hash: int = 0
    name: str = ""
    type: Type
    is_private: bool = False
    added: datetime
    members_count: int = 0
    about: str = ""
    from_group: int = 0
    from_message: int = 0
    bot_index: int = 0
    version: int = 0
    bot_name: str = ""
    aliases: List[str] = Field(default_factory=list)


class GroupReport(BaseModel):
    id: int
    message_count: int = 0
    posts: List[str] = Field(default_factory=list)