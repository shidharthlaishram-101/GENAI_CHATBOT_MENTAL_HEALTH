import streamlit as st
import time
from textblob import TextBlob

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="MindCare AI", page_icon="🧠", layout="centered")

# Custom CSS for a professional chatbot interface
st.markdown("""
    <style>
    .stChatMessage { border-radius: 15px; margin-bottom: 15px; border: 1px solid #f0f2f6; }
    .stButton button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #4CAF50; color: white; }
    .stProgress > div > div > div > div { background-color: #4CAF50; }
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

# ---------------- EMOTION ENGINE ----------------
def get_emotional_response(user_text):
    analysis = TextBlob(user_text.lower())
    polarity = analysis.sentiment.polarity
    emotions = {
        "anxious": ["anxious", "worried", "nervous", "panic", "scared", "fear", "tension"],
        "sad": ["sad", "depressed", "lonely", "unhappy", "hopeless", "crying", "heartbroken"],
        "angry": ["angry", "furious", "annoyed", "frustrated", "mad", "hate"],
        "tired": ["tired", "exhausted", "burnt out", "no energy", "drained"],
        "happy": ["happy", "great", "wonderful", "good", "excited", "blessed", "amazing", "well"]
    }
    
    # 1. Keyword Check
    for emotion, keywords in emotions.items():
        if any(word in user_text.lower() for word in keywords):
            responses = {
                "anxious": "I can feel the anxiety in your words. It's okay to feel overwhelmed; let's take this slowly.",
                "sad": "I'm so sorry things feel heavy right now. Thank you for trusting me with your feelings.",
                "angry": "It sounds like you're carrying a lot of frustration. I'm here to listen without judgment.",
                "tired": "You sound drained. Please remember that taking a break is a form of progress, too.",
                "happy": "It's wonderful to hear that you're feeling good! I love hearing about those bright moments."
            }
            return responses[emotion]
            
    # 2. Polarity Fallback
    if polarity > 0.5:
        return "You seem to be in a very positive headspace! That's fantastic to see."
    elif polarity < -0.4:
        return "I hear a lot of pain in your words. Thank you for being so open with me."
    
    return "Thank you for sharing that with me. It's helpful to know where you're at."

# ---------------- LOGIC HELPERS ----------------
def bot_echo(text, delay=0.02):
    with st.chat_message("assistant"):
        container = st.empty()
        full_text = ""
        for char in text:
            full_text += char
            container.markdown(full_text + "▌")
            time.sleep(delay)
        container.markdown(full_text)
    st.session_state.messages.append({"role": "assistant", "content": text})

def handle_input(val):
    st.session_state.messages.append({"role": "user", "content": str(val)})
    
    if st.session_state.step == "GREETING":
        bot_echo(get_emotional_response(str(val)))
        bot_echo("Even when we feel good, it's helpful to check in on our mental health. Would you like to take a guided screening?")
        st.session_state.step = "CONSENT"

    elif st.session_state.step == "CONSENT":
        if "yes" in str(val).lower():
            bot_echo("Excellent. We'll start with the K10 test. Rate your feelings from **1 (None)** to **5 (All the time)**.")
            st.session_state.step = "K10"
        else:
            bot_echo("I understand. Whenever you're ready, I'm here. Take care! ❤️")
            st.session_state.step = "END"

    elif st.session_state.step == "K10":
        st.session_state.k10_score += int(val)
        st.session_state.q_idx += 1
        if st.session_state.q_idx >= 10:
            bot_echo(f"K10 complete. Score: {st.session_state.k10_score}")
            if st.session_state.k10_score >= 20:
                bot_echo("Your score suggests moderate to high distress. Let's proceed to specialized screening.")
                st.session_state.step = "TIER2"
                st.session_state.current_tool = "PHQ9"
                st.session_state.q_idx = 0
            else:
                bot_echo("Your distress levels are low. Keep maintaining your wellness!")
                st.session_state.step = "END"

    elif st.session_state.step == "TIER2":
        tool = st.session_state.current_tool
        st.session_state.tier2_scores[tool] += int(user_input := val)
        st.session_state.q_idx += 1
        
        if st.session_state.q_idx >= len(tier2_data[tool]["questions"]):
            if tool == "PHQ9":
                st.session_state.current_tool = "GAD7"; st.session_state.q_idx = 0
                bot_echo("Transitioning to Anxiety screening (GAD-7)...")
            elif tool == "GAD7":
                st.session_state.current_tool = "PSS10"; st.session_state.q_idx = 0
                bot_echo("Finally, starting the Stress Scale (PSS-10)...")
            else:
                st.session_state.step = "RESULTS"

# ---------------- UI RENDER ----------------
st.title("🧠 MindCare: AI Mental Health Bot")

# Display historical messages
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# Trigger Start
if st.session_state.step == "START":
    bot_echo("Hello! I'm MindCare. How have you been feeling lately?")
    st.session_state.step = "GREETING"
    st.rerun()

# --- INPUT AREA ---
if st.session_state.step in ["GREETING", "CONSENT"]:
    if prompt := st.chat_input("Type your response..."):
        with st.chat_message("user"): st.markdown(prompt)
        handle_input(prompt)
        st.rerun()

elif st.session_state.step == "K10":
    st.write(f"**K10 Assessment** - Q{st.session_state.q_idx+1}/10")
    st.info(k10_questions[st.session_state.q_idx])
    cols = st.columns(5)
    for i in range(1, 6):
        if cols[i-1].button(f"{i}"):
            handle_input(i); st.rerun()

elif st.session_state.step == "TIER2":
    tool = st.session_state.current_tool
    data = tier2_data[tool]
    st.write(f"**{data['title']}** - Q{st.session_state.q_idx+1}/{len(data['questions'])}")
    st.info(data["questions"][st.session_state.q_idx])
    cols = st.columns(len(data["labels"]))
    for i in range(len(data["labels"])):
        if cols[i].button(data["labels"][i]):
            handle_input(i); st.rerun()

elif st.session_state.step == "RESULTS":
    
    phq, gad, pss = st.session_state.tier2_scores['PHQ9'], st.session_state.tier2_scores['GAD7'], st.session_state.tier2_scores['PSS10']
    
    bot_echo(f"### Results\n- PHQ-9 (Depression): **{phq}**\n- GAD-7 (Anxiety): **{gad}**\n- PSS-10 (Stress): **{pss}**")
    
    if phq >= 10 or gad >= 10 or pss >= 14:
        bot_echo("⚠️ **Note:** Your scores suggest clinical distress. We recommend physiological testing (GSR/ECG sensors).")
    else:
        bot_echo("Your scores are within a manageable range. Remember to practice self-care!")
    
    if st.button("Restart"):
        st.session_state.clear(); st.rerun()