import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

st.set_page_config(
    page_title="B.Pharm Rank List Generator",
    layout="wide"
)

st.title("B.Pharm Rank List Generator")

st.markdown("""
### Upload Files

1. Normalized Score CSV
2. Candidates CSV
3. CBT Responses CSV

Tie Breaking Order:

1. Normalized Score
2. Chemistry Score (Pre-Normalized)
3. Physics Score (Pre-Normalized)
4. Chemistry Correct Responses
5. Physics Correct Responses
6. Older Candidate (DOB)
""")

# ======================================================
# FILE UPLOADS
# ======================================================

norm_file = st.file_uploader(
    "Upload Normalized Score CSV",
    type="csv"
)

cand_file = st.file_uploader(
    "Upload Candidates CSV",
    type="csv"
)

cbt_file = st.file_uploader(
    "Upload CBT Responses CSV",
    type="csv"
)

# ======================================================
# PROCESS
# ======================================================

if norm_file and cand_file and cbt_file:

    try:

        # --------------------------------------------------
        # READ FILES
        # --------------------------------------------------

        norm_df = pd.read_csv(norm_file)
        cand_df = pd.read_csv(cand_file)
        cbt_df = pd.read_csv(cbt_file)

        st.success("All files loaded successfully")

        # --------------------------------------------------
        # CLEAN COLUMN NAMES
        # --------------------------------------------------

        norm_df.columns = norm_df.columns.str.strip()
        cand_df.columns = cand_df.columns.str.strip()
        cbt_df.columns = cbt_df.columns.str.strip()

        # --------------------------------------------------
        # VALIDATE REQUIRED COLUMNS
        # --------------------------------------------------

        required_norm = [
            "RollNo",
            "Norm_Score"
        ]

        required_cand = [
            "ApplNo",
            "RollNo",
            "Name",
            "DOB",
            "BPharm"
        ]

        required_cbt = [
            "RollNo",
            "QNo",
            "Mark"
        ]

        missing_cols = []

        for col in required_norm:
            if col not in norm_df.columns:
                missing_cols.append(f"Normalization : {col}")

        for col in required_cand:
            if col not in cand_df.columns:
                missing_cols.append(f"Candidates : {col}")

        for col in required_cbt:
            if col not in cbt_df.columns:
                missing_cols.append(f"CBT : {col}")

        if missing_cols:
            st.error("Missing Columns")
            st.write(missing_cols)
            st.stop()

        # --------------------------------------------------
        # DATA TYPES
        # --------------------------------------------------

        norm_df["RollNo"] = pd.to_numeric(
            norm_df["RollNo"],
            errors="coerce"
        )

        cand_df["RollNo"] = pd.to_numeric(
            cand_df["RollNo"],
            errors="coerce"
        )

        cbt_df["RollNo"] = pd.to_numeric(
            cbt_df["RollNo"],
            errors="coerce"
        )

        cbt_df["QNo"] = pd.to_numeric(
            cbt_df["QNo"],
            errors="coerce"
        )

        cbt_df["Mark"] = pd.to_numeric(
            cbt_df["Mark"],
            errors="coerce"
        ).fillna(0)

        cand_df["DOB_Parsed"] = pd.to_datetime(
            cand_df["DOB"],
            errors="coerce"
        )

        # ==================================================
        # VALIDATIONS
        # ==================================================

        validation_results = {}

        # --------------------------------------------------
        # Duplicate Candidate Roll Numbers
        # --------------------------------------------------

        dup_rolls = cand_df[
            cand_df.duplicated(
                subset=["RollNo"],
                keep=False
            )
        ]

        validation_results[
            "Duplicate Roll Numbers"
        ] = dup_rolls

        # --------------------------------------------------
        # Missing Normalized Scores
        # --------------------------------------------------

        missing_norm = cand_df[
            ~cand_df["RollNo"].isin(
                norm_df["RollNo"]
            )
        ]

        validation_results[
            "Missing Normalized Scores"
        ] = missing_norm

        # --------------------------------------------------
        # Missing CBT Responses
        # --------------------------------------------------

        missing_cbt = cand_df[
            ~cand_df["RollNo"].isin(
                cbt_df["RollNo"]
            )
        ]

        validation_results[
            "Missing CBT Responses"
        ] = missing_cbt

        # --------------------------------------------------
        # Invalid DOB
        # --------------------------------------------------

        invalid_dob = cand_df[
            cand_df["DOB_Parsed"].isna()
        ]

        validation_results[
            "Invalid DOB"
        ] = invalid_dob

        # --------------------------------------------------
        # Not Opted B.Pharm
        # --------------------------------------------------

        not_opted = cand_df[
            cand_df["BPharm"].fillna("").str.upper() != "Y"
        ]

        validation_results[
            "Not Opted B.Pharm"
        ] = not_opted

        # --------------------------------------------------
        # Duplicate Normalization Records
        # --------------------------------------------------

        dup_norm = norm_df[
            norm_df.duplicated(
                subset=["RollNo"],
                keep=False
            )
        ]

        validation_results[
            "Duplicate Normalization Records"
        ] = dup_norm

        # --------------------------------------------------
        # Negative Normalized Score
        # --------------------------------------------------

        negative_norm = norm_df[
            norm_df["Norm_Score"] < 0
        ]

        validation_results[
            "Negative Normalized Scores"
        ] = negative_norm

        # ==================================================
        # VALIDATION SUMMARY
        # ==================================================

        st.header("Validation Summary")

        summary = []

        for k, v in validation_results.items():

            summary.append({
                "Validation": k,
                "Count": len(v)
            })

        summary_df = pd.DataFrame(summary)

        st.dataframe(
            summary_df,
            use_container_width=True
        )

        # ==================================================
        # EXCEPTION REPORTS
        # ==================================================

        with st.expander(
            "View Validation Errors"
        ):

            for k, v in validation_results.items():

                if len(v) > 0:

                    st.subheader(
                        f"{k} ({len(v)})"
                    )

                    st.dataframe(
                        v,
                        use_container_width=True
                    )

                    st.download_button(
                        label=f"Download {k}",
                        data=v.to_csv(
                            index=False
                        ),
                        file_name=f"{k}.csv",
                        mime="text/csv",
                        key=k
                    )

        # ==================================================
        # ELIGIBLE CANDIDATES
        # ==================================================

        eligible_df = cand_df.copy()

        eligible_df = eligible_df[
            eligible_df["BPharm"].fillna("").str.upper() == "Y"
        ]

        eligible_df = eligible_df[
            eligible_df["DOB_Parsed"].notna()
        ]

        eligible_df = eligible_df[
            eligible_df["RollNo"].isin(
                norm_df["RollNo"]
            )
        ]

        eligible_df = eligible_df[
            eligible_df["RollNo"].isin(
                cbt_df["RollNo"]
            )
        ]

        eligible_df = eligible_df[
            ~eligible_df["RollNo"].isin(
                dup_rolls["RollNo"]
            )
        ]

        # ==================================================
        # CHEMISTRY & PHYSICS
        # ==================================================

        chemistry_df = cbt_df[
            cbt_df["QNo"] <= 45
        ]

        physics_df = cbt_df[
            cbt_df["QNo"] > 45
        ]

        chemistry_stats = (
            chemistry_df
            .groupby("RollNo")
            .agg(
                Chem_Score=("Mark", "sum"),
                Chem_Correct=(
                    "Mark",
                    lambda x: (x == 4).sum()
                )
            )
            .reset_index()
        )

        physics_stats = (
            physics_df
            .groupby("RollNo")
            .agg(
                Phy_Score=("Mark", "sum"),
                Phy_Correct=(
                    "Mark",
                    lambda x: (x == 4).sum()
                )
            )
            .reset_index()
        )

        # ==================================================
        # MERGE DATA
        # ==================================================

        rank_df = (
            eligible_df
            .merge(
                norm_df[
                    ["RollNo", "Norm_Score"]
                ],
                on="RollNo",
                how="inner"
            )
            .merge(
                chemistry_stats,
                on="RollNo",
                how="left"
            )
            .merge(
                physics_stats,
                on="RollNo",
                how="left"
            )
        )

        # Numeric columns only
        numeric_cols = [
            "Norm_Score",
            "Chem_Score",
            "Phy_Score",
            "Chem_Correct",
            "Phy_Correct"
        ]
        
        for col in numeric_cols:
            if col in rank_df.columns:
                rank_df[col] = rank_df[col].fillna(0)

        # ==================================================
        # SORTING AS PER PROSPECTUS
        # ==================================================

        rank_df = rank_df.sort_values(
            by=[
                "Norm_Score",
                "Chem_Score",
                "Phy_Score",
                "Chem_Correct",
                "Phy_Correct",
                "DOB_Parsed"
            ],
            ascending=[
                False,
                False,
                False,
                False,
                False,
                True
            ]
        )

        # ==================================================
        # GENERATE BRANK
        # ==================================================

        rank_df["BRank"] = np.arange(
            1,
            len(rank_df) + 1
        )

        # ==================================================
        # DISPLAY
        # ==================================================

        st.header("Rank List")

        final_columns = [
            "BRank",
            "ApplNo",
            "RollNo",
            "Name",
            "DOB",
            "Norm_Score",
            "Chem_Score",
            "Phy_Score",
            "Chem_Correct",
            "Phy_Correct"
        ]

        st.dataframe(
            rank_df[final_columns],
            use_container_width=True,
            height=600
        )

        # ==================================================
        # STATISTICS
        # ==================================================

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Total Candidates",
            len(cand_df)
        )

        col2.metric(
            "Eligible Candidates",
            len(rank_df)
        )

        col3.metric(
            "Rejected Candidates",
            len(cand_df) - len(rank_df)
        )

        # ==================================================
        # DOWNLOAD
        # ==================================================

        st.download_button(
            label="Download B.Pharm Rank List",
            data=rank_df[
                final_columns
            ].to_csv(index=False),
            file_name="BPHARM_RANKLIST.csv",
            mime="text/csv"
        )

        # ==================================================
        # SQL UPDATE FILE
        # ==================================================

        sql_df = rank_df[
            ["ApplNo", "BRank"]
        ]

        sql_lines = []

        for _, row in sql_df.iterrows():

            sql_lines.append(
                f"UPDATE candidates "
                f"SET BRank={int(row['BRank'])} "
                f"WHERE ApplNo='{row['ApplNo']}';"
            )

        sql_text = "\n".join(sql_lines)

        st.download_button(
            label="Download BRank Update SQL",
            data=sql_text,
            file_name="Update_BRank.sql",
            mime="text/plain"
        )

    except Exception as e:

        st.error(str(e))
