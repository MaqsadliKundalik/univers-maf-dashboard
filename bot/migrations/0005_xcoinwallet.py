# Generated for unmanaged bot xcoin wallet table state.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0004_remove_transfer_caption'),
    ]

    operations = [
        migrations.CreateModel(
            name='XCoinWallet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('xcoin', models.BigIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='xcoin_wallet', to='bot.user')),
            ],
            options={
                'db_table': 'xcoinwallet',
                'managed': False,
            },
        ),
    ]
