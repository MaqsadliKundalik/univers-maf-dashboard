# Generated for unmanaged bot tables used by public access pages.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='GroupIncome',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('chat_id', models.BigIntegerField()),
                ('user_id', models.BigIntegerField()),
                ('amount', models.BigIntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'group_incomes',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='VipChats',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('chat_id', models.BigIntegerField(unique=True)),
                ('is_active', models.BooleanField(default=True)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'vipchats',
                'managed': False,
            },
        ),
    ]
