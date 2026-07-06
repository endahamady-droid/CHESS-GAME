#ifndef BOARD_HPP_
#define BOARD_HPP_

#include "types.hpp"
#include <string>
using namespace std;

void empty(Board &a);
Piece get_square(Board &A, int ligne, int colone);
void set_square(Board &B, int ligne, int colone, Piece piece);
void start(Board &G);
int move_piece(Board &N, int lignedepart, int colonedepart, int ligneariv, int coloneariv);
void write_FEN(Board &a, const string &filename);
void read_fen(const string &filename, Board &q);

#endif