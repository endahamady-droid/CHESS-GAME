#include <iostream>
using namespace std;
#include "types.hpp"
#include "mask.hpp"
#include "board.hpp"

mask empty_mask()
{
    mask A;
    for (int i = 0; i < 64; i++)
        A.data[i] = 0;
    return A;
}

void clear_mask(mask &A)
{
    for (int i = 0; i < 64; i++)
        A.data[i] = 0;
}

int get_mask(mask &m, int ligne, int colone)
{
    return m.data[ligne * 8 + colone];
}

void set_mask(mask &m, int ligne, int colone, int valeur)
{
    m.data[ligne * 8 + colone] = valeur;
}

void highlight_possible_moves_rook(mask &m, int couleur, int ligne, int colone, Board &b)
{
    for(int j = colone+1; j < 8; j++) {
        if(b[ligne][j] == EMPTY)
            set_mask(m, ligne, j, 1);
        else {
            if((couleur == BLANC && b[ligne][j] >= BLACK_KING) ||
               (couleur == NOIR && b[ligne][j] <= WHITE_PAWN))
                set_mask(m, ligne, j, 1);
            break;
        }
    }
    for(int j = colone-1; j >= 0; j--) {
        if(b[ligne][j] == EMPTY)
            set_mask(m, ligne, j, 1);
        else {
            if((couleur == BLANC && b[ligne][j] >= BLACK_KING) ||
               (couleur == NOIR && b[ligne][j] <= WHITE_PAWN))
                set_mask(m, ligne, j, 1);
            break;
        }
    }
    for(int i = ligne+1; i < 8; i++) {
        if(b[i][colone] == EMPTY)
            set_mask(m, i, colone, 1);
        else {
            if((couleur == BLANC && b[i][colone] >= BLACK_KING) ||
               (couleur == NOIR && b[i][colone] <= WHITE_PAWN))
                set_mask(m, i, colone, 1);
            break;
        }
    }
    for(int i = ligne-1; i >= 0; i--) {
        if(b[i][colone] == EMPTY)
            set_mask(m, i, colone, 1);
        else {
            if((couleur == BLANC && b[i][colone] >= BLACK_KING) ||
               (couleur == NOIR && b[i][colone] <= WHITE_PAWN))
                set_mask(m, i, colone, 1);
            break;
        }
    }
}

void pawnmoves(mask &m, Board &b, int ligne, int colone, int couleur)
{
    clear_mask(m);
    int direction = (couleur == BLANC) ? -1 : 1;
    int nouvposi = ligne + direction;
    if(nouvposi >= 0 && nouvposi < 8 && b[nouvposi][colone] == EMPTY) {
        set_mask(m, nouvposi, colone, 1);
        if((ligne == 6 && couleur == BLANC) || (ligne == 1 && couleur == NOIR)) {
            int doubleposi = ligne + 2*direction;
            if(doubleposi >= 0 && doubleposi < 8 && b[doubleposi][colone] == EMPTY)
                set_mask(m, doubleposi, colone, 1);
        }
    }
    int case_suiv = ligne + direction;
    if(case_suiv >= 0 && case_suiv <= 7) {
        if(colone+1 <= 7 && b[case_suiv][colone+1] != EMPTY &&
           ((couleur == BLANC && b[case_suiv][colone+1] >= BLACK_KING) ||
            (couleur == NOIR && b[case_suiv][colone+1] <= WHITE_PAWN)))
            set_mask(m, case_suiv, colone+1, 1);
        if(colone-1 >= 0 && b[case_suiv][colone-1] != EMPTY &&
           ((couleur == BLANC && b[case_suiv][colone-1] >= BLACK_KING) ||
            (couleur == NOIR && b[case_suiv][colone-1] <= WHITE_PAWN)))
            set_mask(m, case_suiv, colone-1, 1);
    }
}

void highlight_possible_moves_king(mask &m, int couleur, int ligne, int colone, Board &b)
{
    for(int di = -1; di <= 1; di++)
        for(int dj = -1; dj <= 1; dj++) {
            if(di == 0 && dj == 0) continue;
            int ni = ligne + di, nj = colone + dj;
            if(ni >= 0 && ni < 8 && nj >= 0 && nj < 8) {
                if(b[ni][nj] == EMPTY ||
                   (couleur == BLANC && b[ni][nj] >= BLACK_KING) ||
                   (couleur == NOIR && b[ni][nj] <= WHITE_PAWN))
                    set_mask(m, ni, nj, 1);
            }
        }
}

void highlight_possible_moves_bishop(mask &m, int couleur, int ligne, int colone, Board &b)
{
    for(int di = -1; di <= 1; di+=2)
        for(int dj = -1; dj <= 1; dj+=2) {
            for(int i = 1; i < 8; i++) {
                int ni = ligne + i*di, nj = colone + i*dj;
                if(ni < 0 || ni >= 8 || nj < 0 || nj >= 8) break;
                if(b[ni][nj] == EMPTY)
                    set_mask(m, ni, nj, 1);
                else {
                    if((couleur == BLANC && b[ni][nj] >= BLACK_KING) ||
                       (couleur == NOIR && b[ni][nj] <= WHITE_PAWN))
                        set_mask(m, ni, nj, 1);
                    break;
                }
            }
        }
}

