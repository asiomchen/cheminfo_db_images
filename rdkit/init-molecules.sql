-- Ensure the RDKit extension is loaded
CREATE EXTENSION IF NOT EXISTS rdkit;

-- Create a table for molecules
CREATE TABLE IF NOT EXISTS molecules (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    mol MOL
);

-- Insert 5 example molecules
-- Note: the 'mol' type is provided by the RDKit extension
INSERT INTO
    molecules (name, mol)
VALUES (
        'Aspirin',
        'CC(=O)OC1=CC=CC=C1C(=O)O'::mol
    ),
    (
        'Caffeine',
        'CN1C=NC2=C1C(=O)N(C(=O)N2C)C'::mol
    ),
    ('Ethanol', 'CCO'::mol),
    ('Methane', 'C'::mol),
    ('Benzene', 'c1ccccc1'::mol);

-- Create a gist index on the mol column for substructure searches
CREATE INDEX IF NOT EXISTS mol_idx ON molecules USING gist (mol);