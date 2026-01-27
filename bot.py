import streamlit as st
import time
from textblob import TextBlob
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# 1. ---------------- User Authentication ----------------
uid = st.query_params.get("userid")

if not uid:
    st.error("User not authenticated. Please log in through the main application.")
    st.stop()

if not firebase_admin._apps:
    # ------------------------------------------------------------------
    # Ensure you have your service account key file path correct if hosting locally ⬇️
    # cred = credentials.Certificate("service_account.json")
    # firebase_admin.initialize_app(cred)
    # ------------------------------------------------------------------

    # Using Streamlit Secrets for Firebase Initialization
    firebase_secrets = dict(st.secrets["firebase"] )
    firebase_secrets["private_key"] = firebase_secrets["private_key"].replace("\\n", "\n")

    cred = credentials.Certificate(firebase_secrets)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Fetch First Name from Firestore
if "first_name" not in st.session_state:
    try:
        user_doc = db.collection("Users").document(uid).get()
        if user_doc.exists:
            # Safely get firstName or default to "Friend"
            st.session_state.first_name = user_doc.to_dict().get("firstName", "Friend")
        else:
            st.session_state.first_name = "Friend"
    except Exception:
        st.session_state.first_name = "Friend"

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="MindCare AI", page_icon="🧠", layout="centered")

