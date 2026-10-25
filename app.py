"""AI Resume Tailor — Streamlit application."""

import os
from collections.abc import Callable
from datetime import date
from typing import Any

import anthropic
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.ai_engine import (  # noqa: E402
    AIError,
    analyze_job_description,
    generate_cover_letter,
    generate_tailored_resume,
    keyword_match_report,
    score_fit,
)
from src.cover_letter import generate_cover_letter_docx  # noqa: E402
from src.job_tracker import (  # noqa: E402
    STATUSES,
    add_application,
    delete_application,
    export_csv,
    get_all_applications,
    init_db,
    update_status,
)
from src.resume_generator import generate_docx, generate_pdf  # noqa: E402
from src.resume_parser import parse_resume  # noqa: E402
from src.truthcheck import unsupported_numbers  # noqa: E402
from src.utils import fetch_job_description  # noqa: E402


def run_ai(fn: Callable[..., Any], *args: Any) -> Any:
    """Call Claude and show a plain error instead of a stack trace."""
    try:
        return fn(*args)
    except AIError as exc:
        st.error(str(exc))
    except anthropic.AuthenticationError:
        st.error("Your Anthropic API key was rejected. Check ANTHROPIC_API_KEY in your .env file.")
    except anthropic.RateLimitError:
        st.error("Claude is rate-limiting this key. Wait a minute and try again.")
    except anthropic.APIConnectionError:
        st.error("Could not reach Claude. Check your internet connection.")
    except anthropic.APIStatusError as exc:
        st.error(f"Claude returned an error ({exc.status_code}). Please try again.")
    return None


def warn_unsupported(original: str, generated: str, profile: dict[str, str]) -> None:
    """Point out numbers Claude may have invented, before the user sends anything."""
    today = date.today().strftime("%B %d %Y %m/%d/%Y")
    known = " ".join([original, today, *profile.values()])
    invented = unsupported_numbers(known, generated)
    if invented:
        st.warning(
            "Check these numbers before you send. They are not in your original resume: "
            + ", ".join(invented)
        )


# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="AI Resume Tailor",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Sidebar — User profile
# ---------------------------------------------------------------------------

st.sidebar.title("👤 Your Profile")
user_name = st.sidebar.text_input("Full Name", key="user_name")
user_email = st.sidebar.text_input("Email", key="user_email")
user_phone = st.sidebar.text_input("Phone", key="user_phone")
user_linkedin = st.sidebar.text_input("LinkedIn URL", key="user_linkedin")

user_profile = {
    "name": user_name,
    "email": user_email,
    "phone": user_phone,
    "linkedin": user_linkedin,
}

st.sidebar.divider()
st.sidebar.caption("Built with Claude API & Streamlit")

# ---------------------------------------------------------------------------
# Main content — Tabs
# ---------------------------------------------------------------------------

st.title("📄 AI Resume Tailor")
if not os.environ.get("ANTHROPIC_API_KEY"):
    st.warning(
        "No ANTHROPIC_API_KEY found. Copy .env.example to .env and add your key, "
        "then restart the app. Analysis and generation will not work until then."
    )
st.caption("Tailor your resume and cover letter for any job — powered by Claude AI")

tab_input, tab_analysis, tab_resume, tab_cover, tab_tracker = st.tabs(
    ["📝 Input", "🔍 Analysis", "📄 Tailored Resume", "✉️ Cover Letter", "📊 Job Tracker"]
)

# ======================== TAB 1: INPUT ====================================

with tab_input:
    st.header("Job Description")

    input_method = st.radio(
        "How would you like to provide the job description?",
        ["Paste text", "Fetch from URL"],
        horizontal=True,
    )

    if input_method == "Paste text":
        job_desc = st.text_area(
            "Paste the job description below",
            height=300,
            placeholder="Paste the full job description here...",
        )
    else:
        job_url = st.text_input(
            "Job posting URL",
            placeholder="https://example.com/jobs/software-engineer",
        )
        job_desc = ""
        if job_url and st.button("Fetch Job Description"):
            with st.spinner("Fetching job posting..."):
                try:
                    job_desc = fetch_job_description(job_url)
                    st.session_state["job_desc_fetched"] = job_desc
                    st.success("Job description fetched!")
                except ValueError as exc:
                    st.error(str(exc))

        if "job_desc_fetched" in st.session_state:
            job_desc = st.session_state["job_desc_fetched"]
            st.text_area(
                "Fetched job description (editable)",
                value=job_desc,
                height=300,
                key="fetched_jd_display",
            )

    st.divider()

    st.header("Your Base Resume")
    uploaded_file = st.file_uploader(
        "Upload your resume",
        type=["pdf", "docx", "txt"],
        help="Supported formats: .pdf, .docx, .txt",
    )

    resume_text = ""
    if uploaded_file:
        with st.spinner("Parsing resume..."):
            try:
                resume_text = parse_resume(uploaded_file)
                st.session_state["resume_text"] = resume_text
                st.success(f"Parsed {uploaded_file.name} ({len(resume_text):,} characters)")
                with st.expander("Preview parsed resume"):
                    st.text(resume_text)
            except ValueError as exc:
                st.error(str(exc))

    # Persist across tabs
    if job_desc:
        st.session_state["job_desc"] = job_desc
    if resume_text:
        st.session_state["resume_text"] = resume_text


