import streamlit as st
import time
from textblob import TextBlob

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="MindCare AI", page_icon="🧠", layout="centered")

# Custom CSS
st.markdown("""
    <style>
    .stChatMessage { border-radius: 15px; margin-bottom: 15px; border: 1px solid #f0f2f6; }
    .stButton button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #4CAF50; color: white; }
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

# ---------------- EMOTION ENGINE ----------------
def get_emotional_response(user_text):
    analysis = TextBlob(user_text.lower())
    polarity = analysis.sentiment.polarity
    
    emotions = {
        "anxious": ["anxious", "worried", "nervous", "panic", "scared", "fear", "tension"],
        "sad": ["sad", "unhappy", "crying", "heartbroken", "gloomy"],
        "depressed": ["depressed", "hopeless", "worthless", "empty", "no point", "miserable", "lonely"],
        "angry": ["angry", "furious", "annoyed", "frustrated", "mad", "hate"],
        "tired": ["tired", "exhausted", "burnt out", "no energy", "drained"],
        "happy": ["happy", "great", "wonderful", "good", "excited", "blessed", "amazing", "well", "fine", "okay"]
    }
    
    found_emotion = False
    for emotion, keywords in emotions.items():
        if any(word in user_text.lower() for word in keywords):
            found_emotion = True
            responses = {
                "anxious": "I can feel the anxiety in your words. It's okay to feel overwhelmed.",
                "sad": "I'm so sorry things feel heavy right now. Thank you for sharing.",
                "depressed": "I hear how much pain you are in. It takes strength to speak up.",
                "angry": "It sounds like you're carrying a lot of frustration. I'm here to listen.",
                "tired": "You sound drained. Please remember that taking a break is progress, too.",
                "happy": "It's wonderful to hear that you're feeling good!"
            }
            return responses[emotion], True

    if polarity < -0.3:
        return "I can tell things are difficult right now. I'm here for you.", True
    elif polarity > 0.3:
        return "You seem to be in a positive headspace! That's great to see.", True
    
    # If no keywords and neutral polarity, it's considered "irrelevant"
    return "I'm not quite sure I understand how you're feeling based on that. Could you tell me more about your mood today?", False

# ---------------- LOGIC HELPERS ----------------
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
    if display_question:
        st.session_state.messages.append({"role": "assistant", "content": f"**Question:** {display_question}"})
    
    answer_text = display_answer if display_answer else str(val)
    st.session_state.messages.append({"role": "user", "content": answer_text})
    
    if st.session_state.step == "GREETING":
        response_text, is_relevant = get_emotional_response(str(val))
        if is_relevant:
            st.session_state.pending_bot_responses = [
                response_text,
                "Even when we feel good, it's helpful to check in on our mental health. Would you like to take a guided screening?"
            ]
            st.session_state.step = "CONSENT"
        else:
            # Irrelevant input - stay in GREETING step but show error
            st.session_state.pending_bot_responses = [response_text]

    elif st.session_state.step == "CONSENT":
        if "yes" in str(val).lower():
            st.session_state.pending_bot_responses = ["Excellent. We'll start with the K10 test. Rate your feelings from **1 (None)** to **5 (All the time)**."]
            st.session_state.step = "K10"
        else:
            st.session_state.pending_bot_responses = ["I understand. Whenever you're ready, I'm here. Take care! ❤️"]
            st.session_state.step = "END"

    elif st.session_state.step == "K10":
        st.session_state.k10_score += int(val)
        st.session_state.q_idx += 1
        if st.session_state.q_idx >= 10:
            resp = [f"K10 complete. Total Score: {st.session_state.k10_score}"]
            if st.session_state.k10_score >= 20:
                resp.append("Your score suggests moderate to high distress. Let's proceed to specialized screening.")
                st.session_state.step = "TIER2"
                st.session_state.current_tool = "PHQ9"
                st.session_state.q_idx = 0
            else:
                resp.append("Your distress levels appear low. Keep maintaining your wellness!")
                st.session_state.step = "END"
            st.session_state.pending_bot_responses = resp

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
    responses = st.session_state.pending_bot_responses.copy()
    st.session_state.pending_bot_responses = [] 
    for r in responses:
        bot_echo(r)
    st.rerun()

if st.session_state.step == "START":
    st.session_state.pending_bot_responses = ["Hello! I'm MindCare. I can help conduct guided mental health screenings. How have you been feeling lately?"]
    st.session_state.step = "GREETING"
    st.rerun()

if st.session_state.step in ["GREETING", "CONSENT"]:
    if prompt := st.chat_input("Type your response..."):
        handle_input(prompt)
        st.rerun()

elif st.session_state.step == "K10":
    current_q = k10_questions[st.session_state.q_idx]
    st.write(f"**K10 Assessment** - Question {st.session_state.q_idx+1} of 10")
    st.info(current_q)
    cols = st.columns(5)
    labels = ["None", "Rarely", "Some", "Often", "Always"]
    for i in range(1, 6):
        if cols[i-1].button(f"{i}", help=labels[i-1]):
            handle_input(i, display_question=current_q, display_answer=f"Rated: {i} ({labels[i-1]})")
            st.rerun()

elif st.session_state.step == "TIER2":
    tool = st.session_state.current_tool
    data = tier2_data[tool]
    current_q = data["questions"][st.session_state.q_idx]
    st.write(f"**{data['title']}** - Question {st.session_state.q_idx+1} of {len(data['questions'])}")
    st.info(current_q)
    cols = st.columns(len(data["labels"]))
    for i in range(len(data['labels'])):
        if cols[i].button(data["labels"][i]):
            handle_input(i, display_question=current_q, display_answer=data["labels"][i])
            st.rerun()

elif st.session_state.step == "RESULTS":
    phq, gad, pss = st.session_state.tier2_scores['PHQ9'], st.session_state.tier2_scores['GAD7'], st.session_state.tier2_scores['PSS10']
    st.write("### Assessment Summary")
    st.write(f"- **PHQ-9 (Depression):** {phq}")
    st.write(f"- **GAD-7 (Anxiety):** {gad}")
    st.write(f"- **PSS-10 (Stress):** {pss}")
    if phq >= 10 or gad >= 10 or pss >= 14:
        st.warning("⚠️ Your scores suggest significant distress. Please consult a professional.")
    if st.button("Start New Session"):
        for key in st.session_state.keys(): del st.session_state[key]
        st.rerun()