from datetime import timedelta

from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Sum, Count, Q, Subquery, OuterRef
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from .models import User, BlockedUser, Profile, Transfer, VipUser, Para, Geroy, Chat, Giveaway, Game, GamePlayer, GamePhase, DiamondBuyStars, TransferPrice
from .utils import parse_price_from_caption


@login_required
def dashboard(request):
    total_users = User.objects.filter(profile__isnull=False).count()
    total_vip = VipUser.objects.count()
    total_blocked = BlockedUser.objects.count()
    total_transfers = Transfer.objects.count()

    top_players = Profile.objects.select_related('user').order_by('-wins')[:10]
    richest = Profile.objects.select_related('user').order_by('-dollar')[:10]
    recent_transfers = Transfer.objects.select_related('from_user', 'to_user').order_by('-created_at')[:10]

    context = {
        'total_users': total_users,
        'total_vip': total_vip,
        'total_blocked': total_blocked,
        'total_transfers': total_transfers,
        'top_players': top_players,
        'richest': richest,
        'recent_transfers': recent_transfers,
    }
    return render(request, 'bot/dashboard.html', context)


@login_required
def users_list(request):
    query = request.GET.get('q', '')
    sort = request.GET.get('sort', '-id')

    sort_map = {
        'name': 'full_name',
        '-name': '-full_name',
        'dollar': 'profile__dollar',
        '-dollar': '-profile__dollar',
        'diamond': 'profile__diamond',
        '-diamond': '-profile__diamond',
        'wins': 'profile__wins',
        '-wins': '-profile__wins',
        'id': 'id',
        '-id': '-id',
    }
    order_by = sort_map.get(sort, '-id')

    users = User.objects.filter(profile__isnull=False).select_related('profile').order_by(order_by)

    if query:
        users = users.filter(
            Q(full_name__icontains=query) | Q(mention__icontains=query) | Q(user_id__icontains=query)
        )

    paginator = Paginator(users, 50)
    page = request.GET.get('page')
    users = paginator.get_page(page)

    return render(request, 'bot/users.html', {'users': users, 'query': query, 'sort': sort})


@login_required
def user_detail(request, user_id):
    user = get_object_or_404(User, id=user_id)
    profile = Profile.objects.filter(user=user).first()
    is_vip = VipUser.objects.filter(user=user).exists()
    is_blocked = BlockedUser.objects.filter(user=user).exists()
    transfers_sent = Transfer.objects.filter(from_user=user).order_by('-created_at')[:20]
    transfers_received = Transfer.objects.filter(to_user=user).order_by('-created_at')[:20]
    pairs = Para.objects.filter(Q(user1=user) | Q(user2=user)).select_related('user1', 'user2')[:10]

    context = {
        'user': user,
        'profile': profile,
        'is_vip': is_vip,
        'is_blocked': is_blocked,
        'transfers_sent': transfers_sent,
        'transfers_received': transfers_received,
        'pairs': pairs,
    }
    return render(request, 'bot/user_detail.html', context)


@login_required
def transfers_list(request):
    type_filter = request.GET.get('type', '')
    transfers = Transfer.objects.select_related('from_user', 'to_user').order_by('-created_at')

    if type_filter:
        transfers = transfers.filter(type=type_filter)

    paginator = Paginator(transfers, 50)
    page = request.GET.get('page')
    transfers = paginator.get_page(page)

    return render(request, 'bot/transfers.html', {'transfers': transfers, 'type_filter': type_filter})


@login_required
def vip_list(request):
    vips = VipUser.objects.select_related('user').order_by('-created_at')
    return render(request, 'bot/vip.html', {'vips': vips})


@login_required
def top_players(request):
    profiles = Profile.objects.select_related('user').order_by('-wins')
    paginator = Paginator(profiles, 50)
    page = request.GET.get('page')
    profiles = paginator.get_page(page)
    return render(request, 'bot/top.html', {'profiles': profiles})


@login_required
def blocked_list(request):
    query = request.GET.get('q', '')
    blocked = BlockedUser.objects.select_related('user').order_by('-created_at')

    if query:
        blocked = blocked.filter(
            Q(user__full_name__icontains=query) |
            Q(user__mention__icontains=query) |
            Q(user__user_id__icontains=query)
        )

    paginator = Paginator(blocked, 50)
    page = request.GET.get('page')
    blocked = paginator.get_page(page)

    return render(request, 'bot/blocked.html', {'blocked': blocked, 'query': query})


