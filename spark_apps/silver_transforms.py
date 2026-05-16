def enrich_orders(upserts, user_df, item_df):
    return (
        upserts.join(
            user_df.withColumnRenamed("created_at", "user_registered_at"),
            upserts.customer_email == user_df.email,
            "left",
        )
        .drop(user_df.id)
        .withColumnRenamed("email", "user_email")
        .join(item_df, upserts.id == item_df.order_id, "left")
        .drop("order_id")
        .drop("cdc_op")
    )
