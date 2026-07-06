#include <iostream>
#include <string>
#include <cstdlib>
#include <ctime>
using namespace std;
 
#include "types.hpp"
#include "board.hpp"
#include "view.hpp"
#include "mask.hpp"
 
// ============================================================
// Utilitaires couleur
// ============================================================
 
// Retourne BLANC ou NOIR selon la piece p (p ne doit pas etre EMPTY)
int piece_color(Piece p)
{
    if (p >= WHITE_KING && p <= WHITE_PAWN) return BLANC;
    return NOIR;
}
 
// Retourne true si la piece p appartient au joueur couleur
bool is_mine(Piece p, int couleur)
{
    if (p == EMPTY) return false;
    return piece_color(p) == couleur;
}
 
// ============================================================
// Localisation du roi
// ============================================================
 
// Trouve la position du roi du joueur couleur sur le plateau b
// Retourne false si introuvable
bool find_king(Board &b, int couleur, int &kl, int &kc)
{
    Piece king = (couleur == BLANC) ? WHITE_KING : BLACK_KING;
    for (int i = 0; i < 8; i++)
        for (int j = 0; j < 8; j++)
            if (b[i][j] == king) { kl = i; kc = j; return true; }
    return false;
}
 
// ============================================================
// Detection d'echec
// ============================================================
 
// Retourne true si le roi du joueur couleur est en echec sur le plateau b
bool king_in_check(Board &b, int couleur)
{
    int kl, kc;
    if (!find_king(b, couleur, kl, kc)) return false;
 
    int adverse = (couleur == BLANC) ? NOIR : BLANC;
 
    for (int i = 0; i < 8; i++)
        for (int j = 0; j < 8; j++)
        {
            Piece p = b[i][j];
            if (p == EMPTY || piece_color(p) != adverse) continue;
            mask temp = empty_mask();
            highlight_possible_moves(temp, adverse, i, j, b);
            if (get_mask(temp, kl, kc) == 1) return true;
        }
    return false;
}
 
// ============================================================
// Validation d'un mouvement
// ============================================================
 
// Retourne true si deplacer la piece de (ld,cd) vers (la,ca) est legal :
//   - piece du joueur en (ld,cd)
//   - destination dans le masque des mouvements possibles
//   - apres le mouvement, le propre roi n'est pas en echec
bool is_legal_move(Board &b, int couleur, int ld, int cd, int la, int ca)
{
    Piece p = b[ld][cd];
    if (p == EMPTY || !is_mine(p, couleur)) return false;
 
    mask m = empty_mask();
    highlight_possible_moves(m, couleur, ld, cd, b);
    if (get_mask(m, la, ca) != 1) return false;
 
    // Simuler le mouvement sur une copie
    Board copy;
    for (int i = 0; i < 8; i++)
        for (int j = 0; j < 8; j++)
            copy[i][j] = b[i][j];
    copy[la][ca] = copy[ld][cd];
    copy[ld][cd] = EMPTY;
 
    // Rejeter si le propre roi se retrouve en echec
    return !king_in_check(copy, couleur);
}
 
// ============================================================
// Detection echec et mat / pat
// ============================================================
 
// Retourne true si le joueur couleur n'a aucun mouvement legal
bool has_no_legal_move(Board &b, int couleur)
{
    for (int ld = 0; ld < 8; ld++)
        for (int cd = 0; cd < 8; cd++)
        {
            if (!is_mine(b[ld][cd], couleur)) continue;
            mask m = empty_mask();
            highlight_possible_moves(m, couleur, ld, cd, b);
            for (int la = 0; la < 8; la++)
                for (int ca = 0; ca < 8; ca++)
                    if (get_mask(m, la, ca) == 1 &&
                        is_legal_move(b, couleur, ld, cd, la, ca))
                        return false;
        }
    return true;
}
 
// ============================================================
// Promotion du pion
// ============================================================
 
// Demande au joueur humain quelle piece choisir pour la promotion
Piece ask_promotion(int couleur)
{
    cout << "Promotion ! Choisissez : Q(reine) R(tour) B(fou) N(cavalier) : ";
    char c;
    cin >> c;
    if (couleur == BLANC)
    {
        if (c == 'R' || c == 'r') return WHITE_ROOK;
        if (c == 'B' || c == 'b') return WHITE_BISHOP;
        if (c == 'N' || c == 'n') return WHITE_KNIGHT;
        return WHITE_QUEEN;
    }
    else
    {
        if (c == 'R' || c == 'r') return BLACK_ROOK;
        if (c == 'B' || c == 'b') return BLACK_BISHOP;
        if (c == 'N' || c == 'n') return BLACK_KNIGHT;
        return BLACK_QUEEN;
    }
}
 
