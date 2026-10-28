from django.core.management.base import BaseCommand, CommandError
from word.resource_packages import PackageError, apply_package, validate_package


class Command(BaseCommand):
    help = "Validate our legacy-tsv-v1 directory/ZIP package (no writes by default); --apply requires an existing --importer username."
    requires_system_checks = []
    requires_migrations_checks = False

    def add_arguments(self, parser):
        parser.add_argument("package")
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--publish", action="store_true")
        parser.add_argument("--importer")

    def handle(self, *args, **options):
        try:
            plan = validate_package(options["package"], publish=options["publish"])
            self.stdout.write(f"Profile: {plan['metadata'].get('profile', '?')}; package: {plan['metadata'].get('package_id', '?')}; encoding: {plan['encoding']}; rows: {len(plan['rows'])}; SHA256: {plan['digest']}")
            if plan["errors"]:
                raise PackageError("\n".join(plan["errors"]))
            if options["publish"] and not options["apply"]:
                raise PackageError("--publish requires --apply; preview without --publish is read-only")
            if not options["apply"]:
                self.stdout.write("Preview valid: no database or media writes. Use --apply --importer EXISTING_USERNAME; private by default.")
                return
            if not options["importer"]:
                raise PackageError("--apply requires --importer EXISTING_USERNAME; no account is created")
            receipt, created = apply_package(plan, options["importer"], publish=options["publish"])
            self.stdout.write(f"{'Imported' if created else 'Skipped identical package'}: {receipt.package_id}; published={receipt.published}; rows={receipt.entries.count()}")
        except (PackageError, OSError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
