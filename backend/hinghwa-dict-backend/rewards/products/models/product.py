from django.db import models
from django.conf import settings


def default_product_picture():
    return getattr(settings, "DEFAULT_AVATAR_URL", "")


class Product(models.Model):
    name = models.CharField(max_length=100, verbose_name="商品名称")
    points = models.IntegerField(verbose_name="所需积分", default=0)
    quantity = models.IntegerField(verbose_name="剩余数量", default=0)
    picture = models.URLField(
        default=default_product_picture,
        verbose_name="商品图片",
    )
    details = models.TextField(blank=True, max_length=200, verbose_name="商品详情")
    id = models.CharField(max_length=20, verbose_name="ID", primary_key=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "商品"
        verbose_name = "商品"
