-- ============================================================
-- Initialisation de la base post-trade (données de test)
-- ============================================================

-- Table clients
CREATE TABLE clients (
    id_client SERIAL PRIMARY KEY,
    nom VARCHAR(100) NOT NULL,
    pays VARCHAR(50) NOT NULL,
    type_client VARCHAR(20) NOT NULL
);

-- Table comptes_clients
CREATE TABLE comptes_clients (
    id_compte SERIAL PRIMARY KEY,
    id_client INTEGER NOT NULL REFERENCES clients(id_client),
    type_compte VARCHAR(20) NOT NULL,
    devise VARCHAR(3) NOT NULL,
    solde NUMERIC(15, 2) DEFAULT 0
);

-- Table titres
CREATE TABLE titres (
    isin VARCHAR(12) PRIMARY KEY,
    nom VARCHAR(100) NOT NULL,
    type_titre VARCHAR(20) NOT NULL,
    emetteur VARCHAR(100)
);

-- Table instructions
CREATE TABLE instructions (
    id_instruction SERIAL PRIMARY KEY,
    id_compte INTEGER NOT NULL REFERENCES comptes_clients(id_compte),
    isin VARCHAR(12) NOT NULL REFERENCES titres(isin),
    sens VARCHAR(10) NOT NULL,
    quantite INTEGER NOT NULL,
    montant NUMERIC(15, 2) NOT NULL,
    devise VARCHAR(3) NOT NULL,
    date_negociation DATE NOT NULL,
    date_reglement DATE NOT NULL,
    statut VARCHAR(20) NOT NULL,
    motif_echec VARCHAR(100)
);

-- Table mouvements_cash
CREATE TABLE mouvements_cash (
    id_mouvement SERIAL PRIMARY KEY,
    id_compte INTEGER NOT NULL REFERENCES comptes_clients(id_compte),
    sens VARCHAR(10) NOT NULL,
    montant NUMERIC(15, 2) NOT NULL,
    devise VARCHAR(3) NOT NULL,
    date_valeur DATE NOT NULL,
    statut VARCHAR(20) NOT NULL
);

-- ============================================================
-- Données de test : 10 clients
-- ============================================================
INSERT INTO clients (nom, pays, type_client) VALUES
('Nile Bank', 'Tunisie', 'banque'),
('Atlas Fund', 'Maroc', 'fonds'),
('Mediterranée Assurance', 'Tunisie', 'assurance'),
('Sahara Capital', 'Tunisie', 'fonds'),
('EuroTrade SA', 'France', 'entreprise'),
('Maghreb Invest', 'Algérie', 'fonds'),
('Carthage Bank', 'Tunisie', 'banque'),
('Global Asset Mgmt', 'Luxembourg', 'fonds'),
('Tunisie Leasing', 'Tunisie', 'entreprise'),
('North Africa Bank', 'Égypte', 'banque');

-- ============================================================
-- Données de test : 20 comptes
-- ============================================================
INSERT INTO comptes_clients (id_client, type_compte, devise, solde) VALUES
(1, 'cash', 'TND', 1500000.00),
(1, 'titres', 'TND', 0),
(2, 'cash', 'EUR', 850000.00),
(2, 'titres', 'EUR', 0),
(3, 'cash', 'TND', 620000.00),
(3, 'titres', 'TND', 0),
(4, 'cash', 'USD', 920000.00),
(4, 'titres', 'USD', 0),
(5, 'cash', 'EUR', 1100000.00),
(5, 'titres', 'EUR', 0),
(6, 'cash', 'USD', 780000.00),
(6, 'titres', 'USD', 0),
(7, 'cash', 'TND', 2300000.00),
(7, 'titres', 'TND', 0),
(8, 'cash', 'EUR', 3400000.00),
(8, 'titres', 'EUR', 0),
(9, 'cash', 'TND', 450000.00),
(9, 'titres', 'TND', 0),
(10, 'cash', 'USD', 1800000.00),
(10, 'titres', 'USD', 0);

