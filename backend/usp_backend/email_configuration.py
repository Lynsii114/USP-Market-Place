def resolve_email_provider(provider, smtp_host, resend_api_key, *, is_deployed=False):
    """Hosted deployments always use HTTPS; SMTP is local-only."""
    if is_deployed:
        return "resend"
    if provider != "auto":
        return provider
    if resend_api_key.strip():
        return "resend"
    if smtp_host:
        return "smtp"
    return "console"