void highlight_possible_moves_queen(mask &m, int couleur, int ligne, int colone, Board &b)
{
    highlight_possible_moves_rook(m, couleur, ligne, colone, b);
    highlight_possible_moves_bishop(m, couleur, ligne, colone, b);
}

void highlight_possible_moves_horse(mask &m, int couleur, int ligne, int colone, Board &b)
{
    int deltas[8][2] = {{2,1},{2,-1},{-2,1},{-2,-1},{1,2},{1,-2},{-1,2},{-1,-2}};
    for(int k = 0; k < 8; k++) {
        int ni = ligne + deltas[k][0], nj = colone + deltas[k][1];
        if(ni >= 0 && ni < 8 && nj >= 0 && nj < 8) {
            if(b[ni][nj] == EMPTY ||
               (couleur == BLANC && b[ni][nj] >= BLACK_KING) ||
               (couleur == NOIR && b[ni][nj] <= WHITE_PAWN))
                set_mask(m, ni, nj, 1);
        }
    }
}

void highlight_possible_moves(mask &m, int couleur, int ligne, int colone, Board &b)
{
    Piece p = b[ligne][colone];
    if(p == WHITE_KING || p == BLACK_KING)
        highlight_possible_moves_king(m, couleur, ligne, colone, b);
    else if(p == WHITE_ROOK || p == BLACK_ROOK)
        highlight_possible_moves_rook(m, couleur, ligne, colone, b);
    else if(p == WHITE_PAWN || p == BLACK_PAWN)
        pawnmoves(m, b, ligne, colone, couleur);
    else if(p == WHITE_BISHOP || p == BLACK_BISHOP)
        highlight_possible_moves_bishop(m, couleur, ligne, colone, b);
    else if(p == WHITE_QUEEN || p == BLACK_QUEEN)
        highlight_possible_moves_queen(m, couleur, ligne, colone, b);
    else if(p == WHITE_KNIGHT || p == BLACK_KNIGHT)
        highlight_possible_moves_horse(m, couleur, ligne, colone, b);
}

void highlight_movable_pieces(mask &m, int couleur, Board &b)
{
    clear_mask(m);
    for(int i = 0; i < 8; i++)
        for(int j = 0; j < 8; j++) {
            if(b[i][j] != EMPTY && ((couleur == BLANC && b[i][j] <= WHITE_PAWN) ||
                                    (couleur == NOIR && b[i][j] >= BLACK_KING))) {
                mask temp;
                clear_mask(temp);
                highlight_possible_moves(temp, couleur, i, j, b);
                for(int k = 0; k < 64; k++)
                    if(temp.data[k] == 1) {
                        set_mask(m, i, j, 1);
                        break;
                    }
            }
        }
}

void highlight_attacked_pieces(mask &m, int couleur, Board &b)
{
    clear_mask(m);
    for(int i = 0; i < 8; i++)
        for(int j = 0; j < 8; j++) {
            if(b[i][j] != EMPTY && ((couleur == BLANC && b[i][j] <= WHITE_PAWN) ||
                                    (couleur == NOIR && b[i][j] >= BLACK_KING))) {
                mask temp;
                clear_mask(temp);
                highlight_possible_moves(temp, couleur, i, j, b);
                for(int k = 0; k < 64; k++)
                    if(temp.data[k] == 1 && b[k/8][k%8] != EMPTY)
                        set_mask(m, k/8, k%8, 1);
            }
        }
}

void highlight_take_pieces(mask &m, int couleur, int ligne, int colone, Board &b)
{
    clear_mask(m);
    int adv = (couleur == BLANC) ? NOIR : BLANC;
    for(int i = 0; i < 8; i++)
        for(int j = 0; j < 8; j++) {
            if((couleur == BLANC && b[i][j] != EMPTY && b[i][j] >= BLACK_KING) ||
               (couleur == NOIR && b[i][j] != EMPTY && b[i][j] <= WHITE_PAWN)) {
                mask temp;
                clear_mask(temp);
                highlight_possible_moves(temp, adv, i, j, b);
                if(get_mask(temp, ligne, colone) == 1)
                    set_mask(m, i, j, 1);
            }
        }
}

void mask_choices_menu()
{
    cout << "1 - Pieces qui peuvent bouger" << endl;
    cout << "2 - Pieces adverses attaquables" << endl;
    cout << "3 - Pieces qui menacent une piece" << endl;
    cout << "0 - Quitter" << endl;
}

void mask_choices(mask &m, int couleur, Board &b)
{
    int choix, ligne, colone;
    mask_choices_menu();
    cin >> choix;
    if(choix == 1)
        highlight_movable_pieces(m, couleur, b);
    else if(choix == 2)
        highlight_attacked_pieces(m, couleur, b);
    else if(choix == 3) {
        do {
            cout << "ligne (0-7) : "; cin >> ligne;
        } while(ligne < 0 || ligne > 7);
        do {
            cout << "colone (0-7) : "; cin >> colone;
        } while(colone < 0 || colone > 7);
        highlight_take_pieces(m, couleur, ligne, colone, b);
    }
}