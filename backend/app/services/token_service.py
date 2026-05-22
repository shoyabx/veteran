from app.services.security import decrypt_secret

def get_graph_access_token(encrypted_access_token: str | None, encrypted_refresh_token: str | None) -> str:
    # Foundation behavior: decrypt existing access token.
    # Refresh-token exchange is intentionally separated for later secret-manager integration.
    if encrypted_access_token:
        return decrypt_secret(encrypted_access_token)
    if encrypted_refresh_token:
        # explicit unsupported branch for now
        raise ValueError('access_token_missing_refresh_flow_not_implemented_in_phase1b')
    raise ValueError('missing_graph_tokens')
