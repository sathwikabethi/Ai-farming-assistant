import streamlit as st
from PIL import Image
import io
import requests
import tempfile
import unicodedata
import os
import hashlib
import pyttsx3
import json
import pandas as pd
from datetime import date
import geocoder


# --- NEW: User Authentication Functions ---

def hash_password(password):
    """Hashes the password using SHA-256."""
    return hashlib.sha256(str.encode(password)).hexdigest()


def check_password(password, hashed_password):
    """Checks if the provided password matches the stored hash."""
    return hash_password(password) == hashed_password


def load_user_db():
    """Loads the user database from a JSON file."""
    if os.path.exists("users.json"):
        with open("users.json", "r") as f:
            return json.load(f)
    return {}


def save_user_db(db):
    """Saves the user database to a JSON file."""
    with open("users.json", "w") as f:
        json.dump(db, f, indent=4)


# Gemini AI Integration
try:
    import google.generativeai as genai

    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# --- ⚠️ IMPORTANT: REPLACE WITH YOUR OWN API KEYS ---
# It's highly recommended to use Streamlit Secrets for production
GEMINI_API_KEY = "AIzaSyB9Df80jQ6IRxoG7zgET6c-lzJlqZZhGmY"  # st.secrets["GEMINI_API_KEY"]
WEATHERAPI_KEY = "2385b7a7051045f382d62111252807"  # st.secrets["WEATHERAPI_KEY"]

# Configure Gemini AI
if GEMINI_AVAILABLE and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_HERE":
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
    except Exception as e:
        st.error(f"Failed to configure Gemini AI: {e}")
        GEMINI_AVAILABLE = False
else:
    GEMINI_AVAILABLE = False
    if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        st.warning("Gemini AI is not configured. Please add your API key.")

# --- Streamlit Page Configuration ---
st.set_page_config(page_title="🌾 RYTHU MITRA", layout="wide", initial_sidebar_state="expanded")

# --- UI Styling ---
st.markdown("""
<style>
/* --- NEW: Background Image Style --- */
/* You can change the background image URL below */
body {
    background-image: linear-gradient(rgba(255, 255, 255, 0.8), rgba(232, 245, 233, 0.7)), url("https://images.pexels.com/photos/3601094/pexels-photo-3601094.jpeg");
    background-size: cover;
    background-repeat: no-repeat;
    background-attachment: fixed;
    background-position: center;
    font-family: 'Segoe UI', sans-serif;
}
section[data-testid="stSidebar"] {
    background-color: rgba(232, 245, 233, 0.9); /* Slightly increased opacity for better readability */
    border-right: 2px solid #81c784;
}
h1, h2, h3, .stTextInput label, .stRadio label {
    color: #2e7d32 !important;
}
.stButton>button {
    background-color: #43a047;
    color: white;
    font-weight: bold;
    border-radius: 10px;
    border: none;
    padding: 10px 24px;
    transition: background-color 0.3s ease;
}
.stButton>button:hover {
    background-color: #2e7d32;
}

/* --- Card Layout Styles --- */
.card-container {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    justify-content: center;
}
div[data-testid="stVerticalBlock"]>div[style*="flex-direction: column;"]>div[data-testid="stVerticalBlock"] {
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    padding: 1rem;
    background-color: rgba(255, 255, 255, 0.85); /* Card background with slight transparency */
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    transition: all 0.3s ease-in-out;
    text-align: center;
}
div[data-testid="stVerticalBlock"]>div[style*="flex-direction: column;"]>div[data-testid="stVerticalBlock"]:hover {
    transform: scale(1.05);
    box-shadow: 0 8px 16px rgba(0,0,0,0.2);
    border-color: #4CAF50;
    background-color: #ffffff;
}
/* Style for the button inside the card */
div[data-testid="stVerticalBlock"]>div[style*="flex-direction: column;"]>div[data-testid="stVerticalBlock"] .stButton>button {
    background-color: transparent;
    color: #2e7d32;
    width: 100%;
    font-size: 1.1rem;
    padding: 1rem 0.5rem;
    border: none;
}
div[data-testid="stVerticalBlock"]>div[style*="flex-direction: column;"]>div[data-testid="stVerticalBlock"] .stButton>button:hover {
    background-color: transparent;
    color: #1b5e20;
}
/* --- End Card Layout Styles --- */

</style>
""", unsafe_allow_html=True)

