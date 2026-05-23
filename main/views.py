from datetime import timedelta

from django.core.cache import cache
from django.db.models import Case, Count, F, IntegerField, OuterRef, Q, Subquery, Sum, When
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from bot.models import (
    BlockedUser,
    Chat,
    Game,
    GamePlayer,
    Geroy,
    GroupIncome,
    Para,
    PlayersGameBall,
    Profile,
    Transfer,
    User,
    VipUser,
)
from .models import GroupStatsLink, UserProfileLink


def index(request):
    stats = cache.get('public_index_stats')
    if not stats:
        stats = {
            'users_count': User.objects.filter(profile__isnull=False).count(),
            'chats_count': Chat.objects.count(),
            'games_count': Game.objects.count(),
        }
        cache.set('public_index_stats', stats, 1800)

    top_players = Profile.objects.select_related('user').order_by('-wins')[:10]
    return render(request, 'main/index.html', {'stats': stats, 'top_players': top_players})


def generate_group_link(request):
    chat_id = request.GET.get('chat_id')
    if not chat_id:
        return JsonResponse({'error': 'chat_id is required'}, status=400)

    chat = Chat.objects.filter(chat_id=chat_id).first()
    if not chat:
        return JsonResponse({'error': 'Chat not found'}, status=404)

    now = timezone.now()
    link = GroupStatsLink.objects.filter(chat=chat, expires_at__gt=now).order_by('-expires_at').first()
    if not link:
        link = GroupStatsLink.objects.create(chat=chat, expires_at=now + timedelta(days=1))

    url = request.build_absolute_uri(f'/group/{link.token}/')
    return JsonResponse({'url': url, 'expires_at': link.expires_at.isoformat()})


def generate_user_profile_link(request):
    user_id = request.GET.get('user_id')
    if not user_id:
        return JsonResponse({'error': 'user_id is required'}, status=400)

    user = User.objects.filter(user_id=user_id).first()
    if not user:
        return JsonResponse({'error': 'User not found'}, status=404)

    now = timezone.now()
    link = UserProfileLink.objects.filter(user=user, expires_at__gt=now).order_by('-expires_at').first()
    if not link:
        link = UserProfileLink.objects.create(user=user, expires_at=now + timedelta(days=1))

    url = request.build_absolute_uri(f'/profile/{link.token}/')
    return JsonResponse({'url': url, 'expires_at': link.expires_at.isoformat()})


def _period_start(period):
    now = timezone.now()
    if period == 'day':
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == 'week':
        start = now - timedelta(days=now.weekday())
        return start.replace(hour=0, minute=0, second=0, microsecond=0)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _players_score_queryset(players_qs):
    game_player_qs = GamePlayer.objects.filter(game_id=OuterRef('game_id'))
    total_players = Subquery(game_player_qs.values('game_id').annotate(c=Count('id')).values('c')[:1])
    winners_count = Subquery(
        game_player_qs.filter(win=True).values('game_id').annotate(c=Count('id')).values('c')[:1]
    )
    extra_ball = Subquery(PlayersGameBall.objects.filter(player_id=OuterRef('id')).values('ball')[:1])

    return players_qs.annotate(
        game_total=Coalesce(total_players, 0),
        game_winners=Coalesce(winners_count, 0),
        extra=Coalesce(extra_ball, 0),
    ).annotate(
        delta=Case(
            When(win=True, then=2 * F('game_total') - F('game_winners')),
            default=-F('game_winners'),
            output_field=IntegerField(),
        ) + F('extra')
    )


