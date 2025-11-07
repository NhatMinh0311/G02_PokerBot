"""
Module này triển khai một trò chơi Texas Hold'em đơn giản
một chọi một giữa người chơi và bot điều khiển bởi máy. Bot
sử dụng phương pháp Monte Carlo minimax để ước lượng khả năng
thắng so với tay bài ngẫu nhiên của đối thủ và sau đó chọn
giữa fold, call hoặc raise dựa trên giá trị kỳ vọng (EV). Ngoài
việc ra quyết định, bot sẽ in ra các đánh giá nội bộ ở mỗi
điểm quyết định để người chơi thấy cách nó suy luận về ván bài.
Luật cược được đơn giản hóa: mỗi vòng chỉ có một lượt đặt cược
cho người chơi và một phản hồi từ bot.

Để chơi, chạy script này trực tiếp. Bạn sẽ bắt đầu với 1.000 chips
và có thể chơi bao nhiêu ván tùy thích. Ở mỗi giai đoạn cược
(pre-flop, flop, turn, river) bạn có thể fold, call hoặc raise. Bot
sẽ hiển thị suy nghĩ của nó lên console sau khi bạn cược.
"""

import random
from collections import Counter
from itertools import combinations
from typing import List, Tuple

# Định nghĩa các hạng và chất bài cho bộ bài 52 lá. Hạng từ '2' (thấp nhất)
# đến 'A' (Át, cao nhất). Chất sử dụng ký tự Unicode để dễ nhìn.
RANKS = '23456789TJQKA'
SUITS = '♠♥♦♣'

# Ánh xạ hạng sang giá trị số. 2 = 2 điểm, J = 11, Q = 12, K = 13, A = 14.
# Giá trị này dùng để so sánh sức mạnh bài.
RANK_VALUE = {r: i + 2 for i, r in enumerate(RANKS)}

# Tên các loại tay bài. Số lớn hơn nghĩa là mạnh hơn.
HAND_NAMES = {
    8: "Straight Flush",
    7: "Four of a Kind",
    6: "Full House",
    5: "Flush",
    4: "Straight",
    3: "Three of a Kind",
    2: "Two Pair",
    1: "One Pair",
    0: "High Card",
}


def create_deck() -> List[str]:
    """Tạo một bộ bài 52 lá mới và chưa xáo."""
    return [r + s for r in RANKS for s in SUITS]


def deal(deck: List[str], n: int) -> List[str]:
    """Chia n lá bài từ bộ bài, đồng thời loại chúng khỏi deck."""
    return [deck.pop() for _ in range(n)]


def rank_to_value(card: str) -> int:
    """Chuyển một lá bài như 'A♠' thành giá trị số tương ứng của hạng."""
    return RANK_VALUE[card[0]]


def is_flush(cards: List[str]) -> bool:
    """Trả về True nếu tất cả lá cùng một chất (flush)."""
    suits = [c[1] for c in cards]
    return len(set(suits)) == 1


def is_straight(values: List[int]) -> Tuple[bool, int]:
    """
    Xác định xem một danh sách giá trị bài có tạo thành một straight hay không.
    Trả về (True, giá_trên_cùng) nếu có straight, ngược lại (False, None).
    Xử lý trường hợp wheel A-2-3-4-5 bằng cách coi Át là 1 trong trường hợp đặc biệt.
    """
    if not values:
        return False, None
    vals = sorted(set(values), reverse=True)
    # Cho phép Át đếm là 1 cho wheel (A-5 straight)
    if 14 in vals:
        vals.append(1)
    consec = 1
    best_high = None
    # Kiểm tra bất kỳ dãy 5 giá liên tiếp nào
    for i in range(len(vals) - 1):
        if vals[i] - vals[i + 1] == 1:
            consec += 1
        else:
            consec = 1
        if consec >= 5:
            best_high = vals[i - 3]
            break
    # Kiểm tra từng cửa sổ dài 5 nếu cần
    if len(vals) >= 5 and best_high is None:
        for i in range(len(vals) - 4):
            window = vals[i:i + 5]
            if window[0] - window[-1] == 4 and len(window) == 5:
                best_high = window[0]
                break
    # Kiểm tra wheel A-2-3-4-5 đặc biệt
    if best_high is None and len(vals) >= 5:
        if {14, 5, 4, 3, 2}.issubset(set(values)):
            best_high = 5
    return (best_high is not None), best_high


