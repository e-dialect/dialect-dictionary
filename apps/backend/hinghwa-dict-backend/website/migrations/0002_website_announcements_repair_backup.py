from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('website', '0001_initial')]
    operations = [migrations.AddField(
        model_name='website', name='announcements_repair_backup',
        field=models.JSONField(blank=True, default=dict, editable=False, verbose_name='上次公告修复备份'),
    )]
