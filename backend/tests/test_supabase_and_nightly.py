"""Supabase access tokens, prepared outfits, and the nightly batch helpers."""

from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.jobs.nightly_outfits import queue_pending_tagging, target_day
from app.models.outfit import Outfit, OutfitSource, OutfitStatus
from app.models.user import User
from app.services.ai_service import AIDisabledError
from app.services.recommendation_service import AIRecommendationError, RecommendationService
from app.utils.supabase_jwt import SupabaseTokenError, verify_supabase_access_token
from app.utils.timezone import get_user_today

SUPABASE_URL = "https://example.supabase.co"
JWT_SECRET = "supabase-test-secret"


def _settings(**overrides) -> Settings:
    base = {
        "debug": False,
        "secret_key": "a-strong-custom-secret",
        "supabase_url": SUPABASE_URL,
    }
    base.update(overrides)
    return Settings(**base)


def _token(**extra) -> str:
    now = datetime.now(UTC)
    payload = {
        "iss": f"{SUPABASE_URL}/auth/v1",
        "aud": "authenticated",
        "sub": str(uuid4()),
        "email": "angel@example.com",
        "role": "authenticated",
        "exp": now + timedelta(hours=1),
        "iat": now,
    }
    payload.update(extra)
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def _install(monkeypatch, settings: Settings) -> None:
    monkeypatch.setattr("app.utils.auth.settings", settings)
    monkeypatch.setattr("app.utils.supabase_jwt.get_settings", lambda: settings)


class TestSupabaseSettings:
    def test_supabase_disables_dev_login_even_with_debug(self):
        settings = _settings(debug=True)
        assert settings.supabase_configured is True
        assert settings.dev_mode is False
        assert settings.get_auth_mode() == "supabase"

    def test_default_secret_is_refused_when_supabase_is_configured(self):
        settings = Settings(supabase_url=SUPABASE_URL)
        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            settings.validate_security()

    def test_cors_origins_accept_a_comma_separated_list(self):
        settings = _settings(cors_origins="https://app.vercel.app, http://localhost:3000")
        assert settings.cors_origins == ["https://app.vercel.app", "http://localhost:3000"]

    def test_database_schema_rejects_anything_but_an_identifier(self):
        with pytest.raises(ValueError):
            _settings(database_schema="armario;public")
        assert _settings(database_schema="armario").database_schema == "armario"


class TestSupabaseJwt:
    def test_hs256_access_token(self, monkeypatch):
        _install(monkeypatch, _settings(supabase_jwt_secret=JWT_SECRET))
        claims = verify_supabase_access_token(_token())
        assert claims["email"] == "angel@example.com"
        assert claims["role"] == "authenticated"

    def test_rejects_anon_and_service_role(self, monkeypatch):
        _install(monkeypatch, _settings(supabase_jwt_secret=JWT_SECRET))
        with pytest.raises(SupabaseTokenError):
            verify_supabase_access_token(_token(role="anon", aud="anon"))
        with pytest.raises(SupabaseTokenError):
            verify_supabase_access_token(_token(role="service_role"))

    def test_rejects_a_forged_signature(self, monkeypatch):
        _install(monkeypatch, _settings(supabase_jwt_secret=JWT_SECRET))
        forged = jwt.encode(
            {
                "iss": f"{SUPABASE_URL}/auth/v1",
                "aud": "authenticated",
                "sub": str(uuid4()),
                "email": "angel@example.com",
                "role": "authenticated",
                "exp": datetime.now(UTC) + timedelta(hours=1),
            },
            "other-secret",
            algorithm="HS256",
        )
        with pytest.raises(SupabaseTokenError):
            verify_supabase_access_token(forged)

    def test_es256_uses_the_jwks(self, monkeypatch):
        from cryptography.hazmat.primitives.asymmetric import ec

        _install(monkeypatch, _settings())
        private = ec.generate_private_key(ec.SECP256R1())
        now = datetime.now(UTC)
        token = jwt.encode(
            {
                "iss": f"{SUPABASE_URL}/auth/v1",
                "aud": "authenticated",
                "sub": str(uuid4()),
                "email": "angel@example.com",
                "role": "authenticated",
                "exp": now + timedelta(hours=1),
                "iat": now,
            },
            private,
            algorithm="ES256",
            headers={"kid": "test-key"},
        )

        class _Key:
            key = private.public_key()

        class _Client:
            def get_signing_key_from_jwt(self, _token):
                return _Key()

        monkeypatch.setattr("app.utils.supabase_jwt._jwks_client", lambda _url: _Client())
        claims = verify_supabase_access_token(token)
        assert claims["email"] == "angel@example.com"


