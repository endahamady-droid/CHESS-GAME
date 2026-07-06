#include<iostream>
#include<cstdlib>
#include<cctype>
#include "game.hpp"
#include "mask.hpp"
using namespace std ;

PieceColor getcolor(Piece piece){
    if(piece>=WHITE_KING && piece<=WHITE_PAWN){
        return BLANC;
    }
    if(piece>=BLACK_KING && piece<=BLACK_PAWN){
        return NOIR;
    }
    return NOIR;
}

bool test_run(int ligneD,int coloneD,int ligneA,int coloneA,game &tour){
    Piece piece = tour.board[ligneD][coloneD];
    if(piece == EMPTY){
        return false ;
    }
    PieceColor color = getcolor(piece);
    if(tour.tourdesblanc==true && color!=BLANC){
        return false ;
    }
    if(tour.tourdesblanc==false && color!=NOIR){
        return false ;
    }
    Piece dest = tour.board[ligneA][coloneA];
    if(dest!=EMPTY){
        PieceColor colorDest = getcolor(dest);
        if(colorDest == color){
            return false ;
        }
    }
    
    mask m;
    clear_mask(m);
    highlight_possible_moves(m, color, ligneD, coloneD, tour.board);

    if(get_mask(m, ligneA, coloneA) != 1){
        return false;
    }

    // Simuler le coup pour verifier qu'il ne laisse pas son propre roi en echec
    game simulation;
    for(int i = 0; i < 8; i++)
        for(int j = 0; j < 8; j++)
            simulation.board[i][j] = tour.board[i][j];
    simulation.tourdesblanc = tour.tourdesblanc;

    simulation.board[ligneA][coloneA] = simulation.board[ligneD][coloneD];
    simulation.board[ligneD][coloneD] = EMPTY;

    if(king_in_check(simulation, color)){
        return false;
    }

    return true;
}

void one_run(joueur current_player,game &tour){
    if(current_player== humain){
        one_run_humain(tour);
    
    }
    else{
        one_run_computer(tour);
    }
}

void choose_movement_computer(int &ligneD, int &coloneD, int &ligneA, int &coloneA, game &tour) {
    int liste_coups[1000][4];
    int nb_coups = 0;

    for (int i = 0; i < 8; i++) {
        for (int j = 0; j < 8; j++) {
            Piece p = tour.board[i][j];
            if(p == EMPTY || getcolor(p) != (tour.tourdesblanc ? BLANC : NOIR))
                continue;

            mask m;
            clear_mask(m);
            highlight_possible_moves(m, (tour.tourdesblanc ? BLANC : NOIR), i, j, tour.board);

            for(int k = 0; k < 8; k++) {
                for(int l = 0; l < 8; l++) {
                    if(get_mask(m, k, l) == 1 && test_run(i, j, k, l, tour) && nb_coups < 1000) {
                        liste_coups[nb_coups][0] = i;
                        liste_coups[nb_coups][1] = j;
                        liste_coups[nb_coups][2] = k;
                        liste_coups[nb_coups][3] = l;
                        nb_coups++;
                    }
                }
            }
        }
    }

    if(nb_coups > 0) {
        int index = rand() % nb_coups;
        ligneD = liste_coups[index][0];
        coloneD = liste_coups[index][1];
        ligneA = liste_coups[index][2];
        coloneA = liste_coups[index][3];
        return;
    }

    // Aucun coup legal disponible
    ligneD = coloneD = ligneA = coloneA = -1;
}

void one_run_computer(game &tour){
    int ligned, coloned , lignea,colonea;

    choose_movement_computer(ligned,coloned,lignea,colonea,tour);

    if(ligned == -1){
        cout << "Aucun coup legal disponible." << endl;
        return;
    }

    tour.board[lignea][colonea]=tour.board[ligned][coloned];
    tour.board[ligned][coloned]=EMPTY;
    
    tour.tourdesblanc= !tour.tourdesblanc;
}