# --- Core Functions (App-specific, non-auth) ---
# Language Options
LANG_OPTIONS = ["English", "Telugu", "Hindi"]


def speak(text):
    if not text:
        st.warning("No text to speak.")
        return
    try:
        key = hashlib.md5(str(text).encode()).hexdigest()
        file_path = os.path.join(tempfile.gettempdir(), f"{key}.wav")
        if not os.path.exists(file_path):
            with st.spinner(f"🔊 Generating audio..."):
                engine = pyttsx3.init()
                engine.save_to_file(text, file_path)
                engine.runAndWait()
        st.audio(file_path, format="audio/wav", autoplay=True)
    except Exception as e:
        st.warning(f"🔈 Offline Text-to-Speech not available: {e}")


def recognize_speech(timeout=5, phrase_time_limit=10):
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.Microphone() as source:
            st.info("🎤 Listening... Please speak clearly.")
            r.adjust_for_ambient_noise(source)
            try:
                audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                query = r.recognize_google(audio)
                st.success(f"Heard: '{query}'")
                return query
            except Exception as e:
                st.error(f"Voice input failed: {e}")
                return None
    except ImportError:
        st.error("Speech recognition library not found. Please install it: pip install SpeechRecognition PyAudio")
        return None


def get_user_location():
    try:
        g = geocoder.ip('me')
        city = g.city or g.address or ""
        if city:
            city = unicodedata.normalize('NFKD', city).encode('ascii', 'ignore').decode('utf-8')
            return city.strip()
        return "Not Found"
    except Exception:
        return "Not Found"


def save_profile(profile_data):
    try:
        with open(f"profile_{st.session_state['username']}.json", "w") as f:
            json.dump(profile_data, f)
    except Exception as e:
        st.warning(f"Could not save profile: {e}")


def load_profile():
    profile_path = f"profile_{st.session_state['username']}.json"
    if os.path.exists(profile_path):
        try:
            with open(profile_path, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


# --- Expense Tracker Data Functions ---
def load_tracker_data(username):
    """Loads tracker data for a specific user from a JSON file."""
    file_path = f"tracker_data_{username}.json"
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    return []


def save_tracker_data(username, data):
    """Saves tracker data for a specific user to a JSON file."""
    file_path = f"tracker_data_{username}.json"
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)


# --- Gemini and Weather Functions ---
def gemini_text_response(user_input, system_prompt, lang_instruction):
    if not GEMINI_AVAILABLE: return f"**[AI not available]** Your query was: '{user_input}'"
    try:
        prompt = f"{system_prompt}\n\n{lang_instruction}\n\nUser: {user_input}"
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ An error occurred with the AI model: {e}"


def gemini_image_analysis(image_bytes, lang_instruction="Respond in English."):
    if not GEMINI_AVAILABLE: return "**[Image analysis not available]** — Check Gemini configuration."
    try:
        with st.spinner("🖼️ Analyzing image..."):
            image_part = {"mime_type": "image/jpeg", "data": image_bytes}
            prompt = (
                "You are an expert agricultural botanist. Analyze this image to identify the crop and any visible diseases, pests, or nutrient deficiencies. "
                "Provide a clear diagnosis and suggest practical, actionable treatment plans. Include both chemical and organic solutions. "
                f"Structure your response clearly. {lang_instruction}"
            )
            response = model.generate_content([prompt, image_part])
            return response.text
    except Exception as e:
        return f"❌ An error occurred during image analysis: {e}"