class TestSupabaseLogin:
    async def test_first_request_creates_the_user(self, client: AsyncClient, monkeypatch):
        settings = _settings(supabase_jwt_secret=JWT_SECRET)
        _install(monkeypatch, settings)
        subject = str(uuid4())
        token = _token(sub=subject, email="primera@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        created = await client.get("/api/v1/users/me", headers=headers)
        assert created.status_code == 200
        body = created.json()
        assert body["email"] == "primera@example.com"

        again = await client.get("/api/v1/users/me", headers=headers)
        assert again.status_code == 200
        assert again.json()["id"] == body["id"]

    async def test_missing_token_is_rejected(self, client: AsyncClient, monkeypatch):
        _install(monkeypatch, _settings(supabase_jwt_secret=JWT_SECRET))
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 401

    async def test_dev_sync_is_closed_when_supabase_is_configured(
        self, client: AsyncClient, monkeypatch
    ):
        _install(monkeypatch, _settings(debug=True, supabase_jwt_secret=JWT_SECRET))
        monkeypatch.setattr(
            "app.api.auth.settings", _settings(debug=True, supabase_jwt_secret=JWT_SECRET)
        )
        response = await client.post(
            "/api/v1/auth/sync",
            json={"external_id": "dev-user", "email": "dev@example.com", "display_name": "Dev"},
        )
        assert response.status_code == 401


class TestPreparedOutfits:
    async def test_suggest_returns_prepared_outfits_when_ai_is_down(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers
    ):
        outfit = Outfit(
            user_id=test_user.id,
            occasion="casual",
            scheduled_for=get_user_today(test_user),
            status=OutfitStatus.pending,
            source=OutfitSource.scheduled,
        )
        db_session.add(outfit)
        await db_session.commit()

        async def _down(*_args, **_kwargs):
            raise AIRecommendationError("model is off")

        with patch.object(RecommendationService, "generate_recommendations", _down):
            response = await client.post(
                "/api/v1/outfits/suggest-options",
                json={"occasion": "casual"},
                headers=auth_headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body[0]["id"] == str(outfit.id)
        assert body[0]["ai_unavailable"] is True

        prepared = await client.get("/api/v1/outfits/prepared", headers=auth_headers)
        assert prepared.status_code == 200
        assert prepared.json()[0]["id"] == str(outfit.id)
        assert prepared.json()[0]["ai_unavailable"] is False

    async def test_suggest_explains_when_nothing_was_prepared(
        self, client: AsyncClient, auth_headers
    ):
        async def _disabled(*_args, **_kwargs):
            raise AIDisabledError("text off")

        with patch.object(RecommendationService, "generate_recommendations", _disabled):
            response = await client.post(
                "/api/v1/outfits/suggest-options",
                json={"occasion": "casual"},
                headers=auth_headers,
            )

        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "ai_unavailable"


class TestNightlyHelpers:
    def test_target_day_is_tomorrow_unless_asked_for_today(self):
        user = User(timezone="UTC", email="a@b.c", display_name="A")
        today = get_user_today(user)
        assert target_day(user, for_today=False, explicit=None) == today + timedelta(days=1)
        assert target_day(user, for_today=True, explicit=None) == today
        assert target_day(user, for_today=False, explicit=date(2026, 11, 4)) == date(2026, 11, 4)

    async def test_pending_descriptions_stay_queued_without_vision(
        self, db_session: AsyncSession, monkeypatch
    ):
        monkeypatch.setattr(
            "app.jobs.nightly_outfits.get_settings",
            lambda: Settings(
                debug=True,
                secret_key="a-strong-custom-secret",
                ai_internal_enabled=True,
                ai_vision_enabled=False,
            ),
        )
        result = await queue_pending_tagging(db_session)
        assert result["reason"] == "vision_disabled"
        assert result["enqueued"] == 0


def test_cached_settings_still_construct():
    # Importing the app caches settings from the environment. This only checks
    # the helper still returns that object after the cases above patched callers.
    assert get_settings().debug is True
