from django.db import migrations, models
import user.models


class Migration(migrations.Migration):
    dependencies = [("user", "0003_userinfo_points")]
    operations = [
        migrations.AlterField(
            model_name="userinfo",
            name="avatar",
            field=models.URLField(
                blank=True, default=user.models.default_avatar, verbose_name="头像"
            ),
        )
    ]
