import os
import django
from django.conf import settings
from django.urls import resolve

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mafiadash.settings')
django.setup()

match = resolve('/')
print(f"Match for /: {match.view_name}, App: {match.app_name}")
match_panel = resolve('/panel/')
print(f"Match for /panel/: {match_panel.view_name}, App: {match_panel.app_name}")
