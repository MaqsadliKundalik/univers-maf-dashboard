from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum, Count, F, Case, When, IntegerField, OuterRef, Subquery
from django.db.models.functions import Coalesce
from django.core.cache import cache
from bot.models import VipChats, Chat, User, Game, Profile, GamePlayer, PlayersGameBall

def index(request):
    # Try to get cached data
    cache_key = 'index_page_data_v2'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        stats = cached_data['stats']
        top_players = cached_data['top_players']
    else:
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # All-time Global Stats
        stats = {
            'users_count': User.objects.count(),
            'chats_count': Chat.objects.count(),
            'games_count': Game.objects.count(),
        }
        
        # Complex Scoring Logic for Top 30 Players of the Month
        game_player_qs = GamePlayer.objects.filter(game_id=OuterRef('game_id'))
        
        total_players_subquery = Subquery(
            game_player_qs.values('game_id')
            .annotate(c=Count('id'))
            .values('c')[:1]
        )
        
        winners_count_subquery = Subquery(
            game_player_qs.filter(win=True)
            .values('game_id')
            .annotate(c=Count('id'))
            .values('c')[:1]
        )
        
        extra_ball_subquery = Subquery(
            PlayersGameBall.objects.filter(player_id=OuterRef('id'))
            .values('ball')[:1]
        )

        players_this_month = GamePlayer.objects.filter(game__created_at__gte=month_start).select_related('user')
        
        # Annotate with game stats and extra balls, ensuring no None values
        players_annotated = players_this_month.annotate(
            game_total=Coalesce(total_players_subquery, 0),
            game_winners=Coalesce(winners_count_subquery, 0),
            extra=Coalesce(extra_ball_subquery, 0)
        )
        
        # Calculate delta per game record with Coalesce to avoid None issues
        players_with_delta = players_annotated.annotate(
            delta=Case(
                When(win=True, then=2 * F('game_total') - F('game_winners')),
                default=-F('game_winners'),
                output_field=IntegerField()
            ) + F('extra')
        )
        
        # Sum up deltas per user
        top_winners = players_with_delta.values('user__full_name', 'user__mention').annotate(
            total_score=Coalesce(Sum('delta'), 0),
            monthly_games=Count('game', distinct=True)
        ).order_by('-total_score')[:30]
        
        top_players = []
        for entry in top_winners:
            top_players.append({
                'user': {
                    'full_name': entry['user__full_name'],
                    'mention': entry['user__mention'],
                },
                'score': entry['total_score'],
                'games_count': entry['monthly_games'],
            })
        
        # Cache for 30 minutes (1800 seconds)
        cache.set(cache_key, {'stats': stats, 'top_players': top_players}, 1800)

    # VIP Chats
    vip_records = VipChats.objects.filter(is_active=True)
    vip_chat_ids = [record.chat_id for record in vip_records]
    vip_chats = Chat.objects.filter(chat_id__in=vip_chat_ids)

    return render(request, 'main/index.html', {
        'vip_chats': vip_chats, 
        'stats': stats,
        'top_players': top_players
    })
