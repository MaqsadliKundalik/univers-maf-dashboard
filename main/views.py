from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum, Count, F, Case, When, IntegerField, OuterRef, Subquery
from django.db.models.functions import Coalesce
from bot.models import VipChats, Chat, User, Game, Profile, GamePlayer, PlayersGameBall

def index(request):
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # VIP Chats
    vip_records = VipChats.objects.filter(is_active=True)
    vip_chat_ids = [record.chat_id for record in vip_records]
    vip_chats = Chat.objects.filter(chat_id__in=vip_chat_ids)
    
    # Monthly Global Stats
    monthly_games = Game.objects.filter(created_at__gte=month_start)
    games_count = monthly_games.count()
    
    monthly_users_count = GamePlayer.objects.filter(game__created_at__gte=month_start).values('user_id').distinct().count()
    monthly_chats_count = monthly_games.values('chat_id').distinct().count()
    
    stats = {
        'users_count': monthly_users_count,
        'chats_count': monthly_chats_count,
        'games_count': games_count,
    }
    
    # Complex Scoring Logic for Top Players
    # Subqueries to get per-game stats
    game_player_qs = GamePlayer.objects.filter(game_id=OuterRef('game_id'))
    total_players_subquery = Subquery(game_player_qs.values('game_id').annotate(c=Count('id')).values('c')[:1])
    winners_count_subquery = Subquery(game_player_qs.filter(win=True).values('game_id').annotate(c=Count('id')).values('c')[:1])
    extra_ball_subquery = Subquery(PlayersGameBall.objects.filter(player_id=OuterRef('id')).values('ball')[:1])

    players_this_month = GamePlayer.objects.filter(game__created_at__gte=month_start).select_related('user')
    
    # Annotate with game stats and extra balls
    players_annotated = players_this_month.annotate(
        game_total=total_players_subquery,
        game_winners=winners_count_subquery,
        extra=Coalesce(extra_ball_subquery, 0)
    )
    
    # Calculate delta per game record
    players_with_delta = players_annotated.annotate(
        delta=Case(
            When(win=True, then=2 * F('game_total') - F('game_winners')),
            default=-F('game_winners'),
            output_field=IntegerField()
        ) + F('extra')
    )
    
    # Sum up deltas per user
    top_winners = players_with_delta.values('user__full_name', 'user__mention').annotate(
        total_score=Sum('delta'),
        monthly_games=Count('game', distinct=True)
    ).order_by('-total_score')[:10]
    
    formatted_top_players = []
    for entry in top_winners:
        formatted_top_players.append({
            'user': {
                'full_name': entry['user__full_name'],
                'mention': entry['user__mention'],
            },
            'score': entry['total_score'],
            'games_count': entry['monthly_games'],
        })

    return render(request, 'main/index.html', {
        'vip_chats': vip_chats, 
        'stats': stats,
        'top_players': formatted_top_players
    })
