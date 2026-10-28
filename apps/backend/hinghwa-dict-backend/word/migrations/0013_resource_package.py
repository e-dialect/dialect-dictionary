from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("word", "0012_merge_20260901_000000"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name="ResourcePackage", fields=[
            ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("package_id", models.CharField(max_length=120, unique=True)),
            ("digest", models.CharField(max_length=64)),
            ("profile", models.CharField(max_length=40)),
            ("metadata", models.JSONField()),
            ("published", models.BooleanField(default=False)),
            ("storage_path", models.TextField()),
            ("imported_at", models.DateTimeField(auto_now_add=True)),
            ("importer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.CreateModel(name="ResourcePackageEntry", fields=[
            ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("external_id", models.CharField(max_length=4)),
            ("source_line", models.PositiveIntegerField()),
            ("audio_name", models.CharField(max_length=200)),
            ("package", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="entries", to="word.resourcepackage")),
            ("word", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, to="word.word")),
            ("pronunciation", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, to="word.pronunciation")),
        ]),
        migrations.AddConstraint(model_name="resourcepackageentry", constraint=models.UniqueConstraint(fields=("package", "external_id"), name="resource_package_external_id_unique")),
    ]
