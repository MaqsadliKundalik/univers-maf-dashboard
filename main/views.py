from datetime import timedelta, timezone as dt_timezone

from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import DatabaseError
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
    GroupBalance,
    Geroy,
    GroupIncome,
    GroupSubscription,
    Para,
    PlayersGameBall,
    Profile,
    SubscriptionConfig,
    Transfer,
    User,
    VipUser,
    ActiveRole,
    XCoinWallet,
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
    start_date = timezone.now() - timedelta(days=30)
    cache_key = f'group_stats_{chat.chat_id}_last_30_days'
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
        ).order_by('-total_score')[:200]

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

    top_players_page = Paginator(top_players, 20).get_page(request.GET.get('top_page'))
    for index, player in enumerate(top_players_page.object_list, start=top_players_page.start_index()):
        player['rank'] = index

    try:
        incomes_qs = GroupIncome.objects.filter(
            chat_id=chat.chat_id,
            created_at__gte=start_date,
        ).order_by('-created_at')
        total_diamond = incomes_qs.aggregate(Sum('amount'))['amount__sum'] or 0
        transfer_history_page = Paginator(incomes_qs, 20).get_page(request.GET.get('transfers_page'))
        recent_incomes = list(transfer_history_page)
    except DatabaseError:
        total_diamond = 0
        recent_incomes = []
        transfer_history_page = Paginator([], 20).get_page(1)

    try:
        group_balance = GroupBalance.objects.filter(chat_id=chat.chat_id).first()
        subscription = GroupSubscription.objects.filter(chat_id=chat.chat_id).first()
        subscription_config = SubscriptionConfig.objects.order_by('id').first()
    except Exception:
        group_balance = None
        subscription = None
        subscription_config = None

    now = timezone.now()
    balance_amount = group_balance.balance if group_balance else 0
    subscription_expires_at = subscription.expires_at if subscription else None
    if subscription_expires_at and timezone.is_naive(subscription_expires_at):
        subscription_expires_at = timezone.make_aware(subscription_expires_at, dt_timezone.utc)
    subscription_is_active = bool(subscription_expires_at and subscription_expires_at > now)
    subscription_days_left = (subscription_expires_at - now).days if subscription_is_active else 0
    if subscription_is_active:
        subscription_status = 'Faol'
    elif subscription_expires_at:
        subscription_status = 'Tugagan'
    else:
        subscription_status = "Yo'q"

    users_map = {u.user_id: u for u in User.objects.filter(user_id__in=[inc.user_id for inc in recent_incomes])}
    transfer_history = []
    for inc in recent_incomes:
        u = users_map.get(inc.user_id)
        transfer_history.append({
            'user': u.full_name if u and u.full_name else (u.mention if u else f"ID: {inc.user_id}"),
            'amount': inc.amount,
            'created_at': inc.created_at,
        })

    return render(request, 'main/group_stats.html', {
        'chat': chat,
        'stats': stats,
        'top_players': top_players_page,
        'total_diamond': total_diamond,
        'transfer_history': transfer_history,
        'transfer_history_page': transfer_history_page,
        'stats_period_label': "So'nggi 30 kun",
        'group_account': {
            'balance': balance_amount,
            'subscription_status': subscription_status,
            'subscription_is_active': subscription_is_active,
            'subscription_expires_at': subscription_expires_at,
            'subscription_days_left': subscription_days_left,
            'subscription_price': subscription_config.price if subscription_config else 80,
            'subscription_duration_days': subscription_config.duration_days if subscription_config else 30,
        },
    })


def user_profile(request, token):
    link = get_object_or_404(UserProfileLink, token=token)
    if link.is_expired():
        return render(request, 'main/expired.html', {'subject': link.user}, status=403)

    user = link.user
    profile = Profile.objects.filter(user=user).first()
    xcoin_wallet = XCoinWallet.objects.filter(user=user).first()
    geroy = Geroy.objects.filter(user=user).first()
    active_roles = ActiveRole.objects.filter(profile=profile, is_active=True).order_by('-created_at') if profile else []
    is_vip = VipUser.objects.filter(user=user).exists()
    is_blocked = BlockedUser.objects.filter(user=user).exists()
    pairs = Para.objects.filter(Q(user1=user) | Q(user2=user)).select_related('user1', 'user2')[:10]
    transfers = Transfer.objects.filter(Q(from_user=user) | Q(to_user=user)).select_related(
        'from_user', 'to_user'
    ).order_by('-created_at')
    transfers_page = Paginator(transfers, 8).get_page(request.GET.get('transfers_page'))

    games = GamePlayer.objects.filter(user=user).select_related('game', 'game__chat').order_by('-joined_at')[:20]

    month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    try:
        score = _players_score_queryset(GamePlayer.objects.filter(user=user, game__created_at__gte=month_start)).aggregate(
            total=Coalesce(Sum('delta'), 0)
        )['total'] or 0
    except DatabaseError:
        score = 0

    try:
        group_rows = list(GroupIncome.objects.filter(user_id=user.user_id).values('chat_id').annotate(
            total=Sum('amount')
        ).filter(total__gt=0).order_by('-total')[:10])
    except DatabaseError:
        group_rows = list(Transfer.objects.filter(
            Q(from_user=user) | Q(to_user=user),
            chat_id__isnull=False,
        ).values('chat_id').annotate(total=Count('id')).order_by('-total')[:10])

    chats_map = {chat.chat_id: chat for chat in Chat.objects.filter(chat_id__in=[row['chat_id'] for row in group_rows])}
    groups = [{'chat': chats_map.get(row['chat_id']), 'chat_id': row['chat_id'], 'total': row['total']} for row in group_rows]

    return render(request, 'main/user_profile.html', {
        'user': user,
        'profile': profile,
        'xcoin_wallet': xcoin_wallet,
        'geroy': geroy,
        'active_roles': active_roles,
        'is_vip': is_vip,
        'is_blocked': is_blocked,
        'pairs': pairs,
        'transfers_page': transfers_page,
        'games': games,
        'score': score,
        'groups': groups,
    })
