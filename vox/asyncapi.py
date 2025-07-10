import aiohttp
from typing import Optional, List, Union, Any
from urllib.parse import quote
from loguru import logger
from .exceptions import (
    AuthenticationError,
    ValidationError,
    NotFoundError,
    ServerError,
    ApiError,
)
from .models import Subject, AIAnalytics, EmptyResponse, CosineSimilarityResponse, FastReport, UserStructuredReport, CloseUsers, UserActivity, ActivitiesHourly, ActivitiesWeekly, ActivitiesTotal, UserLanguageResponse, GenderResponse, CompactResponse, UserNameAlias, UserID, UserRegistrationDate, UserProfile, Group, GroupReport


class AsyncVoxAPI:
    def __init__(self, token: str, base_url: str = "https://api.vox-lab.com/"):
        self.base_url = base_url.rstrip("/")
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            }
        )

    async def close(self):
        await self.session.close()

    async def _request(self, method: str, path: str, **kwargs) -> any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        async with self.session.request(method, url, **kwargs) as resp:
            text = await resp.text()
            if resp.status in (401, 403):
                raise AuthenticationError(text)
            if resp.status == 422:
                try:
                    detail = await resp.json()
                except Exception:
                    raise ValidationError(
                        "Validation failed (422), but response is not valid JSON"
                    )
                raise ValidationError(detail)
            if resp.status == 404:
                raise NotFoundError(text)
            if 500 <= resp.status < 600:
                raise ServerError(text)
            try:
                return await resp.json()
            except Exception:
                raise ApiError("Invalid JSON response")

    async def ping(self) -> str:
        return await self._request("GET", "/ping")

    async def ai_analytics(
        self,
        subject: Subject,
        subject_id: int,
        model: Optional[str] = None,
        no_cache: bool = False,
    ):
        params = {}
        if model:
            params["model"] = model
        if no_cache:
            params["no_cache"] = "true"
        return await self._request(
            "GET", f"/ai_analytics/{subject.name}/{subject_id}", params=params
        )

    async def custom_report(
        self,
        subject: Subject,
        subject_id: int,
        custom_prompt: str,
        model: Optional[str] = None,
    ):
        params = {"custom_prompt": custom_prompt}
        if model:
            params["model"] = model
        return await self._request(
            "GET", f"/ai_analytics/custom/{subject.name}/{subject_id}", params=params
        )

    async def cosine_similarity(
        self, subject: Subject, subject_id_1: int, subject_id_2: int
    ):
        return await self._request(
            "GET",
            f"/ai_analytics/{subject.name}/cosine_similarity/{subject_id_1}/{subject_id_2}",
        )

    async def fast_report(self, user_id: int):
        return await self._request("GET", f"/reports/user/{user_id}/fast")

    async def user_structured_report(self, user_id: int):
        return await self._request("GET", f"/reports/user/{user_id}")

    async def search_users(
        self, query: str, limit: Optional[int] = None, offset: Optional[int] = None
    ):
        params = {"query": query}
        if limit:
            params["limit"] = str(limit)
        if offset:
            params["offset"] = str(offset)
        return await self._request("GET", "/search/ai/users", params=params)

    async def search_raw(
        self,
        subject: Subject,
        query: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ):
        params = {"query": query}
        if limit:
            params["limit"] = str(limit)
        if offset:
            params["offset"] = str(offset)
        return await self._request(
            "GET", f"/search/ai/raw/{subject.name}", params=params
        )

    async def search_users_by_activity(
        self, query: str, start_date: str, end_date: str, limit: Optional[int] = None
    ):
        params = {"query": query, "start_date": start_date, "end_date": end_date}
        if limit:
            params["limit"] = str(limit)
        return await self._request("GET", "/search/ai/users/activity", params=params)

    async def get_activity_hourly(self, user_id: int):
        return await self._request("GET", f"/users/{user_id}/activity/hourly")

    async def get_activity_weekly(self, user_id: int):
        return await self._request("GET", f"/users/{user_id}/activity/weekly")

    async def get_activity_total(self, user_id: int):
        return await self._request("GET", f"/users/{user_id}/activity/total")

    async def get_language(self, user_id: int):
        return await self._request("GET", f"/users/{user_id}/language")

    async def get_gender(self, user_id: int):
        return await self._request("GET", f"/users/{user_id}/gender")

    async def get_compact(self, user_id: int):
        return await self._request("GET", f"/users/{user_id}/compact")

    async def get_user_names(self, user_id: int):
        return await self._request("GET", f"/users/{user_id}/names")

    async def get_user_id(self, username: str):
        # Ensure username is str before quoting (fix for TypeError)
        if isinstance(username, bytes):
            username = username.decode()
        # URL-кодируем username для корректной обработки специальных символов
        encoded_username = quote(username, safe='')
        return await self._request("GET", f"/users/username/{encoded_username}")

    async def get_registration_date(self, user_id: int):
        return await self._request("GET", f"/users/{user_id}/registration")

    async def get_profile(self, user_id: int):
        return await self._request("GET", f"/users/{user_id}/profile")

    async def get_group(self, group_id: int):
        return await self._request("GET", f"/groups/{group_id}")

    async def group_posts(
        self, group_id: int, messages_limit: int, messages_min: int, members_min: int
    ):
        params = {
            "messages_limit": str(messages_limit),
            "messages_min": str(messages_min),
            "members_min": str(members_min),
        }
        return await self._request("GET", f"/groups/{group_id}/messages", params=params)
