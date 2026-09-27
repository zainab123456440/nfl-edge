
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
