from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'

    def ready(self):
        """
        Import signal handlers when the app is ready.
        """
        import apps.accounts.signals  # noqa
