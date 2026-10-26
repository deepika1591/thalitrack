# Nutrition data — sources and licence

**Nutrient values** come from the U.S. Department of Agriculture, Agricultural
Research Service, **FoodData Central** (fdc.nal.usda.gov):

- SR Legacy, April 2018 (`FoodData_Central_sr_legacy_food_csv_2018-04.zip`):
  the base ingredients in `ingredients.json`, each listed by its `fdc_id`.
- FNDDS 2021–2023, released 31 Oct 2024
  (`FoodData_Central_survey_food_csv_2024-10-31.zip`): one ingredient,
  **paneer** ("Cheese, paneer", fdc_id 2705740), which SR Legacy lacks. Also
  used to sanity-check our dishes against USDA's own versions.

FoodData Central is in the **U.S. public domain** (CC0). USDA asks for this
citation as a courtesy:

> U.S. Department of Agriculture, Agricultural Research Service. FoodData
> Central. fdc.nal.usda.gov.

**Recipes** (`recipes.json`: which ingredients make up each dish, in what
amounts, and the standard servings) were written for this course. They describe
typical home cooking and are approximate.

**Known limitations, stated in the course:**
- USDA measures American foods. Some Indian ingredients have no USDA match and
  use a stand-in, marked in `ingredients.json` (jaggery uses brown sugar;
  semiya uses dry pasta).
- Home recipes vary a lot, especially in oil and ghee. Treat totals as
  estimates, not medical or dietary advice.

The raw USDA files (`usda_raw/`) are not shipped; download them from the
FoodData Central "Download Datasets" page to rebuild the table.