// Promotion automatique en reine (utilisee pour le PC)
Piece auto_promotion(int couleur)
{
    return (couleur == BLANC) ? WHITE_QUEEN : BLACK_QUEEN;
}
 
// ============================================================
// Conversion coordonnees
// ============================================================
 
// Colonne lettre ('a'-'h') -> indice 0-7, -1 si invalide
int col_to_index(char c)
{
    if (c >= 'a' && c <= 'h') return c - 'a';
    return -1;
}
 
// Chiffre ligne ('1'-'8') -> indice interne (ligne 8 = index 0)
int row_to_index(char c)
{
    if (c >= '1' && c <= '8') return 8 - (c - '0');
    return -1;
}
 
// Parse un coup au format "e2e4" (4 caracteres sans espace)
bool parse_move(const string &input, int &ld, int &cd, int &la, int &ca)
{
    string clean = "";
    for (char c : input)
        if (c != ' ') clean += c;
    if (clean.size() != 4) return false;
 
    cd = col_to_index(clean[0]);
    ld = row_to_index(clean[1]);
    ca = col_to_index(clean[2]);
    la = row_to_index(clean[3]);
 
    return (ld != -1 && cd != -1 && la != -1 && ca != -1);
}
 
// ============================================================
// Coup du joueur humain
// ============================================================
 
// Demande et applique un coup valide au joueur humain
// Retourne false si le joueur abandonne
bool human_turn(Board &b, int couleur)
{
    cout << "---------------------------------------" << endl;
    cout << "  Joueur : " << (couleur == BLANC ? "BLANCS" : "NOIRS") << endl;
    cout << "  Format  : colonne+ligne -> colonne+ligne  (ex: e2e4)" << endl;
    cout << "  Tapez q pour abandonner la partie." << endl;
    cout << "---------------------------------------" << endl;
    // Menu masques (optionnel)
    cout << "Afficher un masque ? (o/n) : ";
    char rep;
    cin >> rep;
    if (rep == 'o' || rep == 'O')
    {
        mask m = empty_mask();
        mask_choices(m, couleur, b);
        print_board_color(b, m);
    }
 
    while (true)
    {
        cout << "[ " << (couleur == BLANC ? "BLANCS" : "NOIRS") << " ] Votre coup : ";
        string input;
        cin >> input;
 
        if (input == "q" || input == "Q")
            return false;
 
        int ld, cd, la, ca;
        if (!parse_move(input, ld, cd, la, ca))
        {
            cout << "Format invalide. Utilisez : e2e4" << endl;
            continue;
        }
 
        if (!is_legal_move(b, couleur, ld, cd, la, ca))
        {
            if (b[ld][cd] == EMPTY)
                cout << "Coup illegal : la case de depart est vide." << endl;
            else if (!is_mine(b[ld][cd], couleur))
                cout << "Coup illegal : ce n'est pas votre piece." << endl;
            else
                cout << "Coup illegal : mouvement interdit ou laisse votre roi en echec." << endl;
            continue;
        }
 
        move_piece(b, ld, cd, la, ca);
 
        // Promotion du pion
        if (b[la][ca] == WHITE_PAWN && la == 0)
            b[la][ca] = ask_promotion(BLANC);
        if (b[la][ca] == BLACK_PAWN && la == 7)
            b[la][ca] = ask_promotion(NOIR);
 
        return true;
    }
}
 
// ============================================================
// Coup du joueur PC
// ============================================================
 
