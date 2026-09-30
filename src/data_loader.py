import pandas as pd


def load_data():

    data = {}

    data["customers"] = pd.read_csv(
        "data/olist_customers_dataset.csv"
    )

    data["geolocation"] = pd.read_csv(
        "data/olist_geolocation_dataset.csv"
    )

    data["order_items"] = pd.read_csv(
        "data/olist_order_items_dataset.csv"
    )

    data["payments"] = pd.read_csv(
        "data/olist_order_payments_dataset.csv"
    )

    data["reviews"] = pd.read_csv(
        "data/olist_order_reviews_dataset.csv"
    )

    data["orders"] = pd.read_csv(
        "data/olist_orders_dataset.csv"
    )

    data["products"] = pd.read_csv(
        "data/olist_products_dataset.csv"
    )

    data["sellers"] = pd.read_csv(
        "data/olist_sellers_dataset.csv"
    )

    data["category_translation"] = pd.read_csv(
        "data/product_category_name_translation.csv"
    )

    return data