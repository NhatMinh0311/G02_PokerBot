import random
import statistics
import pygame
from treys import Deck, Card, Evaluator
from bot2 import bot_decision_wrapper, BOT_LOG

# =========================
# Poker helpers (giữ nguyên)
# =========================
def compare_hands(cards1, cards2, community):
    evaluator = Evaluator()
    r1 = evaluator.evaluate(community, cards1)
    r2 = evaluator.evaluate(community, cards2)
    if r1 < r2:
        return 1
    elif r1 > r2:
        return -1
    return 0

class Player:
    def __init__(self, name, is_bot=False):
        self.name = name
        self.is_bot = is_bot
        self.money = 100
        self.hand = []
        self.folded = False
        self.current_bet = 0

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
# Pygame UI
# =========================
pygame.init()
W, H = 1200, 800
SCREEN = pygame.display.set_mode((W, H))
pygame.display.set_caption("Texas Hold'em — You vs Bot (Buttons)")
CLOCK = pygame.time.Clock()
FPS = 60

WHITE=(255,255,255); BLACK=(0,0,0); GREEN=(34,139,34); BLUE=(70,130,180)
RED=(220,20,60); YELLOW=(255,215,0); GRAY=(128,128,128); DARK=(26,26,28); PANEL=(36,36,40)
ACCENT=(255,230,120)

FONT_HUGE = pygame.font.SysFont("consolas", 40, bold=True)
FONT_BIG  = pygame.font.SysFont("consolas", 28, bold=True)
FONT      = pygame.font.SysFont("consolas", 22)
FONT_SM   = pygame.font.SysFont("consolas", 18)

class Button:
    def __init__(self, rect, text, bg=GRAY, fg=WHITE, font=FONT):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.bg = bg
        self.fg = fg
        self.font = font
        self.disabled = False
    def draw(self, surf):
        color = (90,90,90) if self.disabled else self.bg
        pygame.draw.rect(surf, color, self.rect, border_radius=10)
        pygame.draw.rect(surf, BLACK, self.rect, 2, border_radius=10)
        ts = self.font.render(self.text, True, (200,200,200) if self.disabled else self.fg)
        surf.blit(ts, ts.get_rect(center=self.rect.center))
    def handle(self, ev):
        return (not self.disabled and ev.type==pygame.MOUSEBUTTONDOWN
                and ev.button==1 and self.rect.collidepoint(ev.pos))

def card_label(cint):
    s = Card.int_to_str(cint)  # 'As'
    rank, suit = s[0].upper(), s[1].lower()
    sym = {'s':'♠','h':'♥','d':'♦','c':'♣'}[suit]
    col = RED if suit in ('h','d') else BLACK
    return f"{rank}{sym}", col

def draw_card(cint, x, y, w=64, h=92, face_up=True):
    r = pygame.Rect(x,y,w,h)
    pygame.draw.rect(SCREEN, WHITE if face_up else GRAY, r, border_radius=10)
    pygame.draw.rect(SCREEN, BLACK, r, 2, border_radius=10)
    if face_up and cint:
        label, col = card_label(cint)
        SCREEN.blit(FONT_BIG.render(label, True, col), (x+8, y+6))
    elif not face_up:
        for i in range(4):
            pygame.draw.rect(SCREEN, (210,210,210), (x+10+i*12, y+10, 8, h-20), border_radius=6)

def draw_row(cards, x, y, show=True):
    for i,c in enumerate(cards):
        draw_card(c, x+i*72, y, face_up=show)

