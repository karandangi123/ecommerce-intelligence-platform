-- Data Cleaning: Fix missing category translations
-- Goal: Insert English translations for the two missing Portuguese categories.

INSERT INTO raw_category_translation (product_category_name, product_category_name_english)
SELECT 'portateis_cozinha_e_preparadores_de_alimentos', 'portable_kitchen_and_food_processors'
WHERE NOT EXISTS (
    SELECT 1 FROM raw_category_translation WHERE product_category_name = 'portateis_cozinha_e_preparadores_de_alimentos'
);

INSERT INTO raw_category_translation (product_category_name, product_category_name_english)
SELECT 'pc_gamer', 'pc_gamer'
WHERE NOT EXISTS (
    SELECT 1 FROM raw_category_translation WHERE product_category_name = 'pc_gamer'
);
