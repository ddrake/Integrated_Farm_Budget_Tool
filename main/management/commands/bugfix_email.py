from django.core.management.base import BaseCommand, CommandError
from main.models.util import notify_user_of_bugfix


class Command(BaseCommand):
    help = "Notifies the user (specified by username) of a bug fix."

    def add_arguments(self, parser):
        parser.add_argument("username", type=str)

    def handle(self, *args, **options):
        try:
            notify_user_of_bugfix(options['username'])
            self.stdout.write(
                self.style.SUCCESS('The user has been notified.')
            )
        except Exception as ex:
            raise CommandError(str(ex))
