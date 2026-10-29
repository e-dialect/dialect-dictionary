import json
from django.core.management.base import BaseCommand, CommandError
from word.ime_export import ExportError, prepare_export, write_export


class Command(BaseCommand):
    help = 'Local operator exports a versioned Pouleng addon; private data requires explicit selection and importer/superuser scope.'
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument('package_id')
        parser.add_argument('--mapping', required=True)
        parser.add_argument('--requester', required=True)
        parser.add_argument('--export-version', dest='version', required=True)
        parser.add_argument('--include-private', action='store_true')
        parser.add_argument('--preview', action='store_true')
        parser.add_argument('--output')
        parser.add_argument('--authorization-statement')

    def handle(self, *args, **options):
        try:
            plan = prepare_export(options['package_id'], options['requester'], options['mapping'], options['version'], options['include_private'])
            if options['preview']:
                if options['output']:
                    raise ExportError('--preview cannot be combined with --output')
                self.stdout.write(json.dumps(plan, ensure_ascii=False, indent=2))
            else:
                if not options['output']:
                    raise ExportError('Use --preview first, or supply --output and --authorization-statement')
                self.stdout.write(json.dumps(write_export(plan, options['output'], options['authorization_statement']), ensure_ascii=False))
        except (ExportError, OSError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
