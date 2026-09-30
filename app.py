import streamlit as st
import sqlite3
import pandas as pd
from datetime import date
from pathlib import Path

# =========================================================
# CONFIG
# =========================================================

st.set_page_config(
    page_title="Activity Tracker",
    page_icon="📝",
    layout="wide"
)

DB_FILE = Path("activity_tracker.db")


# =========================================================
# DATABASE
# =========================================================

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():

    conn = get_connection()
    cursor = conn.cursor()

    # Master kategori
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """)

    # History aktivitas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            activity_date TEXT NOT NULL,
            description TEXT,
            cost REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id)
                REFERENCES categories(id)
        )
    """)

    # Kategori awal
    cursor.execute("""
        SELECT COUNT(*) FROM categories
    """)

    count = cursor.fetchone()[0]

    if count == 0:

        default_categories = [
            "Servis Motor",
            "Servis Mobil",
            "Potong Rambut",
            "Servis Laptop"
        ]

        for category in default_categories:

            cursor.execute("""
                INSERT INTO categories (name)
                VALUES (?)
            """, (category,))

    conn.commit()
    conn.close()


init_database()


# =========================================================
# FUNCTIONS
# =========================================================

def get_categories():

    conn = get_connection()

    df = pd.read_sql_query("""
        SELECT id, name
        FROM categories
        ORDER BY name
    """, conn)

    conn.close()

    return df


def add_category(name):

    conn = get_connection()

    try:

        conn.execute("""
            INSERT INTO categories (name)
            VALUES (?)
        """, (name.strip(),))

        conn.commit()

        return True

    except sqlite3.IntegrityError:

        return False

    finally:

        conn.close()


def add_activity(
    category_id,
    activity_date,
    description,
    cost
):

    conn = get_connection()

    conn.execute("""
        INSERT INTO activities (
            category_id,
            activity_date,
            description,
            cost
        )
        VALUES (?, ?, ?, ?)
    """, (
        category_id,
        activity_date.isoformat(),
        description,
        cost
    ))

    conn.commit()
    conn.close()


def get_history():

    conn = get_connection()

    df = pd.read_sql_query("""
        SELECT
            a.id,
            c.name AS kategori,
            a.activity_date AS tanggal,
            a.description AS deskripsi,
            a.cost AS biaya
        FROM activities a
        JOIN categories c
            ON a.category_id = c.id
        ORDER BY
            a.activity_date DESC,
            a.id DESC
    """, conn)

    conn.close()

    return df


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("📝 Activity Tracker")

page = st.sidebar.radio(
    "Menu",
    [
        "🏠 Dashboard",
        "⚙️ Master Data"
    ]
)


# =========================================================
# PAGE 1
# DASHBOARD / INPUT
# =========================================================