def evaluate_5(cards: List[str]) -> Tuple[int, ...]:
    """
    Đánh giá một tay 5 lá. Trả về một tuple mà phần tử đầu là loại tay (0-8)
    và các phần tử sau là tiêu chí so kè để phá vỡ hòa. Tuple trả về có thể
    so sánh theo thứ tự từ trái sang phải để xác định tay mạnh hơn.
    """
    vals = sorted([rank_to_value(c) for c in cards], reverse=True)
    counts = Counter(vals)
    counts_by_freq = sorted(((freq, val) for val, freq in counts.items()), reverse=True)
    freqs = sorted(counts.values(), reverse=True)
    flush = is_flush(cards)
    straight, high_straight = is_straight(vals)
    if straight and flush:
        return (8, high_straight)
    if freqs[0] == 4:
        quad = counts_by_freq[0][1]
        kicker = max(v for v in vals if v != quad)
        return (7, quad, kicker)
    if freqs[0] == 3 and len(freqs) > 1 and freqs[1] == 2:
        trip = counts_by_freq[0][1]
        pair = counts_by_freq[1][1]
        return (6, trip, pair)
    if flush:
        return (5,) + tuple(vals)
    if straight:
        return (4, high_straight)
    if freqs[0] == 3:
        trip = counts_by_freq[0][1]
        kickers = sorted((v for v in vals if v != trip), reverse=True)
        return (3, trip) + tuple(kickers)
    if freqs[0] == 2 and len(freqs) > 1 and freqs[1] == 2:
        pair_high = counts_by_freq[0][1]
        pair_low = counts_by_freq[1][1]
        kicker = max(v for v in vals if v != pair_high and v != pair_low)
        return (2, pair_high, pair_low, kicker)
    if freqs[0] == 2:
        pair = counts_by_freq[0][1]
        kickers = sorted((v for v in vals if v != pair), reverse=True)
        return (1, pair) + tuple(kickers)
    return (0,) + tuple(vals)


def best_hand_rank(seven_cards: List[str]) -> Tuple[int, ...]:
    """Trả về xếp hạng tốt nhất của 5 lá từ tối đa 7 lá bài."""
    best = None
    for comb in combinations(seven_cards, 5):
        rank = evaluate_5(list(comb))
        if best is None or rank > best:
            best = rank
    return best  # type: ignore


def card_list_to_str(cards: List[str]) -> str:
    """Ghép danh sách lá bài thành một chuỗi in được."""
    return ' '.join(cards)


def pretty_rank(rank: Tuple[int, ...]) -> str:
    """Trả về tên tay bài dễ đọc từ tuple xếp hạng."""
    return HAND_NAMES[rank[0]]


