#include <iostream>
using namespace std;
#include "types.hpp"
#include "mask.hpp"

void set_background(int color)
{
    cout << "\x1b[" << color << "m";
}

void set_foreground(int color)
{
    cout << "\x1b[" << color << "m";
}

void print_square_color(Piece piece, int i, int j, int mask_value)
{
    
    if (mask_value == 0)
    {
        if ((i + j) % 2 == 0)
            cout << "\x1b[48;5;230m"; // case claire (bois clair)
        else
            cout << "\x1b[48;5;94m";  // case foncée (bois foncé)
    }
    else
    {
        cout << "\x1b[48;5;21m"; // masque bleu
    }

    // 2️ Couleur des pièces
    if (piece == WHITE_KING || piece == WHITE_QUEEN || piece == WHITE_ROOK ||
        piece == WHITE_BISHOP || piece == WHITE_KNIGHT || piece == WHITE_PAWN)
        cout << "\x1b[30m"; 
    else if (piece != EMPTY)
        cout << "\x1b[97m"; 

   
    if (piece == WHITE_KING) cout << "♔";
    else if (piece == WHITE_QUEEN) cout << "♕";
    else if (piece == WHITE_ROOK) cout << "♖";
    else if (piece == WHITE_BISHOP) cout << "♗";
    else if (piece == WHITE_KNIGHT) cout << "♘";
    else if (piece == WHITE_PAWN) cout << "♙";
    else if (piece == BLACK_KING) cout << "♚";
    else if (piece == BLACK_QUEEN) cout << "♛";
    else if (piece == BLACK_ROOK) cout << "♜";
    else if (piece == BLACK_BISHOP) cout << "♝";
    else if (piece == BLACK_KNIGHT) cout << "♞";
    else if (piece == BLACK_PAWN) cout << "♟";
    else cout << " "; 

    cout << " "; 

    
    cout << "\x1b[0m";
}

void print_board_color(Board &A, mask m)
{
    cout << "  a b c d e f g h" << endl;

    for (int i = 0; i < 8; i++)
    {
        cout << 8 - i << " ";

        for (int j = 0; j < 8; j++)
        {
            print_square_color(A[i][j], i, j, m.data[i*8+j]);
        }

        cout << " " << 8 - i << endl;
    }

    cout << "  a b c d e f g h" << endl;
}
