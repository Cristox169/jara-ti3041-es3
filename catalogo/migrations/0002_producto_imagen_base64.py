# Generated for Django 5.0 on 2026-10-08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogo', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='producto',
            name='imagen_base64',
            field=models.TextField(blank=True, verbose_name='imagen Base64'),
        ),
    ]
