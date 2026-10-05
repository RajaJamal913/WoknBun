from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from pos.models import StaffProfile


class Command(BaseCommand):
    help = "Create (or update) a POS staff login: make_staff <username> <role> [--password PW]"

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("role", choices=[r for r, _ in StaffProfile.ROLE_CHOICES])
        parser.add_argument("--password", help="Required when creating a new user.")

    def handle(self, *args, **opts):
        User = get_user_model()
        user = User.objects.filter(username=opts["username"]).first()
        if user is None:
            if not opts["password"]:
                raise CommandError("User doesn't exist - pass --password to create it.")
            user = User.objects.create_user(opts["username"], password=opts["password"])
            self.stdout.write(f"Created user {user.username}")
        elif opts["password"]:
            user.set_password(opts["password"])
            user.save()
        StaffProfile.objects.update_or_create(user=user, defaults={"role": opts["role"]})
        self.stdout.write(self.style.SUCCESS(f"{user.username} is now a {opts['role']}."))
