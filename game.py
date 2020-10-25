from numpy import flip, pad, zeros
from random import choice as random_choice
from gpiozero import Button
from servo import ExtendedServo
from stepper import Stepper
from lcd import CharLCD
from lcd_msgs import lcd_msgs


class Board:
    """
    - manages and solves Connect 4 game states
    - interface-independent methods
    """

    def __init__(self, width=7, height=6):
        self.w = width
        self.h = height
        self.align_len = 4
        self.reset_board()

    def __repr__(self):
        inverted = flip(self.board, 0)
        repr_str = ''
        for row in inverted:
            row_str = ''
            for col in row:
                row_str += 'x ' if col == 1 else 'o ' if col == 2 else '. '
            repr_str += row_str + '\n'
        return '\n' + repr_str

    def reset_board(self):
        self.board = zeros((self.h, self.w), dtype=int)
        self.col_heights = zeros((self.w), dtype=int)
        self.moves = 0
        self.history = []

    def get_current_player(self):
        return 1 + self.moves % 2

    def get_opponent(self):
        return 1 + (self.moves + 1) % 2

    def get_playable_cols(self):
        cols = list(range(self.w))
        cols.sort(key=lambda x: abs(self.w // 2 - x))   # favour middle cols
        playable = filter(lambda col: self.col_heights[col] < self.h, cols)
        return list(playable)

    def play(self, col):
        if col in self.get_playable_cols():
            self.board[self.col_heights[col]][col] = self.get_current_player()
            self.col_heights[col] += 1
            self.moves += 1
            self.history.append(col)

    def backtrack(self):
        col = self.history.pop()
        self.col_heights[col] -= 1
        self.moves -= 1
        self.board[self.col_heights[col]][col] = 0

    def winning_state(self, player):
        pad_b = pad(self.board, 3, mode='constant', constant_values=-1)
        for row in range(3, self.h + 3):
            for col in range(3, self.w + 3):
                windows = self.__get_windows(pad_b, row, col)
                for w in windows:
                    if w.count(player) == 4:
                        return True
        return False

    def score_board(self, player):
        score = 0

        # center column
        center = list(self.board[:, self.w // 2])
        center_count = center.count(player)
        score += center_count * 3

        # horizontal, vertical and diagonal windows
        pad_b = pad(self.board, 3, mode='constant', constant_values=-1)
        for row in range(3, self.h + 3):
            for col in range(3, self.w + 3):
                windows = self.__get_windows(pad_b, row, col)
                for w in windows:
                    score += self.__window_eval(w, player)

        return score

    def terminal_state(self):
        if self.winning_state(1):
            return True
        if self.winning_state(2):
            return True
        if self.moves == self.w * self.h:
            return True
        return False

    def solve(self, depth):
        maximiser_id = self.get_current_player()
        minimiser_id = self.get_opponent()

        def recurse(d, alpha, beta, maximiser):

            # recursive base cases
            if self.terminal_state():
                if self.winning_state(maximiser_id):
                    return (None, 100000 + d)       # win for maximiser
                elif self.winning_state(minimiser_id):
                    return (None, -(100000 + d))    # win for minimiser
                else:
                    return (None, 0)                # draw game
            if d == 0:
                return (None, self.score_board(maximiser_id))

            # minimax implementation
            playable_cols = self.get_playable_cols()
            if maximiser:
                value = -1000000
                column = random_choice(playable_cols)
                for col in playable_cols:
                    self.play(col)
                    next_value = recurse(d - 1, alpha, beta, False)[1]
                    self.backtrack()
                    if next_value > value:
                        value = next_value
                        column = col
                    alpha = max(alpha, value)
                    if alpha >= beta:
                        break   # alpha cut-off
                return (column, value)
            else:
                value = 1000000
                column = random_choice(playable_cols)
                for col in playable_cols:
                    self.play(col)
                    next_value = recurse(d - 1, alpha, beta, True)[1]
                    self.backtrack()
                    if next_value < value:
                        value = next_value
                        column = col
                    beta = min(beta, value)
                    if beta <= alpha:
                        break   # beta cut-off
                return (column, value)
        return recurse(depth, -1000000, 1000000, True)

    def __get_windows(self, pad_b, row, col):
        # private method called in winning_state and score_board
        alignments = [
            [(-1, 0), (-2, 0), (-3, 0)],    # | vertical
            [(0, -3), (0, -2), (0, -1)],    # - horizontal
            [(3, -3), (2, -2), (1, -1)],    # \ diagonal
            [(-3, -3), (-2, -2), (-1, -1)],  # / diagonal
        ]
        windows = []
        for a in alignments:
            window = [
                pad_b[row][col],
                pad_b[row + a[0][0]][col + a[0][1]],
                pad_b[row + a[1][0]][col + a[1][1]],
                pad_b[row + a[2][0]][col + a[2][1]]
            ]
            if -1 in window:    # exclude windows in padding
                continue
            windows.append(window)
        return windows

    def __window_eval(self, window, player):
        # private method called in score_board
        opp = 1 if player == 2 else 2
        score = 0

        if window.count(player) == 4:
            score += 100
        elif window.count(player) == 3 and window.count(0) == 1:
            score += 5
        elif window.count(player) == 2 and window.count(0) == 2:
            score += 2

        if window.count(opp) == 3 and window.count(0) == 1:
            score -= 4

        return score


class GameInterface(Board):
    """
    - extends Board class with interface-specific game management
    - configures and controls physical output devices
    """

    def __init__(self):
        super().__init__()

        # init output devices
        self.button_r = Button(4)
        self.button_c = Button(3)
        self.button_g = Button(2)

        self.photointerrupters = [
            Button(14, pull_up=None, active_state=False),
            Button(15, pull_up=None, active_state=False),
            Button(18, pull_up=None, active_state=False),
            Button(23, pull_up=None, active_state=False),
            Button(24, pull_up=None, active_state=False),
            Button(25, pull_up=None, active_state=False),
            Button(8, pull_up=None, active_state=False)
        ]

        self.dispense_disc = ExtendedServo(7, 0.5)
        self.empty_board = ExtendedServo(12, 1)
        self.stepper = Stepper(17, 27, 400)
        self.lcd = CharLCD(26, 19, 13, 6, 5, 11)

        # set button and photointerrupter callbacks
        self.button_r.when_pressed = self.reset
        self.button_c.when_pressed = self.c_callback
        self.button_g.when_pressed = self.g_callback

        for interrupter in self.photointerrupters:
            interrupter.when_released = self.interrupter_release
        self.reset()

    def reset(self):
        self.lcd.clear()
        self.reset_board()
        self.empty_board.return_ticket(-1, 2)
        self.game_state = 'home'
        self.lcd.disp_msg(lcd_msgs[0])
        self.lvl_depth = {
            'easy': 2,
            'med': 3,
            'hard': 4
        }
        self.player_id, self.bot_id, self.depth = 1, 2, self.lvl_depth['easy']
        self.col_0_pos, self.col_6_pos = self.get_stepper_calibration()

    def bot_play(self):
        col, score = self.solve(self.depth)
        print('column {} scores {}'.format(col, score))
        # temporarily disable interrupters (bug fix)
        for interrupter in self.photointerrupters:
            interrupter.when_pressed = None
        self.lcd.disp_msg(lcd_msgs[9])
        self.play(col)
        self.drop_disc(col)

    def get_stepper_calibration(self):
        # reads from txt file to allow recalibration from a separate script
        calib_data = open(
            '/home/pi/Documents/RobotFinal/stepper_calibration.txt', 'r')
        calib_data = calib_data.read()
        calib_values = calib_data.splitlines()
        return float(calib_values[0]), float(calib_values[1])

    def drop_disc(self, col):
        revs = self.col_0_pos + col * (self.col_6_pos - self.col_0_pos) / 6
        self.stepper.turn(revs)
        self.dispense_disc.value = -0.5

    def dispenser_return(self):
        self.dispense_disc.reset()
        self.stepper.return_home()

    # light gate factory func
    def interrupter_factory(self, col_index):
        def interrupter_callback():
            if self.game_state == 'active':
                # move detected - update board in memory
                self.play(col_index)
        return interrupter_callback

    def interrupter_release(self):
        print(self)
        if self.game_state == 'active':
            # return dispenser
            self.dispenser_return()
            opp = self.get_opponent()
            cur = self.get_current_player()

            # check for game over
            if self.winning_state(opp) and opp == self.player_id:
                # game over - player win
                self.game_state = 'completed'
                self.lcd.disp_msg(lcd_msgs[10])
            elif self.winning_state(opp) and opp == self.bot_id:
                # game over - bot win
                self.game_state = 'completed'
                self.lcd.disp_msg(lcd_msgs[11])
            elif self.moves == self.w * self.h:
                # game over - draw game
                self.game_state = 'completed'
                self.lcd.disp_msg(lcd_msgs[12])

            # prepare for next move
            if self.game_state == 'active' and cur == self.player_id:
                # player to move - restore photointerrupters
                for col, interrupter in enumerate(self.photointerrupters):
                    interrupter.when_pressed = self.interrupter_factory(col)
                self.lcd.disp_msg(lcd_msgs[7])

            elif self.game_state == 'active' and cur == self.bot_id:
                # bot to move
                self.lcd.disp_msg(lcd_msgs[8])
                self.bot_play()

    def c_callback(self):
        if self.game_state == 'set difficulty':
            cur = self.depth
            if cur == self.lvl_depth['easy']:
                self.depth = self.lvl_depth['med']
                self.lcd.disp_msg(lcd_msgs[2])
            elif cur == self.lvl_depth['med']:
                self.depth = self.lvl_depth['hard']
                self.lcd.disp_msg(lcd_msgs[3])
            else:
                self.depth = self.lvl_depth['easy']
                self.lcd.disp_msg(lcd_msgs[1])

        elif self.game_state == 'set player 1':
            self.bot_id, self.player_id = self.player_id, self.bot_id
            if self.player_id == 1:
                self.lcd.disp_msg(lcd_msgs[4])
            else:
                self.lcd.disp_msg(lcd_msgs[5])

    def g_callback(self):
        if self.game_state == 'home':
            self.game_state = 'set difficulty'
            self.lcd.disp_msg(lcd_msgs[1])
        elif self.game_state == 'set difficulty':
            self.game_state = 'set player 1'
            self.lcd.disp_msg(lcd_msgs[4])
        elif self.game_state == 'set player 1':
            self.game_state = 'fill counters'
            self.lcd.disp_msg(lcd_msgs[6])
        elif self.game_state == 'fill counters':
            self.game_state = 'active'
            if self.player_id == 1:
                # setup photointerrupters for disc detection
                for col, interrupter in enumerate(self.photointerrupters):
                    interrupter.when_pressed = self.interrupter_factory(col)
                self.lcd.disp_msg(lcd_msgs[7])
            else:
                self.lcd.disp_msg(lcd_msgs[8])
                self.bot_play()
