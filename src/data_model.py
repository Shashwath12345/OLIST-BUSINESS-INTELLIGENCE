def create_sales_data(data):

    sales = data["order_items"].merge(
        data["orders"],
        on="order_id",
        how="left"
    )

    sales = sales.merge(
        data["products"],
        on="product_id",
        how="left"
    )

    sales = sales.merge(
        data["sellers"],
        on="seller_id",
        how="left"
    )

    sales = sales.merge(
        data["category_translation"],
        on="product_category_name",
        how="left"
    )

    return sales