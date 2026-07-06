#include <iostream>
#include <fstream>
#include <string>
using namespace std;
#include "board.hpp"

void empty(Board &a)
{
    for (int i = 0; i < 8; i++)
    {
        for (int j = 0; j < 8; j++)
        {
            a[i][j] = EMPTY;
        }
    }
}

Piece get_square(Board &A, int ligne, int colone)
{
    return A[ligne][colone];
}

void set_square(Board &B, int ligne, int colone, Piece piece)
{
    B[ligne][colone] = piece;
}

void start(Board &G)
{
    empty(G);

    for (int j = 0; j < 8; j++)
    {
        G[1][j] = BLACK_PAWN;
        G[6][j] = WHITE_PAWN;
    }

    G[0][0] = BLACK_ROOK;
    G[0][1] = BLACK_KNIGHT;
    G[0][2] = BLACK_BISHOP;
    G[0][3] = BLACK_QUEEN;
    G[0][4] = BLACK_KING;
    G[0][5] = BLACK_BISHOP;
    G[0][6] = BLACK_KNIGHT;
    G[0][7] = BLACK_ROOK;

    G[7][0] = WHITE_ROOK;
    G[7][1] = WHITE_KNIGHT;
    G[7][2] = WHITE_BISHOP;
    G[7][3] = WHITE_QUEEN;
    G[7][4] = WHITE_KING;
    G[7][5] = WHITE_BISHOP;
    G[7][6] = WHITE_KNIGHT;
    G[7][7] = WHITE_ROOK;
}

int move_piece(Board &N, int lignedepart, int colonedepart, int ligneariv, int coloneariv)
{
    if (get_square(N, lignedepart, colonedepart) == EMPTY)
    {
        return 0;
    }

    Piece piece = get_square(N, lignedepart, colonedepart);
    set_square(N, ligneariv, coloneariv, piece);
    set_square(N, lignedepart, colonedepart, EMPTY);

    return 1;
}

void write_FEN(Board &a, const string &filename)
{
    ofstream file(filename);
    if(!file.is_open())
    {
        cerr << "Erreur : impossible d'ouvrir le fichier " << filename << " en ecriture." << endl;
        return;
    }

    for (int i = 0; i < 8; i++)
    {
        int vide = 0;
        for (int j = 0; j < 8; j++)
        {
            Piece piece = a[i][j];
            if (piece == EMPTY)
            {
                vide++;
            }
            else
            {
                if (vide > 0)
                {
                    file << vide;
                    vide = 0;
                }
                if (piece == WHITE_KING)
                    file << 'K';
                else if (piece == WHITE_QUEEN)
                    file << 'Q';
                else if (piece == WHITE_ROOK)
                    file << 'R';
                else if (piece == WHITE_BISHOP)
                    file << 'B';
                else if (piece == WHITE_KNIGHT)
                    file << 'N';
                else if (piece == WHITE_PAWN)
                    file << 'P';
                else if (piece == BLACK_KING)
                    file << 'k';
                else if (piece == BLACK_QUEEN)
                    file << 'q';
                else if (piece == BLACK_ROOK)
                    file << 'r';
                else if (piece == BLACK_BISHOP)
                    file << 'b';
                else if (piece == BLACK_KNIGHT)
                    file << 'n';
                else if (piece == BLACK_PAWN)
                    file << 'p';
            }
        }
        if (vide > 0)
        {
            file << vide;
        }
        if (i < 7)
        {
            file << "/";
        }
    }
    file << endl;
    file.close();
}

void read_fen(const string &filename, Board &q)
{
    for (int x = 0; x < 8; x++)
    {
        for (int y = 0; y < 8; y++)
        {
            q[x][y] = EMPTY;
        }
    }
    ifstream file(filename);
    if(!file.is_open())
    {
        cerr << "Erreur : impossible d'ouvrir le fichier " << filename << " en lecture." << endl;
        return;
    }
    string fen;

    getline(file, fen);
    file.close();

    int i = 0;
    int j = 0;

    for (size_t k = 0; k < fen.length(); k++)
    {
        char c = fen[k];

        if (c == '/')
        {
            i++;
            j = 0;
        }
        else if (c >= '1' && c <= '8')
        {
            int nbvides = c - '0';
            j = j + nbvides;
        }
        else
        {
            if (c == 'r')
                q[i][j] = BLACK_ROOK;
            if (c == 'n')
                q[i][j] = BLACK_KNIGHT;
            if (c == 'b')
                q[i][j] = BLACK_BISHOP;
            if (c == 'q')
                q[i][j] = BLACK_QUEEN;
            if (c == 'k')
                q[i][j] = BLACK_KING;
            if (c == 'p')
                q[i][j] = BLACK_PAWN;

            if (c == 'R')
                q[i][j] = WHITE_ROOK;
            if (c == 'N')
                q[i][j] = WHITE_KNIGHT;
            if (c == 'B')
                q[i][j] = WHITE_BISHOP;
            if (c == 'Q')
                q[i][j] = WHITE_QUEEN;
            if (c == 'K')
                q[i][j] = WHITE_KING;
            if (c == 'P')
                q[i][j] = WHITE_PAWN;

            j++;
        }
    }
}