-- ============================================================
-- Données de test : 10 titres
-- ============================================================
INSERT INTO titres (isin, nom, type_titre, emetteur) VALUES
('TN0001100254', 'BIAT', 'action', 'BIAT'),
('TN0007720012', 'Poulina Group', 'action', 'Poulina'),
('TN0003400058', 'SFBT', 'action', 'SFBT'),
('TN0001100395', 'Attijari Bank', 'action', 'Attijari'),
('TN0002400123', 'Banque de Tunisie', 'action', 'BT'),
('FR0000120073', 'Air Liquide', 'action', 'Air Liquide'),
('FR0000131104', 'BNP Paribas', 'action', 'BNP'),
('US0378331005', 'Apple', 'action', 'Apple Inc'),
('US5949181045', 'Microsoft', 'action', 'Microsoft'),
('TN0000000001', 'Obligation État Tunisien 2025', 'obligation', 'État Tunisien');

-- ============================================================
-- Données de test : 15 instructions (achats/ventes)
-- ============================================================
INSERT INTO instructions (id_compte, isin, sens, quantite, montant, devise, date_negociation, date_reglement, statut, motif_echec) VALUES
(1, 'TN0001100254', 'achat', 500, 62500.00, 'TND', '2026-09-12', '2026-09-14', 'regle', NULL),
(3, 'TN0007720012', 'vente', 200, 21000.00, 'TND', '2026-09-17', '2026-09-19', 'regle', NULL),
(5, 'TN0003400058', 'achat', 1000, 18500.00, 'TND', '2026-09-22', '2026-09-24', 'echoue', 'Fonds insuffisants'),
(7, 'TN0001100395', 'achat', 300, 45000.00, 'TND', '2026-10-05', '2026-10-07', 'regle', NULL),
(9, 'TN0002400123', 'vente', 150, 12000.00, 'TND', '2026-10-10', '2026-10-12', 'en_attente', NULL),
(2, 'FR0000120073', 'achat', 100, 150000.00, 'EUR', '2026-10-15', '2026-10-17', 'apparie', NULL),
(4, 'FR0000131104', 'achat', 500, 250000.00, 'USD', '2026-10-18', '2026-10-20', 'en_attente', NULL),
(6, 'US0378331005', 'achat', 50, 95000.00, 'USD', '2026-10-20', '2026-10-22', 'en_attente', NULL),
(8, 'US5949181045', 'achat', 200, 180000.00, 'EUR', '2026-10-25', '2026-10-27', 'en_attente', NULL),
(10, 'TN0000000001', 'achat', 1000, 100000.00, 'USD', '2026-10-28', '2026-10-30', 'en_attente', NULL),
(1, 'TN0007720012', 'vente', 100, 10500.00, 'TND', '2026-10-30', '2026-11-01', 'en_attente', NULL),
(3, 'TN0001100254', 'achat', 250, 31250.00, 'TND', '2026-11-02', '2026-11-04', 'en_attente', NULL),
(5, 'TN0003400058', 'vente', 500, 9250.00, 'TND', '2026-09-15', '2026-09-17', 'echoue', 'Titre non disponible'),
(7, 'FR0000120073', 'achat', 200, 300000.00, 'TND', '2026-09-20', '2026-09-22', 'echoue', 'Fonds insuffisants'),
(9, 'TN0001100395', 'vente', 100, 15000.00, 'TND', '2026-10-08', '2026-10-10', 'regle', NULL);

-- ============================================================
-- Données de test : 10 mouvements cash
-- ============================================================
INSERT INTO mouvements_cash (id_compte, sens, montant, devise, date_valeur, statut) VALUES
(1, 'entrant', 500000.00, 'TND', '2026-10-15', 'execute'),
(1, 'sortant', 62500.00, 'TND', '2026-10-16', 'execute'),
(3, 'entrant', 21000.00, 'TND', '2026-10-17', 'execute'),
(5, 'sortant', 18500.00, 'TND', '2026-10-18', 'execute'),
(2, 'entrant', 150000.00, 'EUR', '2026-10-20', 'prevu'),
(4, 'entrant', 250000.00, 'USD', '2026-10-22', 'prevu'),
(6, 'entrant', 95000.00, 'USD', '2026-10-25', 'prevu'),
(8, 'entrant', 180000.00, 'EUR', '2026-10-28', 'prevu'),
(1, 'entrant', 1500000.00, 'TND', '2026-11-01', 'prevu'),
(10, 'sortant', 100000.00, 'USD', '2026-11-05', 'prevu');