# Custom CSS for UI, Red Quit Button, and Mobile Responsiveness
st.markdown("""
    <style>
    /* Main Chat Bubbles */
    .stChatMessage { border-radius: 15px; margin-bottom: 15px; border: 1px solid #f0f2f6; }
    
    /* General Button Styling */
    .stButton button { 
        width: 100%; 
        border-radius: 10px; 
        height: 3em; 
        background-color: #4CAF50; 
        color: white; 
        border: none;
        transition: 0.3s;
    }
    
    /* FORCE HORIZONTAL BUTTONS ON MOBILE */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 5px !important;
    }
    [data-testid="stHorizontalBlock"] > div {
        flex: 1 1 0% !important;
        min-width: 0 !important;
    }

    /* Red styling for the Quit Button */
    div.stButton > button:first-child[key*="quit"] {
        background-color: #ff4b4b;
        margin-top: 10px;
    }
    
    /* Style for the Sensor Button */
    div.stButton > button[key*="sensor"] {
        background-color: #2196F3;
    }

    /* Adjusting text size for mobile buttons so labels don't clip */
    @media (max-width: 480px) {
        .stButton button {
            font-size: 12px;
            padding: 0px 2px;
            height: 3.5em;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# ---------------- DATA ----------------
k10_questions = [
    "In the last 4 weeks, how often did you feel tired out for no good reason?",
    "How often did you feel nervous?",
    "How often did you feel so nervous that nothing could calm you down?",
    "How often did you feel hopeless?",
    "How often did you feel restless or fidgety?",
    "How often did you feel so restless you could not sit still?",
    "How often did you feel depressed?",
    "How often did you feel that everything was an effort?",
    "How often did you feel so sad that nothing could cheer you up?",
    "How often did you feel worthless?"
]

tier2_data = {
    "PHQ9": {
        "title": "Depression Screening (PHQ-9)",
        "labels": ["Not at all", "Several days", "More than half", "Nearly every day"],
        "questions": [
            "Little interest or pleasure in doing things?",
            "Feeling down, depressed, or hopeless?",
            "Trouble falling or staying asleep, or sleeping too much?",
            "Feeling tired or having little energy?",
            "Poor appetite or overeating?",
            "Feeling bad about yourself — or that you are a failure?",
            "Trouble concentrating on things?",
            "Moving or speaking so slowly that others noticed? Or the opposite?",
            "Thoughts that you would be better off dead, or of hurting yourself?"
        ]
    },
    "GAD7": {
        "title": "Anxiety Screening (GAD-7)",
        "labels": ["Not at all", "Several days", "More than half", "Nearly every day"],
        "questions": [
            "Feeling nervous, anxious, or on edge?",
            "Not being able to stop or control worrying?",
            "Worrying too much about different things?",
            "Trouble relaxing?",
            "Being so restless that it is hard to sit still?",
            "Becoming easily annoyed or irritable?",
            "Feeling afraid as if something awful might happen?"
        ]
    },
    "PSS10": {
        "title": "Perceived Stress Scale (PSS-10)",
        "labels": ["Never", "Almost Never", "Sometimes", "Fairly Often", "Very Often"],
        "questions": [
            "Upset because of something that happened unexpectedly?",
            "Unable to control the important things in your life?",
            "Feeling nervous and 'stressed'?",
            "Confident about handling personal problems?",
            "Feeling that things were going your way?",
            "Could not cope with all the things you had to do?",
            "Able to control irritations in your life?",
            "Feeling that you were on top of things?",
            "Angered by things outside of your control?",
            "Difficulties piling up so high you could not overcome them?"
        ]
    }
}

# ---------------- SESSION STATE ----------------
if "messages" not in st.session_state: st.session_state.messages = []
if "step" not in st.session_state: st.session_state.step = "START"
if "q_idx" not in st.session_state: st.session_state.q_idx = 0
if "k10_score" not in st.session_state: st.session_state.k10_score = 0
if "tier2_scores" not in st.session_state: st.session_state.tier2_scores = {"PHQ9": 0, "GAD7": 0, "PSS10": 0}
if "current_tool" not in st.session_state: st.session_state.current_tool = "PHQ9"
if "pending_bot_responses" not in st.session_state: st.session_state.pending_bot_responses = []

# ---------------- INTENT ENGINE ----------------
def check_intent(user_text):
    text = user_text.lower().strip()
    affirmations = ["yes", "yep", "sure", "okay", "ok", "fine", "let's do it"]
    denials = ["no", "nah", "nope"]
    exit_intents = ["quit", "stop", "exit", "end", "cancel"]
    
    if any(word in text for word in exit_intents): return "EXIT"
    if any(word in text for word in affirmations): return "YES"
    if any(word in text for word in denials): return "NO"
    return "UNKNOWN"

def get_emotional_response(user_text):
    analysis = TextBlob(user_text.lower())
    polarity = analysis.sentiment.polarity
    emotions = {
        "anxious": ["anxious", "worried", "nervous", "panic"],
        "sad": ["sad", "unhappy", "crying"],
        "depressed": ["depressed", "hopeless", "worthless"],
        "happy": ["happy", "great", "wonderful", "good", "fine", "okay"],
        "stressed": ["stressed", "overwhelmed", "tense"]
    }
    for emotion, keywords in emotions.items():
        if any(word in user_text.lower() for word in keywords):
            responses = {
                "anxious": "I can feel the anxiety in your words. It's okay to feel overwhelmed.",
                "sad": "I'm so sorry things feel heavy right now.",
                "depressed": "I hear how much pain you are in. It takes strength to speak up.",
                "happy": "It's wonderful to hear that you're feeling good!",
                "stressed": "Stress can be really tough to manage. I'm here to help you through it."
            }
            return responses[emotion], True
    if polarity < -0.3: return "I can tell things are difficult right now. I'm here for you.", True
    elif polarity > 0.3: return "You seem to be in a positive headspace! That's great.", True
    return "I'm not quite sure I understand. Could you tell me more about your mood?", False

# ---------------- LOGIC HELPERS ----------------
def reset_session():
    for key in list(st.session_state.keys()): del st.session_state[key]
    st.rerun()

def bot_echo(text, delay=0.015):
    with st.chat_message("assistant"):
        container = st.empty()
        full_text = ""
        for char in text:
            full_text += char
            container.markdown(full_text + "▌")
            time.sleep(delay)
        container.markdown(full_text)
    st.session_state.messages.append({"role": "assistant", "content": text})

def handle_input(val, display_question=None, display_answer=None):
    if check_intent(str(val)) == "EXIT":
        st.session_state.pending_bot_responses = ["Session ended. Take care of yourself! ❤️"]
        st.session_state.step = "END"
        return

    if display_question:
        st.session_state.messages.append({"role": "assistant", "content": f"**Question:** {display_question}"})
    
    answer_text = display_answer if display_answer else str(val)
    st.session_state.messages.append({"role": "user", "content": answer_text})
    
    if st.session_state.step == "GREETING":
        resp, relevant = get_emotional_response(str(val))
        if relevant:
            st.session_state.pending_bot_responses = [resp, "Would you like to take a guided screening? (Yes/No)"]
            st.session_state.step = "CONSENT"
        else:
            st.session_state.pending_bot_responses = [resp]

    elif st.session_state.step == "CONSENT":
        intent = check_intent(str(val))
        if intent == "YES":
            st.session_state.pending_bot_responses = ["Excellent. We'll start with the K10 test. Rate from **1 (None)** to **5 (All the time)**."]
            st.session_state.step = "K10"
        elif intent == "NO":
            st.session_state.pending_bot_responses = ["I understand. Come back whenever you're ready! ❤️"]
            st.session_state.step = "END"
        else:
            st.session_state.pending_bot_responses = ["Please say Yes or No to proceed."]

    elif st.session_state.step == "K10":
        st.session_state.k10_score += int(val)
        st.session_state.q_idx += 1
        if st.session_state.q_idx >= 10:
            if st.session_state.k10_score >= 20:
                st.session_state.pending_bot_responses = [f"K10 complete (Score: {st.session_state.k10_score}). Your score suggests distress. Let's proceed to specialized screening."]
                st.session_state.step = "TIER2"
                st.session_state.current_tool = "PHQ9"
                st.session_state.q_idx = 0
            else:
                st.session_state.pending_bot_responses = [f"K10 complete (Score: {st.session_state.k10_score}). Your distress levels appear low!"]
                st.session_state.step = "END"

    elif st.session_state.step == "TIER2":
        tool = st.session_state.current_tool
        st.session_state.tier2_scores[tool] += int(val)
        st.session_state.q_idx += 1
        if st.session_state.q_idx >= len(tier2_data[tool]["questions"]):
            if tool == "PHQ9":
                st.session_state.current_tool = "GAD7"; st.session_state.q_idx = 0
                st.session_state.pending_bot_responses = ["Transitioning to Anxiety screening (GAD-7)..."]
            elif tool == "GAD7":
                st.session_state.current_tool = "PSS10"; st.session_state.q_idx = 0
                st.session_state.pending_bot_responses = ["Finally, starting the Stress Scale (PSS-10)..."]
            else:
                st.session_state.step = "RESULTS"

# ---------------- UI RENDER ----------------
st.title("🧠 MindCare: AI Mental Health Bot")

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if st.session_state.pending_bot_responses:
    resps = st.session_state.pending_bot_responses.copy()
    st.session_state.pending_bot_responses = []
    for r in resps: bot_echo(r)
    st.rerun()

if st.session_state.step == "START":
    name = st.session_state.first_name
    st.session_state.pending_bot_responses = [f"Hello {name}! I'm MindCare. How have you been feeling lately?"]
    st.session_state.step = "GREETING"
    st.rerun()

if st.session_state.step in ["GREETING", "CONSENT"]:
    if prompt := st.chat_input("Type your response..."):
        handle_input(prompt)
        st.rerun()

elif st.session_state.step == "K10":
    current_q = k10_questions[st.session_state.q_idx]
    st.write(f"**K10 Assessment** - Q{st.session_state.q_idx+1}/10")
    st.info(current_q)
    cols = st.columns(5)
    for i in range(1, 6):
        if cols[i-1].button(f"{i}"):
            handle_input(i, display_question=current_q, display_answer=f"Rated: {i}")
            st.rerun()
    if st.button("🚪 End Session", key="quit_k10"):
        handle_input("quit")
        st.rerun()

elif st.session_state.step == "TIER2":
    tool = st.session_state.current_tool
    data = tier2_data[tool]
    current_q = data["questions"][st.session_state.q_idx]
    st.write(f"**{data['title']}** - Q{st.session_state.q_idx+1}/{len(data['questions'])}")
    st.info(current_q)
    cols = st.columns(len(data["labels"]))
    for i in range(len(data['labels'])):
        if cols[i].button(data["labels"][i]):
            handle_input(i, display_question=current_q, display_answer=data["labels"][i])
            st.rerun()
    if st.button("🚪 End Session", key="quit_tier2"):
        handle_input("quit")
        st.rerun()

elif st.session_state.step == "RESULTS":
    phq, gad, pss = st.session_state.tier2_scores['PHQ9'], st.session_state.tier2_scores['GAD7'], st.session_state.tier2_scores['PSS10']
    
    st.write("### 📊 Comprehensive Assessment Summary")
    
    # Create columns for a cleaner layout
    c1, c2, c3 = st.columns(3)
    c1.metric("PHQ-9 (Depression)", phq)
    c2.metric("GAD-7 (Anxiety)", gad)
    c3.metric("PSS-10 (Stress)", pss)

    # Specific Threshold Logic
    distress_types = []
    
    # PHQ-9 Threshold: 10+ indicates Moderate Depression
    if phq >= 10: distress_types.append("Depressive Symptoms")
    
    # GAD-7 Threshold: 10+ indicates Moderate Anxiety
    if gad >= 10: distress_types.append("Anxiety Symptoms")
    
    # PSS-10 Threshold: 14+ indicates Moderate/High Stress
    if pss >= 14: distress_types.append("High Perceived Stress")

    st.divider()

    if distress_types:
        st.warning(f"⚠️ **Clinical Indicator:** Your responses show indicators primarily associated with: **{', '.join(distress_types)}**.")
        
        # Categorical Advice based on the "highest" relative indicator
        if phq >= gad and phq >= pss and phq >= 10:
            st.info("💡 **Observation:** Your results suggest you are currently most prone toward **Depressive patterns**, which may affect your energy and interest levels.")
        elif gad >= phq and gad >= pss and gad >= 10:
            st.info("💡 **Observation:** Your results suggest you are primarily experiencing **Anxiety-driven distress**, characterized by persistent worry or restlessness.")
        elif pss >= 14:
            st.info("💡 **Observation:** You are showing high levels of **Environmental Stress**, suggesting your current life demands may be exceeding your coping resources.")

        st.write("---")
        st.write("### 🩺 Recommended Next Step: Physiological Sensor Testing")
        st.write("""
        Self-reported screenings are a great first step, but they can be subjective. 
        **Sensor Testing** (GSR & ECG) provides objective data by analyzing your Autonomic Nervous System.
        """)
        
        # Instructional diagram placeholder for user understanding
        # 
        
        if st.button("🔗 Proceed to Objective Sensor Assessment", key="sensor_btn"):
            st.success("Module Loading: Calibrating GSR/ECG sensors...")
            # Logic to trigger hardware integration or external dashboard
            
    else:
        st.success("✅ **Wellness Check:** Your scores do not meet the clinical threshold for significant distress at this time. Continue your current wellness practices!")

    if st.button("🔄 Restart Assessment"): reset_session()