from django.core.management.base import BaseCommand, CommandError
from main.models.util import notify_users_of_budget_updates


class Command(BaseCommand):
    help = "Notifies users who have updated budgets available."

    def add_arguments(self, parser):
        parser.add_argument("budget_crop_ids", nargs="+", type=int)

    def handle(self, *args, **options):
        try:
            users = notify_users_of_budget_updates(options['budget_crop_ids'])
            userstr = ', '.join(users)
            self.stdout.write(
                self.style.SUCCESS(
                    f'The following users have been notified:\n{userstr}')
            )
        except Exception as ex:
            raise CommandError(str(ex))
