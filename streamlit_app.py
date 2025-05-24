from collections import defaultdict
from pathlib import Path
import sqlite3

import streamlit as st
import altair as alt
import pandas as pd


# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title="Inventory tracker",
    page_icon=":shopping_bags:",  # This is an emoji shortcode. Could be a URL too.
)


# -----------------------------------------------------------------------------
# Declare some useful functions.


def connect_db():
    """Connects to the sqlite database."""

    DB_FILENAME = Path(__file__).parent / "inventory.db"
    db_already_exists = DB_FILENAME.exists()

    conn = sqlite3.connect(DB_FILENAME)
    db_was_just_created = not db_already_exists

    return conn, db_was_just_created


def initialize_data(conn):
    """Initializes the inventory table with some data."""
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT,
            price REAL,
            units_sold INTEGER,
            units_left INTEGER,
            cost_price REAL,
            reorder_point INTEGER,
            description TEXT
        )
        """
    )

    cursor.execute(
      """
        INSERT INTO inventory
            (item_name, price, units_sold, units_left, cost_price, reorder_point, description)
        VALUES
           -- Beverages  
('Bisleri Water (500ml)', 50, 115, 15, 20.00, 5, 'Pure mineral water'),  
('Thums Up (300ml)', 40, 93, 8, 35.00, 10, 'Strong carbonated cola drink'),  
('Red Bull (250ml)', 125, 12, 18, 70.00, 8, 'Energy-boosting drink'),  
('Nescafe Coffee (hot, large)', 55, 11, 14, 40.00, 5, 'Freshly brewed instant coffee'),  
('Real Fruit Juice (200ml)', 45, 11, 9, 35.00, 5, 'Healthy mixed fruit juice'),  
('Masala Chai (Cup)', 100, 11, 12, 20.00, 5, 'Authentic Indian spiced tea'),  

-- Snacks  
('Lays Chips (small)', 50, 34, 16, 20.00, 10, 'Crispy salted potato chips'),  
('Dairy Milk Chocolate', 50, 6, 19, 35.00, 5, 'Milk chocolate bar'),  
('Britannia Nutri Bar', 40, 3, 12, 30.00, 8, 'Healthy granola bar with nuts'),  
('Parle-G Biscuits (large pack)', 80, 8, 8, 40.00, 5, 'Classic glucose biscuits'),  
('Haldiram’s Namkeen (small)', 60, 5, 10, 40.00, 8, 'Spicy and crunchy Indian snack'),  

-- Personal Care  
('Colgate Toothpaste (small)', 20, 1, 9, 15.00, 5, 'Fluoride toothpaste for strong teeth'),  
('Dettol Hand Sanitizer (small)', 40, 2, 13, 25.00, 8, 'Antibacterial sanitizer for hygiene'),  
('Crocin Pain Reliever (strip)', 40, 1, 5, 35.00, 3, 'Over-the-counter paracetamol tablet'),  
('Band-Aid Strips (box)', 25, 0, 10, 20.00, 5, 'Adhesive bandages for wounds'),  
('Himalaya Sunscreen (small)', 150, 6, 5, 120.00, 3, 'Herbal sunscreen lotion'),  
('Mediker Anti-Lice Shampoo', 100, 6, 8, 75.00, 5, 'Effective shampoo for lice removal'),  

-- Household  
('Eveready AA Batteries (4-pack)', 100, 1, 5, 70.00, 3, 'Long-lasting alkaline batteries'),  
('Syska LED Bulb (9W, 2-pack)', 200, 3, 3, 150.00, 2, 'Energy-efficient LED bulbs'),  
('Garbage Bags (small, 10-pack)', 70, 5, 10, 50.00, 5, 'Disposable trash bags for home use'),  
('Origami Paper Towels (single roll)', 40, 3, 8, 30.00, 5, 'Absorbent paper towels'),  
('Harpic Toilet Cleaner (500ml)', 105, 2, 5, 95.00, 3, 'Powerful toilet cleaning liquid'),  