# ======================== TAB 2: ANALYSIS =================================

with tab_analysis:
    st.header("AI Job Analysis")

    jd = st.session_state.get("job_desc", "")
    rt = st.session_state.get("resume_text", "")

    if not jd:
        st.info("Paste or fetch a job description in the Input tab first.")
    else:
        # --- Job Description Analysis ---
        if st.button("Analyze Job Description", key="btn_analyze_jd"):
            with st.spinner("Analyzing job description with Claude..."):
                analysis = run_ai(analyze_job_description, jd)
                if analysis is not None:
                    st.session_state["jd_analysis"] = analysis

        if "jd_analysis" in st.session_state:
            a = st.session_state["jd_analysis"]
            if "error" not in a:
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader(f"🏢 {a.get('company', 'N/A')} — {a.get('title', 'N/A')}")
                    st.write(f"**Experience Level:** {a.get('experience_level', 'N/A')}")
                    st.write(a.get("summary", ""))

                    st.markdown("**Key Requirements:**")
                    for r in a.get("requirements", []):
                        st.markdown(f"- {r}")

                with col2:
                    st.markdown("**Required Skills:**")
                    for s in a.get("skills", []):
                        st.markdown(f"- {s}")

                    st.markdown("**ATS Keywords:**")
                    keywords = a.get("keywords", [])
                    if keywords:
                        st.write(", ".join(f"`{k}`" for k in keywords))
            else:
                st.error(a.get("error", "Unknown error"))

        st.divider()

        # --- Fit Score ---
        if not rt:
            st.info("Upload a resume in the Input tab to enable fit scoring.")
        else:
            if st.button("Score Resume Fit", key="btn_score"):
                with st.spinner("Scoring alignment with Claude..."):
                    result = run_ai(score_fit, jd, rt)
                    if result is not None:
                        st.session_state["fit_score"] = result

            if "fit_score" in st.session_state:
                fs = st.session_state["fit_score"]
                if "error" not in fs:
                    score = fs.get("score", 0)
                    color = "green" if score >= 70 else "orange" if score >= 40 else "red"
                    st.markdown(f"### Alignment Score: :{color}[{score}/100]")
                    st.write(fs.get("explanation", ""))

                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**✅ Strengths:**")
                        for s in fs.get("strengths", []):
                            st.markdown(f"- {s}")
                    with col2:
                        st.markdown("**⚠️ Gaps:**")
                        for g in fs.get("gaps", []):
                            st.markdown(f"- {g}")

                    st.markdown("**💡 Suggestions:**")
                    for s in fs.get("suggestions", []):
                        st.markdown(f"- {s}")

            st.divider()

            # --- Keyword Report ---
            if st.button("Keyword Match Report", key="btn_keywords"):
                with st.spinner("Generating keyword report..."):
                    report = run_ai(keyword_match_report, jd, rt)
                    if report is not None:
                        st.session_state["keyword_report"] = report

            if "keyword_report" in st.session_state:
                kr = st.session_state["keyword_report"]
                if "error" not in kr:
                    pct = kr.get("match_percentage", 0)
                    color = "green" if pct >= 70 else "orange" if pct >= 40 else "red"
                    st.markdown(f"### Keyword Match: :{color}[{pct}%]")

                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**✅ Matched Keywords:**")
                        matched = kr.get("matched", [])
                        if matched:
                            st.write(", ".join(f"`{k}`" for k in matched))
                    with col2:
                        st.markdown("**❌ Missing Keywords:**")
                        missing = kr.get("missing", [])
                        if missing:
                            st.write(", ".join(f"`{k}`" for k in missing))


# ======================== TAB 3: TAILORED RESUME ==========================

