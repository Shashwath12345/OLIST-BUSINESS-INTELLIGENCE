import pandas as pd


def clean_data(data):

    orders = data["orders"]

    date_columns = [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date"
    ]

    for column in date_columns:
        orders[column] = pd.to_datetime(
            orders[column],
            errors="coerce"
        )

    data["order_items"]["shipping_limit_date"] = pd.to_datetime(
        data["order_items"]["shipping_limit_date"],
        errors="coerce"
    )

    data["reviews"]["review_creation_date"] = pd.to_datetime(
        data["reviews"]["review_creation_date"],
        errors="coerce"
    )

    data["reviews"]["review_answer_timestamp"] = pd.to_datetime(
        data["reviews"]["review_answer_timestamp"],
        errors="coerce"
    )

    return data