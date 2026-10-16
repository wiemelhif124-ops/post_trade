"""Rapports par entité (clients, comptes, instructions, titres).
S'enregistre automatiquement dans rapports.RAPPORTS à l'import."""
import rapports
from rapports import _lire, _section


def _n(engine, sql):
    return int(_lire(engine, sql).iloc[0, 0])


# ---------------------------------------------------------------- CLIENTS
def _rapport_clients(engine, d1, d2):
    nb_clients = _n(engine, "SELECT COUNT(*) AS n FROM clients")
    nb_pays = _n(engine, "SELECT COUNT(DISTINCT pays) AS n FROM clients")
    sans_compte = _n(engine, "SELECT COUNT(*) AS n FROM clients c WHERE NOT EXISTS "
                             "(SELECT 1 FROM comptes_clients cc WHERE cc.id_client = c.id_client)")
    indicateurs = [("Clients", nb_clients), ("Pays", nb_pays), ("Clients sans compte", sans_compte)]
    sections = [
        _section("Clients par pays", _lire(
            engine, "SELECT pays, COUNT(*) AS nb_clients FROM clients GROUP BY pays ORDER BY nb_clients DESC"),
            "histogramme"),
        _section("Clients par type", _lire(
            engine, "SELECT type_client, COUNT(*) AS nb_clients FROM clients GROUP BY type_client "
                    "ORDER BY nb_clients DESC"), "histogramme"),
        _section("Liste des clients et nombre de comptes", _lire(
            engine, "SELECT c.id_client, c.nom, c.pays, c.type_client, COUNT(cc.id_compte) AS nb_comptes "
                    "FROM clients c LEFT JOIN comptes_clients cc ON cc.id_client = c.id_client "
                    "GROUP BY c.id_client, c.nom, c.pays, c.type_client ORDER BY c.id_client")),
    ]
    return indicateurs, sections


# ---------------------------------------------------------------- COMPTES
def _rapport_comptes_detail(engine, d1, d2):
    nb = _n(engine, "SELECT COUNT(*) AS n FROM comptes_clients")
    nb_titres = _n(engine, "SELECT COUNT(*) AS n FROM comptes_clients WHERE type_compte = 'titres'")
    nb_cash = _n(engine, "SELECT COUNT(*) AS n FROM comptes_clients WHERE type_compte = 'cash'")
    nb_dev = _n(engine, "SELECT COUNT(DISTINCT devise) AS n FROM comptes_clients")
    indicateurs = [("Comptes", nb), ("Comptes titres", nb_titres), ("Comptes cash", nb_cash),
                   ("Devises", nb_dev)]
    sections = [
        _section("Comptes par type", _lire(
            engine, "SELECT type_compte, COUNT(*) AS nb_comptes FROM comptes_clients GROUP BY type_compte "
                    "ORDER BY nb_comptes DESC"), "histogramme"),
        _section("Solde total par devise", _lire(
            engine, "SELECT devise, SUM(solde) AS solde_total FROM comptes_clients GROUP BY devise "
                    "ORDER BY devise"), "histogramme"),
        _section("Soldes par devise et type de compte", _lire(
            engine, "SELECT devise, type_compte, COUNT(*) AS nb_comptes, SUM(solde) AS solde_total "
                    "FROM comptes_clients GROUP BY devise, type_compte ORDER BY devise, type_compte")),
        _section("Détail des comptes", _lire(
            engine, "SELECT cc.id_compte, c.nom AS client, cc.type_compte, cc.devise, cc.solde "
                    "FROM comptes_clients cc JOIN clients c ON c.id_client = cc.id_client "
                    "ORDER BY cc.id_compte")),
    ]
    return indicateurs, sections


