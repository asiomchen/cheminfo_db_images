\set ON_ERROR_STOP on

CREATE EXTENSION IF NOT EXISTS rdkit;

DROP SCHEMA IF EXISTS rdkit_test CASCADE;
CREATE SCHEMA rdkit_test;
SET search_path = rdkit_test, public;

DO $$
DECLARE
    ethanol mol := mol_from_smiles('CCO');
    benzene mol := mol_from_smiles('c1ccccc1');
    reaction_value reaction := reaction_from_smiles('CCO>>CC=O');
BEGIN
    IF rdkit_version() IS NULL OR rdkit_version()::text = '' THEN
        RAISE EXCEPTION 'rdkit_version() returned no version';
    END IF;

    IF NOT is_valid_smiles('CCO') OR is_valid_smiles('C1CC') THEN
        RAISE EXCEPTION 'SMILES validation returned an unexpected result';
    END IF;

    IF mol_to_smiles(ethanol)::text <> 'CCO' OR mol_numatoms(ethanol) <> 9 THEN
        RAISE EXCEPTION 'SMILES parsing or serialization failed';
    END IF;

    IF mol_to_smiles(mol_from_ctab(mol_to_ctab(ethanol)))::text <> 'CCO' THEN
        RAISE EXCEPTION 'CTAB round trip failed';
    END IF;

    IF NOT (mol_from_smiles('Oc1ccccc1') @> qmol_from_smiles('c1ccccc1')) THEN
        RAISE EXCEPTION 'substructure query failed';
    END IF;

    IF mol_numheavyatoms(ethanol) <> 3
       OR mol_hba(ethanol) <> 1
       OR mol_hbd(ethanol) <> 1
       OR mol_amw(ethanol) NOT BETWEEN 46 AND 47
       OR mol_logp(ethanol) NOT BETWEEN -0.1 AND 0.1 THEN
        RAISE EXCEPTION 'molecular descriptor returned an unexpected result';
    END IF;

    IF position('<svg' IN mol_to_svg(ethanol)::text) = 0 THEN
        RAISE EXCEPTION 'SVG rendering failed';
    END IF;

    IF tanimoto_sml(rdkit_fp(benzene), rdkit_fp(benzene)) <> 1.0
       OR tanimoto_sml(morganbv_fp(benzene), morganbv_fp(benzene)) <> 1.0
       OR dice_sml(maccs_fp(benzene), maccs_fp(benzene)) <> 1.0 THEN
        RAISE EXCEPTION 'fingerprint similarity failed';
    END IF;

    IF reaction_numreactants(reaction_value) <> 1
       OR reaction_numproducts(reaction_value) <> 1
       OR reaction_numagents(reaction_value) <> 0
       OR tanimoto_sml(
            reaction_difference_fp(reaction_value, 1),
            reaction_difference_fp(reaction_value, 1)
          ) <> 1.0 THEN
        RAISE EXCEPTION 'reaction support failed';
    END IF;
END
$$;

CREATE TABLE compounds (
    id integer PRIMARY KEY,
    m mol NOT NULL,
    bfp bfp NOT NULL,
    sfp sfp NOT NULL
);

INSERT INTO compounds (id, m, bfp, sfp)
VALUES
    (1, mol_from_smiles('CCO'), rdkit_fp(mol_from_smiles('CCO')), morgan_fp(mol_from_smiles('CCO'))),
    (2, mol_from_smiles('c1ccccc1'), rdkit_fp(mol_from_smiles('c1ccccc1')), morgan_fp(mol_from_smiles('c1ccccc1'))),
    (3, mol_from_smiles('Oc1ccccc1'), rdkit_fp(mol_from_smiles('Oc1ccccc1')), morgan_fp(mol_from_smiles('Oc1ccccc1')));

CREATE INDEX compounds_mol_gist ON compounds USING gist (m);
CREATE INDEX compounds_bfp_gist ON compounds USING gist (bfp);
CREATE INDEX compounds_sfp_gist ON compounds USING gist (sfp);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM compounds
        WHERE m @> qmol_from_smiles('c1ccccc1')
    ) THEN
        RAISE EXCEPTION 'molecule GiST operator query failed';
    END IF;

    PERFORM set_config('rdkit.tanimoto_threshold', '0.7', true);
    IF NOT EXISTS (
        SELECT 1
        FROM compounds
        WHERE rdkit_fp(mol_from_smiles('Oc1ccccc1')) % bfp
    ) THEN
        RAISE EXCEPTION 'bit fingerprint GiST operator query failed';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM compounds
        WHERE morgan_fp(mol_from_smiles('Oc1ccccc1')) % sfp
    ) THEN
        RAISE EXCEPTION 'sparse fingerprint GiST operator query failed';
    END IF;
END
$$;

DROP SCHEMA rdkit_test CASCADE;
