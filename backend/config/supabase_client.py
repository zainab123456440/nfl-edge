"""
Centralized Supabase client for Green Flora.

Creates the Supabase client from environment variables.

The client is configured without passing a custom HTTPX client because
the Supabase version used in the Vercel deployment does not support the
`httpx_client` ClientOptions argument.
"""

from typing import Optional

from supabase import Client, ClientOptions, create_client

from config.settings import settings


# -------------------------------------------------------------------
# Service-role Supabase client
# -------------------------------------------------------------------
# Used for trusted backend operations such as:
# - Cron/data synchronization
# - Background jobs
# - Server-side data ingestion
# - Operations that intentionally bypass Row Level Security (RLS)
# -------------------------------------------------------------------

supabase: Optional[Client] = None


if settings.supabase_url and settings.supabase_service_key:

    options = ClientOptions(
        postgrest_client_timeout=30,
        storage_client_timeout=30,
        function_client_timeout=30,
    )

    supabase = create_client(
        settings.supabase_url,
        settings.supabase_service_key,
        options=options,
    )


# -------------------------------------------------------------------
# User-scoped Supabase client
# -------------------------------------------------------------------
# Creates a client using the Supabase anonymous key and the logged-in
# user's access token.
#
# This client should be used for user-facing operations where Supabase
# Row Level Security (RLS) must apply to the authenticated user.
# -------------------------------------------------------------------

def get_user_client(access_token: str) -> Client:
    """
    Create a Supabase client authenticated as the current user.

    The anonymous key is used to create the client, while the user's
    access token is attached to the PostgREST client so database
    queries execute in the user's authenticated context and RLS
    policies can be enforced.
    """

    if not (
        settings.supabase_url
        and settings.supabase_anon_key
    ):
        raise RuntimeError(
            "SUPABASE_URL / SUPABASE_ANON_KEY are not configured."
        )

    if not access_token:
        raise ValueError("A Supabase access token is required.")

    client = create_client(
        settings.supabase_url,
        settings.supabase_anon_key,
        options=ClientOptions(
            postgrest_client_timeout=30,
        ),
    )

    client.postgrest.auth(access_token)

    return client