@login_required
def block_user(request):
    if request.method == 'POST':
        user_id_input = request.POST.get('user_id', '').strip()
        user = None

        if user_id_input.isdigit():
            user = User.objects.filter(user_id=int(user_id_input)).first()
        if not user:
            user = User.objects.filter(
                Q(full_name__icontains=user_id_input) | Q(mention__icontains=user_id_input)
            ).first()

        if not user:
            messages.error(request, f'Foydalanuvchi topilmadi: {user_id_input}')
        elif BlockedUser.objects.filter(user=user).exists():
            messages.warning(request, f'{user.full_name or user.mention} allaqachon bloklangan.')
        else:
            BlockedUser.objects.create(user=user)
            messages.success(request, f'{user.full_name or user.mention} bloklandi.')

    return redirect('blocked')


@login_required
def unblock_user(request, blocked_id):
    if request.method == 'POST':
        blocked = get_object_or_404(BlockedUser, id=blocked_id)
        name = blocked.user.full_name or blocked.user.mention
        blocked.delete()
        messages.success(request, f'{name} blokdan chiqarildi.')
    return redirect('blocked')


@login_required
def geroys_list(request):
    query = request.GET.get('q', '')
    level_filter = request.GET.get('level', '')
    geroys = Geroy.objects.select_related('user').order_by('-level', '-ball')

    if query:
        geroys = geroys.filter(
            Q(name__icontains=query) |
            Q(user__full_name__icontains=query) |
            Q(user__mention__icontains=query)
        )
    if level_filter.isdigit():
        geroys = geroys.filter(level=int(level_filter))

    paginator = Paginator(geroys, 50)
    page = request.GET.get('page')
    geroys = paginator.get_page(page)

    levels = Geroy.objects.values_list('level', flat=True).distinct().order_by('level')
    return render(request, 'bot/geroys.html', {'geroys': geroys, 'query': query, 'level_filter': level_filter, 'levels': levels})


@login_required
def giveaways_list(request):
    query = request.GET.get('q', '')
    sort = request.GET.get('sort', '-created_at')

    sort_map = {
        'total': 'total_amount',
        '-total': '-total_amount',
        'remaining': 'remaining_amount',
        '-remaining': '-remaining_amount',
        'date': 'created_at',
        '-date': '-created_at',
    }
    order_by = sort_map.get(sort, '-created_at')

    chat_title_sq = Chat.objects.filter(chat_id=OuterRef('chat_id')).values('title')[:1]
    giveaways = Giveaway.objects.select_related('creator').exclude(remaining_amount=0).annotate(
        chat_title=Subquery(chat_title_sq)
    ).order_by(order_by)

    if query:
        giveaways = giveaways.filter(
            Q(creator__full_name__icontains=query) |
            Q(creator__mention__icontains=query) |
            Q(creator__user_id__icontains=query)
        )

    paginator = Paginator(giveaways, 50)
    page = request.GET.get('page')
    giveaways = paginator.get_page(page)

    return render(request, 'bot/giveaways.html', {'giveaways': giveaways, 'query': query, 'sort': sort})


@login_required
def chats_list(request):
    query = request.GET.get('q', '')
    type_filter = request.GET.get('type', '')
    chats = Chat.objects.order_by('-created_at')

    if query:
        chats = chats.filter(Q(title__icontains=query) | Q(chat_id__icontains=query))
    if type_filter:
        chats = chats.filter(type=type_filter)

    paginator = Paginator(chats, 50)
    page = request.GET.get('page')
    chats = paginator.get_page(page)

    return render(request, 'bot/chats.html', {'chats': chats, 'query': query, 'type_filter': type_filter})


@login_required
def active_games(request):
    """1-bosqich: faol o'yini bor guruhlar ro'yxati"""
    sort = request.GET.get('sort', '-players')

    chat_ids = Game.objects.filter(is_active=True).values_list('chat_id', flat=True).distinct()
    chats = Chat.objects.filter(id__in=chat_ids).annotate(
        active_count=Count('games', filter=Q(games__is_active=True)),
        total_players=Count('games__players', filter=Q(games__is_active=True)),
    )

    sort_map = {
        'players': 'total_players',
        '-players': '-total_players',
        'games': 'active_count',
        '-games': '-active_count',
        'name': 'title',
        '-name': '-title',
    }
    order_by = sort_map.get(sort, '-total_players')
    chats = chats.order_by(order_by)

    total_games = Game.objects.filter(is_active=True).count()

    paginator = Paginator(chats, 30)
    page = request.GET.get('page')
    chats = paginator.get_page(page)

    return render(request, 'bot/active_games.html', {
        'chats': chats,
        'total_games': total_games,
        'sort': sort,
    })


