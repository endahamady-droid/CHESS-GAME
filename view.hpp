#ifndef VIEW_HPP_
#define VIEW_HPP_

#include <iostream>
#include <string>
using namespace std;
#include "types.hpp"

void set_background(int color);
void set_foreground(int color);
void print_square_color(Piece piece, int i, int j, int mask_value);
void print_board_color(Board &A, mask m);

#endif