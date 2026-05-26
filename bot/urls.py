from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('users/', views.users_list, name='users'),
    path('users/<int:user_id>/', views.user_detail, name='user_detail'),
    path('transfers/', views.transfers_list, name='transfers'),
    path('vip/', views.vip_list, name='vip'),
    path('top/', views.top_players, name='top'),
    path('blocked/', views.blocked_list, name='blocked'),
    path('blocked/block/', views.block_user, name='block_user'),
    path('blocked/unblock/<int:blocked_id>/', views.unblock_user, name='unblock_user'),
    path('geroys/', views.geroys_list, name='geroys'),
    path('giveaways/', views.giveaways_list, name='giveaways'),
    path('chats/', views.chats_list, name='chats'),
    path('group-owners/', views.group_owners_list, name='group_owners'),
    path('group-owners/create/', views.group_owner_create, name='group_owner_create'),
    path('group-owners/user-suggestions/', views.group_owner_user_suggestions, name='group_owner_user_suggestions'),
    path('group-owners/chat-suggestions/', views.group_owner_chat_suggestions, name='group_owner_chat_suggestions'),
    path('group-owners/<int:owner_id>/edit/', views.group_owner_edit, name='group_owner_edit'),
    path('group-owners/<int:owner_id>/toggle/', views.group_owner_toggle, name='group_owner_toggle'),
    path('games/', views.active_games, name='active_games'),
    path('games/chat/<int:chat_id>/', views.active_games_chat, name='active_games_chat'),
    path('games/<int:game_id>/', views.active_game_detail, name='active_game_detail'),
    path('sales/', views.sales_analytics, name='sales'),
    path('sales/edit/<int:price_id>/', views.edit_transfer_price, name='edit_transfer_price'),
    path('sales/cancel/<int:price_id>/', views.cancel_transfer_price, name='cancel_transfer_price'),
]
