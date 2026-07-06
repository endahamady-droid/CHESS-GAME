#ifndef GAME_HPP_
#define GAME_HPP_

#include "types.hpp"

void one_run(joueur current_player, game &tour);
void choose_movement_computer(int &ligneD, int &coloneD, int &ligneA, int &coloneA, game &tour);
void one_run_computer(game &tour);
void choose_movement_humain(int &ligned, int &coloned, int &lignea, int &colonea, game &tour);
void one_run_humain(game &tour);
bool test_run(int ligneD, int coloneD, int ligneA, int coloneA, game &tour);
PieceColor getcolor(Piece piece);
bool king_in_check(game &tour, int couleur);
bool king_in_checkmate(game &tour, int couleur);
int compute_score(game &tour, int couleur);

#endif