"""
Traduction française des genres AniList (liste fixe, 18 valeurs officielles).
Les genres anglais bruts restent la source de vérité pour la similarité/recommandations ;
genres_fr ne sert qu'à l'affichage.
"""

GENRES_FR: dict[str, str] = {
    "Action":         "Action",
    "Adventure":      "Aventure",
    "Comedy":         "Comédie",
    "Drama":          "Drame",
    "Ecchi":          "Ecchi",
    "Fantasy":        "Fantastique",
    "Hentai":         "Hentai",
    "Horror":         "Horreur",
    "Mahou Shoujo":   "Magical Girl",
    "Mecha":          "Mecha",
    "Music":          "Musique",
    "Mystery":        "Mystère",
    "Psychological":  "Psychologique",
    "Romance":        "Romance",
    "Sci-Fi":         "Science-Fiction",
    "Slice of Life":  "Tranche de vie",
    "Sports":         "Sport",
    "Supernatural":   "Surnaturel",
    "Thriller":       "Thriller",
}


def to_fr(genres_en: list[str]) -> list[str]:
    """Traduit une liste de genres AniList ; conserve l'original si absent du mapping."""
    return [GENRES_FR.get(g, g) for g in genres_en]
