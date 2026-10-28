-- ============================================================
-- Initialisation de la base post-trade (Données Massives Vermeg)
-- ============================================================

DROP TABLE IF EXISTS mouvements_cash;
DROP TABLE IF EXISTS instructions;
DROP TABLE IF EXISTS titres;
DROP TABLE IF EXISTS comptes_clients;
DROP TABLE IF EXISTS clients;

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
-- 50 CLIENTS (Institutions financières réalistes)
-- ============================================================
INSERT INTO clients (nom, pays, type_client) VALUES
('Nile Bank', 'Tunisie', 'banque'), ('Atlas Fund', 'Maroc', 'fonds'),
('Mediterranée Assurance', 'Tunisie', 'assurance'), ('Sahara Capital', 'Tunisie', 'fonds'),
('EuroTrade SA', 'France', 'entreprise'), ('Maghreb Invest', 'Algérie', 'fonds'),
('Carthage Bank', 'Tunisie', 'banque'), ('Global Asset Mgmt', 'Luxembourg', 'fonds'),
('Tunisie Leasing', 'Tunisie', 'entreprise'), ('North Africa Bank', 'Égypte', 'banque'),
('BNA', 'Tunisie', 'banque'), ('BIAT', 'Tunisie', 'banque'),
('Amen Bank', 'Tunisie', 'banque'), ('UIB', 'Tunisie', 'banque'),
('Attijari Bank', 'Tunisie', 'banque'), ('STB', 'Tunisie', 'banque'),
('BH Bank', 'Tunisie', 'banque'), ('BT', 'Tunisie', 'banque'),
('Zitouna Bank', 'Tunisie', 'banque'), ('Qatar National Bank', 'Qatar', 'banque'),
('Société Générale', 'France', 'banque'), ('BNP Paribas', 'France', 'banque'),
('Deutsche Bank', 'Allemagne', 'banque'), ('HSBC', 'UK', 'banque'),
('Allianz', 'Allemagne', 'assurance'), ('AXA', 'France', 'assurance'),
('BlackRock', 'USA', 'fonds'), ('Vanguard', 'USA', 'fonds'),
('Fidelity', 'USA', 'fonds'), ('Amundi', 'France', 'fonds'),
('Natixis', 'France', 'banque'), ('Credit Agricole', 'France', 'banque'),
('BPCE', 'France', 'banque'), ('CIC', 'France', 'banque'),
('Swiss Re', 'Suisse', 'assurance'), ('Zurich Insurance', 'Suisse', 'assurance'),
('Generali', 'Italie', 'assurance'), ('UniCredit', 'Italie', 'banque'),
('Santander', 'Espagne', 'banque'), ('BBVA', 'Espagne', 'banque'),
('ING', 'Pays-Bas', 'banque'), ('Rabobank', 'Pays-Bas', 'banque'),
('UBS', 'Suisse', 'banque'), ('Credit Suisse', 'Suisse', 'banque'),
('Nomura', 'Japon', 'banque'), ('Mizuho', 'Japon', 'banque'),
('Mitsubishi UFJ', 'Japon', 'banque'), ('Bank of China', 'Chine', 'banque'),
('ICBC', 'Chine', 'banque'), ('Standard Chartered', 'UK', 'banque');

-- ============================================================
-- 100 COMPTES (2 par client : Cash et Titres)
-- ============================================================
INSERT INTO comptes_clients (id_client, type_compte, devise, solde)
SELECT id_client, 'cash', 
       CASE WHEN id_client % 4 = 0 THEN 'TND' WHEN id_client % 4 = 1 THEN 'EUR' WHEN id_client % 4 = 2 THEN 'USD' ELSE 'GBP' END,
       (random() * 10000000)::numeric(15,2) + 500000
FROM clients;

INSERT INTO comptes_clients (id_client, type_compte, devise, solde)
SELECT id_client, 'titres', 'TND', 0 FROM clients;

