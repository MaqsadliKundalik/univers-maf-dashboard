from django.shortcuts import render
from bot.models import VipChats, Chat, User, Game

def index(request):
    vip_records = VipChats.objects.filter(is_active=True)
    vip_chat_ids = [record.chat_id for record in vip_records]
    vip_chats = Chat.objects.filter(chat_id__in=vip_chat_ids)
    
    stats = {
        'users_count': User.objects.count(),
        'chats_count': Chat.objects.count(),
        'games_count': Game.objects.count(),
    }
    
    return render(request, 'main/index.html', {'vip_chats': vip_chats, 'stats': stats})