class PokerMinimaxBot:
    """
    Bot poker sử dụng thuật toán Monte Carlo minimax đơn giản để
    đánh giá khả năng thắng so với tay đối thủ ngẫu nhiên. Bot
    tính toán giá trị kỳ vọng (EV) cho fold, call và raise dựa trên
    xác suất thắng và hòa thu được từ mô phỏng. Bot in ra lý do
    suy nghĩ nội bộ mỗi khi đưa quyết định.
    """

    def __init__(self, max_depth: int = 2, samples: int = 200) -> None:
        self.max_depth = max_depth
        self.samples = samples

    def evaluate_hand(self, hand: List[str], community_cards: List[str]) -> Tuple[int, ...]:
        """
        Đánh giá tay tốt nhất có thể từ hole cards và các lá chung.
        Trả về cùng định dạng tuple như best_hand_rank().
        """
        return best_hand_rank((hand or []) + (community_cards or []))

    def minimax(
        self,
        bot_hand: List[str],
        community_cards: List[str],
        player_bet: int,
        pot: int,
        bot_chips: int,
        player_chips: int,
        depth: int = 1,
    ) -> Tuple[str, int]:
        """
        Thực hiện đánh giá Monte Carlo cho trạng thái hiện tại và chọn
        hành động tốt nhất. Bot lấy mẫu các lá bài tẩy của đối thủ
        ngẫu nhiên và, nếu còn lá chung chưa lật, hoàn thành bằng
        lá ngẫu nhiên. Sau đó so sánh tay của bot với đối thủ qua
        nhiều mô phỏng để ước lượng xác suất thắng và hòa. Tính toán
        EV cho fold, call và raise dựa trên các xác suất này. In
        quá trình suy nghĩ và trả về hành động cùng số chips tương ứng.
        """
        # Giới hạn số mẫu để tránh tính toán quá nặng.
        SAMPLES = max(50, min(self.samples, 2000))

        # Xây bộ bài còn lại, loại bỏ các lá đã biết khỏi bộ bài đầy đủ.
        full_deck = create_deck()
        known = set((bot_hand or []) + (community_cards or []))
        remaining = [c for c in full_deck if c not in known]
        # Nếu không còn đủ lá để mô phỏng tay đối thủ, mặc định call.
        if len(remaining) < 2:
            print("[Bot]: Không đủ bài để mô phỏng. Mặc định call.")
            return 'call', player_bet

        wins = ties = 0
        for _ in range(SAMPLES):
            deck_copy = remaining.copy()
            random.shuffle(deck_copy)
            if len(deck_copy) < 2:
                break
            opp_hole = [deck_copy.pop(), deck_copy.pop()]
            # Xác định còn bao nhiêu lá chung cần lật
            needed = max(0, 5 - len(community_cards or []))
            extra_comm = (
                [deck_copy.pop() for _ in range(needed)] if needed <= len(deck_copy) else []
            )
            full_comm = (community_cards or []) + extra_comm
            bot_rank = best_hand_rank(bot_hand + full_comm)
            opp_rank = best_hand_rank(opp_hole + full_comm)
            if bot_rank > opp_rank:
                wins += 1
            elif bot_rank == opp_rank:
                ties += 1

        # Tính xác suất thắng và hòa
        p_win = wins / SAMPLES
        p_tie = ties / SAMPLES

        # Tính EV cho mỗi hành động
        ev_fold = -0.0
        ev_call = (
            p_win * (pot + player_bet)
            + p_tie * ((pot + player_bet) / 2)
            - (1 - p_win - p_tie) * player_bet
        )
        # Xác định mức raise hợp lý: ít nhất gấp đôi player_bet,
        # hoặc player_bet + 10, nhưng không vượt quá chips của bot.
        raise_amount = min(max(player_bet * 2, player_bet + 10), bot_chips)
        ev_raise = (
            p_win * (pot + player_bet + raise_amount)
            + p_tie * ((pot + player_bet + raise_amount) / 2)
            - (1 - p_win - p_tie) * raise_amount
        )

        # Chọn hành động có EV cao nhất; ưu tiên call khi hòa EV.
        best_action = 'fold'
        best_amt = 0
        best_ev = ev_fold
        for act, amt, ev in [('call', player_bet, ev_call), ('raise', raise_amount, ev_raise)]:
            if ev > best_ev or (ev == best_ev and act == 'call' and best_action == 'raise'):
                best_action, best_amt, best_ev = act, amt, ev
        print(f"  ==> Bot quyết định: {best_action.upper()} với {best_amt} chips\n")
        return best_action, int(best_amt)

    def get_action(
        self,
        bot_hand: List[str],
        community_cards: List[str],
        player_bet: int,
        pot: int,
        bot_chips: int,
        player_chips: int,
    ) -> Tuple[str, int]:
        """
        Wrapper quanh minimax để sử dụng bên ngoài. Nhận hole cards của bot,
        lá chung hiện tại, cược của người chơi, kích thước pot và stack chips.
        Trả về hành động đã chọn và số chips tương ứng.
        """
        return self.minimax(
            bot_hand, community_cards, player_bet, pot, bot_chips, player_chips, depth=self.max_depth
        )


