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
    path('games/', views.active_games, name='active_games'),
    path('games/chat/<int:chat_id>/', views.active_games_chat, name='active_games_chat'),
    path('games/<int:game_id>/', views.active_game_detail, name='active_game_detail'),
    path('sales/', views.sales_analytics, name='sales'),
    path('sales/edit/<int:price_id>/', views.edit_transfer_price, name='edit_transfer_price'),
]
