from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from marketplace.exceptions import ApiError
from marketplace.services import email_provider, require_resend_settings, send_email


class Command(BaseCommand):
    help = "Check Resend configuration or send one explicit test email without accessing the database."
    requires_system_checks = []

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--check-only", action="store_true")
        group.add_argument("--to", help="A recipient you control; sends one test email.")

    def handle(self, *args, **options):
        if email_provider() != "resend":
            raise CommandError("Set EMAIL_PROVIDER=resend to test Resend HTTPS delivery.")
        try:
            require_resend_settings("Resend configuration incomplete")
            if options["check_only"]:
                self.stdout.write("Resend HTTPS settings present (API key hidden). Sender verification and delivery are not tested.")
                self.stdout.write("Transport: HTTPS (https://api.resend.com/emails). Gmail SMTP settings are ignored.")
                self.stdout.write(f"Frontend URL: {settings.FRONTEND_URL}")
                return
            try:
                validate_email(options["to"])
            except ValidationError:
                raise CommandError("Enter a valid recipient email address.") from None
            send_email(
                "USP Marketplace email delivery test",
                "This test was requested by the USP Marketplace operator. No account or database record was changed.\n\n"
                f"Frontend: {settings.FRONTEND_URL}",
                options["to"],
            )
        except ApiError as exc:
            raise CommandError(str(exc)) from None
        self.stdout.write(self.style.SUCCESS("Test email accepted by Resend. Check the recipient inbox and Resend delivery logs."))