def group_stats(request, token):
    link = get_object_or_404(GroupStatsLink, token=token)
    if link.is_expired():
        return render(request, 'main/expired.html', {'subject': link.chat}, status=403)

    chat = link.chat
    period = request.GET.get('period', 'month')
    start_date = _period_start(period)
    cache_key = f'group_stats_{chat.chat_id}_{period}'
    cached_data = cache.get(cache_key)

    if cached_data:
        stats = cached_data['stats']
        top_players = cached_data['top_players']
    else:
        group_games = Game.objects.filter(chat=chat, created_at__gte=start_date)
        players_period = GamePlayer.objects.filter(game__chat=chat, game__created_at__gte=start_date).select_related('user')
        scored_players = _players_score_queryset(players_period)
        top_winners = scored_players.values('user__full_name', 'user__mention').annotate(
            total_score=Coalesce(Sum('delta'), 0),
            games_count=Count('game', distinct=True),
        ).order_by('-total_score')[:50]

        top_players = [
            {
                'user': {'full_name': entry['user__full_name'], 'mention': entry['user__mention']},
                'score': entry['total_score'],
                'games_count': entry['games_count'],
            }
            for entry in top_winners
        ]
        stats = {
            'games_count': group_games.count(),
            'participants_count': players_period.values('user_id').distinct().count(),
        }
        cache.set(cache_key, {'stats': stats, 'top_players': top_players}, 1800)

    total_diamond = GroupIncome.objects.filter(chat_id=chat.chat_id).aggregate(Sum('amount'))['amount__sum'] or 0
    recent_incomes = GroupIncome.objects.filter(chat_id=chat.chat_id).order_by('-created_at')[:50]
    users_map = {u.user_id: u for u in User.objects.filter(user_id__in=[inc.user_id for inc in recent_incomes])}
    transfer_history = [
        {
            'user': users_map.get(inc.user_id).full_name
            if users_map.get(inc.user_id) and users_map.get(inc.user_id).full_name
            else (users_map.get(inc.user_id).mention if users_map.get(inc.user_id) else f"ID: {inc.user_id}"),
            'amount': inc.amount,
            'created_at': inc.created_at,
        }
        for inc in recent_incomes
    ]

    return render(request, 'main/group_stats.html', {
        'chat': chat,
        'stats': stats,
        'top_players': top_players,
        'period': period,
        'total_diamond': total_diamond,
        'transfer_history': transfer_history,
    })


def user_profile(request, token):
    link = get_object_or_404(UserProfileLink, token=token)
    if link.is_expired():
        return render(request, 'main/expired.html', {'subject': link.user}, status=403)

    user = link.user
    profile = Profile.objects.filter(user=user).first()
    geroy = Geroy.objects.filter(user=user).first()
    is_vip = VipUser.objects.filter(user=user).exists()
    is_blocked = BlockedUser.objects.filter(user=user).exists()
    pairs = Para.objects.filter(Q(user1=user) | Q(user2=user)).select_related('user1', 'user2')[:10]
    transfers_sent = Transfer.objects.filter(from_user=user).order_by('-created_at')[:10]
    transfers_received = Transfer.objects.filter(to_user=user).order_by('-created_at')[:10]

    games = GamePlayer.objects.filter(user=user).select_related('game', 'game__chat').order_by('-joined_at')[:20]
    score = _players_score_queryset(GamePlayer.objects.filter(user=user)).aggregate(total=Coalesce(Sum('delta'), 0))['total']
    group_incomes = GroupIncome.objects.filter(user_id=user.user_id).values('chat_id').annotate(
        total=Sum('amount')
    ).filter(total__gt=0).order_by('-total')[:10]
    chats_map = {chat.chat_id: chat for chat in Chat.objects.filter(chat_id__in=[inc['chat_id'] for inc in group_incomes])}
    groups = [{'chat': chats_map.get(inc['chat_id']), 'chat_id': inc['chat_id'], 'total': inc['total']} for inc in group_incomes]

    return render(request, 'main/user_profile.html', {
        'user': user,
        'profile': profile,
        'geroy': geroy,
        'is_vip': is_vip,
        'is_blocked': is_blocked,
        'pairs': pairs,
        'transfers_sent': transfers_sent,
        'transfers_received': transfers_received,
        'games': games,
        'score': score,
        'groups': groups,
    })
