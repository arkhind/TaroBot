# src/vox_wrapper/client.py

import requests
from typing import Optional, List, Union, Any
from .exceptions import (
    AuthenticationError,
    ValidationError,
    NotFoundError,
    ServerError,
    ApiError,
)
from .models import (  # импорт моделей
    Subject,
    AIAnalytics,
    EmptyResponse,
    CosineSimilarityResponse,
    FastReport,
    UserStructuredReport,
    CloseUsers,
    UserActivity,
    ActivitiesHourly,
    ActivitiesWeekly,
    ActivitiesTotal,
    UserLanguageResponse,
    GenderResponse,
    CompactResponse,
    UserNameAlias,
    UserID,
    UserRegistrationDate,
    UserProfile,
    Group,
    GroupReport,
)


class VoxAPI:
    def __init__(self, token: str, base_url: str = "https://api.vox-lab.com/"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            }
        )

    def _request(self, method: str, path: str, **kwargs) -> any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        resp = self.session.request(method, url, **kwargs)

        if resp.status_code in (401, 403):
            raise AuthenticationError(resp.text)
        if resp.status_code == 422:
            try:
                detail = resp.json()
            except ValueError:
                raise ValidationError(
                    "Validation failed (422), but response is not valid JSON"
                )
            raise ValidationError(detail)
        if resp.status_code == 404:
            raise NotFoundError(resp.text)
        if 500 <= resp.status_code < 600:
            raise ServerError(resp.text)

        try:
            return resp.json()
        except ValueError:
            raise ApiError("Invalid JSON response")

    def ping(self) -> str:
        return self._request("GET", "/ping")

    # —— AI Analytics ——
    def ai_analytics(
        self,
        subject: Subject,
        subject_id: int,
        model: Optional[str] = None,
        no_cache: bool = False,
    ) -> Union[AIAnalytics, EmptyResponse]:
        params: dict[str, Any] = {}
        if model is not None:
            params["model"] = model
        if no_cache:
            params["no_cache"] = True
        return self._request(
            "GET",
            f"/ai_analytics/{subject.name}/{subject_id}",
            params=params,
        )

    def custom_report(
        self,
        subject: Subject,
        subject_id: int,
        custom_prompt: str,
        model: Optional[str] = None,
    ) -> Union[AIAnalytics, EmptyResponse]:
        params = {"custom_prompt": custom_prompt}
        if model is not None:
            params["model"] = model
        return self._request(
            "GET",
            f"/ai_analytics/custom/{subject.name}/{subject_id}",
            params=params,
        )

    def cosine_similarity(
        self,
        subject: Subject,
        subject_id_1: int,
        subject_id_2: int,
    ) -> Union[CosineSimilarityResponse, EmptyResponse]:
        return self._request(
            "GET",
            f"/ai_analytics/{subject.name}/cosine_similarity/{subject_id_1}/{subject_id_2}",
        )

    # —— Reports for user ——
    def fast_report(self, user_id: int) -> FastReport:
        return self._request("GET", f"/reports/user/{user_id}/fast")

    def user_structured_report(self, user_id: int) -> UserStructuredReport:
        return self._request("GET", f"/reports/user/{user_id}")

    # —— Search ——
    def search_users(
        self,
        query: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> CloseUsers:
        params: dict[str, Any] = {"query": query}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        return self._request("GET", "/search/ai/users", params=params)

    def search_raw(
        self,
        subject: Subject,
        query: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[AIAnalytics]:
        params: dict[str, Any] = {"query": query}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        return self._request("GET", f"/search/ai/raw/{subject.name}", params=params)

    def search_users_by_activity(
        self,
        query: str,
        start_date: str,
        end_date: str,
        limit: Optional[int] = None,
    ) -> List[UserActivity]:
        params = {"query": query, "start_date": start_date, "end_date": end_date}
        if limit is not None:
            params["limit"] = str(limit)
        return self._request("GET", "/search/ai/users/activity", params=params)

    # —— User activity endpoints ——
    def get_activity_hourly(self, user_id: int) -> ActivitiesHourly:
        return self._request("GET", f"/users/{user_id}/activity/hourly")

    def get_activity_weekly(self, user_id: int) -> ActivitiesWeekly:
        return self._request("GET", f"/users/{user_id}/activity/weekly")

    def get_activity_total(self, user_id: int) -> ActivitiesTotal:
        return self._request("GET", f"/users/{user_id}/activity/total")

    # —— User profile endpoints ——
    def get_language(self, user_id: int) -> UserLanguageResponse:
        return self._request("GET", f"/users/{user_id}/language")

    def get_gender(self, user_id: int) -> GenderResponse:
        return self._request("GET", f"/users/{user_id}/gender")

    def get_compact(self, user_id: int) -> CompactResponse:
        return self._request("GET", f"/users/{user_id}/compact")

    def get_user_names(self, user_id: int) -> List[UserNameAlias]:
        return self._request("GET", f"/users/{user_id}/names")

    def get_user_id(self, username: str) -> UserID:
        return self._request("GET", f"/users/username/{username}")

    def get_registration_date(self, user_id: int) -> UserRegistrationDate:
        return self._request("GET", f"/users/{user_id}/registration")

    def get_profile(self, user_id: int) -> UserProfile:
        return self._request("GET", f"/users/{user_id}/profile")

    # —— Groups ——
    def get_group(self, group_id: int) -> Group:
        return self._request("GET", f"/groups/{group_id}")

    def group_posts(
        self,
        group_id: int,
        messages_limit: int,
        messages_min: int,
        members_min: int,
    ) -> Union[GroupReport, None]:
        params = {
            "messages_limit": messages_limit,
            "messages_min": messages_min,
            "members_min": members_min,
        }
        return self._request(
            "GET",
            f"/groups/{group_id}/messages",
            params=params,
        )
