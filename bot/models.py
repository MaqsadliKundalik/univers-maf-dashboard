from django.db import models


class User(models.Model):
    id = models.BigAutoField(primary_key=True)
    user_id = models.BigIntegerField()
    full_name = models.CharField(max_length=100, default="", null=True, blank=True)
    is_bot = models.BooleanField(default=False)
    mention = models.TextField()

    class Meta:
        db_table = "user"
        managed = False

    def __str__(self):
        return self.full_name or str(self.user_id)


class BlockedUser(models.Model):
    user = models.ForeignKey(User, related_name="blocked_users", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "blocked_user"
        managed = False

    def __str__(self):
        return f"Blocked: {self.user}"


class Profile(models.Model):
    user = models.OneToOneField(User, related_name="profile", on_delete=models.CASCADE)
    dollar = models.BigIntegerField(default=0)
    diamond = models.BigIntegerField(default=0)
    himoya = models.IntegerField(default=0)
    hujjat = models.IntegerField(default=0)
    qotildan_himoya = models.IntegerField(default=0)
    osishdan_himoya = models.IntegerField(default=0)
    miltiq = models.IntegerField(default=0)
    doridan_himoya = models.IntegerField(default=0)
    maska = models.IntegerField(default=0)
    wins = models.BigIntegerField(default=0)
    slip_himoya = models.IntegerField(default=0)
    geroy_himoya = models.IntegerField(default=0)
    games_count = models.BigIntegerField(default=0)
    on_himoya = models.BooleanField(default=True)
    on_hujjat = models.BooleanField(default=True)
    on_qotildan_himoya = models.BooleanField(default=True)
    on_osishdan_himoya = models.BooleanField(default=True)
    on_miltiq = models.BooleanField(default=True)
    on_doridan_himoya = models.BooleanField(default=True)
    on_maska = models.BooleanField(default=True)
    on_slip_himoya = models.BooleanField(default=True)
    on_geroy_himoya = models.BooleanField(default=True)

    class Meta:
        db_table = "profile"
        managed = False

    def __str__(self):
        return f"Profile: {self.user}"


class ActiveRole(models.Model):
    profile = models.ForeignKey(Profile, related_name="active_roles", on_delete=models.CASCADE)
    role = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "activerole"
        managed = False

    def __str__(self):
        return f"{self.role} - {self.profile}"


class Transfer(models.Model):
    id = models.BigAutoField(primary_key=True)
    from_user = models.ForeignKey(User, related_name="transfers_from", on_delete=models.CASCADE)
    to_user = models.ForeignKey(User, related_name="transfers_to", on_delete=models.CASCADE)
    amount = models.BigIntegerField()
    type = models.CharField(max_length=50)  # "diamond", "dollar"
    caption = models.CharField(max_length=100, default="", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "transfers"
        managed = False

    def __str__(self):
        return f"{self.from_user} → {self.to_user}: {self.amount} {self.type}"


class DiamondBuyStars(models.Model):
    user_id = models.BigIntegerField(unique=True)
    amount = models.IntegerField()
    stars = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "diamondbuystars"
        managed = False

    def __str__(self):
        return f"User {self.user_id}: {self.amount} 💎 = {self.stars} ⭐"


class TransferPrice(models.Model):
    """Transferdagi savdo narxini keshlaydigan model (managed=True — Django boshqaradi)"""
    transfer = models.OneToOneField(Transfer, related_name="cached_price", on_delete=models.CASCADE)
    price = models.BigIntegerField()  # so'mdagi narx
    is_manual = models.BooleanField(default=False)  # qo'lda tahrirlangan
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "transfer_price"

    def __str__(self):
        return f"Transfer #{self.transfer_id}: {self.price:,} so'm"


class VipUser(models.Model):
    user = models.OneToOneField(User, related_name="vip", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vipuser"
        managed = False

    def __str__(self):
        return f"VIP: {self.user}"


class Para(models.Model):
    user1 = models.ForeignKey(User, related_name="paralar1", on_delete=models.CASCADE)
    user2 = models.ForeignKey(User, related_name="paralar2", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "paralar"
        managed = False

    def __str__(self):
        return f"{self.user1} & {self.user2}"


class Geroy(models.Model):
    user = models.ForeignKey(User, related_name="geroy", on_delete=models.CASCADE)
    name = models.CharField(max_length=70)
    patron = models.IntegerField(default=10)
    level = models.IntegerField(default=1)
    himoya = models.IntegerField(default=0)
    ball = models.IntegerField(default=0)

    class Meta:
        db_table = "geroys"
        managed = False

    def __str__(self):
        return f"{self.name} (lv.{self.level}) — {self.user}"

    @property
    def min_dmg(self):
        return 40 + (self.level - 1) * 7

    @property
    def max_dmg(self):
        return 40 + self.level * 7

    @property
    def is_max_dmg(self):
        return self.min_dmg >= 100

    @property
    def max_himoya(self):
        return int(10 * (self.level / 1.2))

    @property
    def next_level_balls(self):
        return 1100 * self.level

    @property
    def progress_percent(self):
        needed = 1100 * self.level
        prev = 1100 * (self.level - 1)
        if needed == prev:
            return 100
        return min(100, int((self.ball - prev) / (needed - prev) * 100))


class Giveaway(models.Model):
    id = models.BigAutoField(primary_key=True)
    creator = models.ForeignKey(User, related_name="giveaways", on_delete=models.CASCADE)
    chat_id = models.BigIntegerField()
    message_id = models.BigIntegerField()
    total_amount = models.BigIntegerField()
    remaining_amount = models.BigIntegerField()
    collected_users = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "giveaway"
        managed = False

    def __str__(self):
        return f"Giveaway #{self.id} by {self.creator}"

    @property
    def distributed_amount(self):
        return self.total_amount - self.remaining_amount

    @property
    def collected_count(self):
        return len(self.collected_users) if self.collected_users else 0


class Game(models.Model):
    id = models.BigAutoField(primary_key=True)
    chat = models.ForeignKey('Chat', related_name="games", on_delete=models.CASCADE)
    creator = models.ForeignKey(User, related_name="created_games", on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    message_id = models.BigIntegerField()
    phase = models.CharField(max_length=10, default="waiting")  # waiting / night / day / end
    mode = models.CharField(max_length=20, default="classic")
    bot_id = models.BigIntegerField(null=True)

    class Meta:
        db_table = "game"
        managed = False

    def __str__(self):
        return f"Game #{self.id} ({self.phase})"


class GamePlayer(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, related_name="game_players", on_delete=models.CASCADE)
    game = models.ForeignKey(Game, related_name="players", on_delete=models.CASCADE)
    role = models.CharField(max_length=70)
    is_alive = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now=True)
    deaded_at = models.DateTimeField(auto_now=True)
    is_sayed_last_word = models.BooleanField(default=False)
    can_heal_self = models.BooleanField(default=True)
    can_protection_self = models.BooleanField(default=True)
    can_document_self = models.BooleanField(default=True)
    can_investigate_self = models.BooleanField(default=True)
    can_osishdan_himoya = models.BooleanField(default=True)
    can_osishdan_himoya_adv = models.BooleanField(default=True)
    can_slip_himoya = models.BooleanField(default=True)
    is_sleep = models.BooleanField(default=False)
    is_osilmas = models.BooleanField(default=False)
    osildi = models.BooleanField(default=False)
    missed_nights = models.BigIntegerField(default=0)
    should_choose_card = models.BooleanField(default=False)
    is_really_winner = models.BooleanField(default=False)
    last_visited_user_id = models.BigIntegerField(null=True)
    maxsus_raqam = models.BigIntegerField(null=True)
    win = models.BooleanField(default=False)
    is_actioned = models.BooleanField(default=False)
    life = models.IntegerField(default=100)
    team = models.CharField(max_length=20, null=True)

    class Meta:
        db_table = "gameplayer"
        managed = False

    def __str__(self):
        return f"{self.user} — {self.role}"


class GamePhase(models.Model):
    id = models.BigAutoField(primary_key=True)
    game = models.ForeignKey(Game, related_name="phases", on_delete=models.CASCADE)
    phase_type = models.CharField(max_length=10)  # day / night
    number = models.BigIntegerField()
    started_at = models.DateTimeField(auto_now_add=True)
    is_end = models.BooleanField(default=False)

    class Meta:
        db_table = "gamephase"
        managed = False

    def __str__(self):
        return f"Phase {self.phase_type} #{self.number} (Game #{self.game_id})"


class Vote(models.Model):
    id = models.BigAutoField(primary_key=True)
    phase = models.ForeignKey(GamePhase, related_name="votes", on_delete=models.CASCADE)
    voter = models.ForeignKey(GamePlayer, related_name="votes_given", on_delete=models.CASCADE)
    target = models.ForeignKey(GamePlayer, related_name="votes_received", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vote"
        managed = False


class Action(models.Model):
    id = models.BigAutoField(primary_key=True)
    phase = models.ForeignKey(GamePhase, related_name="actions", on_delete=models.CASCADE)
    actor = models.ForeignKey(GamePlayer, related_name="actions_made", on_delete=models.CASCADE)
    target = models.ForeignKey(GamePlayer, related_name="actions_received", on_delete=models.CASCADE)
    action_type = models.CharField(max_length=20)  # kill, heal, investigate
    result = models.CharField(max_length=100, null=True)
    with_miltiq = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "action"
        managed = False


class PlayersGameBall(models.Model):
    player = models.ForeignKey(GamePlayer, related_name="player_game_ball", on_delete=models.CASCADE)
    game = models.ForeignKey(Game, related_name="players_ball", on_delete=models.CASCADE)
    ball = models.IntegerField(default=0)

    class Meta:
        db_table = "playersgameball"
        managed = False


class GazabdorPick(models.Model):
    actor = models.ForeignKey(GamePlayer, related_name="gazabdor_actions", on_delete=models.CASCADE)
    target = models.ForeignKey(GamePlayer, related_name="gazabdor_targets_back", on_delete=models.CASCADE)
    phase = models.ForeignKey(GamePhase, related_name="gazabdor_picks", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gazabdorpick"
        managed = False
        unique_together = (("actor", "target", "phase"),)


class VoteLike(models.Model):
    id = models.BigAutoField(primary_key=True)
    phase = models.ForeignKey(GamePhase, related_name="vote_likes", on_delete=models.CASCADE)
    target = models.ForeignKey(GamePlayer, related_name="vote_target_likes", on_delete=models.CASCADE)
    voter = models.ForeignKey(GamePlayer, related_name="voted_likes", on_delete=models.CASCADE)
    is_like = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "votelike"
        managed = False


class GiveTopChat(models.Model):
    chat = models.ForeignKey('Chat', related_name="givetops", on_delete=models.CASCADE)
    gived_at = models.DateTimeField(auto_now_add=True)
    give_type = models.CharField(max_length=3)  # 1, 7, 30, 365

    class Meta:
        db_table = "givetopchat"
        managed = False


class GeroyAction(models.Model):
    id = models.BigAutoField(primary_key=True)
    geroy = models.ForeignKey(Geroy, related_name="actions", on_delete=models.CASCADE)
    action_type = models.CharField(max_length=20)  # attack, shield, skip
    target_user = models.ForeignKey(User, related_name="geroy_actions", on_delete=models.CASCADE, null=True, blank=True)
    phase = models.ForeignKey(GamePhase, related_name="geroy_actions", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "geroyaction"
        managed = False


class Chat(models.Model):
    id = models.BigAutoField(primary_key=True)
    chat_id = models.BigIntegerField()
    title = models.CharField(max_length=255)
    type = models.CharField(max_length=50)  # group / supergroup
    created_at = models.DateTimeField(auto_now_add=True)
    invite_link = models.CharField(max_length=500, default="")

    class Meta:
        db_table = "chat"
        managed = False

    def __str__(self):
        return self.title