def get_weather_advisory(location, lang_instruction="Please respond in English.", raw_data_only=False):
    if not WEATHERAPI_KEY or WEATHERAPI_KEY == "YOUR_WEATHERAPI_KEY_HERE":
        return "[Weather service not configured — please set the WEATHERAPI_KEY]."
    try:
        with st.spinner(f"Fetching weather for {location}..."):
            url = f"http://api.weatherapi.com/v1/forecast.json?key={WEATHERAPI_KEY}&q={location}&days=3&aqi=no&alerts=yes"
            data = requests.get(url, timeout=10).json()
        if "error" in data: return f"❌ Location '{location}' not found or weather service error."
        loc_info, curr_info, forecast_day = data["location"], data["current"], data["forecast"]["forecastday"][0]["day"]
        weather_summary = (
            f"Current weather in {loc_info['name']}, {loc_info['region']}: "
            f"Temp {curr_info['temp_c']}°C (feels like {curr_info['feelslike_c']}°C). "
            f"Condition is {curr_info['condition']['text']}. Humidity {curr_info['humidity']}%. "
            f"Wind {curr_info['wind_kph']} km/h.\n"
            f"Forecast: Max {forecast_day['maxtemp_c']}°C, Min {forecast_day['mintemp_c']}°C. "
            f"Rain chance {forecast_day['daily_chance_of_rain']}%. "
        )
        if raw_data_only: return weather_summary
        system_prompt = "You are an agricultural meteorologist. Based on the following weather data, provide a concise and actionable advisory for farmers."
        return gemini_text_response(weather_summary, system_prompt, lang_instruction)
    except Exception as e:
        return f"⚠️ Error fetching weather data: {e}"


TOOL_OPTIONS = [
    "🌿 Crop & Disease Detection", "🤖 AI Farming Chatbot", "☔ Weather Advisory",
    "🧪 Soil & Fertilizer Advice", "📈 Market Prices", "💰 Expense Tracker", "🗓️ Crop Calendar",
    "💧 Water Management", "🏫 Govt. Schemes", "👨‍🌾 Contact Agri Officer"
]


def route_voice_command(command):
    if not GEMINI_AVAILABLE:
        st.error("AI Router not available. Please select a tool manually.")
        return None
    prompt = f"Tools: {', '.join(TOOL_OPTIONS)}. User command: '{command}'. Respond with ONLY the best tool name from the list. Default to '🤖 AI Farming Chatbot'."
    try:
        with st.spinner("🧠 Assistant is routing your command..."):
            response = model.generate_content(prompt).text.strip()
            if any(tool.strip() in response for tool in TOOL_OPTIONS):
                return next(tool for tool in TOOL_OPTIONS if tool.strip() in response)
            else:
                return "🤖 AI Farming Chatbot"
    except Exception as e:
        st.error(f"AI Router failed: {e}")
        return None


# --- Main App Logic ---

# Initialize session state for authentication
if 'authentication_status' not in st.session_state:
    st.session_state['authentication_status'] = None
    st.session_state['username'] = None
    st.session_state['name'] = None
    st.session_state['active_tool'] = TOOL_OPTIONS[0]

# --- AUTHENTICATION UI ---
if not st.session_state["authentication_status"]:
    st.title("🌾 Welcome to Rythu Mitra")
    choice = st.sidebar.selectbox("Login / Sign Up", ["Login", "Sign Up"])

    if choice == "Login":
        st.sidebar.subheader("Login")
        username = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type="password")
        if st.sidebar.button("Login"):
            users = load_user_db()
            if username in users and check_password(password, users[username]['password']):
                st.session_state['authentication_status'] = True
                st.session_state['username'] = username
                st.session_state['name'] = users[username]['name']
                st.rerun()
            else:
                st.sidebar.error("Incorrect username or password.")

    elif choice == "Sign Up":
        st.sidebar.subheader("Create a New Account")
        new_name = st.sidebar.text_input("Name")
        new_username = st.sidebar.text_input("Username")
        new_password = st.sidebar.text_input("Password", type="password")
        if st.sidebar.button("Sign Up"):
            users = load_user_db()
            if new_username in users:
                st.sidebar.warning("Username already exists.")
            elif not (new_name and new_username and new_password):
                st.sidebar.warning("Please fill out all fields.")
            else:
                users[new_username] = {
                    'name': new_name,
                    'password': hash_password(new_password)
                }
                save_user_db(users)
                st.sidebar.success("Account created successfully! Please Login.")

