from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import User, BlockedUser, Profile, Transfer, VipUser, Para, Geroy, Chat, Giveaway


@login_required
def dashboard(request):
    total_users = User.objects.count()
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

    users = User.objects.prefetch_related('profile').order_by(order_by)

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

    giveaways = Giveaway.objects.select_related('creator').order_by(order_by)

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