class TexasHoldemGame:
    """
    Quản lý một ván Texas Hold'em heads-up giữa người chơi và bot.
    Xử lý xáo bài, chia bài, các vòng cược, showdown và theo dõi chips.
    Dùng PokerMinimaxBot để bot ra quyết định và in ra trạng thái trò chơi.
    """

    def __init__(self) -> None:
        self.player_chips = 1000
        self.bot_chips = 1000
        self.pot = 0
        self.min_bet = 20
        # Khởi tạo bot Minimax với depth thấp để chơi nhanh hơn
        self.bot_agent = PokerMinimaxBot(max_depth=2, samples=200)

    def get_player_action(self, stage: str, current_bet: int, player_contrib: int) -> Tuple[str, int]:
        """
        Yêu cầu người chơi chọn hành động dựa trên cược hiện tại và
        số tiền người chơi đã đóng góp trong vòng cược này. Tuple
        trả về gồm hành động ('fold', 'call' hoặc 'raise') và tổng
        số tiền người chơi muốn đặt trong vòng này (đối với fold
        giá trị này bị bỏ qua, với call bằng current_bet, với raise
        là tổng cược mới).

        Tham số
        ----------
        stage : str
            Nhãn cho giai đoạn cược hiện tại (ví dụ "Pre-flop",
            "Flop", "Turn", "River") để hiển thị.
        current_bet : int
            Cược cao nhất hiện tại trong vòng cược mà call phải khớp.
            Raise phải lớn hơn giá trị này.
        player_contrib : int
            Số chips người chơi đã cam kết trong vòng cược này.
            Hiệu số giữa tổng trả về và giá trị này là số người chơi
            phải thêm.

        Trả về
        -------
        Tuple[str, int]
            Tuple với phần tử đầu là hành động và phần tử thứ hai là
            tổng cược mới của người chơi. Với call bằng current_bet,
            với raise là mức đã nâng, với fold không dùng giá trị thứ hai.
        """
        while True:
            # Tính số tiền người chơi phải bỏ ra để call
            call_cost = max(current_bet - player_contrib, 0)
            print(f"\nChips của bạn: {self.player_chips}")
            print(f"Chips của bot: {self.bot_chips}")
            print(f"Pot: {self.pot}")
            print(f"Bạn đã đặt cược {player_contrib} chips trong vòng này. Giá call: {call_cost} chips.")
            action = input(
                f"Lượt của bạn ({stage}) - Chọn: (f)old, (c)all, (r)aise: "
            ).strip().lower()
            # Fold: người chơi bỏ bài
            if action == 'f':
                return 'fold', 0
            # Call: khớp cược hiện tại
            if action == 'c':
                # Không tốn thêm nếu call_cost = 0 (check)
                if call_cost <= self.player_chips:
                    return 'call', current_bet
                print("Bạn không đủ chips để call!")
                continue
            # Raise: tăng cược hiện tại
            if action == 'r':
                while True:
                    try:
                        min_raise = max(current_bet * 2, current_bet + self.min_bet)
                        amount_str = input(
                            f"Nhập tổng cược (tối thiểu {min_raise}, đang là {current_bet}): "
                        )
                        new_total = int(amount_str)
                        # new_total phải lớn hơn hoặc bằng min_raise và người chơi phải có đủ chips
                        if new_total >= min_raise and (new_total - player_contrib) <= self.player_chips:
                            return 'raise', new_total
                        if new_total < min_raise:
                            print(f"Số chips quá nhỏ! Cần ít nhất {min_raise}.")
                        else:
                            print("Bạn không đủ chips để raise tới mức đó!")
                    except ValueError:
                        print("Vui lòng nhập số hợp lệ!")
                # End inner loop
            print("Lựa chọn không hợp lệ!")

    def play_betting_round(
        self,
        stage: str,
        community_cards: List[str],
        bot_hand: List[str],
    ) -> bool:
        """
        Tiến hành một vòng cược nơi bất kỳ lần call nào đều kết thúc
        ngay lập tức vòng cược và chỉ raise mới khiến cược tiếp tục.
        Nếu người chơi call khi chưa có raise, bot tự động match
        để cả hai có đóng góp bằng nhau. Fold bởi bất kỳ bên nào
        sẽ kết thúc ván bài ngay.

        Tham số
        ----------
        stage : str
            Nhãn cho giai đoạn cược hiện tại (ví dụ "Pre-flop",
            "Flop", "Turn", "River"). Dùng để nhắc người chơi.
        community_cards : List[str]
            Lá chung đã lật, dùng cho hàm đánh giá của bot.
        bot_hand : List[str]
            Lá tẩy của bot.

        Trả về
        -------
        bool
            True nếu có người fold trong vòng cược này (và ván kết thúc),
            False nếu không.
        """
        # Khi bắt đầu vòng cược, cược tối thiểu là small blind
        current_bet = self.min_bet
        player_contrib = 0
        bot_contrib = 0
        while True:
            # Hỏi người chơi hành động
            action, new_player_total = self.get_player_action(stage, current_bet, player_contrib)
            if action == 'fold':
                # Người chơi fold: bot thắng pot
                self.bot_chips += self.pot
                print("Bạn đã fold. Bot thắng pot!")
                self.pot = 0
                return True

            if action == 'call':
                # Người chơi call: trả đủ để khớp current_bet
                diff = current_bet - player_contrib
                if diff < 0:
                    diff = 0
                self.pot += diff
                self.player_chips -= diff
                player_contrib = current_bet
                # Nếu đây là lần call đầu (chưa có raise) thì bot auto-match
                # để cả hai đóng góp bằng nhau. Nếu không, bot_contrib đã
                # khớp current_bet từ raise trước đó.
                if bot_contrib < current_bet:
                    bot_match = current_bet - bot_contrib
                    if bot_match < 0:
                        bot_match = 0
                    self.pot += bot_match
                    self.bot_chips -= bot_match
                    bot_contrib = current_bet
                    if bot_match > 0:
                        print(f"Bot call với {current_bet} chips")
                # Call luôn kết thúc vòng cược
                break

            # Người chơi raise: new_player_total là tổng họ muốn đặt
            raise_diff = new_player_total - player_contrib
            if raise_diff < 0:
                raise_diff = 0
            # Cập nhật pot và stack người chơi
            self.pot += raise_diff
            self.player_chips -= raise_diff
            player_contrib = new_player_total
            current_bet = new_player_total
            # Yêu cầu bot phản hồi raise
            bot_action, new_bot_total = self.bot_action(bot_hand, community_cards, current_bet)
            if bot_action == 'fold':
                # Bot fold: người chơi thắng pot
                self.player_chips += self.pot
                print("Bot đã fold. Bạn thắng pot!")
                self.pot = 0
                return True
            # Tính bot cần bỏ thêm bao nhiêu để đạt new_bot_total
            bot_diff = new_bot_total - bot_contrib
            if bot_diff < 0:
                bot_diff = 0
            # Nếu bot raise cao hơn raise của người chơi, cập nhật và tiếp tục
            if new_bot_total > current_bet:
                # Bot raise thêm lên trên raise của người chơi
                self.pot += bot_diff
                self.bot_chips -= bot_diff
                bot_contrib = new_bot_total
                current_bet = new_bot_total
                print(f"Bot raise với {new_bot_total} chips")
                # Vòng lặp tiếp tục: người chơi phải đáp trả raise của bot
                continue
            else:
                # Bot call raise của người chơi
                self.pot += bot_diff
                self.bot_chips -= bot_diff
                bot_contrib = new_bot_total
                print(f"Bot call với {current_bet} chips")
                # Call sau raise kết thúc vòng cược
                break
        # Không ai fold: vòng cược kết thúc bình thường
        return False

    def bot_action(self, bot_hand: List[str], community: List[str], player_bet: int) -> Tuple[str, int]:
        """Ủy quyền hành động của bot cho PokerMinimaxBot."""
        return self.bot_agent.get_action(
            bot_hand=bot_hand,
            community_cards=community,
            player_bet=player_bet,
            pot=self.pot,
            bot_chips=self.bot_chips,
            player_chips=self.player_chips,
        )

    def run_game(self) -> None:
        """
        Chạy một ván Texas Hold'em hoàn chỉnh. Chia bài, xử lý các vòng cược,
        và thực hiện showdown nếu không ai fold. In tất cả hành động và kết quả.
        """
        print("=== Texas Hold'em: You vs Bot ===")
        print("Ván bài bắt đầu...\n")

        # Tạo và xáo bộ bài mới
        deck = create_deck()
        random.shuffle(deck)

        # Chia bài tẩy
        player_hole = deal(deck, 2)
        bot_hole = deal(deck, 2)

        print(f"Bài của bạn: {card_list_to_str(player_hole)}")
        # Hiển thị bài tẩy của bot để người chơi có thể thấy toàn bộ ván bài.
        # Nếu muốn ẩn bài của bot, thay card_list_to_str(bot_hole) bằng "?? ??".
        print(f"Bài của bot: ?? ??")

        # Vòng cược Pre-flop: cho phép raise và call cho đến khi cả hai khớp
        if self.play_betting_round("Pre-flop", [], bot_hole):
            return

        # Flop
        deal(deck, 1)  # burn một lá
        flop = deal(deck, 3)
        print("\nFLOP:")
        print(f"Bài trên bàn: {card_list_to_str(flop)}")
        # Vòng cược Flop
        if self.play_betting_round("Flop", flop, bot_hole):
            return

        # Turn
        deal(deck, 1)  # burn
        turn = deal(deck, 1)
        print("\nTURN:")
        print(f"Bài trên bàn: {card_list_to_str(flop + turn)}")
        # Vòng cược Turn
        if self.play_betting_round("Turn", flop + turn, bot_hole):
            return

        # River
        deal(deck, 1)  # burn
        river = deal(deck, 1)
        community = flop + turn + river
        print("\nRIVER:")
        print(f"Bài trên bàn: {card_list_to_str(community)}")
        # Vòng cược River
        if self.play_betting_round("River", community, bot_hole):
            return

        # Showdown
        player_rank = best_hand_rank(player_hole + community)
        bot_rank = best_hand_rank(bot_hole + community)
        print("\nSHOWDOWN:")
        print(f"Bài trên bàn: {card_list_to_str(community)}")
        print(
            f"Bài của bạn: {card_list_to_str(player_hole)} {pretty_rank(player_rank)}"
        )
        print(
            f"Bài của bot: {card_list_to_str(bot_hole)} {pretty_rank(bot_rank)}"
        )
        if player_rank > bot_rank:
            print("BẠN THẮNG! 🎉")
            self.player_chips += self.pot
        elif player_rank < bot_rank:
            print("BOT THẮNG! 🤖")
            self.bot_chips += self.pot
        else:
            print("HÒA! 🤝")
            split_pot = self.pot // 2
            self.player_chips += split_pot
            self.bot_chips += split_pot
        # Reset pot cho ván tiếp theo
        self.pot = 0


def main() -> None:
    """
    Điểm vào để chạy trò chơi poker. Lặp vô hạn cho phép người dùng
    chơi nhiều ván cho đến khi họ chọn dừng.
    """
    while True:
        game = TexasHoldemGame()
        game.run_game()
        print(
            f"\nSố chips còn lại - Bạn: {game.player_chips}, Bot: {game.bot_chips}"
        )
        play_again = input("\nChơi tiếp? (y/n): ").strip().lower()
        if play_again != 'y':
            break
    print("\nCảm ơn đã chơi!")


if __name__ == "__main__":
    main()
