from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.db.models import Sum, Count, F, Case, When, IntegerField, OuterRef, Subquery
from django.db.models.functions import Coalesce
from django.core.cache import cache
from django.http import JsonResponse
from bot.models import VipChats, Chat, User, Game, Profile, GamePlayer, PlayersGameBall
from .models import GroupStatsLink
from datetime import timedelta
import uuid

def index(request):
    # (Existing index logic...)
    cache_key = 'index_page_data_v2'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        stats = cached_data['stats']
        top_players = cached_data['top_players']
    else:
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        stats = {
            'users_count': User.objects.count(),
            'chats_count': Chat.objects.count(),
            'games_count': Game.objects.count(),
        }
        
        game_player_qs = GamePlayer.objects.filter(game_id=OuterRef('game_id'))
        total_players_subquery = Subquery(game_player_qs.values('game_id').annotate(c=Count('id')).values('c')[:1])
        winners_count_subquery = Subquery(game_player_qs.filter(win=True).values('game_id').annotate(c=Count('id')).values('c')[:1])
        extra_ball_subquery = Subquery(PlayersGameBall.objects.filter(player_id=OuterRef('id')).values('ball')[:1])

        players_this_month = GamePlayer.objects.filter(game__created_at__gte=month_start).select_related('user')
        
        players_annotated = players_this_month.annotate(
            game_total=Coalesce(total_players_subquery, 0),
            game_winners=Coalesce(winners_count_subquery, 0),
            extra=Coalesce(extra_ball_subquery, 0)
        )
        
        players_with_delta = players_annotated.annotate(
            delta=Case(
                When(win=True, then=2 * F('game_total') - F('game_winners')),
                default=-F('game_winners'),
                output_field=IntegerField()
            ) + F('extra')
        )
        
        top_winners = players_with_delta.values('user__full_name', 'user__mention').annotate(
            total_score=Coalesce(Sum('delta'), 0),
            monthly_games=Count('game', distinct=True)
        ).order_by('-total_score')[:30]
        
        top_players = []
        for entry in top_winners:
            top_players.append({
                'user': {'full_name': entry['user__full_name'], 'mention': entry['user__mention']},
                'score': entry['total_score'],
                'games_count': entry['monthly_games'],
            })
        
        cache.set(cache_key, {'stats': stats, 'top_players': top_players}, 1800)

    vip_records = VipChats.objects.filter(is_active=True)
    vip_chat_ids = [record.chat_id for record in vip_records]
    vip_chats = Chat.objects.filter(chat_id__in=vip_chat_ids)

    return render(request, 'main/index.html', {
        'vip_chats': vip_chats, 
        'stats': stats,
        'top_players': top_players
    })

def generate_group_link(request):
    """Bot calls this to get a one-day link for group stats"""
    chat_id = request.GET.get('chat_id')
    if not chat_id:
        return JsonResponse({'error': 'chat_id is required'}, status=400)
    
    try:
        chat = Chat.objects.get(chat_id=chat_id)
    except Chat.DoesNotExist:
        # If chat doesn't exist in our DB yet, we might need to handle it or error
        return JsonResponse({'error': 'Chat not found'}, status=404)

    # Create a new link valid for 24 hours
    expires_at = timezone.now() + timedelta(days=1)
    link = GroupStatsLink.objects.create(chat=chat, expires_at=expires_at)
    
    url = request.build_absolute_uri(f'/group/{link.token}/')
    return JsonResponse({'url': url, 'expires_at': expires_at.isoformat()})

def group_stats(request, token):
    link = get_object_or_404(GroupStatsLink, token=token)
    
    if link.is_expired():
        return render(request, 'main/expired.html', {'chat': link.chat}, status=403)
    
    chat = link.chat
    period = request.GET.get('period', 'month') # day, week, month
    
    now = timezone.now()
    if period == 'day':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'week':
        start_date = now - timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    else: # month
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Group specific stats
    monthly_games = Game.objects.filter(chat=chat, created_at__gte=start_date)
    games_count = monthly_games.count()
    
    # Participants in this group
    participants_count = GamePlayer.objects.filter(game__chat=chat, game__created_at__gte=start_date).values('user_id').distinct().count()
    
    # Top participants for this group and period
    game_player_qs = GamePlayer.objects.filter(game_id=OuterRef('game_id'))
    total_players_subquery = Subquery(game_player_qs.values('game_id').annotate(c=Count('id')).values('c')[:1])
    winners_count_subquery = Subquery(game_player_qs.filter(win=True).values('game_id').annotate(c=Count('id')).values('c')[:1])
    extra_ball_subquery = Subquery(PlayersGameBall.objects.filter(player_id=OuterRef('id')).values('ball')[:1])

    players_period = GamePlayer.objects.filter(game__chat=chat, game__created_at__gte=start_date).select_related('user')
    
    players_annotated = players_period.annotate(
        game_total=Coalesce(total_players_subquery, 0),
        game_winners=Coalesce(winners_count_subquery, 0),
        extra=Coalesce(extra_ball_subquery, 0)
    )
    
    players_with_delta = players_annotated.annotate(
        delta=Case(
            When(win=True, then=2 * F('game_total') - F('game_winners')),
            default=-F('game_winners'),
            output_field=IntegerField()
        ) + F('extra')
    )
    
    top_winners = players_with_delta.values('user__full_name', 'user__mention').annotate(
        total_score=Coalesce(Sum('delta'), 0),
        games_count=Count('game', distinct=True)
    ).order_by('-total_score')[:50]
    
    top_players = []
    for entry in top_winners:
        top_players.append({
            'user': {'full_name': entry['user__full_name'], 'mention': entry['user__mention']},
            'score': entry['total_score'],
            'games_count': entry['games_count'],
        })

    return render(request, 'main/group_stats.html', {
        'chat': chat,
        'stats': {
            'games_count': games_count,
            'participants_count': participants_count,
        },
        'top_players': top_players,
        'period': period,
        'token': token
    })
