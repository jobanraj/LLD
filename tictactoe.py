from abc import ABC, abstractmethod
from collections import deque

# Observer Pattern
class IObserver(ABC):
    @abstractmethod
    def update(self, msg: str) -> None:
        pass

class ConsoleNotifier(IObserver):
    def update(self, msg: str) -> None:
        print(f"[Notification] {msg}")

# Symbol class
class Symbol:
    def __init__(self, mark: str):
        self._mark = mark
        
    @property
    def mark(self) -> str:
        return self._mark

# Board class
class Board:
    def __init__(self, size: int):
        self.size = size
        self.empty_cell = Symbol('-')
        self.grid = [[self.empty_cell for _ in range(size)] for _ in range(size)]
        
    def is_cell_empty(self, row: int, col: int) -> bool:
        if row < 0 or row >= self.size or col < 0 or col >= self.size:
            return False
        return self.grid[row][col] == self.empty_cell
        
    def place_mark(self, row: int, col: int, mark: Symbol) -> bool:
        if not self.is_cell_empty(row, col):
            return False
        self.grid[row][col] = mark
        return True
        
    def get_cell(self, row: int, col: int) -> Symbol:
        if row < 0 or row >= self.size or col < 0 or col >= self.size:
            return self.empty_cell
        return self.grid[row][col]
        
    def display(self) -> None:
        print("\n  " + " ".join(str(i) for i in range(self.size)))
        for i in range(self.size):
            row_str = " ".join(self.grid[i][j].mark for j in range(self.size))
            print(f"{i} {row_str}")
        print()

# Player class
class TicTacToePlayer:
    def __init__(self, player_id: int, name: str, symbol: Symbol):
        self.player_id = player_id
        self.name = name
        self.symbol = symbol
        self.score = 0
        
    def increment_score(self) -> None:
        self.score += 1

# Strategy Pattern for game rules
class TicTacToeRules(ABC):
    @abstractmethod
    def is_valid_move(self, board: Board, row: int, col: int) -> bool:
        pass
        
    @abstractmethod
    def check_win_condition(self, board: Board, symbol: Symbol) -> bool:
        pass
        
    @abstractmethod
    def check_draw_condition(self, board: Board) -> bool:
        pass

class StandardTicTacToeRules(TicTacToeRules):
    def is_valid_move(self, board: Board, row: int, col: int) -> bool:
        return board.is_cell_empty(row, col)
        
    def check_win_condition(self, board: Board, symbol: Symbol) -> bool:
        size = board.size
        
        # Check rows
        for i in range(size):
            if all(board.get_cell(i, j) == symbol for j in range(size)):
                return True
                
        # Check columns
        for j in range(size):
            if all(board.get_cell(i, j) == symbol for i in range(size)):
                return True
                
        # Check main diagonal
        if all(board.get_cell(i, i) == symbol for i in range(size)):
            return True
            
        # Check anti-diagonal
        if all(board.get_cell(i, size - 1 - i) == symbol for i in range(size)):
            return True
            
        return False
        
    def check_draw_condition(self, board: Board) -> bool:
        size = board.size
        for i in range(size):
            for j in range(size):
                if board.get_cell(i, j) == board.empty_cell:
                    return False
        return True

# Game class
class TicTacToeGame:
    def __init__(self, board_size: int):
        self.board = Board(board_size)
        self.players = deque()
        self.rules = StandardTicTacToeRules()
        self.observers = []
        self.game_over = False
        
    def add_player(self, player: TicTacToePlayer) -> None:
        self.players.append(player)
        
    def add_observer(self, observer: IObserver) -> None:
        self.observers.append(observer)
        
    def notify_observers(self, msg: str) -> None:
        for observer in self.observers:
            observer.update(msg)
            
    def play(self) -> None:
        if len(self.players) < 2:
            print("Need at least 2 players!")
            return
            
        self.notify_observers("Tic Tac Toe Game Started!")
        
        while not self.game_over:
            self.board.display()
            
            current_player = self.players[0]
            print(f"{current_player.name} ({current_player.symbol.mark}) - Enter row and column: ", end="")
            
            try:
                # Read row and column inputs
                user_input = input().split()
                row, col = int(user_input[0]), int(user_input[1])
            except (ValueError, IndexError):
                print("Invalid input format! Enter two numbers.")
                continue
                
            if self.rules.is_valid_move(self.board, row, col):
                self.board.place_mark(row, col, current_player.get_symbol) # passing mark reference indirectly or directly
                self.board.grid[row][col] = current_player.symbol
                self.notify_observers(f"{current_player.name} played ({row},{col})")
                
                if self.rules.check_win_condition(self.board, current_player.symbol):
                    self.board.display()
                    print(f"{current_player.name} wins!")
                    current_player.increment_score()
                    self.notify_observers(f"{current_player.name} wins!")
                    self.game_over = True
                    
                elif self.rules.check_draw_condition(self.board):
                    self.board.display()
                    print("It's a draw!")
                    self.notify_observers("Game is Draw!")
                    self.game_over = True
                    
                else:
                    # Move player to back of queue
                    self.players.rotate(-1)
            else:
                print("Invalid move! Try again.")

# Factory Pattern
class GameType:
    STANDARD = "STANDARD"

class TicTacToeGameFactory:
    @staticmethod
    def create_game(game_type: str, board_size: int) -> TicTacToeGame:
        if game_type == GameType.STANDARD:
            return TicTacToeGame(board_size)
        return None

# Main execution
if __name__ == "__main__":
    print("=== TIC TAC TOE GAME ===")
    
    try:
        size = int(input("Enter board size: "))
    except ValueError:
        size = 3
        
    game = TicTacToeGameFactory.create_game(GameType.STANDARD, size)
    
    # Add console logger
    logger = ConsoleNotifier()
    game.add_observer(logger)
    
    # Add standard players
    p1 = TicTacToePlayer(1, "Alice", Symbol("X"))
    p2 = TicTacToePlayer(2, "Bob", Symbol("O"))
    
    game.add_player(p1)
    game.add_player(p2)
    
    game.play()
