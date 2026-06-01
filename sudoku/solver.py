"""
Sudoku backtracking solver.
Original logic by Tim Ruscica, kept as-is — works perfectly.
"""


def solve(board):
    """Solves the board in-place. Returns True if solved, False if unsolvable."""
    find = find_empty(board)
    if not find:
        return True

    row, col = find
    for num in range(1, 10):
        if is_valid(board, num, (row, col)):
            board[row][col] = num
            if solve(board):
                return True
            board[row][col] = 0

    return False


def is_valid(board, num, pos):
    row, col = pos

    # Check row
    if any(board[row][j] == num and j != col for j in range(9)):
        return False

    # Check column
    if any(board[i][col] == num and i != row for i in range(9)):
        return False

    # Check 3x3 box
    box_r, box_c = (row // 3) * 3, (col // 3) * 3
    for i in range(box_r, box_r + 3):
        for j in range(box_c, box_c + 3):
            if board[i][j] == num and (i, j) != pos:
                return False

    return True


def find_empty(board):
    for i in range(len(board)):
        for j in range(len(board[0])):
            if board[i][j] == 0:
                return (i, j)
    return None


def print_board(board):
    for i, row in enumerate(board):
        if i % 3 == 0 and i != 0:
            print("------+-------+------")
        for j, val in enumerate(row):
            if j % 3 == 0 and j != 0:
                print("| ", end="")
            print(f"{val} ", end="")
        print()
