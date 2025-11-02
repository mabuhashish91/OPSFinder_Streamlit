# streamlit_app.py
import io
import csv
import pandas as pd
import streamlit as st
from ops import extract_single

# -------------------- Page --------------------
st.set_page_config(page_title="OPS Extractor", layout="wide")
st.title("OPS Extractor (gesund.bund.de)")

# -------------------- Helpers --------------------
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

# -------------------- UI (improved, no cache/limits) --------------------
with st.sidebar:
    st.subheader("About")
    st.write(
        "This app fetches official OPS code descriptions from gesund.bund.de.\n\n"
        "• Single: type a code and press **Enter** or click **Extract**.\n"
        "• Batch: upload a CSV (first column = codes)."
    )
    st.caption("Tip: Example code: `5-787.3M`")

tab_single, tab_batch = st.tabs(["🔎 Single search", "📦 Batch (CSV)"])

# ---------- Single (Enter submits via form) ----------
with tab_single:
    st.subheader("Single Search")

    # Card-like container
    with st.container():
        with st.form("single_search_form", clear_on_submit=False):
            c1, c2 = st.columns([3, 1])
            with c1:
                code = st.text_input("OPS-Code", placeholder="e.g. 5-787.3M")
            with c2:
                st.write("")
                go = st.form_submit_button("Extract", type="primary", use_container_width=True)

    if go and code.strip():
        with st.status("Fetching data from gesund.bund.de …", expanded=False) as status:
            result = extract_single(code.strip())
            status.update(label="Fetched", state="complete", expanded=False)

        st.divider()

        # 2-column result "card"
        left, right = st.columns([2, 1], vertical_alignment="top")
        with left:
            render_block(result)
        with right:
            df = results_to_df([result])
            csv_buf = io.StringIO()
            df.to_csv(csv_buf, index=False)
            st.download_button(
                "⬇️ Export as CSV",
                csv_buf.getvalue().encode("utf-8"),
                file_name="ops_export.csv",
                mime="text/csv",
                use_container_width=True,
            )
            # Nicely formatted one-block output for copy
            st.caption("Formatted block")
            st.code(
                f"**{df.iloc[0,0]}**\n{df.iloc[0,1]}\n{df.iloc[0,2]}\n{df.iloc[0,3]}",
                language=None,
            )

# ---------- Batch (sequential with progress bar) ----------
with tab_batch:
    st.subheader("Batch Extraction")
    with st.expander("CSV format", expanded=False):
        st.write(
            "Upload a CSV where the **first column** contains OPS codes.\n"
            "A header named `Code` is optional."
        )

    up = st.file_uploader("Upload CSV", type=["csv"])
    run = st.button("Run batch extraction", type="primary")

    if run:
        if up is None:
            st.warning("Please upload a CSV file first.")
        else:
            # Read codes
            text = up.getvalue().decode("utf-8", errors="replace")
            reader = csv.reader(io.StringIO(text))
            codes = [row[0].strip() for row in reader if row and row[0].strip()]
            # Drop header if present
            if codes and codes[0].lower() == "code":
                codes = codes[1:]
            # De-duplicate but keep order
            seen = set()
            unique_codes = []
            for c in codes:
                if c not in seen:
                    unique_codes.append(c)
                    seen.add(c)

            if not unique_codes:
                st.warning("No valid OPS codes found.")
            else:
                total = len(unique_codes)
                st.info(f"Processing **{total}** codes…")

                progress = st.progress(0)
                status = st.empty()
                results = []

                for i, c in enumerate(unique_codes, start=1):
                    r = extract_single(c)
                    results.append(r)
                    progress.progress(i / total)
                    status.write(f"Processed {i}/{total} — {c}")

                st.success("✅ Batch completed")
                st.divider()

                # Table + download
                df = results_to_df(results)
                st.dataframe(df, use_container_width=True)

                csv_buf = io.StringIO()
                df.to_csv(csv_buf, index=False)
                st.download_button(
                    "⬇️ Export all as CSV",
                    csv_buf.getvalue().encode("utf-8"),
                    file_name="ops_batch_export.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

                # Readable text block
                st.subheader("Formatted text output")
                lines = []
                for r in results:
                    if r.get("error"):
                        lines.append(f"**{r['Code']}**\n❌ Error: {r['error']}\n")
                    else:
                        lines.append(
                            f"**{r['Code']}**\n{r['Description'] or '(no description found)'}\n"
                            f"{r['Zusatzkennzeichen'] or '(none listed)'}\n{r['DirectLink']}\n"
                        )
                st.text_area("Output", value="".join(lines).strip(), height=300)