with tab_resume:
    st.header("Tailored Resume Generator")

    jd = st.session_state.get("job_desc", "")
    rt = st.session_state.get("resume_text", "")

    if not jd or not rt:
        st.info("Provide a job description and upload your resume in the Input tab first.")
    else:
        if st.button("Generate Tailored Resume", key="btn_gen_resume"):
            if not user_name:
                st.warning("Fill in your profile in the sidebar for best results.")
            with st.spinner("Generating tailored resume with Claude... this may take a moment."):
                tailored = run_ai(generate_tailored_resume, jd, rt, user_profile)
                if tailored is not None:
                    st.session_state["tailored_resume"] = tailored

        if "tailored_resume" in st.session_state:
            tailored = st.session_state["tailored_resume"]
            warn_unsupported(rt, tailored, user_profile)
            st.text_area(
                "Tailored Resume (editable)", value=tailored, height=500, key="resume_edit"
            )

            # Use the edited version for downloads
            final_resume = st.session_state.get("resume_edit", tailored)

            col1, col2 = st.columns(2)
            with col1:
                docx_bytes = generate_docx(final_resume)
                st.download_button(
                    "⬇️ Download .docx",
                    data=docx_bytes,
                    file_name="tailored_resume.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            with col2:
                pdf_bytes = generate_pdf(final_resume)
                st.download_button(
                    "⬇️ Download .pdf",
                    data=pdf_bytes,
                    file_name="tailored_resume.pdf",
                    mime="application/pdf",
                )


# ======================== TAB 4: COVER LETTER =============================

with tab_cover:
    st.header("Cover Letter Generator")

    jd = st.session_state.get("job_desc", "")
    rt = st.session_state.get("resume_text", "")

    if not jd or not rt:
        st.info("Provide a job description and upload your resume in the Input tab first.")
    else:
        if st.button("Generate Cover Letter", key="btn_gen_cover"):
            if not user_name:
                st.warning("Fill in your profile in the sidebar for best results.")
            with st.spinner("Generating cover letter with Claude..."):
                cl = run_ai(generate_cover_letter, jd, rt, user_profile)
                if cl is not None:
                    st.session_state["cover_letter"] = cl

        if "cover_letter" in st.session_state:
            cl = st.session_state["cover_letter"]
            warn_unsupported(rt, cl, user_profile)
            st.text_area("Cover Letter (editable)", value=cl, height=400, key="cover_edit")

            final_cl = st.session_state.get("cover_edit", cl)

            docx_bytes = generate_cover_letter_docx(final_cl, user_profile)
            st.download_button(
                "⬇️ Download Cover Letter .docx",
                data=docx_bytes,
                file_name="cover_letter.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )


# ======================== TAB 5: JOB TRACKER ==============================

with tab_tracker:
    st.header("Job Application Tracker")

    init_db()

    # --- Add new application ---
    with st.expander("➕ Add New Application", expanded=False), st.form("add_app_form"):
        col1, col2 = st.columns(2)
        with col1:
            new_company = st.text_input("Company")
            new_title = st.text_input("Job Title")
            new_status = st.selectbox("Status", STATUSES)
        with col2:
            new_url = st.text_input("Job URL")
            new_date = st.date_input("Applied Date")
            new_notes = st.text_area("Notes", height=80)

        if st.form_submit_button("Add Application"):
            if new_company and new_title:
                add_application(
                    company=new_company,
                    title=new_title,
                    status=new_status,
                    url=new_url,
                    notes=new_notes,
                    applied_date=str(new_date),
                )
                st.success(f"Added {new_title} at {new_company}")
                st.rerun()
            else:
                st.warning("Company and Job Title are required.")

    # --- Display applications ---
    apps = get_all_applications()

    if apps:
        st.write(f"**{len(apps)} application(s) tracked**")

        # Status summary
        status_counts = {}
        for app in apps:
            s = app["status"]
            status_counts[s] = status_counts.get(s, 0) + 1
        cols = st.columns(min(len(status_counts), 4))
        for i, (status, count) in enumerate(status_counts.items()):
            cols[i % len(cols)].metric(status, count)

        st.divider()

        # Application list
        for app in apps:
            with st.container():
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.markdown(f"**{app['title']}** at {app['company']}")
                    if app.get("url"):
                        st.caption(app["url"])
                with col2:
                    new_stat = st.selectbox(
                        "Status",
                        STATUSES,
                        index=STATUSES.index(app["status"]) if app["status"] in STATUSES else 0,
                        key=f"status_{app['id']}",
                    )
                    if new_stat != app["status"]:
                        update_status(app["id"], new_stat)
                        st.rerun()
                with col3:
                    if st.button("🗑️", key=f"del_{app['id']}"):
                        delete_application(app["id"])
                        st.rerun()
                if app.get("notes"):
                    st.caption(f"Notes: {app['notes']}")
                st.divider()

        # Export
        csv_data = export_csv()
        if csv_data:
            st.download_button(
                "⬇️ Export to CSV",
                data=csv_data,
                file_name="job_applications.csv",
                mime="text/csv",
            )
    else:
        st.info("No applications tracked yet. Add one above!")
