import streamlit as st
import pandas as pd

from src.data_loader import load_data
from src.data_cleaning import clean_data
from src.data_model import create_sales_data
from src.gemini_ai import ask_gemini


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Olist Business Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# CUSTOM STYLING
# =========================================================

st.markdown(
    """
    <style>
        /* Main page */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1500px;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            border-right: 1px solid rgba(255,255,255,0.08);
        }

        section[data-testid="stSidebar"] h1 {
            font-size: 1.45rem;
        }

        /* KPI cards */
        div[data-testid="stMetric"] {
            background: linear-gradient(
                145deg,
                rgba(255,255,255,0.055),
                rgba(255,255,255,0.025)
            );
            border: 1px solid rgba(255,255,255,0.09);
            border-radius: 14px;
            padding: 18px 18px 14px 18px;
            min-height: 120px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.12);
        }

        div[data-testid="stMetric"] label {
            font-size: 0.82rem;
            font-weight: 600;
            opacity: 0.72;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }

        div[data-testid="stMetricValue"] {
            font-size: 1.75rem;
            font-weight: 700;
        }

        /* Titles */
        h1 {
            letter-spacing: -0.03em;
        }

        h2, h3 {
            letter-spacing: -0.02em;
        }

        /* Section divider */
        .section-label {
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            opacity: 0.55;
            margin-top: 1.5rem;
            margin-bottom: 0.25rem;
        }

        .page-subtitle {
            font-size: 1.05rem;
            opacity: 0.70;
            margin-top: -0.65rem;
            margin-bottom: 1.5rem;
        }

        .insight-box {
            padding: 16px 18px;
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.10);
            background: rgba(255,255,255,0.035);
            line-height: 1.55;
        }

        /* Buttons */
        .stButton > button {
            border-radius: 10px;
            font-weight: 600;
        }

        /* Dataframes */
        div[data-testid="stDataFrame"] {
            border-radius: 10px;
            overflow: hidden;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def compact_currency(value):
    """Format large BRL values compactly."""
    value = float(value)
    if abs(value) >= 1_000_000_000:
        return f"R$ {value / 1_000_000_000:.2f}B"
    if abs(value) >= 1_000_000:
        return f"R$ {value / 1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"R$ {value / 1_000:.1f}K"
    return f"R$ {value:,.0f}"


def compact_number(value):
    """Format large numbers compactly."""
    value = float(value)
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{value:,.0f}"


def page_header(title, subtitle, icon="📊"):
    st.markdown(f'<div class="section-label">OLIST BUSINESS INTELLIGENCE</div>', unsafe_allow_html=True)
    st.title(f"{icon} {title}")
    st.markdown(f'<div class="page-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def section_title(title):
    st.markdown(f"### {title}")


def download_csv(df, filename, label="⬇️ Download CSV"):
    """Provide a downloadable CSV for the currently filtered view."""
    st.download_button(
        label=label,
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
    )


def sales_filters(df, key_prefix="sales"):
    """Render reusable interactive filters for sales-based analysis."""
    filtered = df.copy()

    with st.expander("🎛️ Interactive Filters", expanded=True):
        c1, c2, c3 = st.columns(3)

        with c1:
            state_options = sorted(df["customer_state"].dropna().unique())
            selected_states = st.multiselect(
                "Customer State",
                state_options,
                key=f"{key_prefix}_states",
            )

        with c2:
            category_options = sorted(
                df["product_category_name_english"].dropna().unique()
            )
            selected_categories = st.multiselect(
                "Product Category",
                category_options,
                key=f"{key_prefix}_categories",
            )

        with c3:
            min_date = df["order_purchase_timestamp"].min().date()
            max_date = df["order_purchase_timestamp"].max().date()
            selected_dates = st.date_input(
                "Purchase Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                key=f"{key_prefix}_dates",
            )

        if selected_states:
            filtered = filtered[filtered["customer_state"].isin(selected_states)]

        if selected_categories:
            filtered = filtered[
                filtered["product_category_name_english"].isin(selected_categories)
            ]

        if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
            start_date, end_date = selected_dates
            filtered = filtered[
                filtered["order_purchase_timestamp"].dt.date.between(
                    start_date, end_date
                )
            ]

        active_filters = []
        if selected_states:
            active_filters.append(f"{len(selected_states)} state(s)")
        if selected_categories:
            active_filters.append(f"{len(selected_categories)} categor(ies)")
        if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
            if selected_dates != (min_date, max_date):
                active_filters.append("custom date range")

        if active_filters:
            st.caption("Active filters: " + " • ".join(active_filters))
        else:
            st.caption("Showing all available records.")

    return filtered


def customer_filters(df, key_prefix="customer"):
    """Render geographic filters for customer analysis."""
    filtered = df.copy()

    with st.expander("🎛️ Customer Filters", expanded=True):
        c1, c2 = st.columns(2)

        with c1:
            state_options = sorted(df["customer_state"].dropna().unique())
            selected_states = st.multiselect(
                "Customer State",
                state_options,
                key=f"{key_prefix}_states",
            )

        city_source = (
            df[df["customer_state"].isin(selected_states)]
            if selected_states
            else df
        )

        with c2:
            city_options = sorted(city_source["customer_city"].dropna().unique())
            selected_cities = st.multiselect(
                "Customer City",
                city_options,
                key=f"{key_prefix}_cities",
            )

        if selected_states:
            filtered = filtered[filtered["customer_state"].isin(selected_states)]

        if selected_cities:
            filtered = filtered[filtered["customer_city"].isin(selected_cities)]

        active_filters = []
        if selected_states:
            active_filters.append(f"{len(selected_states)} state(s)")
        if selected_cities:
            active_filters.append(f"{len(selected_cities)} cit(y/ies)")

        if active_filters:
            st.caption("Active filters: " + " • ".join(active_filters))
        else:
            st.caption("Showing all customers.")

    return filtered


# =========================================================
# SIDEBAR NAVIGATION
# =========================================================

with st.sidebar:
    st.title("📊 Olist BI")
    st.caption("Brazilian E-Commerce Analytics")

    st.markdown("**EXECUTIVE**")

    page = st.radio(
        "Navigate to",
        [
            "🏠 Overview",
            "👥 Customer Analysis",
            "💰 Sales Analysis",
            "🏷️ Category Analysis",
            "📦 Product Analysis",
            "🏪 Seller Analysis",
            "💳 Payment Analysis",
            "⭐ Review Analysis",
            "🚚 Delivery Analysis",
            "📚 Data & Methodology",
            "💡 Business Insights",
            "🤖 Gemini AI",
        ],
        label_visibility="collapsed",
    )

    st.divider()
    st.caption("Built with Python • Pandas • Streamlit • Gemini")


# =========================================================
# LOAD AND PREPARE DATA
# =========================================================

data = load_data()
data = clean_data(data)
sales = create_sales_data(data)

# Ensure customer geography is available in the master sales table.
# The sales model may not include customer_state/customer_city by default,
# but the interactive sales filters require these fields.
customer_geo = data["customers"][["customer_id", "customer_state", "customer_city"]].drop_duplicates("customer_id")
for geo_col in ["customer_state", "customer_city"]:
    if geo_col not in sales.columns:
        sales = sales.merge(
            customer_geo[["customer_id", geo_col]],
            on="customer_id",
            how="left"
        )


# =========================================================
# OVERVIEW
# =========================================================

if page == "🏠 Overview":

    page_header(
        "Olist Business Intelligence",
        "Executive overview of Olist's Brazilian e-commerce marketplace",
        "📊",
    )

    # ---------------------------------------------------------
    # EXECUTIVE SNAPSHOT
    # ---------------------------------------------------------

    st.markdown("### Executive Snapshot")

    total_sales = sales["price"].sum()
    total_orders = sales["order_id"].nunique()

    if "customer_unique_id" in data["customers"].columns:
        total_customers = data["customers"]["customer_unique_id"].nunique()
    else:
        total_customers = sales["customer_id"].nunique()

    total_sellers = sales["seller_id"].nunique()
    average_order_value = total_sales / total_orders if total_orders else 0

    reviews = data["reviews"]
    average_review = reviews["review_score"].mean()

    orders = data["orders"].copy()
    delivered_mask = (
        orders["order_delivered_customer_date"].notna()
        & orders["order_estimated_delivery_date"].notna()
    )

    late_mask = (
        delivered_mask
        & (
            orders["order_delivered_customer_date"]
            > orders["order_estimated_delivery_date"]
        )
    )

    late_rate = (
        late_mask.sum() / delivered_mask.sum() * 100
        if delivered_mask.sum()
        else 0
    )

    k1, k2, k3, k4, k5 = st.columns(5)

    with k1:
        st.metric("Total Sales", compact_currency(total_sales))

    with k2:
        st.metric("Total Orders", compact_number(total_orders))

    with k3:
        st.metric("Customers", compact_number(total_customers))

    with k4:
        st.metric("Sellers", compact_number(total_sellers))

    with k5:
        st.metric("Average Order Value", f"R$ {average_order_value:,.2f}")

    # ---------------------------------------------------------
    # CUSTOMER & OPERATIONS
    # ---------------------------------------------------------

    st.markdown("### Customer & Operations")

    k6, k7, k8 = st.columns(3)

    with k6:
        st.metric("Average Review Score", f"{average_review:.2f} / 5")

    with k7:
        st.metric("Late Delivery Rate", f"{late_rate:.1f}%")

    with k8:
        st.metric(
            "Delivered Orders",
            compact_number(delivered_mask.sum()),
        )

    # ---------------------------------------------------------
    # PREPARE OVERVIEW CHARTS
    # ---------------------------------------------------------

    monthly_sales = (
        sales.assign(
            month=sales["order_purchase_timestamp"]
            .dt.to_period("M")
            .astype(str)
        )
        .groupby("month")["price"]
        .sum()
    )

    category_sales = (
        sales.dropna(subset=["product_category_name_english"])
        .groupby("product_category_name_english")["price"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
    )

    seller_sales = (
        sales.groupby("seller_id")["price"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
    )

    # ---------------------------------------------------------
    # SALES & CATEGORY PERFORMANCE
    # ---------------------------------------------------------

    st.markdown("### Sales & Category Performance")

    chart_left, chart_right = st.columns([1.65, 1])

    with chart_left:
        section_title("📈 Monthly Sales Trend")

        st.line_chart(
            monthly_sales,
            use_container_width=True,
            height=360,
        )

    with chart_right:
        section_title("🏷️ Top Categories by Sales")

        st.bar_chart(
            category_sales.sort_values(ascending=True),
            use_container_width=True,
            height=360,
        )

    # ---------------------------------------------------------
    # SELLER PERFORMANCE
    # ---------------------------------------------------------

    st.markdown("### Seller Performance")

    seller_left, seller_right = st.columns([1, 1])

    with seller_left:
        section_title("🏪 Top 10 Sellers by Sales")

        st.bar_chart(
            seller_sales.sort_values(ascending=True),
            use_container_width=True,
            height=360,
        )

    with seller_right:
        section_title("📊 Executive Metrics")

        st.markdown(
            f"""
            <div class="insight-box">
                <b>Marketplace Scale</b><br>
                {compact_number(total_customers)} unique customers and
                {compact_number(total_sellers)} sellers are represented in the dataset.
                <br><br>

                <b>Sales Performance</b><br>
                The marketplace generated approximately
                <b>{compact_currency(total_sales)}</b> in product sales,
                with an average order value of
                <b>R$ {average_order_value:,.2f}</b>.
                <br><br>

                <b>Customer Experience</b><br>
                The average review score is
                <b>{average_review:.2f}/5</b>, while
                <b>{late_rate:.1f}%</b> of delivered orders were late.
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ---------------------------------------------------------
    # KEY BUSINESS SIGNALS
    # ---------------------------------------------------------

    st.markdown("### 💡 Key Business Signals")

    signal1, signal2, signal3 = st.columns(3)

    top_category = (
        category_sales.index[0]
        if len(category_sales)
        else "Not available"
    )

    top_seller = (
        seller_sales.index[0]
        if len(seller_sales)
        else "Not available"
    )

    with signal1:
        st.markdown(
            f"""
            <div class="insight-box">
                <b>🏷️ Leading Category</b><br>
                {top_category}<br>
                <small>{compact_currency(category_sales.iloc[0]) if len(category_sales) else "N/A"} in sales</small>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with signal2:
        st.markdown(
            f"""
            <div class="insight-box">
                <b>🏪 Leading Seller</b><br>
                {top_seller}<br>
                <small>{compact_currency(seller_sales.iloc[0]) if len(seller_sales) else "N/A"} in sales</small>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with signal3:
        st.markdown(
            f"""
            <div class="insight-box">
                <b>🚚 Delivery Signal</b><br>
                {late_rate:.1f}% late delivery rate<br>
                <small>Based on orders with delivery and estimated-delivery dates</small>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ---------------------------------------------------------
    # DATA OVERVIEW
    # ---------------------------------------------------------

    st.markdown("### Data Overview")

    overview_left, overview_right = st.columns(2)

    with overview_left:
        st.metric("Master Sales Rows", f"{sales.shape[0]:,}")

    with overview_right:
        st.metric("Master Sales Columns", f"{sales.shape[1]:,}")

    with st.expander("Preview Master Sales Data"):
        st.dataframe(
            sales.head(10),
            use_container_width=True,
            hide_index=True,
        )


# =========================================================
# =========================================================
# CUSTOMER ANALYSIS
# =========================================================

if page == "👥 Customer Analysis":

    page_header(
        "Customer Analysis",
        "Understand customer distribution and geographic concentration",
        "👥",
    )

    st.caption(
        "Business question: Where are Olist customers concentrated, and how does "
        "the customer base vary across states and cities?"
    )

    customers = data["customers"].copy()
    customers_filtered = customer_filters(customers, "customer_page")

    total_customers = (
        customers_filtered["customer_unique_id"].nunique()
        if "customer_unique_id" in customers_filtered.columns
        else customers_filtered["customer_id"].nunique()
    )

    states = customers_filtered["customer_state"].nunique()
    cities = customers_filtered["customer_city"].nunique()

    k1, k2, k3 = st.columns(3)
    with k1:
        st.metric("Unique Customers", compact_number(total_customers))
    with k2:
        st.metric("States", states)
    with k3:
        st.metric("Cities", cities)

    customers_by_state = (
        customers_filtered.groupby("customer_state")
        .size()
        .sort_values(ascending=False)
    )

    top_customer_cities = (
        customers_filtered.groupby("customer_city")
        .size()
        .sort_values(ascending=False)
        .head(10)
    )

    left, right = st.columns(2)

    with left:
        section_title("Customers by State")
        if len(customers_by_state):
            st.bar_chart(
                customers_by_state.sort_values(ascending=True),
                use_container_width=True,
                height=420,
            )
        else:
            st.info("No customers match the selected filters.")

    with right:
        section_title("Top 10 Customer Cities")
        if len(top_customer_cities):
            st.bar_chart(
                top_customer_cities.sort_values(ascending=True),
                use_container_width=True,
                height=420,
            )
        else:
            st.info("No customers match the selected filters.")

    st.markdown("### 💡 Business Interpretation")

    if len(customers_by_state):
        leading_state = customers_by_state.index[0]
        leading_state_count = customers_by_state.iloc[0]
        leading_city = top_customer_cities.index[0] if len(top_customer_cities) else "N/A"

        st.markdown(
            f"""
            <div class="insight-box">
                <b>Geographic concentration</b><br>
                The largest customer concentration in the current view is
                <b>{leading_state}</b>, with approximately
                <b>{compact_number(leading_state_count)}</b> customer records.
                The leading city in the top-10 view is <b>{leading_city}</b>.
                Use the state and city filters above to investigate regional
                concentration in more detail.
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("### 📋 Filtered Customer Data")
    st.dataframe(
        customers_filtered.head(500),
        use_container_width=True,
        hide_index=True,
    )

    download_csv(
        customers_filtered,
        "olist_filtered_customers.csv",
        "⬇️ Download Filtered Customer Data",
    )


# =========================================================
# SALES ANALYSIS
# =========================================================

if page == "💰 Sales Analysis":

    page_header(
        "Sales Analysis",
        "Track sales volume, order activity and average order value over time",
        "💰",
    )

    st.caption(
        "Business question: How do sales, orders and average order value change "
        "over time, and which market segments drive the results?"
    )

    filtered_sales = sales_filters(sales, "sales_page")

    if filtered_sales.empty:
        st.warning("No records match the selected filters. Please broaden your selection.")
    else:
        monthly_sales = (
            filtered_sales.assign(
                month=filtered_sales["order_purchase_timestamp"]
                .dt.to_period("M")
                .astype(str)
            )
            .groupby("month")["price"]
            .sum()
        )

        monthly_orders = (
            filtered_sales.assign(
                month=filtered_sales["order_purchase_timestamp"]
                .dt.to_period("M")
                .astype(str)
            )
            .groupby("month")["order_id"]
            .nunique()
        )

        monthly_aov = (monthly_sales / monthly_orders).dropna()

        total_filtered_sales = filtered_sales["price"].sum()
        total_filtered_orders = filtered_sales["order_id"].nunique()
        overall_aov = (
            total_filtered_sales / total_filtered_orders
            if total_filtered_orders
            else 0
        )

        k1, k2, k3 = st.columns(3)
        with k1:
            st.metric("Filtered Sales", compact_currency(total_filtered_sales))
        with k2:
            st.metric("Filtered Orders", compact_number(total_filtered_orders))
        with k3:
            st.metric("Filtered AOV", f"R$ {overall_aov:,.2f}")

        left, right = st.columns(2)

        with left:
            section_title("📈 Monthly Revenue")
            st.line_chart(monthly_sales, use_container_width=True, height=350)

        with right:
            section_title("📦 Monthly Orders")
            st.line_chart(monthly_orders, use_container_width=True, height=350)

        section_title("💳 Monthly Average Order Value")
        st.line_chart(monthly_aov, use_container_width=True, height=350)

        st.markdown("### 💡 Business Interpretation")

        peak_sales_month = monthly_sales.idxmax()
        peak_sales_value = monthly_sales.max()
        peak_orders_month = monthly_orders.idxmax()

        st.markdown(
            f"""
            <div class="insight-box">
                <b>Sales trend</b><br>
                The highest monthly sales in the current filtered view occurred in
                <b>{peak_sales_month}</b>, generating approximately
                <b>{compact_currency(peak_sales_value)}</b>.
                The highest order volume occurred in <b>{peak_orders_month}</b>.
                These results update automatically when the filters change.
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### 📋 Filtered Sales Data")
        st.dataframe(
            filtered_sales.head(500),
            use_container_width=True,
            hide_index=True,
        )

        download_csv(
            filtered_sales,
            "olist_filtered_sales.csv",
            "⬇️ Download Filtered Sales Data",
        )


# CATEGORY ANALYSIS
# =========================================================

if page == "🏷️ Category Analysis":

    page_header(
        "Category Analysis",
        "Compare product categories by revenue, order activity and contribution",
        "🏷️",
    )

    st.caption("Business question: Which product categories generate the most revenue and order activity?")
    filtered_sales = sales_filters(sales, key_prefix="category")

    if filtered_sales.empty:
        st.warning("No records match the selected filters.")
    else:
        category_base = filtered_sales.dropna(subset=["product_category_name_english"]).copy()

        category_summary = (
            category_base.groupby("product_category_name_english")
            .agg(
                Revenue=("price", "sum"),
                Orders=("order_id", "nunique"),
                Products=("product_id", "nunique"),
            )
            .sort_values("Revenue", ascending=False)
        )
        category_summary["Average Order Value"] = (
            category_summary["Revenue"] / category_summary["Orders"].replace(0, pd.NA)
        )

        k1, k2, k3 = st.columns(3)
        with k1:
            st.metric("Categories", f"{len(category_summary):,}")
        with k2:
            st.metric("Top Category Revenue", compact_currency(category_summary["Revenue"].max()))
        with k3:
            st.metric("Category Revenue", compact_currency(category_summary["Revenue"].sum()))

        top_revenue = category_summary["Revenue"].head(10)
        top_orders = category_summary["Orders"].sort_values(ascending=False).head(10)

        left, right = st.columns(2)
        with left:
            section_title("Top 10 Categories by Revenue")
            st.bar_chart(top_revenue.sort_values(), use_container_width=True, height=430)
        with right:
            section_title("Top 10 Categories by Orders")
            st.bar_chart(top_orders.sort_values(), use_container_width=True, height=430)

        section_title("Category Performance Table")
        display_category = category_summary.reset_index().head(20).copy()
        display_category["Revenue"] = display_category["Revenue"].round(2)
        display_category["Average Order Value"] = display_category["Average Order Value"].round(2)
        st.dataframe(display_category, use_container_width=True, hide_index=True)

        top_category = category_summary.index[0]
        top_category_share = category_summary.loc[top_category, "Revenue"] / category_summary["Revenue"].sum() * 100
        st.info(
            f"💡 **Business interpretation:** {top_category} is the highest-revenue category in the current view, "
            f"contributing approximately {top_category_share:.1f}% of category revenue. "
            "Category-level revenue concentration can help identify where merchandising and inventory decisions have the largest impact."
        )
        download_csv(display_category, "olist_category_analysis.csv", "⬇️ Download Category Analysis")


# =========================================================
# PRODUCT ANALYSIS
# =========================================================

if page == "📦 Product Analysis":

    page_header(
        "Product Analysis",
        "Identify products driving revenue, orders and customer ratings",
        "📦",
    )

    st.caption("Business question: Which products generate high sales, and which high-sales products receive weaker ratings?")
    filtered_sales = sales_filters(sales, key_prefix="product")

    if filtered_sales.empty:
        st.warning("No records match the selected filters.")
    else:
        product_summary = (
            filtered_sales.groupby("product_id")
            .agg(
                Revenue=("price", "sum"),
                Orders=("order_id", "nunique"),
                Units=("product_id", "size"),
            )
        )

        if "review_score" in filtered_sales.columns:
            product_summary["Average Rating"] = filtered_sales.groupby("product_id")["review_score"].mean()

        product_summary["Average Selling Price"] = (
            product_summary["Revenue"] / product_summary["Units"].replace(0, pd.NA)
        )
        product_summary = product_summary.sort_values("Revenue", ascending=False)

        k1, k2, k3 = st.columns(3)
        with k1:
            st.metric("Unique Products", f"{filtered_sales['product_id'].nunique():,}")
        with k2:
            st.metric("Product Revenue", compact_currency(filtered_sales["price"].sum()))
        with k3:
            st.metric("Units / Line Items", f"{len(filtered_sales):,}")

        left, right = st.columns(2)
        with left:
            section_title("Top 10 Products by Revenue")
            st.bar_chart(
                product_summary["Revenue"].head(10).sort_values(),
                use_container_width=True,
                height=430,
            )
        with right:
            section_title("Top 10 Products by Orders")
            st.bar_chart(
                product_summary.sort_values("Orders", ascending=False)["Orders"].head(10).sort_values(),
                use_container_width=True,
                height=430,
            )

        if "Average Rating" in product_summary.columns:
            rated = product_summary.dropna(subset=["Average Rating"]).copy()
            high_sales_low_rating = rated[
                (rated["Revenue"] >= rated["Revenue"].quantile(0.75)) &
                (rated["Average Rating"] <= rated["Average Rating"].quantile(0.25))
            ].sort_values("Revenue", ascending=False).head(10)

            section_title("High-Revenue Products with Lower Ratings")
            if high_sales_low_rating.empty:
                st.info("No products fall into the high-revenue / lower-rating segment under the current filters.")
            else:
                display_risk = high_sales_low_rating.reset_index()
                st.dataframe(display_risk.round(2), use_container_width=True, hide_index=True)

        section_title("Top Product Performance Table")
        display_products = product_summary.reset_index().head(25).copy()
        st.dataframe(display_products.round(2), use_container_width=True, hide_index=True)

        top_product = product_summary.index[0]
        st.info(
            f"💡 **Business interpretation:** Product {top_product} has the highest revenue in the current filtered view. "
            "Revenue leaders can be monitored alongside order volume and ratings to distinguish strong demand from potential customer-experience issues."
        )
        download_csv(display_products, "olist_product_analysis.csv", "⬇️ Download Product Analysis")


# =========================================================
# SELLER ANALYSIS
# =========================================================

if page == "🏪 Seller Analysis":

    page_header(
        "Seller Analysis",
        "Evaluate seller revenue, order volume and average order value",
        "🏪",
    )

    st.caption("Business question: Which sellers contribute the most revenue and orders, and how does seller AOV vary?")
    filtered_sales = sales_filters(sales, key_prefix="seller")

    if filtered_sales.empty:
        st.warning("No records match the selected filters.")
    else:
        seller_summary = (
            filtered_sales.groupby("seller_id")
            .agg(
                Revenue=("price", "sum"),
                Orders=("order_id", "nunique"),
                Items=("product_id", "size"),
            )
        )
        seller_summary["AOV"] = seller_summary["Revenue"] / seller_summary["Orders"].replace(0, pd.NA)
        seller_summary = seller_summary.sort_values("Revenue", ascending=False)

        k1, k2, k3 = st.columns(3)
        with k1:
            st.metric("Active Sellers", f"{filtered_sales['seller_id'].nunique():,}")
        with k2:
            st.metric("Seller Revenue", compact_currency(filtered_sales["price"].sum()))
        with k3:
            st.metric("Highest Seller AOV", compact_currency(seller_summary["AOV"].max()))

        left, right = st.columns(2)
        with left:
            section_title("Top 10 Sellers by Revenue")
            st.bar_chart(
                seller_summary["Revenue"].head(10).sort_values(),
                use_container_width=True,
                height=430,
            )
        with right:
            section_title("Top 10 Sellers by Orders")
            st.bar_chart(
                seller_summary.sort_values("Orders", ascending=False)["Orders"].head(10).sort_values(),
                use_container_width=True,
                height=430,
            )

        section_title("Top 10 Sellers by Average Order Value")
        st.bar_chart(
            seller_summary.sort_values("AOV", ascending=False)["AOV"].head(10).sort_values(),
            use_container_width=True,
            height=380,
        )

        section_title("Seller Performance Table")
        display_sellers = seller_summary.reset_index().head(25).copy()
        st.dataframe(display_sellers.round(2), use_container_width=True, hide_index=True)

        top_seller = seller_summary.index[0]
        top_seller_share = seller_summary.loc[top_seller, "Revenue"] / seller_summary["Revenue"].sum() * 100
        st.info(
            f"💡 **Business interpretation:** Seller {top_seller} is the largest revenue contributor in the current view, "
            f"accounting for approximately {top_seller_share:.1f}% of seller revenue. "
            "Seller concentration and AOV can be monitored when evaluating marketplace performance."
        )
        download_csv(display_sellers, "olist_seller_analysis.csv", "⬇️ Download Seller Analysis")


# PAYMENT ANALYSIS
# =========================================================

if page == "💳 Payment Analysis":

    page_header(
        "Payment Analysis",
        "Understand payment preferences, transaction volume and instalments",
        "💳",
    )

    payments = data["payments"]

    payment_revenue = (
        payments.groupby("payment_type")["payment_value"]
        .sum()
        .sort_values(ascending=False)
    )

    payment_count = (
        payments.groupby("payment_type")
        .size()
        .sort_values(ascending=False)
    )

    installments = (
        payments["payment_installments"]
        .value_counts()
        .sort_index()
    )

    k1, k2, k3 = st.columns(3)
    with k1:
        st.metric("Payment Value", compact_currency(payments["payment_value"].sum()))
    with k2:
        st.metric("Payment Transactions", f"{len(payments):,}")
    with k3:
        st.metric("Payment Methods", f"{payments['payment_type'].nunique():,}")

    left, right = st.columns(2)

    with left:
        section_title("Revenue by Payment Type")
        st.bar_chart(
            payment_revenue.sort_values(ascending=True),
            use_container_width=True,
            height=400,
        )

    with right:
        section_title("Number of Payments by Type")
        st.bar_chart(
            payment_count.sort_values(ascending=True),
            use_container_width=True,
            height=400,
        )

    section_title("Payment Installments")
    st.bar_chart(installments, use_container_width=True, height=350)


# =========================================================
# REVIEW ANALYSIS
# =========================================================

if page == "⭐ Review Analysis":

    page_header(
        "Review Analysis",
        "Measure customer satisfaction, rating distribution and response performance",
        "⭐",
    )

    reviews = data["reviews"].copy()

    # Enrich reviews with order/customer/product information without
    # multiplying revenue when an order has more than one review record.
    order_context_cols = [
        c for c in [
            "order_id",
            "customer_state",
            "product_category_name_english",
            "price",
            "order_purchase_timestamp",
        ]
        if c in sales.columns
    ]
    order_context = sales[order_context_cols].copy()
    if "order_id" in order_context.columns:
        order_context = (
            order_context.groupby("order_id", as_index=False)
            .agg({
                **({"customer_state": "first"} if "customer_state" in order_context else {}),
                **({"product_category_name_english": "first"} if "product_category_name_english" in order_context else {}),
                **({"price": "sum"} if "price" in order_context else {}),
                **({"order_purchase_timestamp": "first"} if "order_purchase_timestamp" in order_context else {}),
            })
        )

    if "order_id" in reviews.columns and "order_id" in order_context.columns:
        reviews = reviews.merge(order_context, on="order_id", how="left")

    with st.expander("🎛️ Review Filters", expanded=True):
        c1, c2, c3 = st.columns(3)

        with c1:
            score_options = sorted(reviews["review_score"].dropna().unique())
            selected_scores = st.multiselect(
                "Review Score",
                score_options,
                key="review_scores",
            )

        with c2:
            state_options = (
                sorted(reviews["customer_state"].dropna().unique())
                if "customer_state" in reviews.columns
                else []
            )
            selected_states = st.multiselect(
                "Customer State",
                state_options,
                key="review_states",
            )

        with c3:
            category_options = (
                sorted(reviews["product_category_name_english"].dropna().unique())
                if "product_category_name_english" in reviews.columns
                else []
            )
            selected_categories = st.multiselect(
                "Product Category",
                category_options,
                key="review_categories",
            )

        if selected_scores:
            reviews = reviews[reviews["review_score"].isin(selected_scores)]
        if selected_states and "customer_state" in reviews.columns:
            reviews = reviews[reviews["customer_state"].isin(selected_states)]
        if selected_categories and "product_category_name_english" in reviews.columns:
            reviews = reviews[
                reviews["product_category_name_english"].isin(selected_categories)
            ]

    if reviews.empty:
        st.warning("No review records match the selected filters.")
    else:
        average_review = reviews["review_score"].mean()
        five_star_rate = reviews["review_score"].eq(5).mean() * 100
        one_star_rate = reviews["review_score"].eq(1).mean() * 100

        reviews["has_response"] = reviews["review_answer_timestamp"].notna()
        response_rate = reviews["has_response"].mean() * 100

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.metric("Average Rating", f"{average_review:.2f} / 5")
        with k2:
            st.metric("5-Star Rate", f"{five_star_rate:.1f}%")
        with k3:
            st.metric("1-Star Rate", f"{one_star_rate:.1f}%")
        with k4:
            st.metric("Response Rate", f"{response_rate:.1f}%")

        review_distribution = reviews["review_score"].value_counts().sort_index()

        left, right = st.columns(2)
        with left:
            section_title("⭐ Review Score Distribution")
            st.bar_chart(review_distribution, use_container_width=True, height=380)

        with right:
            response_distribution = reviews["has_response"].map(
                {True: "Responded", False: "No Response"}
            ).value_counts()
            section_title("Review Response Coverage")
            st.bar_chart(response_distribution, use_container_width=True, height=380)

        if "product_category_name_english" in reviews.columns:
            category_review = (
                reviews.dropna(subset=["product_category_name_english"])
                .groupby("product_category_name_english")
                .agg(
                    Reviews=("review_score", "count"),
                    Average_Rating=("review_score", "mean"),
                )
                .sort_values("Reviews", ascending=False)
                .head(15)
            )
            category_review["Average_Rating"] = category_review["Average_Rating"].round(2)

            section_title("Category Review Performance")
            st.bar_chart(
                category_review["Average_Rating"].sort_values(),
                use_container_width=True,
                height=420,
            )

        if "price" in reviews.columns:
            rating_revenue = (
                reviews.groupby("review_score")
                .agg(
                    Reviews=("review_score", "size"),
                    Product_Sales=("price", "sum"),
                )
                .reset_index()
                .sort_values("review_score")
            )

            section_title("Product Sales Associated with Review Scores")
            st.dataframe(
                rating_revenue.style.format({"Product_Sales": "R$ {:,.2f}"}),
                use_container_width=True,
                hide_index=True,
            )

        section_title("💡 Business Interpretation")
        if average_review >= 4:
            review_comment = "Overall customer satisfaction is relatively strong, with the average rating at or above 4/5."
        elif average_review >= 3:
            review_comment = "Customer satisfaction is mixed, so rating distribution and low-scoring categories deserve attention."
        else:
            review_comment = "Average satisfaction is below 3/5, indicating a broad need to investigate customer experience issues."

        st.markdown(
            f'<div class="insight-box">{review_comment}<br>'
            f'<b>1-star reviews:</b> {one_star_rate:.1f}% &nbsp;•&nbsp; '
            f'<b>5-star reviews:</b> {five_star_rate:.1f}% &nbsp;•&nbsp; '
            f'<b>Response coverage:</b> {response_rate:.1f}%</div>',
            unsafe_allow_html=True,
        )

        download_columns = [
            c for c in reviews.columns
            if c not in ["has_response"]
        ]
        download_csv(
            reviews[download_columns],
            "olist_filtered_reviews.csv",
            "⬇️ Download Filtered Reviews",
        )


# =========================================================
# DELIVERY ANALYSIS
# =========================================================

if page == "🚚 Delivery Analysis":

    page_header(
        "Delivery & Fulfilment",
        "Monitor delivery speed, estimated-vs-actual performance and late orders",
        "🚚",
    )

    orders = data["orders"].copy()

    orders["delivery_days"] = (
        orders["order_delivered_customer_date"]
        - orders["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400

    orders["estimated_delivery_days"] = (
        orders["order_estimated_delivery_date"]
        - orders["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400

    orders["delivery_delay_days"] = (
        orders["order_delivered_customer_date"]
        - orders["order_estimated_delivery_date"]
    ).dt.total_seconds() / 86400

    delivered = (
        orders["order_delivered_customer_date"].notna()
        & orders["order_estimated_delivery_date"].notna()
    )

    orders["delivery_status"] = "Undelivered"
    orders.loc[delivered, "delivery_status"] = (
        orders.loc[delivered, "order_delivered_customer_date"]
        > orders.loc[delivered, "order_estimated_delivery_date"]
    ).map({True: "Late", False: "On Time"})

    # Enrich orders with customer state and category for operational analysis.
    context_cols = [
        c for c in [
            "order_id",
            "customer_state",
            "product_category_name_english",
        ]
        if c in sales.columns
    ]
    order_context = sales[context_cols].drop_duplicates("order_id")
    if "order_id" in order_context.columns and "order_id" in orders.columns:
        orders = orders.merge(order_context, on="order_id", how="left")

    with st.expander("🎛️ Delivery Filters", expanded=True):
        c1, c2, c3 = st.columns(3)

        with c1:
            status_options = ["On Time", "Late", "Undelivered"]
            selected_status = st.multiselect(
                "Delivery Status",
                status_options,
                key="delivery_status_filter",
            )

        with c2:
            state_options = (
                sorted(orders["customer_state"].dropna().unique())
                if "customer_state" in orders.columns
                else []
            )
            selected_states = st.multiselect(
                "Customer State",
                state_options,
                key="delivery_states",
            )

        with c3:
            category_options = (
                sorted(orders["product_category_name_english"].dropna().unique())
                if "product_category_name_english" in orders.columns
                else []
            )
            selected_categories = st.multiselect(
                "Product Category",
                category_options,
                key="delivery_categories",
            )

        if selected_status:
            orders = orders[orders["delivery_status"].isin(selected_status)]
        if selected_states and "customer_state" in orders.columns:
            orders = orders[orders["customer_state"].isin(selected_states)]
        if selected_categories and "product_category_name_english" in orders.columns:
            orders = orders[
                orders["product_category_name_english"].isin(selected_categories)
            ]

    if orders.empty:
        st.warning("No delivery records match the selected filters.")
    else:
        delivered_orders = orders[orders["delivery_status"].isin(["Late", "On Time"])]

        average_delivery = orders["delivery_days"].mean()
        average_estimated = orders["estimated_delivery_days"].mean()
        late_rate = (
            delivered_orders["delivery_status"].eq("Late").mean() * 100
            if len(delivered_orders)
            else 0
        )
        on_time_rate = (
            delivered_orders["delivery_status"].eq("On Time").mean() * 100
            if len(delivered_orders)
            else 0
        )

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.metric("Average Delivery Time", f"{average_delivery:.1f} days")
        with k2:
            st.metric("Average Estimated Time", f"{average_estimated:.1f} days")
        with k3:
            st.metric("Late Delivery Rate", f"{late_rate:.1f}%")
        with k4:
            st.metric("On-Time Rate", f"{on_time_rate:.1f}%")

        delivery_distribution = (
            orders["delivery_days"]
            .dropna()
            .round()
            .value_counts()
            .sort_index()
            .head(30)
        )
        delivery_status = orders["delivery_status"].value_counts()

        left, right = st.columns(2)
        with left:
            section_title("Delivery Time Distribution")
            st.bar_chart(delivery_distribution, use_container_width=True, height=400)

        with right:
            section_title("On-Time vs Late vs Undelivered")
            st.bar_chart(delivery_status, use_container_width=True, height=400)

        if "customer_state" in orders.columns:
            state_delivery = (
                delivered_orders.dropna(subset=["customer_state"])
                .groupby("customer_state")
                .agg(
                    Orders=("order_id", "nunique"),
                    Average_Delivery_Days=("delivery_days", "mean"),
                    Late_Rate=("delivery_status", lambda x: (x == "Late").mean() * 100),
                )
                .sort_values("Late_Rate", ascending=False)
            )
            state_delivery["Average_Delivery_Days"] = state_delivery["Average_Delivery_Days"].round(2)
            state_delivery["Late_Rate"] = state_delivery["Late_Rate"].round(1)

            section_title("Delivery Performance by State")
            st.dataframe(state_delivery, use_container_width=True)

        if "product_category_name_english" in orders.columns:
            category_delivery = (
                delivered_orders.dropna(subset=["product_category_name_english"])
                .groupby("product_category_name_english")
                .agg(
                    Orders=("order_id", "nunique"),
                    Average_Delivery_Days=("delivery_days", "mean"),
                    Late_Rate=("delivery_status", lambda x: (x == "Late").mean() * 100),
                )
                .sort_values("Late_Rate", ascending=False)
                .head(15)
            )
            category_delivery["Average_Delivery_Days"] = category_delivery["Average_Delivery_Days"].round(2)
            category_delivery["Late_Rate"] = category_delivery["Late_Rate"].round(1)

            section_title("Categories with Higher Late-Delivery Rates")
            st.bar_chart(
                category_delivery["Late_Rate"].sort_values(),
                use_container_width=True,
                height=420,
            )

        delayed_orders = (
            delivered_orders[delivered_orders["delivery_status"] == "Late"]
            .sort_values("delivery_delay_days", ascending=False)
            .head(20)
        )

        section_title("Orders with the Largest Delivery Delays")
        delay_columns = [
            c for c in [
                "order_id",
                "customer_state",
                "product_category_name_english",
                "delivery_days",
                "estimated_delivery_days",
                "delivery_delay_days",
            ]
            if c in delayed_orders.columns
        ]
        delay_display = delayed_orders[delay_columns].copy()
        for col in ["delivery_days", "estimated_delivery_days", "delivery_delay_days"]:
            if col in delay_display.columns:
                delay_display[col] = delay_display[col].round(1)
        st.dataframe(delay_display, use_container_width=True, hide_index=True)

        section_title("💡 Business Interpretation")
        if late_rate <= 10:
            delivery_comment = "The filtered orders show a relatively low late-delivery rate; operational attention can focus on the specific states or categories with higher delay rates."
        elif late_rate <= 20:
            delivery_comment = "Late deliveries are material enough to warrant investigation of the highest-delay states, categories and individual orders."
        else:
            delivery_comment = "A substantial share of delivered orders are late, making fulfilment performance a key area for operational investigation."

        st.markdown(
            f'<div class="insight-box">{delivery_comment}<br>'
            f'<b>Average actual delivery:</b> {average_delivery:.1f} days &nbsp;•&nbsp; '
            f'<b>Average estimated delivery:</b> {average_estimated:.1f} days &nbsp;•&nbsp; '
            f'<b>Late rate:</b> {late_rate:.1f}%</div>',
            unsafe_allow_html=True,
        )

        download_columns = [
            c for c in [
                "order_id",
                "customer_state",
                "product_category_name_english",
                "order_purchase_timestamp",
                "order_delivered_customer_date",
                "order_estimated_delivery_date",
                "delivery_days",
                "estimated_delivery_days",
                "delivery_delay_days",
                "delivery_status",
            ]
            if c in orders.columns
        ]
        download_csv(
            orders[download_columns],
            "olist_filtered_delivery.csv",
            "⬇️ Download Filtered Delivery Data",
        )


# DATA & METHODOLOGY
# =========================================================

if page == "📚 Data & Methodology":

    page_header(
        "Data & Methodology",
        "How the Olist dataset is prepared, modelled and analysed in this dashboard",
        "📚",
    )

    st.markdown("### Business Question")
    st.write(
        "How can Olist's e-commerce data be transformed into actionable business intelligence "
        "across customers, sales, categories, products, sellers, reviews and delivery?"
    )

    st.markdown("### Dataset Overview")
    table_info = []
    for name, df in data.items():
        table_info.append({
            "Table": name,
            "Rows": len(df),
            "Columns": len(df.columns),
        })
    st.dataframe(pd.DataFrame(table_info), use_container_width=True, hide_index=True)

    st.markdown("### Data Preparation")
    prep_steps = [
        "Load the Olist relational CSV tables.",
        "Clean and standardise fields using the project's data-cleaning pipeline.",
        "Convert date/time fields into pandas datetime values for time-based analysis.",
        "Create an integrated sales dataset by connecting relevant order, customer, product, seller and category information.",
        "Calculate derived business metrics such as sales, order counts, average order value, review rates and delivery delays.",
        "Apply page-level filters before calculating the displayed KPIs, charts and downloadable tables.",
    ]
    for i, step in enumerate(prep_steps, 1):
        st.markdown(f"**{i}.** {step}")

    st.markdown("### Core Analytical KPIs")
    kpi_table = pd.DataFrame([
        ["Total Sales", "Sum of product price values in the sales dataset"],
        ["Total Orders", "Unique order IDs"],
        ["Average Order Value", "Total sales ÷ unique orders"],
        ["Customers", "Unique customer_unique_id where available"],
        ["Sellers", "Unique seller IDs"],
        ["Average Review Score", "Mean review score"],
        ["Late Delivery Rate", "Late delivered orders ÷ delivered orders"],
        ["Average Delivery Time", "Mean days from purchase to customer delivery"],
    ], columns=["KPI", "Calculation"])
    st.dataframe(kpi_table, use_container_width=True, hide_index=True)

    st.markdown("### Analytical Methods")
    method_cols = st.columns(3)
    with method_cols[0]:
        st.markdown('<div class="insight-box"><b>Descriptive Analytics</b><br>KPIs, distributions, rankings and time trends are used to describe marketplace performance.</div>', unsafe_allow_html=True)
    with method_cols[1]:
        st.markdown('<div class="insight-box"><b>Segmentation</b><br>Performance is examined across states, cities, categories, products, sellers and review scores.</div>', unsafe_allow_html=True)
    with method_cols[2]:
        st.markdown('<div class="insight-box"><b>Operational Analytics</b><br>Delivery speed, estimated-vs-actual performance and late orders are used to identify fulfilment signals.</div>', unsafe_allow_html=True)

    st.markdown("### Important Scope & Limitations")
    limitations = [
        "Sales-oriented metrics in this dashboard should not be interpreted as accounting profit because the dataset does not provide a complete cost, commission, marketing and operating-expense structure.",
        "Delivery metrics are calculated only where the required order timestamps are available.",
        "Review analysis depends on the review records available in the source data.",
        "The Gemini layer explains calculated evidence; it should not be treated as a replacement for the underlying Pandas calculations.",
    ]
    for item in limitations:
        st.markdown(f"- {item}")

    st.markdown("### Data Model")
    st.info(
        "The dashboard uses the Olist relational tables and creates an integrated sales view for cross-table analysis. "
        "Key relationships include orders connected to customers, order items connected to products and sellers, "
        "products connected to categories, payments connected to orders, and reviews connected to orders."
    )


# BUSINESS INSIGHTS
# =========================================================

if page == "💡 Business Insights":

    page_header(
        "Business Insights",
        "Evidence-based signals generated directly from the dashboard's calculated metrics",
        "💡",
    )

    st.markdown("### Executive Insight Summary")

    total_sales_bi = sales["price"].sum()
    total_orders_bi = sales["order_id"].nunique()
    aov_bi = total_sales_bi / total_orders_bi if total_orders_bi else 0

    category_bi = (
        sales.dropna(subset=["product_category_name_english"])
        .groupby("product_category_name_english")
        .agg(Sales=("price", "sum"), Orders=("order_id", "nunique"))
        .sort_values("Sales", ascending=False)
    )

    seller_bi = (
        sales.groupby("seller_id")
        .agg(Sales=("price", "sum"), Orders=("order_id", "nunique"))
        .sort_values("Sales", ascending=False)
    )

    monthly_bi = (
        sales.assign(month=sales["order_purchase_timestamp"].dt.to_period("M").astype(str))
        .groupby("month")["price"]
        .sum()
    )

    orders_bi = data["orders"].copy()
    delivered_bi = orders_bi[
        orders_bi["order_delivered_customer_date"].notna()
        & orders_bi["order_estimated_delivery_date"].notna()
    ].copy()
    if not delivered_bi.empty:
        delivered_bi["late"] = (
            delivered_bi["order_delivered_customer_date"]
            > delivered_bi["order_estimated_delivery_date"]
        )
        late_rate_bi = delivered_bi["late"].mean() * 100
    else:
        late_rate_bi = 0

    avg_review_bi = data["reviews"]["review_score"].mean()

    insights = []
    if not category_bi.empty:
        top_cat = category_bi.index[0]
        top_cat_sales = category_bi.iloc[0]["Sales"]
        cat_share = top_cat_sales / total_sales_bi * 100 if total_sales_bi else 0
        insights.append(("Category concentration", f"{top_cat} is the highest-sales category in the current dataset, contributing approximately {cat_share:.1f}% of product sales."))

    if not seller_bi.empty:
        top_seller = seller_bi.index[0]
        top_seller_sales = seller_bi.iloc[0]["Sales"]
        seller_share = top_seller_sales / total_sales_bi * 100 if total_sales_bi else 0
        insights.append(("Seller concentration", f"The highest-sales seller contributes approximately {seller_share:.1f}% of product sales, providing a useful concentration signal."))

    if len(monthly_bi) >= 2:
        best_month = monthly_bi.idxmax()
        best_month_sales = monthly_bi.max()
        insights.append(("Sales timing", f"The highest-sales month in the dataset is {best_month}, with approximately R$ {best_month_sales:,.0f} in product sales."))

    insights.append(("Customer experience", f"The average review score is {avg_review_bi:.2f}/5, while the overall late-delivery rate among delivered orders is {late_rate_bi:.1f}%."))
    insights.append(("Order economics", f"The calculated average order value is approximately R$ {aov_bi:,.2f}."))

    for title, text_value in insights:
        st.markdown(
            f'<div class="insight-box"><b>{title}</b><br>{text_value}</div>',
            unsafe_allow_html=True,
        )
        st.write("")

    st.markdown("### Supporting Evidence")
    c1, c2 = st.columns(2)
    with c1:
        section_title("Top Categories")
        st.dataframe(
            category_bi.head(10).style.format({"Sales": "R$ {:,.2f}", "Orders": "{:,.0f}"}),
            use_container_width=True,
        )
    with c2:
        section_title("Top Sellers")
        st.dataframe(
            seller_bi.head(10).style.format({"Sales": "R$ {:,.2f}", "Orders": "{:,.0f}"}),
            use_container_width=True,
        )

    section_title("Monthly Sales")
    st.line_chart(monthly_bi, use_container_width=True, height=360)

    st.caption(
        "These insights are descriptive signals calculated from the dashboard data. "
        "They should be interpreted alongside the underlying tables and filters rather than as causal conclusions."
    )

    download_csv(
        pd.DataFrame(insights, columns=["Insight Area", "Insight"]),
        "olist_business_insights.csv",
        "⬇️ Download Business Insights",
    )


# GEMINI AI BUSINESS ANALYST
# =========================================================

if page == "🤖 Gemini AI":

    page_header(
        "Gemini AI Business Analyst",
        "Ask questions about Olist's business data and receive AI-assisted analysis grounded in calculated evidence",
        "🤖",
    )

    st.info(
        "Workflow: your question → Pandas calculates the relevant evidence → Gemini receives that evidence → "
        "Gemini explains the result in business language."
    )

    # Base metrics
    total_sales_ai = sales["price"].sum()
    total_orders_ai = sales["order_id"].nunique()
    total_customers_ai = (
        data["customers"]["customer_unique_id"].nunique()
        if "customer_unique_id" in data["customers"].columns
        else sales["customer_id"].nunique()
    )
    total_sellers_ai = sales["seller_id"].nunique()
    average_order_value_ai = total_sales_ai / total_orders_ai if total_orders_ai else 0

    category_revenue_ai = (
        sales.dropna(subset=["product_category_name_english"])
        .groupby("product_category_name_english")
        .agg(Sales=("price", "sum"), Orders=("order_id", "nunique"))
        .sort_values("Sales", ascending=False)
        .head(10)
    )

    seller_revenue_ai = (
        sales.groupby("seller_id")
        .agg(Sales=("price", "sum"), Orders=("order_id", "nunique"))
        .sort_values("Sales", ascending=False)
        .head(10)
    )

    payment_revenue_ai = (
        data["payments"].groupby("payment_type")["payment_value"]
        .sum().sort_values(ascending=False)
    )

    average_review_ai = data["reviews"]["review_score"].mean()

    orders_ai = data["orders"].copy()
    orders_ai["delivery_days"] = (
        orders_ai["order_delivered_customer_date"]
        - orders_ai["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400
    average_delivery_ai = orders_ai["delivery_days"].mean()

    delivered_ai = orders_ai[
        orders_ai["order_delivered_customer_date"].notna()
        & orders_ai["order_estimated_delivery_date"].notna()
    ]
    late_rate_ai = (
        (delivered_ai["order_delivered_customer_date"] > delivered_ai["order_estimated_delivery_date"]).mean() * 100
        if not delivered_ai.empty else 0
    )

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Sales", compact_currency(total_sales_ai))
    with k2:
        st.metric("Orders", compact_number(total_orders_ai))
    with k3:
        st.metric("AOV", f"R$ {average_order_value_ai:,.2f}")
    with k4:
        st.metric("Avg Rating", f"{average_review_ai:.2f} / 5")

    st.markdown("### Ask a Business Question")

    examples = [
        "Which product category generates the most revenue?",
        "Which sellers have the highest revenue?",
        "What is the average order value and what does it mean?",
        "What percentage of delivered orders are late?",
        "What should management investigate based on the current data?",
    ]
    st.caption("Example questions: " + " • ".join(examples[:3]))

    question = st.text_input(
        "Your question",
        placeholder="Example: Which product categories generate the most revenue?",
        label_visibility="collapsed",
        key="gemini_business_question",
    )

    if st.button("🔍 Analyze", use_container_width=False, key="gemini_analyze_button"):

        if question.strip():
            q = question.lower()

            # Build evidence specifically relevant to the question.
            evidence_sections = []

            if any(term in q for term in ["category", "categories", "product category"]):
                evidence_sections.append(
                    "CATEGORY EVIDENCE:\n" + category_revenue_ai.to_string()
                )

            if any(term in q for term in ["seller", "sellers"]):
                evidence_sections.append(
                    "SELLER EVIDENCE:\n" + seller_revenue_ai.to_string()
                )

            if any(term in q for term in ["payment", "pay", "installment"]):
                evidence_sections.append(
                    "PAYMENT EVIDENCE:\n" + payment_revenue_ai.to_string()
                )

            if any(term in q for term in ["review", "rating", "star"]):
                review_distribution_ai = data["reviews"]["review_score"].value_counts().sort_index()
                evidence_sections.append(
                    f"REVIEW EVIDENCE:\nAverage review: {average_review_ai:.2f}/5\n"
                    f"1-star rate: {(data['reviews']['review_score'].eq(1).mean()*100):.1f}%\n"
                    f"Distribution:\n{review_distribution_ai.to_string()}"
                )

            if any(term in q for term in ["delivery", "late", "fulfilment", "fulfillment"]):
                evidence_sections.append(
                    f"DELIVERY EVIDENCE:\nAverage delivery: {average_delivery_ai:.1f} days\n"
                    f"Late delivery rate: {late_rate_ai:.1f}%"
                )

            if any(term in q for term in ["customer", "customers", "city", "state"]):
                customer_counts_ai = (
                    data["customers"].groupby("customer_state")["customer_unique_id"]
                    .nunique().sort_values(ascending=False).head(10)
                    if "customer_unique_id" in data["customers"].columns
                    else data["customers"].groupby("customer_state")["customer_id"].nunique().sort_values(ascending=False).head(10)
                )
                evidence_sections.append(
                    "CUSTOMER EVIDENCE — TOP STATES:\n" + customer_counts_ai.to_string()
                )

            if any(term in q for term in ["sales", "revenue", "order", "orders", "aov", "average order"]):
                evidence_sections.append(
                    f"SALES EVIDENCE:\nTotal sales: R$ {total_sales_ai:,.2f}\n"
                    f"Orders: {total_orders_ai:,}\nAOV: R$ {average_order_value_ai:,.2f}"
                )

            if not evidence_sections:
                evidence_sections.append(
                    "GENERAL EVIDENCE:\n"
                    f"Sales: R$ {total_sales_ai:,.2f}\nOrders: {total_orders_ai:,}\n"
                    f"Customers: {total_customers_ai:,}\nSellers: {total_sellers_ai:,}\n"
                    f"AOV: R$ {average_order_value_ai:,.2f}\n"
                    f"Average review: {average_review_ai:.2f}/5\n"
                    f"Average delivery: {average_delivery_ai:.1f} days\n"
                    f"Late delivery rate: {late_rate_ai:.1f}%"
                )

            business_context = f"""
You are the business analyst layer of an Olist Business Intelligence dashboard.
Answer the user's question using ONLY the calculated evidence supplied below.
Do not invent figures or claim causation that the data does not establish.
If the evidence is insufficient, explicitly say so.
Give a concise business explanation and, where appropriate, a practical management implication.
Distinguish calculated facts from interpretation.

OVERALL DATA CONTEXT:
Total sales: R$ {total_sales_ai:,.2f}
Total orders: {total_orders_ai:,}
Total customers: {total_customers_ai:,}
Total sellers: {total_sellers_ai:,}
Average order value: R$ {average_order_value_ai:,.2f}
Average review score: {average_review_ai:.2f}/5
Average delivery time: {average_delivery_ai:.1f} days
Late delivery rate: {late_rate_ai:.1f}%

QUESTION-SPECIFIC EVIDENCE:
{chr(10).join(evidence_sections)}
"""

            with st.spinner("Gemini is analyzing the calculated evidence..."):
                try:
                    answer = ask_gemini(question, business_context)

                    st.markdown("### 📊 Data Evidence Used")
                    for evidence in evidence_sections:
                        st.code(evidence, language="text")

                    st.markdown("### 🤖 Gemini Analysis")
                    st.markdown(
                        f'<div class="insight-box">{answer}</div>',
                        unsafe_allow_html=True,
                    )

                    st.markdown("### 💡 Interpretation")
                    st.caption(
                        "Gemini provides the explanation layer. The numerical evidence above is calculated by the dashboard "
                        "before the response is generated."
                    )

                except Exception as e:
                    st.error(f"Gemini could not generate a response: {e}")
        else:
            st.warning("Please enter a business question first.")
