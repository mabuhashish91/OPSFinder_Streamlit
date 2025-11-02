# streamlit_app.py
import io
import csv
import pandas as pd
import streamlit as st
from ops import extract_single

st.set_page_config(page_title="OPS Finder", layout="wide")
st.title("OPS Finder (gesund.bund.de)")

tab_single, tab_batch = st.tabs(["🔎 Single search", "📦 Batch (CSV)"])

# ---------- Helper functions ----------

def render_block(r):
    if r.get("error"):
        st.markdown(f"**{r['Code']}**  \n❌ Error: {r['error']}")
    else:
        st.markdown(
            f"**{r['Code']}**  \n{r['Description'] or '(no description found)'}  \n"
            f"{r['Zusatzkennzeichen'] or '(none listed)'}  \n"
            f"[🔗 Direct link]({r['DirectLink']})"
        )

def results_to_df(results):
    rows = []
    for r in results:
        if r.get("error"):
            rows.append([r["Code"], f"ERROR: {r['error']}", "", ""])
        else:
            rows.append([r["Code"], r["Description"], r["Zusatzkennzeichen"], r["DirectLink"]])
    return pd.DataFrame(rows, columns=["Code", "Description", "Zusatzkennzeichen", "DirectLink"])

# ---------- Single Code Tab ----------

# --- Single Code Tab (press Enter submits) ---
with tab_single:
    with st.form("single_search_form", clear_on_submit=False):
        col1, col2 = st.columns([2, 1])
        with col1:
            code = st.text_input("OPS-Code", placeholder="e.g. 5-787.3M")
        with col2:
            st.write("")
            go = st.form_submit_button("Extract", type="primary", use_container_width=True)

    if go and code.strip():
        st.info("Fetching data from gesund.bund.de ... ⏳")
        result = extract_single(code.strip())
        st.success("Done ✅")
        st.divider()

        render_block(result)
        df = results_to_df([result])

        csv_buf = io.StringIO()
        df.to_csv(csv_buf, index=False)
        st.download_button(
            "⬇️ Export as CSV",
            csv_buf.getvalue().encode("utf-8"),
            file_name="ops_export.csv",
            mime="text/csv",
        )

# ---------- Batch Tab with Progress Bar ----------

with tab_batch:
    up = st.file_uploader(
        "Upload CSV (first column = OPS codes, optional header 'Code')",
        type=["csv"],
    )
    run = st.button("Run batch extraction 🏃‍♂️")

    if run:
        if up is None:
            st.warning("⚠️ Please upload a CSV file first.")
        else:
            # read CSV
            text = up.getvalue().decode("utf-8", errors="replace")
            reader = csv.reader(io.StringIO(text))
            codes = [
                row[0].strip()
                for row in reader
                if row and row[0].strip() and row[0].strip().lower() != "code"
            ]

            if not codes:
                st.warning("No valid OPS codes found in CSV.")
            else:
                total = len(codes)
                st.info(f"Processing **{total} codes** ... please wait.")

                # setup progress elements
                progress_bar = st.progress(0)
                status = st.empty()
                results = []

                # run extraction with progress
                for i, code in enumerate(codes, start=1):
                    result = extract_single(code)
                    results.append(result)
                    progress = i / total
                    progress_bar.progress(progress)
                    status.text(f"Processed {i}/{total} ({progress*100:.1f}%) — {code}")

                st.success("✅ Batch completed successfully!")
                st.divider()

                # results display
                df = results_to_df(results)
                st.dataframe(df, use_container_width=True)

                # readable text version
                st.subheader("Formatted text output")
                txt_lines = []
                for r in results:
                    if r.get("error"):
                        txt_lines.append(f"**{r['Code']}**\n❌ Error: {r['error']}\n")
                    else:
                        txt_lines.append(
                            f"**{r['Code']}**\n{r['Description'] or '(no description found)'}\n"
                            f"{r['Zusatzkennzeichen'] or '(none listed)'}\n{r['DirectLink']}\n"
                        )
                st.text_area("Output", value="\n".join(txt_lines).strip(), height=300)

                # download
                csv_buf = io.StringIO()
                df.to_csv(csv_buf, index=False)
                st.download_button(
                    "⬇️ Export all as CSV",
                    csv_buf.getvalue().encode("utf-8"),
                    file_name="ops_batch_export.csv",
                    mime="text/csv",
                )