if page == "🏠 Dashboard":

    st.title("🏠 Activity Tracker")

    st.caption(
        "Catat berbagai aktivitas dan pengeluaran Anda."
    )

    # -----------------------------------------------------
    # INPUT
    # -----------------------------------------------------

    st.subheader("➕ Tambah Aktivitas")

    categories = get_categories()

    category_names = categories["name"].tolist()

    col1, col2 = st.columns([4, 1])

    with col1:

        selected_category = st.selectbox(
            "Kategori",
            category_names
        )

    with col2:

        st.write("")
        st.write("")

        if st.button(
            "＋ Kategori",
            use_container_width=True
        ):

            st.session_state["show_add_category"] = True


    # -----------------------------------------------------
    # TAMBAH KATEGORI CEPAT
    # -----------------------------------------------------

    if st.session_state.get(
        "show_add_category",
        False
    ):

        with st.container(border=True):

            st.write("**Tambah Kategori Baru**")

            new_category = st.text_input(
                "Nama Kategori",
                placeholder="Contoh: Servis AC",
                key="new_category"
            )

            col_a, col_b = st.columns(2)

            with col_a:

                if st.button(
                    "💾 Simpan Kategori",
                    type="primary"
                ):

                    if not new_category.strip():

                        st.error(
                            "Nama kategori harus diisi."
                        )

                    else:

                        success = add_category(
                            new_category
                        )

                        if success:

                            st.success(
                                "Kategori berhasil ditambahkan."
                            )

                            st.session_state[
                                "show_add_category"
                            ] = False

                            st.rerun()

                        else:

                            st.error(
                                "Kategori sudah ada."
                            )

            with col_b:

                if st.button("Batal"):

                    st.session_state[
                        "show_add_category"
                    ] = False

                    st.rerun()


    # -----------------------------------------------------
    # FORM AKTIVITAS
    # -----------------------------------------------------

    st.divider()

    activity_date = st.date_input(
        "Tanggal",
        value=date.today()
    )

    description = st.text_area(
        "Deskripsi",
        placeholder=(
            "Contoh: Ganti oli mesin dan oli gardan"
        ),
        height=100
    )

    cost = st.number_input(
        "Biaya",
        min_value=0,
        value=0,
        step=1000,
        format="%d"
    )

    if st.button(
        "💾 Simpan Aktivitas",
        type="primary",
        use_container_width=True
    ):

        if not description.strip():

            st.error(
                "Deskripsi harus diisi."
            )

        else:

            category_id = int(
                categories.loc[
                    categories["name"]
                    == selected_category,
                    "id"
                ].iloc[0]
            )

            add_activity(
                category_id,
                activity_date,
                description.strip(),
                cost
            )

            st.success(
                "Aktivitas berhasil disimpan."
            )

            st.rerun()


    # =====================================================
    # HISTORY
    # =====================================================

    st.divider()

    st.subheader("📋 History")

    history = get_history()

    if history.empty:

        st.info(
            "Belum ada aktivitas."
        )

    else:

        # ---------------------------------------------
        # Filter kategori
        # ---------------------------------------------

        filter_categories = [
            "Semua"
        ] + sorted(
            history["kategori"]
            .unique()
            .tolist()
        )

        filter_category = st.selectbox(
            "Filter Kategori",
            filter_categories
        )

        filtered = history.copy()

        if filter_category != "Semua":

            filtered = filtered[
                filtered["kategori"]
                == filter_category
            ]

        # ---------------------------------------------
        # Format biaya
        # ---------------------------------------------

        display = filtered.copy()

        display["biaya"] = display[
            "biaya"
        ].apply(
            lambda x:
                f"Rp {x:,.0f}"
                .replace(",", ".")
        )

        display = display.rename(
            columns={
                "kategori": "Kategori",
                "tanggal": "Tanggal",
                "deskripsi": "Deskripsi",
                "biaya": "Biaya"
            }
        )

        display = display[
            [
                "Tanggal",
                "Kategori",
                "Deskripsi",
                "Biaya"
            ]
        ]

        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True
        )

        # ---------------------------------------------
        # Total
        # ---------------------------------------------

        total = filtered["biaya"].sum()

        st.metric(
            "Total Biaya",
            f"Rp {total:,.0f}"
            .replace(",", ".")
        )


# =========================================================
# PAGE 2
# MASTER DATA
# =========================================================

elif page == "⚙️ Master Data":

    st.title("⚙️ Master Data")

    st.caption(
        "Pengaturan kategori dan data aplikasi."
    )

    # =====================================================
    # KATEGORI
    # =====================================================

    st.subheader("📂 Kategori")

    categories = get_categories()

    st.dataframe(
        categories.rename(
            columns={
                "id": "ID",
                "name": "Kategori"
            }
        ),
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    st.subheader("➕ Tambah Kategori")

    with st.form("add_category_form"):

        category_name = st.text_input(
            "Nama Kategori",
            placeholder="Contoh: Servis AC"
        )

        submitted = st.form_submit_button(
            "Simpan"
        )

        if submitted:

            if not category_name.strip():

                st.error(
                    "Nama kategori harus diisi."
                )

            else:

                success = add_category(
                    category_name
                )

                if success:

                    st.success(
                        "Kategori berhasil ditambahkan."
                    )

                    st.rerun()

                else:

                    st.error(
                        "Kategori tersebut sudah ada."
                    )

    # =====================================================
    # SETTING
    # =====================================================

    st.divider()

    st.subheader("⚙️ Setting")

    st.info(
        "Pengaturan tambahan dapat ditambahkan "
        "di bagian ini pada pengembangan berikutnya."
    )