void choose_movement_humain(int &ligned, int &coloned, int &lignea, int &colonea, game &tour) {
    (void)tour; // non utilise pour la validation des bornes

    char coloneletter;
    int ligne_saisie;
    do {
        cout << "saisir la case de depart (ex: e2) : ";
        cin >> coloneletter >> ligne_saisie;
        coloneletter = (char)tolower(coloneletter);
    } while(coloneletter < 'a' || coloneletter > 'h' || ligne_saisie < 1 || ligne_saisie > 8);
    coloned = coloneletter - 'a';
    ligned = ligne_saisie - 1;

    char coloneletterariv;
    int ligne_saisie_ariv;
    do {
        cout << "saisir la case d'arrive (ex: e4) : ";
        cin >> coloneletterariv >> ligne_saisie_ariv;
        coloneletterariv = (char)tolower(coloneletterariv);
    } while(coloneletterariv < 'a' || coloneletterariv > 'h' || ligne_saisie_ariv < 1 || ligne_saisie_ariv > 8);
    colonea = coloneletterariv - 'a';
    lignea = ligne_saisie_ariv - 1;
}

void one_run_humain(game &tour ){
    int ligned, coloned, lignea, colonea;
    bool coup_valide;
    do {
        choose_movement_humain(ligned, coloned, lignea, colonea, tour);
        coup_valide = test_run(ligned, coloned, lignea, colonea, tour);
        if(!coup_valide)
            cout << "Coup illegal, recommencez." << endl;
    } while(!coup_valide);

    tour.board[lignea][colonea] = tour.board[ligned][coloned];
    tour.board[ligned][coloned] = EMPTY;
    tour.tourdesblanc = !tour.tourdesblanc;
}

bool king_in_check(game &tour, int couleur) {
    int roi_ligne = -1;
    int roi_colone = -1;
    Piece roi;
    if(couleur == BLANC){
        roi = WHITE_KING;
    } else {
        roi = BLACK_KING;
    }
    for(int i = 0; i < 8; i++) {
        for(int j = 0; j < 8; j++) {
            if(tour.board[i][j] == roi) {
                roi_ligne = i;
                roi_colone = j;
                break;
            }
        }
    }
    if(roi_ligne == -1) return false;
    int couleur_adverse;
    if(couleur == BLANC){
        couleur_adverse = NOIR;
    } else {
        couleur_adverse = BLANC;
    }
    mask m;
    clear_mask(m);
    for(int i = 0; i < 8; i++) {
        for(int j = 0; j < 8; j++) {
            Piece p = tour.board[i][j];
            if(p != EMPTY) {
                PieceColor pc = getcolor(p);
                if(pc == couleur_adverse) {
                    highlight_possible_moves(m, couleur_adverse, i, j, tour.board);
                    if(get_mask(m, roi_ligne, roi_colone) == 1) {
                        return true;
                    }
                    clear_mask(m);
                }
            }
        }
    }
    return false;
}

bool king_in_checkmate(game &tour, int couleur) {
    if(king_in_check(tour, couleur) == false) return false;
    for(int i = 0; i < 8; i++) {
        for(int j = 0; j < 8; j++) {
            Piece p = tour.board[i][j];
            if(p != EMPTY && getcolor(p) == couleur) {
                mask m;
                clear_mask(m);
                highlight_possible_moves(m, couleur, i, j, tour.board);
                for(int k = 0; k < 8; k++) {
                    for(int l = 0; l < 8; l++) {
                        if(get_mask(m, k, l) == 1) {
                            Piece temp = tour.board[k][l];
                            tour.board[k][l] = tour.board[i][j];
                            tour.board[i][j] = EMPTY;
                            bool still_check = king_in_check(tour, couleur);
                            tour.board[i][j] = tour.board[k][l];
                            tour.board[k][l] = temp;
                            if(still_check == false) return false;
                        }
                    }
                }
            }
        }
    }
    return true;
}

int compute_score(game &tour, int couleur) {
    int score = 0;
    for(int i = 0; i < 8; i++) {
        for(int j = 0; j < 8; j++) {
            Piece p = tour.board[i][j];
            if(p != EMPTY && getcolor(p) == couleur) {
                if(p == WHITE_PAWN || p == BLACK_PAWN){
                    score = score + 1;
                }
                else if(p == WHITE_KNIGHT || p == BLACK_KNIGHT){
                    score = score + 3;
                }
                else if(p == WHITE_BISHOP || p == BLACK_BISHOP){
                    score = score + 3;
                }
                else if(p == WHITE_ROOK || p == BLACK_ROOK){
                    score = score + 5;
                }
                else if(p == WHITE_QUEEN || p == BLACK_QUEEN){
                    score = score + 9;
                }
            }
        }
    }
    return score;
}