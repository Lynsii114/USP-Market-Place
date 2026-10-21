def resolve_email_provider(provider, smtp_host, resend_api_key):
    """Keep explicit providers; prefer HTTPS over stale SMTP values in auto mode."""
    if provider != "auto":
        return provider
    if resend_api_key.strip():
        return "resend"
    if smtp_host:
        return "smtp"
    return "console"