-- ============================================================
-- 20 TITRES
-- ============================================================
INSERT INTO titres (isin, nom, type_titre, emetteur) VALUES
('TN0001100254', 'BIAT', 'action', 'BIAT'), ('TN0007720012', 'Poulina Group', 'action', 'Poulina'),
('TN0003400058', 'SFBT', 'action', 'SFBT'), ('TN0001100395', 'Attijari Bank', 'action', 'Attijari'),
('TN0002400123', 'Banque de Tunisie', 'action', 'BT'), ('TN0000000001', 'Obligation État 2025', 'obligation', 'État Tunisien'),
('TN0000000002', 'Obligation État 2030', 'obligation', 'État Tunisien'), ('FR0000120073', 'Air Liquide', 'action', 'Air Liquide'),
('FR0000131104', 'BNP Paribas', 'action', 'BNP'), ('US0378331005', 'Apple', 'action', 'Apple Inc'),
('US5949181045', 'Microsoft', 'action', 'Microsoft'), ('DE0005557508', 'Deutsche Telekom', 'action', 'Deutsche Telekom'),
('GB0002374006', 'Diageo', 'action', 'Diageo'), ('JP3633400001', 'Toyota', 'action', 'Toyota'),
('CH0038863350', 'Nestle', 'action', 'Nestle'), ('FR0000121014', 'LVMH', 'action', 'LVMH'),
('FR0000133308', 'Orange', 'action', 'Orange'), ('FR0010204081', 'Airbus', 'action', 'Airbus'),
('FR0000120271', 'TotalEnergies', 'action', 'Total'), ('FR0000125486', 'Vinci', 'action', 'Vinci');

-- ============================================================
-- 1500 INSTRUCTIONS (Sur 3 ans)
-- ============================================================
DO $$
DECLARE
    i INTEGER := 0;
    v_id_compte INTEGER;
    v_isin VARCHAR(12);
    v_sens VARCHAR(10);
    v_date_nego DATE;
    v_statut VARCHAR(20);
    v_motif VARCHAR(100);
    v_quantite INTEGER;
    v_montant NUMERIC;
BEGIN
    FOR i IN 1..1500 LOOP
        SELECT id_compte INTO v_id_compte FROM comptes_clients WHERE type_compte = 'cash' ORDER BY random() LIMIT 1;
        SELECT isin INTO v_isin FROM titres ORDER BY random() LIMIT 1;
        v_sens := CASE WHEN random() > 0.5 THEN 'achat' ELSE 'vente' END;
        -- Dates sur les 3 dernières années (1080 jours)
        v_date_nego := CURRENT_DATE - (random() * 1080)::int;
        v_quantite := (random() * 5000)::int + 10;
        v_montant := v_quantite * (random() * 50 + 10);
        
        -- Statut : 75% réglé, 15% échoué, 10% en attente
        IF random() > 0.25 THEN
            v_statut := 'regle';
            v_motif := NULL;
        ELSIF random() > 0.4 THEN
            v_statut := 'echoue';
            v_motif := CASE WHEN random() > 0.5 THEN 'Fonds insuffisants' ELSE 'Titre non disponible' END;
        ELSE
            v_statut := 'en_attente';
            v_motif := NULL;
        END IF;

        INSERT INTO instructions (id_compte, isin, sens, quantite, montant, devise, date_negociation, date_reglement, statut, motif_echec)
        VALUES (
            v_id_compte, v_isin, v_sens, v_quantite, v_montant, 
            (SELECT devise FROM comptes_clients WHERE id_compte = v_id_compte),
            v_date_nego, v_date_nego + 2, v_statut, v_motif
        );
    END LOOP;
END $$;

-- ============================================================
-- 2000 MOUVEMENTS CASH
-- ============================================================
DO $$
DECLARE
    i INTEGER := 0;
    v_id_compte INTEGER;
    v_sens VARCHAR(10);
    v_date DATE;
    v_statut VARCHAR(20);
BEGIN
    FOR i IN 1..2000 LOOP
        SELECT id_compte INTO v_id_compte FROM comptes_clients WHERE type_compte = 'cash' ORDER BY random() LIMIT 1;
        v_sens := CASE WHEN random() > 0.5 THEN 'entrant' ELSE 'sortant' END;
        v_date := CURRENT_DATE - (random() * 1080)::int;
        v_statut := CASE WHEN random() > 0.2 THEN 'execute' ELSE 'prevu' END;

        INSERT INTO mouvements_cash (id_compte, sens, montant, devise, date_valeur, statut)
        VALUES (
            v_id_compte, v_sens, 
            (random() * 2000000)::numeric(15,2) + 1000, 
            (SELECT devise FROM comptes_clients WHERE id_compte = v_id_compte),
            v_date, v_statut
        );
    END LOOP;
END $$;