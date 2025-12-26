import random
import statistics
import pygame
from treys import Deck, Card, Evaluator
from .bot import bot_decision_wrapper
from .models import BOT_LOG_TEMPLATE
from .constants import (
    STARTING_MONEY,
    DEFAULT_RAISE_AMOUNT,
    DEFAULT_BOT_DEPTH,
    DEFAULT_BOT_MC_SIMS,
    # Import all constants that might be referenced
    SCREEN_WIDTH as W,
    SCREEN_HEIGHT as H,
    FPS,
    COLOR_WHITE as WHITE,
    COLOR_BLACK as BLACK,
    COLOR_GREEN as GREEN,
    COLOR_BLUE as BLUE,
    COLOR_RED as RED,
    COLOR_YELLOW as YELLOW,
    COLOR_GRAY as GRAY,
    COLOR_DARK as DARK,
    COLOR_PANEL as PANEL,
    COLOR_ACCENT as ACCENT,
)


# =========================
# Pygame INIT
# =========================
pygame.init()
SCREEN = pygame.display.set_mode((W, H))
pygame.display.set_caption("Texas Hold'em — You vs Bot (Deluxe)")
CLOCK = pygame.time.Clock()

# Audio init (safe)
AUDIO_ENABLED = True
try:
    pygame.mixer.init()
except Exception:
    AUDIO_ENABLED = False

def safe_load_sound(path):
    if not AUDIO_ENABLED:
        return None
    try:
        return pygame.mixer.Sound(path)
    except Exception:
        return None

def safe_play(snd):
    if snd:
        snd.play()

# Load sounds (\u0111\u1ec3 test, keeping hardcoded paths for now - will migrate to constants later)
SND_CHECK   = safe_load_sound("assets/check.wav")
SND_CALL    = safe_load_sound("assets/call.wav")
SND_RAISE   = safe_load_sound("assets/chips.wav")
SND_FOLD    = safe_load_sound("assets/fold.wav")
SND_WIN     = safe_load_sound("assets/win.wav")
SND_SHUFFLE = safe_load_sound("assets/shuffle.wav")

# Load avatar & chip image (optional)
def safe_load_image(path):
    try:
        img = pygame.image.load(path).convert_alpha()
        return img
    except Exception:
        return None

AVATAR_YOU = safe_load_image("assets/you.png")
AVATAR_BOT = safe_load_image("assets/bot.png")
CHIP_IMG   = safe_load_image("assets/chip.png")

# =========================
# Fonts
# =========================
FONT_HUGE = pygame.font.SysFont("consolas", 40, bold=True)
FONT_BIG  = pygame.font.SysFont("consolas", 28, bold=True)
FONT      = pygame.font.SysFont("consolas", 22)
FONT_SM   = pygame.font.SysFont("consolas", 18)

# =========================
# Poker helpers
# =========================
def compare_hands(cards1, cards2, community):
    """
    So sánh bài của hai người chơi (7 lá mỗi người = 2 riêng + 5 chung)
    return:
        1  nếu cards1 thắng
       -1  nếu cards2 thắng
        0  hòa
    """
    evaluator = Evaluator()
    rank1 = evaluator.evaluate(community, cards1)
    rank2 = evaluator.evaluate(community, cards2)
    if rank1 < rank2:
        return 1
    elif rank1 > rank2:
        return -1
    return 0


class Player:
    def __init__(self, name, is_bot=False):
        self.name = name
        self.is_bot = is_bot
        self.money = STARTING_MONEY
        self.hand = []
        self.folded = False
        self.current_bet = 0
        if is_bot:
            self.depth = DEFAULT_BOT_DEPTH
            self.mc_sims = DEFAULT_BOT_MC_SIMS
            self.bot_log = BOT_LOG_TEMPLATE.copy()

    def reset(self):
        self.hand = []
        self.folded = False
        self.current_bet = 0

    def bet(self, amount):
        if amount > self.money:
            amount = self.money
        self.money -= amount
        self.current_bet += amount
        return amount


