#ifndef MASK_HPP_
#define MASK_HPP_

#include "types.hpp"

mask empty_mask();
void clear_mask(mask &A);
int get_mask(mask &m, int ligne, int colone);
void set_mask(mask &m, int ligne, int colone, int valeur);
void highlight_possible_moves_rook(mask &m, int couleur, int ligne, int colone, Board &b);
void highlight_possible_moves_king(mask &m, int couleur, int ligne, int colone, Board &b);
void highlight_possible_moves_bishop(mask &m, int couleur, int ligne, int colone, Board &b);
void highlight_possible_moves_queen(mask &m, int couleur, int ligne, int colone, Board &b);
void highlight_possible_moves_horse(mask &m, int couleur, int ligne, int colone, Board &b);
void highlight_possible_moves(mask &m, int couleur, int ligne, int colone, Board &b);
void pawnmoves(mask &m, Board &b, int ligne, int colone, int couleur);
void highlight_movable_pieces(mask &m, int couleur, Board &b);
void highlight_attacked_pieces(mask &m, int couleur, Board &b);
void highlight_take_pieces(mask &m, int couleur, int ligne, int colone, Board &b);
void mask_choices_menu();
void mask_choices(mask &m, int couleur, Board &b);

#endif