# =========================
# Game + Buttons (thay input)
# =========================
class PokerGame:
    def __init__(self):
        self.players = [Player("You"), Player("Bot", is_bot=True)]
        self.deck = None
        self.community = []
        self.pot = 0
        self.current_bet = 0
        self.dealer_index = 0
        self.active_player_index = (self.dealer_index + 2) % len(self.players)
        self.is_pre_flop = True

        # UI state
        self.logs = []
        self.raise_amount = 5
        btn_h = 50
        self.buttons = {
            "new":   Button((40, 720, 150, btn_h), "New Round", bg=BLUE),
            "fold":  Button((210,720,120,btn_h), "Fold", bg=RED),
            "cc":    Button((340,720,170,btn_h), "Check / Call", bg=(40,160,60)),
            "raise": Button((520,720,140,btn_h), "Raise / Bet", bg=YELLOW, fg=BLACK),
            "minus": Button((680,720,60,btn_h),  "−", bg=GRAY),
            "plus":  Button((750,720,60,btn_h),  "+", bg=GRAY),
            "quit":  Button((1050,720,100,btn_h), "Quit", bg=GRAY),
        }

    # ---- dealing
    def create_deck(self): self.deck = Deck()
    def deal_hole_cards(self):
        for p in self.players: p.hand = self.deck.draw(2)
    def burn_card(self):
        if self.deck: self.deck.draw(1)
    def deal_flop(self): self.burn_card(); self.community += self.deck.draw(3)
    def deal_turn(self): self.burn_card(); self.community += self.deck.draw(1)
    def deal_river(self): self.burn_card(); self.community += self.deck.draw(1)

    # ---- utils
    def log(self, s):
        self.logs.append(s)
        if len(self.logs)>7: self.logs = self.logs[-7:]
        print(s)

    def isEnded(self):
        return len([p for p in self.players if not p.folded]) <= 1

    # ---- draw table
    def draw(self, headline="TABLE", reveal_bot=False):
        SCREEN.fill(DARK)
        pygame.draw.rect(SCREEN, GREEN, (20, 20, W-40, 640), border_radius=18)
        pygame.draw.rect(SCREEN, PANEL, (0, 700, W, 100))
        SCREEN.blit(FONT_HUGE.render("Texas Hold'em — You vs Bot", True, ACCENT), (30, 26))
        SCREEN.blit(FONT_BIG.render(headline, True, WHITE), (30, 70))
        # dealer_index luôn hợp lệ nên không còn IndexError nữa
        SCREEN.blit(FONT.render(f"Dealer: {self.players[self.dealer_index].name}", True, WHITE), (30, 110))
        SCREEN.blit(FONT.render(f"Pot: ${self.pot}", True, YELLOW), (30, 140))
        SCREEN.blit(FONT.render(f"Current Bet: ${self.current_bet}", True, WHITE), (30, 170))

        # community
        SCREEN.blit(FONT_BIG.render("Community", True, WHITE), (620, 80))
        draw_row(self.community, 620, 120, True)

        # you
        pygame.draw.rect(SCREEN, (40,40,46), pygame.Rect(20, 240, W-40, 170), border_radius=12)
        you = self.players[0]
        SCREEN.blit(FONT_BIG.render("You", True, WHITE), (40, 250))
        SCREEN.blit(FONT.render(f"Money: ${you.money}", True, YELLOW), (40, 284))
        SCREEN.blit(FONT.render(f"Your Bet: ${you.current_bet}", True, WHITE), (40, 314))
        draw_row(you.hand, 300, 260, True)
        if you.folded: SCREEN.blit(FONT_BIG.render("FOLDED", True, RED), (300, 320))

        # bot
        pygame.draw.rect(SCREEN, (40,40,46), pygame.Rect(20, 430, W-40, 170), border_radius=12)
        bot = self.players[1]
        SCREEN.blit(FONT_BIG.render("Bot", True, WHITE), (40, 440))
        SCREEN.blit(FONT.render(f"Money: ${bot.money}", True, YELLOW), (40, 474))
        SCREEN.blit(FONT.render(f"Bot Bet: ${bot.current_bet}", True, WHITE), (40, 504))
        if reveal_bot: draw_row(bot.hand, 300, 450, True)
        else:
            for i in range(len(bot.hand) if bot.hand else 0):
                draw_card(0, 300+i*72, 450, face_up=False)
        if bot.folded: SCREEN.blit(FONT_BIG.render("FOLDED", True, RED), (300, 510))

        # logs
        y=645; SCREEN.blit(FONT_SM.render("Log:", True, (230,230,230)), (30, y)); y+=22
        for line in self.logs[-5:]:
            SCREEN.blit(FONT_SM.render(line, True, (220,220,220)), (30, y)); y+=20

        # raise amount
        SCREEN.blit(FONT.render(f"Raise Amount: ${self.raise_amount}", True, ACCENT), (760, 680))

        # buttons
        for b in self.buttons.values():
            b.draw(SCREEN)
        pygame.display.flip()
        CLOCK.tick(FPS)

    # ---- blinds
    def post_blinds(self):
        small_blind = 2; big_blind = 5
        sbp = self.players[self.dealer_index % len(self.players)]
        bbp = self.players[(self.dealer_index + 1) % len(self.players)]
        self.pot += sbp.bet(small_blind); sbp.current_bet = small_blind
        self.pot += bbp.bet(big_blind);   bbp.current_bet = big_blind
        self.current_bet = big_blind
        self.active_player_index = (self.dealer_index + 2) % len(self.players)
        self.log(f"{sbp.name} (SB) ${small_blind} | {bbp.name} (BB) ${big_blind} | Pot=${self.pot}")
        self.draw("BLINDS")

    # ---- wait buttons for player's action
    def _wait_player_buttons(self, can_check):
        """Trả về action: 'fold'|'check'|'call'|'bet'|'raise'"""
        for k in self.buttons:
            self.buttons[k].disabled = k not in ("fold","cc","raise","minus","plus","quit")
        self.buttons["cc"].text = "Check" if can_check or self.current_bet==0 else "Call"

        while True:
            for ev in pygame.event.get():
                if ev.type==pygame.QUIT: pygame.quit(); raise SystemExit
                if ev.type==pygame.KEYDOWN and ev.key==pygame.K_ESCAPE: pygame.quit(); raise SystemExit
                if self.buttons["quit"].handle(ev): pygame.quit(); raise SystemExit
                if self.buttons["minus"].handle(ev): self.raise_amount = max(1, self.raise_amount-1)
                elif self.buttons["plus"].handle(ev): self.raise_amount = min(1000, self.raise_amount+1)
                elif self.buttons["fold"].handle(ev): return "fold"
                elif self.buttons["cc"].handle(ev):
                    return "check" if (can_check or self.current_bet==0) else "call"
                elif self.buttons["raise"].handle(ev):
                    return "bet" if self.current_bet==0 else "raise"
            self.draw("YOUR TURN")

    # ---- one actor acts; return True nếu fold kết thúc ngay
    def _act(self, p, can_check):
        self.draw(f"{p.name}'s turn", reveal_bot=False)
        if p.is_bot:
            pygame.event.pump()
            action = bot_decision_wrapper(self, p)
            self.log(f"Bot chooses: {action}")
            if action == 'fold':
                p.folded = True; self.draw("BOT FOLD"); return True
            elif action == 'check':
                if self.current_bet == p.current_bet:
                    self.draw("BOT CHECK")
                else:
                    call_amount = max(0, self.current_bet - p.current_bet)
                    self.pot += p.bet(call_amount); self.draw(f"BOT CALL ${call_amount}")
            elif action == 'call':
                call_amount = max(0, self.current_bet - p.current_bet)
                self.pot += p.bet(call_amount); self.draw(f"BOT CALL ${call_amount}")
            elif action == 'raise':
                raise_to = self.current_bet + 5
                diff = max(0, raise_to - p.current_bet)
                self.pot += p.bet(diff); self.current_bet = raise_to
                self.draw(f"BOT RAISE {raise_to}")
            return False
        else:
            action = self._wait_player_buttons(can_check)
            if action == "fold":
                p.folded = True; self.log("You folded."); self.draw("YOU FOLD"); return True
            elif action == "check":
                if p.current_bet == self.current_bet:
                    self.log("You check."); self.draw("YOU CHECK")
                else:
                    call_amount = max(0, self.current_bet - p.current_bet)
                    self.pot += p.bet(call_amount); self.log(f"You call ${call_amount}"); self.draw("YOU CALL")
            elif action == "call":
                call_amount = max(0, self.current_bet - p.current_bet)
                self.pot += p.bet(call_amount); self.log(f"You call ${call_amount}"); self.draw("YOU CALL")
            elif action == "bet":
                bet_amount = max(5, self.raise_amount)
                diff = max(0, bet_amount - p.current_bet)
                self.pot += p.bet(diff); self.current_bet = bet_amount
                self.log(f"You bet to ${bet_amount}"); self.draw(f"YOU BET {bet_amount}")
                return False
            elif action == "raise":
                new_bet = self.current_bet + max(1, self.raise_amount)
                diff = max(0, new_bet - p.current_bet)
                self.pot += p.bet(diff); self.current_bet = new_bet
                self.log(f"You raise to ${new_bet}"); self.draw(f"YOU RAISE {new_bet}")
                return False
            return False

    # ---- betting round (2 players)
    def betting_round(self):
        self.log("=== Betting Round ===")
        for p in self.players:
            if not hasattr(p, "current_bet"): p.current_bet = 0

        last_raise_idx = -1
        while True:
            start_idx = (last_raise_idx + 1) % 2 if last_raise_idx != -1 else self.active_player_index
            end_round = True

            for i in range(2):
                if self.isEnded(): break
                idx = (start_idx + i) % 2
                p = self.players[idx]
                if p.folded: continue
                if last_raise_idx != -1 and idx == last_raise_idx: break

                can_check = (p.current_bet == self.current_bet)
                ended = self._act(p, can_check)
                if ended: break

            if self.isEnded():
                break

            a, b = self.players[0], self.players[1]
            if a.current_bet == self.current_bet and b.current_bet == self.current_bet:
                if self.current_bet > 0:
                    self.log("Bet/raise has been called. Street ends.")
                    break
                else:
                    self.log("Both checked. Street ends.")
                    break

            if end_round:
                break

        if sum(1 for pl in self.players if not pl.folded) == 1:
            self.log("💥 All others folded!")
            self.showdown()
            return

        self.active_player_index = self.dealer_index % 2
        self.current_bet = 0
        for p in self.players: p.current_bet = 0
        self.draw("STREET ENDED")

    # ---- showdown
    def showdown(self):
        self.draw("SHOWDOWN", reveal_bot=True)
        active = [p for p in self.players if not p.folded]
        if len(active) == 1:
            winner = active[0]; winner.money += self.pot
            self.log(f"{winner.name} wins the pot (${self.pot}) by default!")
            if winner.is_bot: BOT_LOG['rounds']['bot_wins'] += 1
            else: BOT_LOG['rounds']['player_wins'] += 1
            return

        res = compare_hands(self.players[0].hand, self.players[1].hand, self.community)
        if res == 1:
            self.players[0].money += self.pot; BOT_LOG['rounds']['player_wins'] += 1
            self.log(f"You win ${self.pot}!")
        elif res == -1:
            self.players[1].money += self.pot; BOT_LOG['rounds']['bot_wins'] += 1
            self.log(f"Bot wins ${self.pot}!")
        else:
            self.players[0].money += self.pot/2; self.players[1].money += self.pot/2
            BOT_LOG['rounds']['ties'] += 1; self.log("It's a tie! Pot is split.")
        self.draw("SHOWDOWN", reveal_bot=True)

    # ---- round control
    def reset(self):
        # đảm bảo dealer_index luôn trong range [0, len(players)-1]
        self.dealer_index %= len(self.players)
        for p in self.players: p.reset()
        self.pot = 0; self.current_bet = 0; self.community = []; self.create_deck(); self.is_pre_flop = True

    def play_round(self):
        self.reset(); self.logs=[]
        self.draw("NEW ROUND")
        # Blinds + deal
        self.post_blinds()
        self.deal_hole_cards(); self.draw("HOLE CARDS")

        # Pre-Flop
        self.betting_round()
        if self.isEnded():
            self.dealer_index = (self.dealer_index + 1) % len(self.players)
            return

        # Flop
        self.deal_flop(); self.draw("FLOP")
        self.betting_round()
        if self.isEnded():
            self.dealer_index = (self.dealer_index + 1) % len(self.players)
            return

        # Turn
        self.deal_turn(); self.draw("TURN")
        self.betting_round()
        if self.isEnded():
            self.dealer_index = (self.dealer_index + 1) % len(self.players)
            return

        # River
        self.deal_river(); self.draw("RIVER")
        self.betting_round()
        if self.isEnded():
            self.dealer_index = (self.dealer_index + 1) % len(self.players)
            return

        self.showdown()
        # KẾT THÚC VÁN: quay vòng dealer
        self.dealer_index = (self.dealer_index + 1) % len(self.players)

    def play_game(self):
        # màn hình chờ: New / Quit
        for k in self.buttons: self.buttons[k].disabled=True
        self.buttons["new"].disabled=False; self.buttons["quit"].disabled=False
        self.draw("Click New Round to start")
        waiting=True
        while waiting:
            for ev in pygame.event.get():
                if ev.type==pygame.QUIT: pygame.quit(); return
                if ev.type==pygame.KEYDOWN and ev.key==pygame.K_ESCAPE: pygame.quit(); return
                if self.buttons["quit"].handle(ev): pygame.quit(); return
                if self.buttons["new"].handle(ev): waiting=False
            self.draw("Click New Round to start")

        while all(p.money>0 for p in self.players):
            self.play_round()

        # Game over
        SCREEN.fill(DARK)
        SCREEN.blit(FONT_HUGE.render("GAME OVER", True, ACCENT), (30, 26))
        y=90
        for p in self.players:
            SCREEN.blit(FONT_BIG.render(f"{p.name}: ${p.money}", True, WHITE), (30, y)); y+=36
        pygame.display.flip(); pygame.time.delay(1600); pygame.quit()

# =========================
# Run
# =========================
if __name__ == "__main__":
    game = PokerGame()
    game.play_game()