# =========================
# UI Helpers
# =========================
class Button:
    def __init__(self, rect, text, bg=GRAY, fg=WHITE, font=FONT):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.bg = bg
        self.fg = fg
        self.font = font
        self.disabled = False

    def draw(self, surf):
        color = (90, 90, 90) if self.disabled else self.bg
        pygame.draw.rect(surf, color, self.rect, border_radius=10)
        pygame.draw.rect(surf, BLACK, self.rect, 2, border_radius=10)
        ts = self.font.render(
            self.text,
            True,
            (200, 200, 200) if self.disabled else self.fg,
        )
        surf.blit(ts, ts.get_rect(center=self.rect.center))

    def handle(self, ev):
        return (
            not self.disabled
            and ev.type == pygame.MOUSEBUTTONDOWN
            and ev.button == 1
            and self.rect.collidepoint(ev.pos)
        )


def card_label(cint):
    s = Card.int_to_str(cint)  # ví dụ 'As'
    rank, suit = s[0].upper(), s[1].lower()
    sym = {"s": "♠", "h": "♥", "d": "♦", "c": "♣"}[suit]
    col = RED if suit in ("h", "d") else BLACK
    return f"{rank}{sym}", col


def draw_card(cint, x, y, w=64, h=92, face_up=True, scale=1.0):
    # scale theo trục X (lật bài)
    w_scaled = max(1, int(w * scale))
    rect = pygame.Rect(x, y, w_scaled, h)
    pygame.draw.rect(SCREEN, WHITE if face_up else GRAY, rect, border_radius=10)
    pygame.draw.rect(SCREEN, BLACK, rect, 2, border_radius=10)

    if face_up and cint:
        label, col = card_label(cint)
        txt = FONT_BIG.render(label, True, col)
        SCREEN.blit(txt, (x + 8, y + 6))
    elif not face_up:
        for i in range(4):
            pygame.draw.rect(
                SCREEN,
                (210, 210, 210),
                (x + 10 + i * 12, y + 10, 8, h - 20),
                border_radius=6,
            )


def draw_row(cards, x, y, show=True, scale=1.0):
    for i, c in enumerate(cards):
        draw_card(c, x + i * 72, y, face_up=show, scale=scale)


