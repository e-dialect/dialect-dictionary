from django.db import migrations, models
import rewards.products.models.product


class Migration(migrations.Migration):
    dependencies = [("rewards", "0002_reward_verbose_name_plural")]
    operations = [
        migrations.AlterField(
            model_name="product",
            name="picture",
            field=models.URLField(
                default=rewards.products.models.product.default_product_picture,
                verbose_name="商品图片",
            ),
        )
    ]