# --- MAIN APPLICATION UI (after login) ---
else:
    # --- SIDEBAR ---
    with st.sidebar:
        st.title(f"Welcome, {st.session_state['name']}!")
        st.markdown("---")
        if st.button("Logout"):
            st.session_state['authentication_status'] = None
            st.session_state['username'] = None
            st.session_state['name'] = None
            st.session_state['active_tool'] = TOOL_OPTIONS[0]
            st.rerun()

        st.header("🛠️ Tools & Settings")
        st.subheader("Voice Assistant")
        if st.button("🎙️ Activate Voice Assistant"):
            command = recognize_speech()
            if command:
                tool_choice = route_voice_command(command)
                if tool_choice:
                    st.session_state.active_tool = tool_choice
                    st.rerun()

        st.markdown("---")
        with st.expander("View/Edit Farm Profile", expanded=False):
            if 'farm_profile' not in st.session_state:
                st.session_state['farm_profile'] = load_profile()
            if not st.session_state['farm_profile'].get('state'):
                st.session_state['farm_profile']['state'] = get_user_location()

            profile = st.session_state['farm_profile']
            state = st.text_input("State/District", profile.get('state', ''), key="profile_state")
            farm_size = st.number_input("Farm size (acres)", min_value=0.0, value=float(profile.get('farm_size', 0.0)))
            crops = st.text_input("Main crops", profile.get('crops', ''), key="profile_crops")
            if st.button("💾 Save Profile"):
                st.session_state['farm_profile'] = {'state': state, 'farm_size': farm_size, 'crops': crops}
                save_profile(st.session_state['farm_profile'])
                st.success("Profile saved for your account.")

        st.markdown("---")
        LANG = st.selectbox("🌐 Language", LANG_OPTIONS, index=0)
        lang_instruction = f"Please respond in {LANG}."

    # --- MAIN UI ---
    st.title("🌾 RYTHU MITRA – AI Assistant for Farmers")
    st.markdown(f"Empowering **{st.session_state['name']}** with AI — Weather, Crops, Diseases, Market Info & More")

    st.subheader("Select a Service")

    # --- Card Layout for Tool Selection ---
    cols = st.columns(5)  # Create 5 columns for the grid

    # Distribute tools into columns
    for i, tool in enumerate(TOOL_OPTIONS):
        col = cols[i % 5]
        with col:
            if st.button(tool, key=f"tool_btn_{i}"):
                st.session_state.active_tool = tool
                st.rerun()

    st.markdown("---")

    # Get the currently selected tool from session state
    option = st.session_state.get('active_tool', TOOL_OPTIONS[0])

    # --- Service Logic (remains the same) ---
    if option == "🌿 Crop & Disease Detection":
        st.header("🌿 Detect Crop Issues from Image")
        source = st.radio("Image Source", ["📷 Camera", "📁 Upload"], horizontal=True, label_visibility="collapsed")
        img_file = st.camera_input("Take photo") if source == "📷 Camera" else st.file_uploader("Upload image",
                                                                                               type=["jpg", "jpeg",
                                                                                                     "png"])
        if img_file:
            img = Image.open(img_file)
            st.image(img, caption="Your Uploaded Image", use_container_width=True)
            buf = io.BytesIO()
            img.convert('RGB').save(buf, format='JPEG')
            img_bytes = buf.getvalue()
            if st.button("🔍 Analyze Image"):
                result = gemini_image_analysis(img_bytes, lang_instruction)
                st.markdown(result)
                speak(result)

    elif option == "🤖 AI Farming Chatbot":
        st.header("🤖 Ask the AI Farming Expert")
        if "messages" not in st.session_state:
            st.session_state.messages = []
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        if query := st.chat_input("Ask me anything about farming..."):
            st.session_state.messages.append({"role": "user", "content": query})
            with st.chat_message("user"):
                st.markdown(query)
            with st.chat_message("assistant"):
                with st.spinner("🤖 AI is thinking..."):
                    response = gemini_text_response(query, "You are an intelligent and helpful farming assistant.",
                                                    lang_instruction)
                    st.markdown(response)
                    speak(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

    elif option == "☔ Weather Advisory":
        st.header("☔ Weather Advisory and Farming Plan")
        default_location = st.session_state.get('farm_profile', {}).get('state', get_user_location())
        location = st.text_input("Enter your location", default_location)
        if st.button("Get Weather Advisory"):
            if location:
                response = get_weather_advisory(location, lang_instruction)
                st.markdown(response)
                speak(response)
            else:
                st.warning("Please enter a location.")

    elif option == "🧪 Soil & Fertilizer Advice":
        st.header("🧪 Soil & Fertilizer Recommendations")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            ph = st.slider("Soil pH", 3.5, 9.5, 6.5, 0.1)
        with c2:
            n = st.number_input("Nitrogen (N) kg/ha", min_value=0, value=50)
        with c3:
            p = st.number_input("Phosphorus (P) kg/ha", min_value=0, value=30)
        with c4:
            k = st.number_input("Potassium (K) kg/ha", min_value=0, value=40)
        crop_type = st.text_input("What crop are you growing?",
                                  st.session_state.get('farm_profile', {}).get('crops', ''))
        if st.button("🧮 Get Fertilizer Plan"):
            if crop_type:
                prompt = f"For a '{crop_type}' crop, my soil has pH {ph}, N at {n} kg/ha, P at {p} kg/ha, and K at {k} kg/ha. Provide a detailed fertilizer plan."
                result = gemini_text_response(prompt, "You are a world-class soil science and agronomy expert.",
                                              lang_instruction)
                st.markdown(result)
                speak(result)
            else:
                st.warning("Please specify the crop you are growing.")

    elif option == "📈 Market Prices":
        st.header("📈 Live Mandi Market Prices")
        st.info("Note: This is a demonstrative feature. Data accuracy depends on the API source.")
        states = ["Telangana", "Andhra Pradesh", "Maharashtra", "Uttar Pradesh", "Punjab", "Karnataka"]
        crops = ["Cotton", "Paddy (Dhan)", "Maize", "Red Chilli", "Turmeric", "Soyabean"]
        col1, col2, col3 = st.columns(3)
        with col1:
            selected_state = st.selectbox("Select State", states)
        with col2:
            selected_crop = st.selectbox("Select Crop", crops)
        with col3:
            selected_date = st.date_input("Select Date", date.today())
        if st.button("📊 Fetch Prices"):
            with st.spinner(f"Fetching prices for {selected_crop} in {selected_state}..."):
                try:
                    dummy_data = {
                        'Mandi': ['Market A', 'Market B', 'Market C', 'Market D'],
                        'Min Price (₹/Quintal)': [7100, 7050, 7120, 7000],
                        'Max Price (₹/Quintal)': [7400, 7350, 7450, 7300],
                        'Modal Price (₹/Quintal)': [7300, 7250, 7350, 7200]
                    }
                    df = pd.DataFrame(dummy_data)
                    st.success(f"Latest prices for {selected_date.strftime('%Y-%m-%d')}")
                    st.dataframe(df, use_container_width=True)
                    st.subheader("Price Trend (Modal Price)")
                    st.line_chart(df.set_index('Mandi')['Modal Price (₹/Quintal)'])
                    price_summary = df.to_string()
                    prompt = f"Analyze these market prices for {selected_crop}:\n{price_summary}\nProvide a brief summary for a farmer. Which market seems best right now and why?"
                    summary = gemini_text_response(prompt, "You are a market analyst.", lang_instruction)
                    st.markdown(summary)
                    speak(summary)
                except Exception as e:
                    st.error(f"Could not fetch data. The service may be down. Error: {e}")

    elif option == "💰 Expense Tracker":
        st.header("💰 Farm Expense & Income Tracker")

        transactions = load_tracker_data(st.session_state['username'])
        df = pd.DataFrame(transactions)

        with st.form("transaction_form", clear_on_submit=True):
            st.subheader("Add a New Transaction")
            c1, c2 = st.columns(2)
            with c1:
                trans_date = st.date_input("Date", date.today())
                trans_type = st.selectbox("Type", ["Expense", "Income"])
                trans_amount = st.number_input("Amount (₹)", min_value=0.0, format="%.2f")
            with c2:
                if trans_type == "Expense":
                    trans_category = st.selectbox("Category",
                                                  ["Seeds", "Fertilizer", "Pesticides", "Labor", "Machinery", "Fuel",
                                                   "Other"])
                else:
                    trans_category = st.selectbox("Category", ["Crop Sale", "Subsidy", "Other"])
                trans_notes = st.text_area("Notes (Optional)")

            submitted = st.form_submit_button("💾 Add Transaction")
            if submitted:
                if trans_amount > 0:
                    new_transaction = {
                        "Date": str(trans_date),
                        "Type": trans_type,
                        "Category": trans_category,
                        "Amount": trans_amount,
                        "Notes": trans_notes
                    }
                    transactions.append(new_transaction)
                    save_tracker_data(st.session_state['username'], transactions)
                    st.success("Transaction added successfully!")
                    st.rerun()
                else:
                    st.warning("Please enter an amount greater than zero.")

        st.markdown("---")

        if not df.empty:
            st.subheader("Financial Overview")

            df['Amount'] = pd.to_numeric(df['Amount'])

            total_income = df[df['Type'] == 'Income']['Amount'].sum()
            total_expense = df[df['Type'] == 'Expense']['Amount'].sum()
            net_profit = total_income - total_expense

            c1, c2, c3 = st.columns(3)
            c1.metric("Total Income", f"₹ {total_income:,.2f}", delta_color="normal")
            c2.metric("Total Expenses", f"₹ {total_expense:,.2f}", delta_color="inverse")
            c3.metric("Net Profit / Loss", f"₹ {net_profit:,.2f}", delta=f"{net_profit:,.2f}")

            st.markdown("---")
            tab1, tab2 = st.tabs(["📊 Expense Analysis", "📜 Transaction History"])

            with tab1:
                expense_df = df[df['Type'] == 'Expense']
                if not expense_df.empty:
                    st.subheader("Expenses by Category")
                    expense_by_category = expense_df.groupby('Category')['Amount'].sum()
                    st.bar_chart(expense_by_category)
                else:
                    st.info("No expense data to analyze yet.")

            with tab2:
                st.subheader("Full Transaction Log")
                st.dataframe(df, use_container_width=True)
        else:
            st.info("No transactions recorded yet. Use the form above to add your first entry.")

    elif option == "🗓️ Crop Calendar":
        st.header("🗓️ Your Personalized Crop Calendar")
        default_crop = st.session_state.get('farm_profile', {}).get('crops', '').split(',')[0].strip()
        crop_name = st.text_input("Enter your crop", value=default_crop)
        sowing_date = st.date_input("Select the sowing date", date.today())
        if st.button("🌱 Generate Crop Plan"):
            if crop_name and sowing_date:
                prompt = (
                    f"I have planted '{crop_name}' on {sowing_date}. "
                    "Generate a detailed, week-by-week schedule of farming activities for the entire crop cycle. "
                    "Include key tasks like irrigation schedules, fertilizer application stages (with recommended NPK ratios), "
                    "common pest/disease watch-outs for each stage, and the approximate harvesting time."
                )
                system_prompt = "You are an expert agronomist creating a detailed crop calendar. Present the output in a clear, week-by-week format using markdown tables or lists."
                result = gemini_text_response(prompt, system_prompt, lang_instruction)
                st.markdown(result)
                speak(result)
            else:
                st.warning("Please provide both the crop name and sowing date.")

    elif option == "💧 Water Management":
        st.header("💧 Irrigation Water Calculator")
        c1, c2, c3 = st.columns(3)
        with c1:
            crop_type = st.text_input("Your Crop", st.session_state.get('farm_profile', {}).get('crops', ''))
        with c2:
            soil_type = st.selectbox("Soil Type", ["Loam", "Sandy", "Clay", "Silty", "Peaty"])
        with c3:
            farm_area = st.number_input("Farm Area (in acres)", min_value=0.1, value=1.0)
        if st.button("Calculate Water Needs"):
            if crop_type and farm_area:
                location = st.session_state.get('farm_profile', {}).get('state', get_user_location())
                with st.spinner("Getting weather data for calculation..."):
                    weather_data = get_weather_advisory(location, raw_data_only=True)
                prompt = (
                    f"As an irrigation expert, calculate the water requirement for a '{crop_type}' crop on {farm_area} acres of '{soil_type}' soil. "
                    f"The current weather is: {weather_data}. "
                    "Provide a practical irrigation schedule (e.g., how often and for how long to irrigate) for the next 3 days. "
                    "Suggest a water volume in liters or a simple duration for drip or furrow irrigation systems. Be very practical and concise."
                )
                result = gemini_text_response(prompt, "You are a water management specialist for agriculture.",
                                              lang_instruction)
                st.markdown(result)
                speak(result)
            else:
                st.warning("Please provide all the details.")

    elif option in ["🏫 Govt. Schemes", "👨‍🌾 Contact Agri Officer"]:
        st.header(f" {option}")
        default_location = st.session_state.get('farm_profile', {}).get('state', get_user_location())
        search_term = "scheme keyword" if "Schemes" in option else "your district or mandal"
        query = st.text_input(f"Enter {search_term}", default_location if "Contact" in option else "")
        if st.button(f"🔍 Find {option.split(' ')[1]}"):
            if query:
                if option == "👨‍🌾 Contact Agri Officer" and 'secunderabad' in query.lower():
                    st.subheader("📍 Verified Contacts for Secunderabad, Telangana")
                    secunderabad_contacts = """
                    ### Mandal Agriculture Officer (MAO), Secunderabad Mandal
                    - **Purpose**: Primary local contact for schemes, subsidies, and advisory.
                    - **Address**: Office of the Mandal Agriculture Officer, Secunderabad Mandal, Hyderabad District, Telangana.

                    ---

                    ### District Agriculture Office, Hyderabad
                    - **Purpose**: Oversees all mandal-level agricultural activities.
                    - **Address**: Office of the Chief Agriculture Officer, Red Hills, Lakdikapul, Hyderabad, Telangana.
                    - **State Helpline**: **1800 425 1514** (Rythu Call Center)

                    ---

                    ### Krishi Vigyan Kendra (KVK), CRIDA, Hayathnagar
                    - **Purpose**: Farm science center for training, soil testing, and modern techniques.
                    - **Address**: CRIDA - KVK, Hayathnagar, Rangareddy District, Hyderabad - 501505, Telangana.
                    - **Phone**: **040-24591259**
                    - **Email**: kvk-crida@icar.gov.in
                    """
                    st.markdown(secunderabad_contacts)
                    speak("Showing verified contacts for Secunderabad.")
                else:
                    with st.spinner("🤖 AI is searching..."):
                        prompt_map = {
                            "🏫 Govt. Schemes": f"Find government schemes for farmers related to '{query}'.",
                            "👨‍🌾 Contact Agri Officer": f"Provide contact info for Agriculture Officer, KVK for '{query}' area."}
                        system_prompt_map = {
                            "🏫 Govt. Schemes": "You are an expert on government agricultural schemes in India.",
                            "👨‍🌾 Contact Agri Officer": "You are an assistant that provides local agricultural contact information."}
                        result = gemini_text_response(prompt_map[option], system_prompt_map[option], lang_instruction)
                        st.markdown(result)
                        speak(result)
            else:
                st.warning("Please enter a search term.")

    # --- Footer ---
    st.markdown("---")
    st.caption(f"Rythu Mitra v2.9 | Logged in as: {st.session_state['username']} | Language: {LANG}")
