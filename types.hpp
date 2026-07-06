#ifndef TYPES_HPP_
#define TYPES_HPP_

#include <iostream>
using namespace std;

enum PieceColor 
{
    NOIR,
    BLANC
};

enum Piece
{
    EMPTY = 0,
    WHITE_KING,
    WHITE_QUEEN,
    WHITE_ROOK,
    WHITE_BISHOP,
    WHITE_KNIGHT,
    WHITE_PAWN,
    BLACK_KING,
    BLACK_QUEEN,
    BLACK_ROOK,
    BLACK_BISHOP,
    BLACK_KNIGHT,
    BLACK_PAWN
};

using Board = Piece[8][8];

struct game
{
    Board board;
    bool tourdesblanc;
};

struct mask
{
    int data[64];
};

enum joueur
{
    humain,
    computer
};

struct historique
{
    int from_ligne;
    int from_colone;
    int to_ligne;
    int to_colone;
    Piece piece;
    Piece prise;
};

struct game_complete
{
    Board board;
    bool tourdesblanc;
    historique coups[500];
    int nb_coups;
    int pieces_prises_blanc[16];
    int pieces_prises_noir[16];
    int nb_prises_blanc;
    int nb_prises_noir;
};

void MAJ_historique(game_complete &g, int from_ligne, int from_colone, int to_ligne, int to_colone);
void play_historique(game_complete &g);
void backtrack_historique(game_complete &g, int n);
bool king_in_check(game &tour, int couleur);
bool king_in_checkmate(game &tour, int couleur);
int compute_score(game &tour, int couleur);

#endif