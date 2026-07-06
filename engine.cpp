#include <iostream>
#include <sstream>
#include <string>

#include "types.hpp"
#include "board.hpp"
#include "mask.hpp"

using namespace std;

static PieceColor piece_color(Piece piece)
{
    if (piece >= WHITE_KING && piece <= WHITE_PAWN)
        return BLANC;
    return NOIR;
}

static bool is_mine(Piece piece, int color)
{
    if (piece == EMPTY)
        return false;
    return piece_color(piece) == color;
}

static bool find_king(game &state, int color, int &king_row, int &king_col)
{
    Piece king = (color == BLANC) ? WHITE_KING : BLACK_KING;
    for (int row = 0; row < 8; row++)
        for (int col = 0; col < 8; col++)
            if (state.board[row][col] == king)
            {
                king_row = row;
                king_col = col;
                return true;
            }
    return false;
}

static bool king_in_check_engine(game &state, int color)
{
    int king_row = -1;
    int king_col = -1;
    if (!find_king(state, color, king_row, king_col))
        return false;

    int opponent = (color == BLANC) ? NOIR : BLANC;
    for (int row = 0; row < 8; row++)
    {
        for (int col = 0; col < 8; col++)
        {
            Piece piece = state.board[row][col];
            if (piece == EMPTY || piece_color(piece) != opponent)
                continue;

            mask moves;
            clear_mask(moves);
            highlight_possible_moves(moves, opponent, row, col, state.board);
            if (get_mask(moves, king_row, king_col) == 1)
                return true;
        }
    }

    return false;
}

static bool is_legal_move_engine(game &state, int color, int from_row, int from_col, int to_row, int to_col)
{
    Piece piece = state.board[from_row][from_col];
    if (piece == EMPTY || !is_mine(piece, color))
        return false;

    Piece destination = state.board[to_row][to_col];
    if (destination != EMPTY && piece_color(destination) == color)
        return false;

    mask moves;
    clear_mask(moves);
    highlight_possible_moves(moves, color, from_row, from_col, state.board);
    if (get_mask(moves, to_row, to_col) != 1)
        return false;

    game simulation;
    simulation.tourdesblanc = state.tourdesblanc;
    for (int row = 0; row < 8; row++)
        for (int col = 0; col < 8; col++)
            simulation.board[row][col] = state.board[row][col];

    simulation.board[to_row][to_col] = simulation.board[from_row][from_col];
    simulation.board[from_row][from_col] = EMPTY;

    return !king_in_check_engine(simulation, color);
}

static bool has_no_legal_move_engine(game &state, int color)
{
    for (int from_row = 0; from_row < 8; from_row++)
    {
        for (int from_col = 0; from_col < 8; from_col++)
        {
            if (!is_mine(state.board[from_row][from_col], color))
                continue;

            for (int to_row = 0; to_row < 8; to_row++)
                for (int to_col = 0; to_col < 8; to_col++)
                    if (is_legal_move_engine(state, color, from_row, from_col, to_row, to_col))
                        return false;
        }
    }

    return true;
}

static bool parse_fen_board(const string &fen, Board &board)
{
    empty(board);
    int row = 0;
    int col = 0;

    for (char c : fen)
    {
        if (c == ' ')
            break;
        if (c == '/')
        {
            row++;
            col = 0;
            continue;
        }
        if (row < 0 || row >= 8 || col < 0 || col >= 8)
            return false;
        if (c >= '1' && c <= '8')
        {
            col += c - '0';
            continue;
        }

        Piece piece = EMPTY;
        if (c == 'K') piece = WHITE_KING;
        else if (c == 'Q') piece = WHITE_QUEEN;
        else if (c == 'R') piece = WHITE_ROOK;
        else if (c == 'B') piece = WHITE_BISHOP;
        else if (c == 'N') piece = WHITE_KNIGHT;
        else if (c == 'P') piece = WHITE_PAWN;
        else if (c == 'k') piece = BLACK_KING;
        else if (c == 'q') piece = BLACK_QUEEN;
        else if (c == 'r') piece = BLACK_ROOK;
        else if (c == 'b') piece = BLACK_BISHOP;
        else if (c == 'n') piece = BLACK_KNIGHT;
        else if (c == 'p') piece = BLACK_PAWN;
        else return false;

        board[row][col] = piece;
        col++;
    }

    return row == 7 && col == 8;
}

