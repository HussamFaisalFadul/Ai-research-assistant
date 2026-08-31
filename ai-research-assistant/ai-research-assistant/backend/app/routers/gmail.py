from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
import os
import json

from app.core.config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
)

router = APIRouter(
    prefix="/gmail",
    tags=["Gmail"]
)

# صلاحية Gmail التي سنستخدمها في المرحلة الأولى
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly"
]


def create_oauth_flow():
    """
    إنشاء Google OAuth Flow
    """

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth credentials are not configured."
        )

    client_config = {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [
                GOOGLE_REDIRECT_URI
            ],
        }
    }

    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI,
    )

    return flow


@router.get("/auth")
async def gmail_auth():
    """
    بدء تسجيل الدخول والموافقة على Gmail
    """

    flow = create_oauth_flow()

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    # في هذه المرحلة نعيد الرابط فقط.
    # لاحقًا سنحفظ state بشكل آمن في session/database.
    return {
        "authorization_url": authorization_url,
        "state": state,
        "message": "افتح authorization_url لبدء ربط Gmail."
    }


@router.get("/callback")
async def gmail_callback(code: str = None):
    """
    Google يعيد المستخدم إلى هذا الرابط بعد الموافقة.
    """

    if not code:
        raise HTTPException(
            status_code=400,
            detail="Authorization code is missing."
        )

    try:
        flow = create_oauth_flow()

        # بناء callback URL الذي أرسلته Google
        authorization_response = (
            f"{GOOGLE_REDIRECT_URI}?code={code}"
        )

        flow.fetch_token(
            authorization_response=authorization_response
        )

        credentials = flow.credentials

        result = {
            "message": "تم ربط Gmail بنجاح ✅",
            "token_type": credentials.token,
            "refresh_token": bool(credentials.refresh_token),
            "scopes": credentials.scopes,
        }

        # لا نعرض access token أو refresh token للمستخدم.
        return result

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Gmail OAuth failed: {str(e)}"
        )


@router.get("/status")
async def gmail_status():
    """
    فحص إعدادات Gmail OAuth.
    """

    return {
        "configured": bool(
            GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
        ),
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "scopes": SCOPES,
    }