@login_required
def active_games_chat(request, chat_id):
    """2-bosqich: guruhdagi faol o'yinlar tafsiloti bilan"""
    chat = get_object_or_404(Chat, id=chat_id)
    games = Game.objects.filter(chat=chat, is_active=True).select_related('creator').order_by('-created_at')

    games_data = []
    for game in games:
        current_phase = game.phases.order_by('-number').first()
        players = game.players.select_related('user').order_by('-is_alive', 'role')
        games_data.append({
            'game': game,
            'current_phase': current_phase,
            'players': players,
            'alive_count': players.filter(is_alive=True).count(),
            'dead_count': players.filter(is_alive=False).count(),
        })

    return render(request, 'bot/active_games_chat.html', {
        'chat': chat,
        'games_data': games_data,
    })


@login_required
def active_game_detail(request, game_id):
    """3-bosqich: o'yin tafsiloti — o'yinchilar"""
    game = get_object_or_404(Game.objects.select_related('chat', 'creator'), id=game_id)
    current_phase = game.phases.order_by('-number').first()
    players = game.players.select_related('user').order_by('-is_alive', 'role')

    return render(request, 'bot/active_game_detail.html', {
        'game': game,
        'current_phase': current_phase,
        'players': players,
        'alive_count': players.filter(is_alive=True).count(),
        'dead_count': players.filter(is_alive=False).count(),
    })


def _ensure_prices_cached(transfers_qs):
    """Caption'dan narxlarni parse qilib TransferPrice'ga saqlaydi (keshlanmaganlarni)."""
    cached_ids = set(TransferPrice.objects.filter(
        transfer__in=transfers_qs
    ).values_list('transfer_id', flat=True))

    to_create = []
    for t in transfers_qs.exclude(id__in=cached_ids).exclude(caption=''):
        price = parse_price_from_caption(t.caption)
        if price:
            to_create.append(TransferPrice(transfer=t, price=price))

    if to_create:
        TransferPrice.objects.bulk_create(to_create, ignore_conflicts=True)


def _sales_stats(period_start):
    """Berilgan sanadan boshlab savdo statistikasini qaytaradi."""
    qs = TransferPrice.objects.filter(transfer__created_at__gte=period_start)
    agg = qs.aggregate(total=Sum('price'), count=Count('id'))
    return {
        'total': agg['total'] or 0,
        'count': agg['count'] or 0,
    }


@login_required
def sales_analytics(request):
    """Savdo analitikasi: haftalik, oylik, yillik hisobotlar."""
    now = timezone.now()
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

    # captionli transferlarni keshla
    captioned = Transfer.objects.exclude(caption='').exclude(caption__isnull=True)
    _ensure_prices_cached(captioned)

    # Stars statistikasi
    stars_week = DiamondBuyStars.objects.filter(created_at__gte=week_start).aggregate(
        total_stars=Sum('stars'), total_diamonds=Sum('amount'), count=Count('id')
    )
    stars_month = DiamondBuyStars.objects.filter(created_at__gte=month_start).aggregate(
        total_stars=Sum('stars'), total_diamonds=Sum('amount'), count=Count('id')
    )
    stars_year = DiamondBuyStars.objects.filter(created_at__gte=year_start).aggregate(
        total_stars=Sum('stars'), total_diamonds=Sum('amount'), count=Count('id')
    )

    # So'nggi savdolar listi (narxi bor transferlar)
    tab = request.GET.get('tab', 'sales')
    page_num = request.GET.get('page')

    if tab == 'stars':
        items = DiamondBuyStars.objects.order_by('-created_at')
        paginator = Paginator(items, 50)
        items = paginator.get_page(page_num)
    else:
        items = TransferPrice.objects.select_related(
            'transfer', 'transfer__from_user', 'transfer__to_user'
        ).order_by('-transfer__created_at')
        paginator = Paginator(items, 50)
        items = paginator.get_page(page_num)

    context = {
        'week': _sales_stats(week_start),
        'month': _sales_stats(month_start),
        'year': _sales_stats(year_start),
        'stars_week': stars_week,
        'stars_month': stars_month,
        'stars_year': stars_year,
        'items': items,
        'tab': tab,
    }
    return render(request, 'bot/sales.html', context)


@login_required
def edit_transfer_price(request, price_id):
    """Keshlanagan narxni qo'lda tahrirlash."""
    tp = get_object_or_404(TransferPrice, id=price_id)
    if request.method == 'POST':
        new_price = request.POST.get('price', '').replace(' ', '').replace(',', '')
        if new_price.isdigit() and int(new_price) > 0:
            tp.price = int(new_price)
            tp.is_manual = True
            tp.save()
            messages.success(request, f"Narx {tp.price:,} so'mga o'zgartirildi.")
        else:
            messages.error(request, "Noto'g'ri narx kiritildi.")
    return redirect('sales')