-- Others  
('Lottery Tickets', 20, 17, 20, 15.00, 10, 'Government-approved lottery tickets'),  
('The Times of India Newspaper', 12, 22, 20, 10.00, 5, 'Daily national newspaper'),  
('Ball Pens (5-pack)', 70, 1, 8, 50.00, 5, 'Smooth writing ball pens'),  
('Natraj Pencils (10-pack)', 60, 1, 8, 30.00, 5, 'High-quality HB pencils'),  
('Classmate Notebook (200 pages)', 50, 1, 8, 40.00, 5, 'Spiral-bound ruled notebook');       
        """
    )
    conn.commit()


def load_data(conn):
    """Loads the inventory data from the database."""
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM inventory")
        data = cursor.fetchall()
    except:
        return None

    df = pd.DataFrame(
        data,
        columns=[
            "id",
            "item_name",
            "price",
            "units_sold",
            "units_left",
            "cost_price",
            "reorder_point",
            "description",
        ],
    )

    return df


def update_data(conn, df, changes):
    """Updates the inventory data in the database."""
    cursor = conn.cursor()

    if changes["edited_rows"]:
        deltas = st.session_state.inventory_table["edited_rows"]
        rows = []

        for i, delta in deltas.items():
            row_dict = df.iloc[i].to_dict()
            row_dict.update(delta)
            rows.append(row_dict)

        cursor.executemany(
            """
            UPDATE inventory
            SET
                item_name = :item_name,
                price = :price,
                units_sold = :units_sold,
                units_left = :units_left,
                cost_price = :cost_price,
                reorder_point = :reorder_point,
                description = :description
            WHERE id = :id
            """,
            rows,
        )

    if changes["added_rows"]:
        cursor.executemany(
            """
            INSERT INTO inventory
                (id, item_name, price, units_sold, units_left, cost_price, reorder_point, description)
            VALUES
                (:id, :item_name, :price, :units_sold, :units_left, :cost_price, :reorder_point, :description)
            """,
            (defaultdict(lambda: None, row) for row in changes["added_rows"]),
        )

    if changes["deleted_rows"]:
        cursor.executemany(
            "DELETE FROM inventory WHERE id = :id",
            ({"id": int(df.loc[i, "id"])} for i in changes["deleted_rows"]),
        )

    conn.commit()


# -----------------------------------------------------------------------------
# Draw the actual page, starting with the inventory table.

# Set the title that appears at the top of the page.
"""
# :shopping_bags: Inventory tracker

**Welcome to Suhas's Corner Store's intentory tracker!**
This page reads and writes directly from/to our inventory database.
"""

st.info(
    """
    Use the table below to add, remove, and edit items.
    And don't forget to commit your changes when you're done.
    """
)

# Connect to database and create table if needed
conn, db_was_just_created = connect_db()

# Initialize data.
if db_was_just_created:
    initialize_data(conn)
    st.toast("Database initialized with some sample data.")

# Load data from database
df = load_data(conn)

# Display data with editable table
edited_df = st.data_editor(
    df,
    disabled=["id"],  # Don't allow editing the 'id' column.
    num_rows="dynamic",  # Allow appending/deleting rows.
    column_config={
        # Show dollar sign before price columns.
        "price": st.column_config.NumberColumn(format="$%.2f"),
        "cost_price": st.column_config.NumberColumn(format="$%.2f"),
    },
    key="inventory_table",
)

has_uncommitted_changes = any(len(v) for v in st.session_state.inventory_table.values())

st.button(
    "Commit changes",
    type="primary",
    disabled=not has_uncommitted_changes,
    # Update data in database
    on_click=update_data,
    args=(conn, df, st.session_state.inventory_table),
)


# -----------------------------------------------------------------------------
# Now some cool charts

# Add some space
""
""
""

st.subheader("Units left", divider="red")

need_to_reorder = df[df["units_left"] < df["reorder_point"]].loc[:, "item_name"]

if len(need_to_reorder) > 0:
    items = "\n".join(f"* {name}" for name in need_to_reorder)

    st.error(f"We're running dangerously low on the items below:\n {items}")

""
""

st.altair_chart(
    # Layer 1: Bar chart.
    alt.Chart(df)
    .mark_bar(
        orient="horizontal",
    )
    .encode(
        x="units_left",
        y="item_name",
    )
    # Layer 2: Chart showing the reorder point.
    + alt.Chart(df)
    .mark_point(
        shape="diamond",
        filled=True,
        size=50,
        color="salmon",
        opacity=1,
    )
    .encode(
        x="reorder_point",
        y="item_name",
    ),
    use_container_width=True,
)

st.caption("NOTE: The :diamonds: location shows the reorder point.")

""
""
""

# -----------------------------------------------------------------------------

st.subheader("Best sellers", divider="orange")

""
""

st.altair_chart(
    alt.Chart(df)
    .mark_bar(orient="horizontal")
    .encode(
        x="units_sold",
        y=alt.Y("item_name").sort("-x"),
    ),
    use_container_width=True,
)