# ---------------------------------------------------------------- INSTRUCTIONS
def _rapport_instructions(engine, d1, d2):
    statuts = _lire(engine, "SELECT statut, COUNT(*) AS nb FROM instructions GROUP BY statut ORDER BY nb DESC")
    nb = {r.statut: int(r.nb) for r in statuts.itertuples()}
    reglees, echouees = nb.get("regle", 0), nb.get("echoue", 0)
    taux = round(100 * reglees / (reglees + echouees), 1) if (reglees + echouees) else "n/a"
    indicateurs = [("Instructions", sum(nb.values())), ("Réglées", reglees), ("Échouées", echouees),
                   ("En attente", nb.get("en_attente", 0)), ("Appariées", nb.get("apparie", 0)),
                   ("Taux de règlement (%)", taux)]
    sections = [
        _section("Instructions par statut", statuts, "histogramme"),
        _section("Instructions par sens (achat / vente)", _lire(
            engine, "SELECT sens, COUNT(*) AS nb FROM instructions GROUP BY sens ORDER BY nb DESC"),
            "histogramme"),
        _section("Instructions par titre", _lire(
            engine, "SELECT t.nom AS titre, COUNT(*) AS nb FROM instructions i JOIN titres t ON t.isin = i.isin "
                    "GROUP BY t.nom ORDER BY nb DESC"), "histogramme"),
        _section("Instructions par date de règlement", _lire(
            engine, "SELECT date_reglement, COUNT(*) AS nb FROM instructions GROUP BY date_reglement "
                    "ORDER BY date_reglement"), "courbe"),
        _section("Volumes par devise", _lire(
            engine, "SELECT devise, COUNT(*) AS nb_instructions, SUM(montant) AS montant_total "
                    "FROM instructions GROUP BY devise ORDER BY devise")),
        _section("Détail des instructions", _lire(
            engine, "SELECT i.id_instruction, c.nom AS client, t.nom AS titre, i.sens, i.quantite, i.montant, "
                    "i.devise, i.date_reglement, i.statut FROM instructions i "
                    "JOIN comptes_clients cc ON cc.id_compte = i.id_compte "
                    "JOIN clients c ON c.id_client = cc.id_client JOIN titres t ON t.isin = i.isin "
                    "ORDER BY i.date_reglement DESC, i.id_instruction")),
    ]
    return indicateurs, sections


# ---------------------------------------------------------------- TITRES
def _rapport_titres(engine, d1, d2):
    nb = _n(engine, "SELECT COUNT(*) AS n FROM titres")
    nb_act = _n(engine, "SELECT COUNT(*) AS n FROM titres WHERE type_titre = 'action'")
    nb_obl = _n(engine, "SELECT COUNT(*) AS n FROM titres WHERE type_titre = 'obligation'")
    nb_emet = _n(engine, "SELECT COUNT(DISTINCT emetteur) AS n FROM titres")
    indicateurs = [("Titres", nb), ("Actions", nb_act), ("Obligations", nb_obl), ("Émetteurs", nb_emet)]
    sections = [
        _section("Titres par type", _lire(
            engine, "SELECT type_titre, COUNT(*) AS nb_titres FROM titres GROUP BY type_titre "
                    "ORDER BY nb_titres DESC"), "histogramme"),
        _section("Titres par émetteur", _lire(
            engine, "SELECT emetteur, COUNT(*) AS nb_titres FROM titres GROUP BY emetteur "
                    "ORDER BY nb_titres DESC"), "histogramme"),
        _section("Activité par titre (nombre d'instructions)", _lire(
            engine, "SELECT t.nom AS titre, COUNT(i.id_instruction) AS nb_instructions, "
                    "COALESCE(SUM(i.montant), 0) AS montant_total FROM titres t "
                    "LEFT JOIN instructions i ON i.isin = t.isin GROUP BY t.isin, t.nom "
                    "ORDER BY nb_instructions DESC"), "histogramme"),
        _section("Liste des titres", _lire(
            engine, "SELECT isin, nom, type_titre, emetteur FROM titres ORDER BY nom")),
    ]
    return indicateurs, sections


rapports.RAPPORTS.update({
    "Clients": {"fn": _rapport_clients, "debut": None, "fin": None, "titre": "Rapport clients"},
    "Comptes": {"fn": _rapport_comptes_detail, "debut": None, "fin": None, "titre": "Rapport comptes"},
    "Instructions": {"fn": _rapport_instructions, "debut": None, "fin": None,
                     "titre": "Rapport instructions"},
    "Titres": {"fn": _rapport_titres, "debut": None, "fin": None, "titre": "Rapport titres"},
})