# =========================
# Poker Game
# =========================
class PokerGame:
    def __init__(self):
        self.players = [Player("You"), Player("Bot", is_bot=True)]
        self.deck = None
        self.community = []
        self.pot = 0
        self.current_bet = 0
        self.dealer_index = 0  # 0: You, 1: Bot
        self.active_player_index = 0

        # UI state
        self.logs = []         # [(text, color), ...]
        self.raise_amount = 5
        self.log_scroll = 0          # pixel offset
        self.log_line_height = 20    # mỗi dòng log cao 20px
        self.last_action = ""
        self.particles = []          # particle effect khi thắng pot
        self.reveal_scale = 1.0      # scale lật bài bot khi showdown

        # ========== MAIN MENU STATE ==========
        self.last_round_result = "No rounds played yet."
        self.menu_level = 5  # default level 5
        self.in_game = False

        btn_h = 50
        self.buttons = {
            "new": Button((40, 720, 150, btn_h), "New Round", bg=BLUE),
            "fold": Button((210, 720, 120, btn_h), "Fold", bg=RED),
            "cc": Button((340, 720, 170, btn_h), "Check / Call", bg=(40, 160, 60)),
            "raise": Button((520, 720, 140, btn_h), "Raise / Bet", bg=YELLOW, fg=BLACK),
            "minus": Button((680, 720, 60, btn_h), "−", bg=GRAY),
            "plus": Button((750, 720, 60, btn_h), "+", bg=GRAY),
            "quit": Button((1050, 720, 100, btn_h), "Quit", bg=GRAY),
        }

        # Menu buttons
        self.menu_buttons = {
            "start": Button((480, 520, 240, 60), "START GAME", bg=YELLOW, fg=BLACK, font=FONT_BIG),
            "quit":  Button((480, 600, 240, 55), "QUIT", bg=GRAY, fg=WHITE, font=FONT_BIG),

            "level_minus": Button((430, 370, 60, 50), "−", bg=GRAY),
            "level_plus":  Button((710, 370, 60, 50), "+", bg=GRAY),
        }

        self.apply_bot_settings()

    # ===== Apply bot settings from menu =====
    def apply_bot_settings(self):
        bot = self.players[1]
        if bot.is_bot:
            level = self.menu_level
            bot.depth = level
            bot.mc_sims = 50 + (level - 1) * 550  # From constants: MC_SIMS_BASE + (level - 1) * MC_SIMS_PER_LEVEL

    # ---- dealing
    def create_deck(self):
        self.deck = Deck()
        safe_play(SND_SHUFFLE)

    def deal_hole_cards(self):
        for p in self.players:
            p.hand = self.deck.draw(2)

    def burn_card(self):
        if self.deck:
            self.deck.draw(1)

    def deal_flop(self):
        self.burn_card()
        self.community += self.deck.draw(3)

    def deal_turn(self):
        self.burn_card()
        self.community += self.deck.draw(1)

    def deal_river(self):
        self.burn_card()
        self.community += self.deck.draw(1)

    # ---- utils
    def log(self, s, type="info"):
        color_map = {
            "info":   (200, 200, 200),
            "action": (140, 220, 140),
            "error":  (240, 120, 120),
            "win":    (255, 240, 140),
        }
        col = color_map.get(type, (220, 220, 220))
        self.logs.append((s, col))
        if len(self.logs) > 200:
            self.logs = self.logs[-200:]
        print(s)

    def isEnded(self):
        return len([p for p in self.players if not p.folded]) <= 1

    def handle_log_scroll(self, ev):
        if ev.type == pygame.MOUSEWHEEL:
            self.log_scroll += ev.y * 25
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_UP:
                self.log_scroll += 20
            elif ev.key == pygame.K_DOWN:
                self.log_scroll -= 20

    def spawn_win_particles(self, winner_index: int):
        base_x, base_y = 80, 150
        if winner_index == 0:
            base_x, base_y = 260, 260
        elif winner_index == 1:
            base_x, base_y = 260, 460

        for _ in range(25):
            self.particles.append({
                "x": base_x,
                "y": base_y,
                "vx": random.uniform(-2.5, 2.5),
                "vy": random.uniform(-3.5, -1.0),
                "life": random.randint(25, 40),
            })

    def update_and_draw_particles(self):
        alive = []
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vy"] += 0.15
            p["life"] -= 1

            if p["life"] > 0:
                alive.append(p)
                radius = max(1, int(4 * p["life"] / 40))
                col = (255, 215, 0)
                pygame.draw.circle(SCREEN, col, (int(p["x"]), int(p["y"])), radius)
        self.particles = alive

    # =========================
    # MAIN MENU DRAW
    # =========================
    def draw_menu(self):
        SCREEN.fill(DARK)

        pygame.draw.rect(SCREEN, PANEL, (180, 120, 840, 560), border_radius=22)
        pygame.draw.rect(SCREEN, (80, 80, 90), (180, 120, 840, 560), 2, border_radius=22)

        SCREEN.blit(FONT_HUGE.render("Texas Hold'em", True, ACCENT), (220, 150))
        SCREEN.blit(FONT_BIG.render("Main Menu", True, WHITE), (220, 205))

        # Last result
        SCREEN.blit(FONT_BIG.render("Last Round:", True, WHITE), (220, 260))
        msg = self.last_round_result

        # simple wrap (2 lines)
        line1 = msg[:56]
        line2 = msg[56:112] if len(msg) > 56 else ""
        SCREEN.blit(FONT.render(line1, True, (220, 220, 220)), (220, 295))
        if line2:
            SCREEN.blit(FONT.render(line2, True, (220, 220, 220)), (220, 322))

        # Bot strength title
        SCREEN.blit(FONT_BIG.render("Bot Strength", True, WHITE), (220, 350))

        # Level
        SCREEN.blit(FONT.render("Bot Level:", True, ACCENT), (220, 380))
        pygame.draw.rect(SCREEN, (20, 20, 22), (500, 370, 200, 50), border_radius=12)
        pygame.draw.rect(SCREEN, (90, 90, 100), (500, 370, 200, 50), 2, border_radius=12)
        SCREEN.blit(FONT_BIG.render(str(int(self.menu_level)), True, WHITE), (590, 380))

        # hints
        SCREEN.blit(FONT_SM.render("Tip: level 1-10 (depth 1-10, mc sims 50-5000)", True, (180, 180, 180)), (220, 470))

        for b in self.menu_buttons.values():
            b.draw(SCREEN)

        pygame.display.flip()
        CLOCK.tick(FPS)

    # ---- draw table
    def draw(self, headline="TABLE", reveal_bot=False):
        SCREEN.fill(DARK)

        pygame.draw.rect(SCREEN, GREEN, (20, 20, W - 40, 640), border_radius=18)
        pygame.draw.rect(SCREEN, PANEL, (0, 700, W, 100))

        SCREEN.blit(FONT_HUGE.render("Texas Hold'em — You vs Bot", True, ACCENT), (30, 26))
        SCREEN.blit(FONT_BIG.render(headline, True, WHITE), (30, 70))

        SCREEN.blit(
            FONT.render(f"Dealer: {self.players[self.dealer_index].name}", True, WHITE),
            (30, 110),
        )

        if CHIP_IMG:
            SCREEN.blit(CHIP_IMG, (30, 140))
            SCREEN.blit(FONT.render(f"${self.pot}", True, YELLOW), (90, 150))
        else:
            SCREEN.blit(FONT.render(f"Pot: ${self.pot}", True, YELLOW), (30, 140))

        SCREEN.blit(FONT.render(f"Current Bet: ${self.current_bet}", True, WHITE), (30, 180))

        if self.last_action:
            SCREEN.blit(FONT.render(f"Last action: {self.last_action}", True, ACCENT), (620, 50))

        SCREEN.blit(FONT_BIG.render("Community", True, WHITE), (620, 80))
        draw_row(self.community, 620, 120, True)

        # Player
        you_rect = pygame.Rect(20, 240, W - 600, 170)
        pygame.draw.rect(SCREEN, (40, 40, 46), you_rect, border_radius=20)
        you = self.players[0]
        SCREEN.blit(FONT_BIG.render("You", True, WHITE), (40, 250))
        SCREEN.blit(FONT.render(f"Money: ${you.money}", True, YELLOW), (40, 284))
        SCREEN.blit(FONT.render(f"Your Bet: ${you.current_bet}", True, WHITE), (40, 314))

        if AVATAR_YOU:
            SCREEN.blit(AVATAR_YOU, (220, 250))

        draw_row(you.hand, 320, 260, True)

        if you.folded:
            SCREEN.blit(FONT_BIG.render("FOLDED", True, RED), (320, 320))

        # Bot
        bot_rect = pygame.Rect(20, 430, W - 600, 170)
        pygame.draw.rect(SCREEN, (40, 40, 46), bot_rect, border_radius=20)
        bot = self.players[1]
        SCREEN.blit(FONT_BIG.render("Bot", True, WHITE), (40, 440))
        SCREEN.blit(FONT.render(f"Money: ${bot.money}", True, YELLOW), (40, 474))
        SCREEN.blit(FONT.render(f"Bot Bet: ${bot.current_bet}", True, WHITE), (40, 504))

        if AVATAR_BOT:
            SCREEN.blit(AVATAR_BOT, (220, 450))

        if reveal_bot:
            draw_row(bot.hand, 320, 450, True, scale=self.reveal_scale)
        else:
            for i in range(len(bot.hand) if bot.hand else 0):
                draw_card(0, 320 + i * 72, 450, face_up=False)

        if bot.folded:
            SCREEN.blit(FONT_BIG.render("FOLDED", True, RED), (320, 510))

        # Highlight turn
        if self.active_player_index == 0:
            pygame.draw.rect(SCREEN, (120, 220, 120), you_rect, 3, border_radius=20)
        elif self.active_player_index == 1:
            pygame.draw.rect(SCREEN, (220, 120, 120), bot_rect, 3, border_radius=20)

        # Raise amount
        SCREEN.blit(FONT.render(f"Raise Amount: ${self.raise_amount}", True, ACCENT), (500, 680))

        # LOG WINDOW (scrollable)
        LOG_X, LOG_Y, LOG_W, LOG_H = 760, 240, 400, 360

        pygame.draw.rect(SCREEN, (10, 10, 10), pygame.Rect(LOG_X, LOG_Y, LOG_W, LOG_H), border_radius=10)
        pygame.draw.rect(SCREEN, (200, 200, 200), pygame.Rect(LOG_X, LOG_Y, LOG_W, LOG_H), 2, border_radius=10)

        content_h = max(LOG_H, len(self.logs) * self.log_line_height)
        log_surface = pygame.Surface((LOG_W - 20, content_h), pygame.SRCALPHA)
        log_surface.fill((0, 0, 0, 0))

        for i, (line, col) in enumerate(self.logs):
            text = FONT_SM.render(line, True, col)
            log_surface.blit(text, (0, i * self.log_line_height))

        max_scroll = max(0, content_h - LOG_H + 20)
        self.log_scroll = max(-max_scroll, min(0, self.log_scroll))

        clip_rect = pygame.Rect(LOG_X, LOG_Y, LOG_W, LOG_H)
        SCREEN.set_clip(clip_rect)
        SCREEN.blit(log_surface, (LOG_X + 10, LOG_Y + self.log_scroll))
        SCREEN.set_clip(None)

        self.update_and_draw_particles()

        for b in self.buttons.values():
            b.draw(SCREEN)

        pygame.display.flip()
        CLOCK.tick(FPS)

    # ---- blinds
    def post_blinds(self):
        small_blind = 2
        big_blind = 5

        sbp = self.players[self.dealer_index % 2]
        bbp = self.players[(self.dealer_index + 1) % 2]

        self.pot += sbp.bet(small_blind)
        self.pot += bbp.bet(big_blind)
        self.current_bet = big_blind

        self.log(f"{sbp.name} (SB) ${small_blind} | {bbp.name} (BB) ${big_blind} | Pot=${self.pot}", type="action")
        self.draw("BLINDS")

    # ---- wait buttons for player's action
    def _wait_player_buttons(self, can_check):
        for k in self.buttons:
            self.buttons[k].disabled = k not in ("fold", "cc", "raise", "minus", "plus", "quit")

        self.buttons["cc"].text = ("Check" if (can_check or self.current_bet == 0) else "Call")
        self.buttons["raise"].text = ("Bet" if self.current_bet == 0 else "Raise")

        while True:
            for ev in pygame.event.get():
                self.handle_log_scroll(ev)
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    self.in_game = False
                    return "quit"
                if self.buttons["quit"].handle(ev):
                    self.in_game = False
                    return "quit"

                if self.buttons["minus"].handle(ev):
                    self.raise_amount = max(1, self.raise_amount - 1)
                elif self.buttons["plus"].handle(ev):
                    self.raise_amount = min(1000, self.raise_amount + 1)
                elif self.buttons["fold"].handle(ev):
                    return "fold"
                elif self.buttons["cc"].handle(ev):
                    return "check" if (can_check or self.current_bet == 0) else "call"
                elif self.buttons["raise"].handle(ev):
                    return "bet" if self.current_bet == 0 else "raise"

            self.draw("YOUR TURN")

    # ---- 1 action của 1 player
    def _act(self, p):
        self.draw(f"{p.name}'s turn")
        can_check = (p.current_bet == self.current_bet)

        # BOT
        if p.is_bot:
            pygame.time.delay(random.randint(300, 900))
            pygame.event.pump()
            action = bot_decision_wrapper(self, p)

            if action == "bet" or action == "raise":
                action = "raise"
            else:
                self.log(f"Bot {action}", type="action")

            self.last_action = f"Bot: {action.capitalize()}"

            if action == "fold":
                p.folded = True
                safe_play(SND_FOLD)
                return "fold"

            elif action == "check":
                safe_play(SND_CHECK)
                return "check"

            elif action == "call":
                diff = max(0, self.current_bet - p.current_bet)
                if diff > 0:
                    self.pot += p.bet(diff)
                safe_play(SND_CALL)
                return "call"

            elif action == "raise":
                raise_to = self.current_bet + 5
                diff = max(0, raise_to - p.current_bet)
                if diff > 0:
                    self.pot += p.bet(diff)
                self.current_bet = raise_to
                self.log(f"Bot raise {self.current_bet}$", type="action")
                safe_play(SND_RAISE)
                return "raise"

            safe_play(SND_CHECK)
            return "check"

        # PLAYER
        else:
            action = self._wait_player_buttons(can_check)

            if action == "fold":
                p.folded = True
                self.last_action = "You: Fold"
                self.log("You fold.", type="action")
                safe_play(SND_FOLD)
                return "fold"

            if action == "check":
                self.last_action = "You: Check"
                self.log("You check.", type="action")
                safe_play(SND_CHECK)
                return "check"

            if action == "call":
                diff = max(0, self.current_bet - p.current_bet)
                if diff > 0:
                    self.pot += p.bet(diff)
                self.last_action = f"You: Call ${diff}"
                self.log(f"You call ${diff}.", type="action")
                safe_play(SND_CALL)
                return "call"

            if action == "bet":
                bet_amount = max(1, self.raise_amount)
                diff = bet_amount - p.current_bet
                if diff > 0:
                    self.pot += p.bet(diff)
                self.current_bet = bet_amount
                self.last_action = f"You: Bet ${bet_amount}"
                self.log(f"You bet ${bet_amount}.", type="action")
                safe_play(SND_RAISE)
                return "raise"

            if action == "raise":
                new_bet = self.current_bet + max(1, self.raise_amount)
                diff = new_bet - p.current_bet
                if diff > 0:
                    self.pot += p.bet(diff)
                self.current_bet = new_bet
                self.last_action = f"You: Raise ${new_bet}"
                self.log(f"You raise ${new_bet}.", type="action")
                safe_play(SND_RAISE)
                return "raise"

            self.last_action = "You: Check"
            safe_play(SND_CHECK)
            return "check"

    # ---- betting round (2 players)
    def betting_round(self):
        self.log("=== Betting Round ===", type="info")

        for p in self.players:
            if not hasattr(p, "current_bet"):
                p.current_bet = 0

        acted_once = [False, False]
        last_raiser = None
        idx = self.active_player_index

        while True:
            if self.isEnded():
                break

            p = self.players[idx]
            if p.folded:
                idx = (idx + 1) % 2
                continue

            result = self._act(p)
            if result == "quit":
                self.in_game = False
                break
            acted_once[idx] = True

            if result == "fold":
                if self.isEnded():
                    self.log("💥 All others folded!", type="info")
                    self.showdown()
                break

            if result == "raise":
                last_raiser = idx
                acted_once = [False, False]
                acted_once[idx] = True

            a, b = self.players

            if last_raiser is None:
                both_acted = all(acted_once[i] or self.players[i].folded for i in (0, 1))
                if both_acted and a.current_bet == b.current_bet:
                    if self.current_bet == 0:
                        self.log("Both checked. Street ends.", type="info")
                    else:
                        self.log("Both called. Street ends.", type="info")
                    break
            else:
                if idx != last_raiser:
                    if result in ("call", "check") or p.folded:
                        self.log("Raise has been answered. Street ends.", type="info")
                        break

            idx = (idx + 1) % 2

        if not self.isEnded():
            for p in self.players:
                p.current_bet = 0
            self.current_bet = 0
            self.draw("STREET ENDED")

    def _round_end_pause(self, message):
        for k in self.buttons:
            self.buttons[k].disabled = True
        self.buttons["new"].disabled = False
        self.buttons["quit"].disabled = False

        self.draw(f"ROUND OVER — {message}", reveal_bot=True)

        waiting = True
        while waiting:
            for ev in pygame.event.get():
                self.handle_log_scroll(ev)
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    self.in_game = False
                    waiting = False
                if self.buttons["quit"].handle(ev):
                    self.in_game = False
                    waiting = False
                if self.buttons["new"].handle(ev):
                    waiting = False

            self.draw(f"ROUND OVER — {message}", reveal_bot=True)

    # ---- showdown
    def showdown(self):
        self.reveal_scale = 0.0
        for i in range(21):
            self.reveal_scale = i / 20.0
            self.draw("SHOWDOWN", reveal_bot=True)
            pygame.time.delay(30)

        active = [p for p in self.players if not p.folded]

        if len(active) == 1:
            winner = active[0]
            winner_index = self.players.index(winner)
            winner.money += self.pot
            msg = f"{winner.name} wins the pot (${self.pot}) by default!"
            self.log(msg, type="win")
            safe_play(SND_WIN)
            self.spawn_win_particles(winner_index)

            # update last round result for MENU
            self.last_round_result = msg

            if winner.is_bot:
                BOT_LOG_TEMPLATE["rounds"]["bot_wins"] += 1
            else:
                BOT_LOG_TEMPLATE["rounds"]["player_wins"] += 1

            self._round_end_pause(msg)
            return

        res = compare_hands(
            cards1=self.players[0].hand,
            cards2=self.players[1].hand,
            community=self.community,
        )

        winner_index = None

        if res == 1:
            msg = f"You win ${self.pot}!"
            self.players[0].money += self.pot
            BOT_LOG_TEMPLATE["rounds"]["player_wins"] += 1
            winner_index = 0
        elif res == -1:
            msg = f"Bot wins ${self.pot}!"
            self.players[1].money += self.pot
            BOT_LOG_TEMPLATE["rounds"]["bot_wins"] += 1
            winner_index = 1
        else:
            msg = "It's a tie! Pot is split."
            self.players[0].money += self.pot / 2
            self.players[1].money += self.pot / 2
            BOT_LOG_TEMPLATE["rounds"]["ties"] += 1

        self.log(msg, type="win")
        safe_play(SND_WIN)
        if winner_index is not None:
            self.spawn_win_particles(winner_index)

        # update last round result for MENU
        self.last_round_result = msg

        self.draw("SHOWDOWN", reveal_bot=True)
        self._round_end_pause(msg)

    # ---- round control
    def reset(self):
        self.dealer_index %= len(self.players)
        for p in self.players:
            p.reset()
        self.pot = 0
        self.current_bet = 0
        self.community = []
        self.particles = []
        self.last_action = ""
        self.reveal_scale = 1.0
        self.create_deck()

    def play_round(self):
        self.apply_bot_settings()

        self.reset()
        self.logs = []
        self.draw("NEW ROUND")

        self.post_blinds()
        self.deal_hole_cards()
        self.draw("HOLE CARDS")

        self.active_player_index = (self.dealer_index + 1) % 2
        self.betting_round()
        if self.isEnded():
            self.dealer_index = (self.dealer_index + 1) % 2
            return

        self.deal_flop()
        self.draw("FLOP")
        self.active_player_index = self.dealer_index
        self.betting_round()
        if self.isEnded():
            self.dealer_index = (self.dealer_index + 1) % 2
            return

        self.deal_turn()
        self.draw("TURN")
        self.active_player_index = self.dealer_index
        self.betting_round()
        if self.isEnded():
            self.dealer_index = (self.dealer_index + 1) % 2
            return

        self.deal_river()
        self.draw("RIVER")
        self.active_player_index = self.dealer_index
        self.betting_round()
        if self.isEnded():
            self.dealer_index = (self.dealer_index + 1) % 2
            return

        self.showdown()
        self.dealer_index = (self.dealer_index + 1) % 2

    def play_game(self):
        while True:
            # ===== MAIN MENU LOOP =====
            in_menu = True
            while in_menu:
                for ev in pygame.event.get():
                    if ev.type == pygame.QUIT:
                        pygame.quit()
                        return
                    if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                        pygame.quit()
                        return

                    if self.menu_buttons["quit"].handle(ev):
                        pygame.quit()
                        return

                    # level
                    if self.menu_buttons["level_minus"].handle(ev):
                        self.menu_level = max(1, int(self.menu_level) - 1)
                    if self.menu_buttons["level_plus"].handle(ev):
                        self.menu_level = min(10, int(self.menu_level) + 1)

                    if self.menu_buttons["start"].handle(ev):
                        # Reset money for new game
                        for p in self.players:
                            p.money = 100
                        if self.players[1].is_bot:
                            self.players[1].bot_log = BOT_LOG_TEMPLATE.copy()
                        self.apply_bot_settings()
                        in_menu = False

                self.draw_menu()

            # ===== GAME LOOP =====
            self.in_game = True
            while self.in_game:
                self.play_round()
                if not all(p.money > 0 for p in self.players):
                    # Game over, update result
                    p1, p2 = self.players
                    if p1.money > p2.money:
                        winner = p1.name
                    elif p2.money > p1.money:
                        winner = p2.name
                    else:
                        winner = "Tie"
                    self.last_round_result = f"You: ${p1.money} | Bot: ${p2.money} | Winner: {winner}"
                    self.in_game = False


# =========================
# Run
# =========================
if __name__ == "__main__":
    game = PokerGame()
    game.play_game()
