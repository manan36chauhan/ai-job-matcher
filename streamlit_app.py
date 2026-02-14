import streamlit as st
import requests

API = "http://127.0.0.1:8000"
st.caption(f"API: {API}")
if st.button("Check API /health"):
    rr = requests.get(f"{API}/health")
    st.write("Status:", rr.status_code)
    try:
        st.json(rr.json())
    except Exception:
        st.text(rr.text[:2000])

st.title("Job Matcher")

st.header("1) Create Candidate")
name = st.text_input("Name", "Manan")
location_pref = st.text_input("Preferred location", "Berlin")
profile_text = st.text_area("Profile / CV text", height=200)

if st.button("Create candidate"):
    r = requests.post(f"{API}/candidates", json={
        "name": name,
        "profile_text": profile_text,
        "location_pref": location_pref
    })
    st.write("Status:", r.status_code)
    try:
        st.json(r.json())
    except Exception:
        st.text(r.text[:2000])


st.header("2) Import Jobs CSV")
csv_file = st.file_uploader("Upload jobs.csv", type=["csv"])
if st.button("Import CSV") and csv_file:
    files = {"file": (csv_file.name, csv_file.getvalue(), "text/csv")}
    r = requests.post(f"{API}/jobs/import_csv", files=files)
    st.write("Status:", r.status_code)
    try:
        st.json(r.json())
    except Exception:
        st.text(r.text[:2000])


st.header("3) Match")
candidate_id = st.number_input("Candidate ID", min_value=1, value=1)
top_k = st.slider("Top K", 1, 20, 10)

if st.button("Run match"):
    r = requests.post(f"{API}/match/{candidate_id}", params={"top_k": top_k})
    st.write(r.status_code)
    data = r.json()
    for item in data.get("results", []):
        st.subheader(f"{item['title']} — {item['score']}")
        st.caption(item["company"] + " | " + item["location"])
        st.write(item["reasons"])
        st.link_button("Open job", item["url"])