// Choisit et joue un coup legal aleatoire parmi tous les coups disponibles
// Retourne false si aucun coup disponible
bool computer_turn(Board &b, int couleur)
{
    // Liste de tous les coups legaux : [ld, cd, la, ca]
    int moves[220][4];
    int nb = 0;
 
    for (int ld = 0; ld < 8 && nb < 220; ld++)
        for (int cd = 0; cd < 8 && nb < 220; cd++)
        {
            if (!is_mine(b[ld][cd], couleur)) continue;
            mask m = empty_mask();
            highlight_possible_moves(m, couleur, ld, cd, b);
            for (int la = 0; la < 8 && nb < 220; la++)
                for (int ca = 0; ca < 8 && nb < 220; ca++)
                    if (get_mask(m, la, ca) == 1 &&
                        is_legal_move(b, couleur, ld, cd, la, ca))
                    {
                        moves[nb][0] = ld;
                        moves[nb][1] = cd;
                        moves[nb][2] = la;
                        moves[nb][3] = ca;
                        nb++;
                    }
        }
 
    if (nb == 0) return false;
 
    int choix = rand() % nb;
    int ld = moves[choix][0];
    int cd = moves[choix][1];
    int la = moves[choix][2];
    int ca = moves[choix][3];
 
    cout << "PC joue : "
         << (char)('a' + cd) << (8 - ld)
         << (char)('a' + ca) << (8 - la) << endl;
 
    move_piece(b, ld, cd, la, ca);
 
    // Promotion automatique en reine
    if (b[la][ca] == WHITE_PAWN && la == 0)
        b[la][ca] = auto_promotion(BLANC);
    if (b[la][ca] == BLACK_PAWN && la == 7)
        b[la][ca] = auto_promotion(NOIR);
 
    return true;
}
 
// ============================================================
// Types de joueurs
// ============================================================
 
enum TypeJoueur { HUMAIN, ORDINATEUR };
 
// ============================================================
// Boucle de jeu principale
// ============================================================
 
// joueur_blanc et joueur_noir : HUMAIN ou ORDINATEUR
void play(TypeJoueur joueur_blanc, TypeJoueur joueur_noir)
{
    Board b;
    start(b);
 
    int couleur = BLANC;
    const int MAX_COUPS = 100;
    int nb_coups = 0;
 
    while (true)
    {
        mask vide = empty_mask();
        print_board_color(b, vide);
        cout << "\n=== Tour des " << (couleur == BLANC ? "BLANCS" : "NOIRS") << " ===" << endl;
 
        // Annonce echec
        if (king_in_check(b, couleur))
            cout << "*** ECHEC AU ROI ! ***" << endl;
 
        // Echec et mat / pat
        if (has_no_legal_move(b, couleur))
        {
            if (king_in_check(b, couleur))
                cout << "*** ECHEC ET MAT ! Les "
                     << (couleur == BLANC ? "NOIRS" : "BLANCS")
                     << " gagnent ! ***" << endl;
            else
                cout << "*** PAT ! Match nul. ***" << endl;
            break;
        }
 
        // Limite de coups
        if (nb_coups >= MAX_COUPS)
        {
            cout << "*** Limite de " << MAX_COUPS
                 << " coups atteinte. Match nul. ***" << endl;
            break;
        }
 
        // Choisir le bon joueur
        TypeJoueur type = (couleur == BLANC) ? joueur_blanc : joueur_noir;
 
        bool a_joue;
        if (type == HUMAIN)
            a_joue = human_turn(b, couleur);
        else
            a_joue = computer_turn(b, couleur);
 
        if (!a_joue)
        {
            cout << "Les " << (couleur == BLANC ? "BLANCS" : "NOIRS")
                 << " abandonnent. Les "
                 << (couleur == BLANC ? "NOIRS" : "BLANCS")
                 << " gagnent !" << endl;
            break;
        }
 
        nb_coups++;
        couleur = (couleur == BLANC) ? NOIR : BLANC;
    }
}
 
// ============================================================
// Main
// ============================================================
 
int main()
{
    srand((unsigned int)time(NULL));
 
    int choix = 0;
    while (choix < 1 || choix > 3)
    {
        cout << "\n=== JEU D'ECHECS ===" << endl;
        cout << "1 - Humain vs Humain" << endl;
        cout << "2 - Humain (Blancs) vs PC (Noirs)" << endl;
        cout << "3 - PC vs PC" << endl;
        cout << "Votre choix : ";
        cin >> choix;
        if (choix < 1 || choix > 3)
            cout << "Choix invalide, entrez 1, 2 ou 3." << endl;
    }
 
    if (choix == 1)
    {
        cout << "\n--- Humain (Blancs) vs Humain (Noirs) ---" << endl;
        play(HUMAIN, HUMAIN);
    }
    else if (choix == 2)
    {
        cout << "\n--- Humain (Blancs) vs PC (Noirs) ---" << endl;
        play(HUMAIN, ORDINATEUR);
    }
    else
    {
        cout << "\n--- PC (Blancs) vs PC (Noirs) ---" << endl;
        play(ORDINATEUR, ORDINATEUR);
    }
 
    return 0;
}