static char piece_to_fen(Piece piece)
{
    if (piece == WHITE_KING) return 'K';
    if (piece == WHITE_QUEEN) return 'Q';
    if (piece == WHITE_ROOK) return 'R';
    if (piece == WHITE_BISHOP) return 'B';
    if (piece == WHITE_KNIGHT) return 'N';
    if (piece == WHITE_PAWN) return 'P';
    if (piece == BLACK_KING) return 'k';
    if (piece == BLACK_QUEEN) return 'q';
    if (piece == BLACK_ROOK) return 'r';
    if (piece == BLACK_BISHOP) return 'b';
    if (piece == BLACK_KNIGHT) return 'n';
    if (piece == BLACK_PAWN) return 'p';
    return ' ';
}

static string board_to_fen(Board &board)
{
    ostringstream out;
    for (int row = 0; row < 8; row++)
    {
        int empty_count = 0;
        for (int col = 0; col < 8; col++)
        {
            Piece piece = board[row][col];
            if (piece == EMPTY)
            {
                empty_count++;
                continue;
            }
            if (empty_count > 0)
            {
                out << empty_count;
                empty_count = 0;
            }
            out << piece_to_fen(piece);
        }
        if (empty_count > 0)
            out << empty_count;
        if (row < 7)
            out << '/';
    }
    return out.str();
}

static bool parse_move(const string &move, int &from_row, int &from_col, int &to_row, int &to_col)
{
    if (move.size() != 4)
        return false;
    if (move[0] < 'a' || move[0] > 'h' || move[2] < 'a' || move[2] > 'h')
        return false;
    if (move[1] < '1' || move[1] > '8' || move[3] < '1' || move[3] > '8')
        return false;

    from_col = move[0] - 'a';
    from_row = 8 - (move[1] - '0');
    to_col = move[2] - 'a';
    to_row = 8 - (move[3] - '0');
    return true;
}

static void promote_if_needed(game &state, int row, int col)
{
    if (state.board[row][col] == WHITE_PAWN && row == 0)
        state.board[row][col] = WHITE_QUEEN;
    if (state.board[row][col] == BLACK_PAWN && row == 7)
        state.board[row][col] = BLACK_QUEEN;
}

int main(int argc, char **argv)
{
    if (argc >= 2 && string(argv[1]) == "start")
    {
        Board board;
        start(board);
        cout << board_to_fen(board) << endl;
        return 0;
    }

    if (argc != 4)
    {
        cerr << "Usage: engine start | engine <fen> <white|black> <move>" << endl;
        return 2;
    }

    game state;
    if (!parse_fen_board(argv[1], state.board))
    {
        cout << "invalid bad_fen" << endl;
        return 0;
    }

    string turn = argv[2];
    state.tourdesblanc = (turn == "white");
    if (turn != "white" && turn != "black")
    {
        cout << "invalid bad_turn" << endl;
        return 0;
    }

    int from_row, from_col, to_row, to_col;
    if (!parse_move(argv[3], from_row, from_col, to_row, to_col))
    {
        cout << "invalid bad_move_format" << endl;
        return 0;
    }

    int current_color = state.tourdesblanc ? BLANC : NOIR;
    if (!is_legal_move_engine(state, current_color, from_row, from_col, to_row, to_col))
    {
        cout << "invalid illegal_move" << endl;
        return 0;
    }

    state.board[to_row][to_col] = state.board[from_row][from_col];
    state.board[from_row][from_col] = EMPTY;
    promote_if_needed(state, to_row, to_col);
    state.tourdesblanc = !state.tourdesblanc;

    int next_color = state.tourdesblanc ? BLANC : NOIR;
    bool check = king_in_check_engine(state, next_color);
    bool checkmate = check && has_no_legal_move_engine(state, next_color);

    cout << "ok " << board_to_fen(state.board) << " "
         << (state.tourdesblanc ? "white" : "black") << " "
         << (check ? "check" : "safe") << " "
         << (checkmate ? "checkmate" : "playing") << endl;
    return 0;
}
