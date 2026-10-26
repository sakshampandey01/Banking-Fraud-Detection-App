-- =====================================================================================
-- Reference data: transaction types.   Safe to run repeatedly.
--
-- type_enc   = the LabelEncoder code from the notebook (alphabetical order). It MUST match
--              models/preprocessing.json; tests/test_sql_seed.py and the API start-up check enforce it.
-- *_effect   = how the PaySim transaction types move balances. These follow PaySim's documented
--              semantics and the way transaction_service.py uses them. They are the one part of this
--              file that is NOT in your notebook, so `python scripts/export_preprocessing.py` prints the
--              movement it actually observes in Fraud.csv for you to confirm.
-- =====================================================================================
INSERT INTO transaction_types (type_code, type_enc, origin_effect, dest_effect, description) VALUES
    ('CASH_IN',  0, +1, -1, 'Customer pays cash in: origin balance up, counterparty balance down'),
    ('CASH_OUT', 1, -1, +1, 'Customer withdraws cash: origin balance down, counterparty balance up'),
    ('DEBIT',    2, -1, +1, 'Money sent from the service to a bank account'),
    ('PAYMENT',  3, -1, +1, 'Payment for goods/services (merchant balances are not tracked)'),
    ('TRANSFER', 4, -1, +1, 'Money sent to another customer')
ON CONFLICT (type_code) DO UPDATE
   SET type_enc      = EXCLUDED.type_enc,
       origin_effect = EXCLUDED.origin_effect,
       dest_effect   = EXCLUDED.dest_effect,
       description   = EXCLUDED.description;
